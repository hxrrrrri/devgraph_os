"""DevGraph OS command-line interface."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from devgraph.config import DevGraphConfig, ensure_project, find_project_root, load_config
from devgraph.core.graph_store import GraphStore
from devgraph.exports.graphml import export_graphml
from devgraph.exports.json_export import export_json
from devgraph.exports.markdown_wiki import generate_wiki
from devgraph.exports.neo4j import export_neo4j
from devgraph.exports.obsidian import export_obsidian
from devgraph.intelligence.debug import DebugEngine
from devgraph.intelligence.explain import ExplainEngine
from devgraph.intelligence.flows import trace_flow
from devgraph.intelligence.handoff import HandoffEngine
from devgraph.intelligence.onboard import OnboardingEngine
from devgraph.intelligence.review import ReviewEngine, format_review_markdown
from devgraph.logging import configure_logging
from devgraph.server.http_server import serve as serve_http
from devgraph.server.mcp_server import run_mcp_server
from devgraph.update.incremental import build_graph, update_graph
from devgraph.update.watcher import watch as watch_project

app = typer.Typer(
    name="devgraph",
    help="Local-first AI context engine and developer knowledge graph.",
    no_args_is_help=True,
)


@app.callback()
def main(verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging.")) -> None:
    configure_logging(verbose)


@app.command("init")
def init_project(
    platform: str | None = typer.Option(
        None,
        "--platform",
        help="Generate agent instructions for claude, codex, cursor, copilot, gemini, generic, or all.",
    )
) -> None:
    """Initialize DevGraph OS in the current project."""
    root = Path.cwd()
    try:
        created = ensure_project(root, platform=platform)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    if created:
        typer.echo("Created:")
        for path in created:
            typer.echo(f"- {path.relative_to(root)}")
    else:
        typer.echo("DevGraph project is already initialized.")


@app.command("build")
def build(force: bool = typer.Option(False, "--force", help="Re-index files even if hashes are unchanged.")) -> None:
    """Build the project graph."""
    root, config, store = _context()
    stats = build_graph(root, config, store, force=force)
    typer.echo(f"Scanned {stats.scanned} files, indexed {stats.indexed}, skipped {stats.skipped}.")
    _print_warnings(stats.warnings)


@app.command("update")
def update(
    base: str | None = typer.Option(None, "--base", help="Diff base ref, for example origin/main."),
    staged: bool = typer.Option(False, "--staged", help="Use staged diff."),
) -> None:
    """Incrementally update changed graph areas."""
    root, config, store = _context()
    stats = update_graph(root, config, store, base=base, staged=staged)
    typer.echo(
        f"Scanned {stats.scanned} changed files, indexed {stats.indexed}, "
        f"deleted {stats.deleted}, skipped {stats.skipped}."
    )
    _print_warnings(stats.warnings)


@app.command("watch")
def watch() -> None:
    """Watch the project and update the graph incrementally."""
    root, config, store = _context()
    typer.echo(f"Watching {root}")
    watch_project(root, config, store)


@app.command("status")
def status(json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON.")) -> None:
    """Show graph health and freshness."""
    root, config, store = _context()
    graph_status = store.get_status(config.project.name or root.name)
    if json_output:
        typer.echo(json.dumps(graph_status.model_dump(), indent=2))
        return
    typer.echo(f"Project: {graph_status.project}")
    typer.echo(f"Storage: {graph_status.storage_path}")
    typer.echo(f"Files: {graph_status.total_files}")
    typer.echo(f"Nodes: {graph_status.total_nodes}")
    typer.echo(f"Edges: {graph_status.total_edges}")
    typer.echo(f"Chunks: {graph_status.total_chunks}")
    typer.echo(f"Last indexed: {graph_status.last_indexed_at or 'never'}")
    if graph_status.languages:
        typer.echo("Languages:")
        for language, count in graph_status.languages.items():
            typer.echo(f"- {language}: {count}")
    _print_warnings(graph_status.warnings)


@app.command("ask")
def ask(question: str, budget: str = typer.Option("normal", "--budget")) -> None:
    """Ask a graph-grounded project question."""
    _root, _config, store = _context()
    typer.echo(ExplainEngine(store).ask(question, budget=budget))


@app.command("explain")
def explain(target: str, budget: str = typer.Option("normal", "--budget")) -> None:
    """Explain a file, symbol, module, concept, or flow."""
    _root, _config, store = _context()
    typer.echo(ExplainEngine(store).explain(target, budget=budget))


@app.command("path")
def relationship_path(source: str, target: str) -> None:
    """Find a relationship path between two graph nodes."""
    _root, _config, store = _context()
    nodes = store.find_path(source, target)
    if not nodes:
        typer.echo("No graph path found.")
        raise typer.Exit(code=1)
    for node in nodes:
        typer.echo(f"{node.type}: {node.qualified_name}")


@app.command("trace")
def trace(query: str) -> None:
    """Trace execution or domain flow around a node."""
    _root, _config, store = _context()
    typer.echo(json.dumps(trace_flow(store, query), indent=2))


@app.command("review", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def review(
    ctx: typer.Context,
    base: str | None = typer.Option(None, "--base", help="Diff base ref, for example origin/main."),
    staged: bool = typer.Option(False, "--staged", help="Review staged changes."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
    files: list[str] | None = typer.Option(
        None,
        "--files",
        help="Scope review to one or more files. Repeat the option or pass extra paths after it.",
    ),
) -> None:
    """Produce risk-scored review context."""
    root, config, store = _context()
    scoped_files = [*(files or []), *ctx.args]
    result = ReviewEngine(root, config, store).review(base=base, staged=staged, files=scoped_files)
    if json_output:
        typer.echo(json.dumps(result.model_dump(mode="json"), indent=2))
    else:
        typer.echo(format_review_markdown(result))


@app.command("debug")
def debug(issue: str, budget: str = typer.Option("normal", "--budget")) -> None:
    """Create debug context from an error, stack trace, or symptom."""
    _root, _config, store = _context()
    typer.echo(DebugEngine(store).debug(issue, budget=budget))


@app.command("onboard")
def onboard() -> None:
    """Generate guided project onboarding."""
    root, _config, store = _context()
    path = OnboardingEngine(root, store).generate()
    typer.echo(f"Wrote {path}")


@app.command("dashboard")
def dashboard(port: int | None = typer.Option(None, "--port", help="Dashboard port.")) -> None:
    """Start the local dashboard server."""
    root, config, store = _context()
    serve_http(root, config, store, port=port)


@app.command("wiki")
def wiki() -> None:
    """Generate a Markdown wiki from the graph."""
    _root, _config, store = _context()
    path = generate_wiki(store)
    typer.echo(f"Wrote {path}")


@app.command("ingest")
def ingest(target: Path) -> None:
    """Ingest a file or directory into the graph."""
    root, config, store = _context()
    if target.is_dir():
        stats = build_graph(target.resolve(), config, store, force=True)
        typer.echo(f"Ingested directory: indexed {stats.indexed} files.")
        return
    from devgraph.extractors.registry import ExtractorRegistry

    result = ExtractorRegistry(config).extract(root, (root / target).resolve() if not target.is_absolute() else target)
    store.replace_file_graph(result.file, result.nodes, result.edges, result.chunks)
    typer.echo(f"Ingested {result.file.path}")


@app.command("remember")
def remember(
    content: str = typer.Argument(..., help="Memory content to store."),
    kind: str = typer.Option("note", "--kind", help="Memory kind, such as decision, constraint, or task."),
) -> None:
    """Store a user-approved project memory without secret values."""
    _root, _config, store = _context()
    memory_id = store.remember(kind=kind, content=content)
    typer.echo(memory_id)


@app.command("memories")
def memories(
    kind: str | None = typer.Option(None, "--kind", help="Filter by memory kind."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """List user-approved project memories."""
    _root, _config, store = _context()
    rows = store.list_memories(kind=kind)
    if json_output:
        typer.echo(json.dumps(rows, indent=2))
        return
    if not rows:
        typer.echo("No memories recorded.")
        return
    for row in rows:
        typer.echo(f"{row['id']} [{row['kind']}] {row['content']}")


@app.command("forget")
def forget(memory_id: str = typer.Argument(..., help="Memory id returned by devgraph remember.")) -> None:
    """Delete a project memory."""
    _root, _config, store = _context()
    if store.forget_memory(memory_id):
        typer.echo(f"Forgot {memory_id}")
        return
    typer.echo(f"Memory not found: {memory_id}")
    raise typer.Exit(code=1)


@app.command("handoff")
def handoff() -> None:
    """Generate session handoff context."""
    root, config, store = _context()
    markdown, data = HandoffEngine(root, config, store).generate()
    typer.echo(f"Wrote {markdown}")
    typer.echo(f"Wrote {data}")


@app.command("export")
def export_graph(
    format_: str = typer.Option("json", "--format", help="json, graphml, obsidian, or neo4j."),
    output: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    """Export the graph."""
    _root, _config, store = _context()
    exporters = {
        "json": export_json,
        "graphml": export_graphml,
        "obsidian": export_obsidian,
        "neo4j": export_neo4j,
    }
    if format_ not in exporters:
        raise typer.BadParameter("format must be one of: json, graphml, obsidian, neo4j")
    path = exporters[format_](store, output)
    typer.echo(f"Wrote {path}")


@app.command("serve")
def serve(
    http: bool = typer.Option(True, "--http/--no-http", help="Start local HTTP dashboard API."),
    port: int | None = typer.Option(None, "--port", help="HTTP port."),
) -> None:
    """Serve DevGraph interfaces."""
    root, config, store = _context()
    if http:
        serve_http(root, config, store, port=port)


@app.command("mcp")
def mcp() -> None:
    """Start the MCP server."""
    run_mcp_server(Path.cwd())


@app.command("doctor")
def doctor(json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON.")) -> None:
    """Detect local configuration and privacy issues."""
    root, config, store = _context()
    issues = []
    if config.privacy.allow_llm_enrichment:
        issues.append("LLM enrichment is enabled. Confirm external model privacy settings before use.")
    if config.privacy.store_env_values:
        issues.append("store_env_values is enabled. This can persist secrets and is not recommended.")
    status_value = store.get_status(config.project.name)
    if status_value.total_nodes == 0:
        issues.append("Graph has no nodes. Run `devgraph build`.")
    payload = {
        "project_root": str(root),
        "issues": issues,
        "status": status_value.model_dump(),
        "privacy": config.privacy.model_dump(),
    }
    if json_output:
        typer.echo(json.dumps(payload, indent=2))
        return
    typer.echo(f"Project root: {root}")
    if issues:
        typer.echo("Issues:")
        for issue in issues:
            typer.echo(f"- {issue}")
    else:
        typer.echo("No DevGraph configuration issues detected.")


def _context() -> tuple[Path, DevGraphConfig, GraphStore]:
    root = find_project_root()
    ensure_project(root)
    config = load_config(root)
    store = GraphStore(root, root / config.storage.path)
    return root, config, store


def _print_warnings(warnings: list[str]) -> None:
    if not warnings:
        return
    typer.echo("Warnings:")
    for warning in warnings:
        typer.echo(f"- {warning}")
