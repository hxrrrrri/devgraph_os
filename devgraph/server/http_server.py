"""Local HTTP server for dashboard data."""

from __future__ import annotations

import json
import mimetypes
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from devgraph.config import DevGraphConfig
from devgraph.core.graph_store import GraphStore
from devgraph.intelligence.architecture import derive_architecture, layer_detail
from devgraph.intelligence.communities import top_communities
from devgraph.intelligence.debug import DebugEngine
from devgraph.intelligence.flows import trace_flow
from devgraph.intelligence.handoff import HandoffEngine
from devgraph.intelligence.knowledge import stale_docs
from devgraph.intelligence.onboard import OnboardingEngine
from devgraph.intelligence.review import ReviewEngine


class DevGraphHttpHandler(SimpleHTTPRequestHandler):
    store: GraphStore
    config: DevGraphConfig
    root: Path

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            self._json(self.store.get_status(self.config.project.name).model_dump())
            return
        if parsed.path == "/api/graph":
            self._json(self.store.all_graph(limit=500))
            return
        if parsed.path == "/api/search":
            query = parse_qs(parsed.query).get("q", [""])[0]
            self._json(self.store.search(query, limit=25))
            return
        if parsed.path == "/api/communities":
            self._json({"communities": top_communities(self.store)})
            return
        if parsed.path == "/api/review":
            result = ReviewEngine(self.root, self.config, self.store).review()
            self._json(result.model_dump(mode="json"))
            return
        if parsed.path == "/api/debug":
            issue = parse_qs(parsed.query).get("q", [""])[0]
            self._json(DebugEngine(self.store).analyze(issue))
            return
        if parsed.path == "/api/onboarding":
            path = OnboardingEngine(self.root, self.store).generate()
            self._json({"path": str(path), "markdown": path.read_text(encoding="utf-8")})
            return
        if parsed.path == "/api/handoff":
            markdown, data = HandoffEngine(self.root, self.config, self.store).generate()
            self._json(
                {
                    "markdown_path": str(markdown),
                    "json_path": str(data),
                    "markdown": markdown.read_text(encoding="utf-8"),
                    "data": json.loads(data.read_text(encoding="utf-8")),
                }
            )
            return
        if parsed.path == "/api/flows":
            query = parse_qs(parsed.query).get("q", [""])[0]
            self._json(trace_flow(self.store, query) if query else self.store.all_graph(limit=120))
            return
        if parsed.path == "/api/architecture":
            self._json(derive_architecture(self.store))
            return
        if parsed.path.startswith("/api/layers/"):
            layer_id = parsed.path.removeprefix("/api/layers/")
            payload = layer_detail(self.store, layer_id)
            if payload is None:
                self._json({"error": f"layer '{layer_id}' not found"}, status=404)
                return
            self._json(payload)
            return
        if parsed.path == "/api/path":
            qs = parse_qs(parsed.query)
            source = qs.get("source", [""])[0]
            target = qs.get("target", [""])[0]
            try:
                cutoff = int(qs.get("cutoff", ["8"])[0])
            except ValueError:
                cutoff = 8
            cutoff = max(1, min(cutoff, 20))
            if not source or not target:
                self._json({"error": "source and target required"}, status=400)
                return
            nodes = self.store.shortest_path_by_id(source, target, cutoff=cutoff)
            self._json(
                {
                    "source": source,
                    "target": target,
                    "found": bool(nodes),
                    "nodes": [node.model_dump() for node in nodes],
                }
            )
            return
        if parsed.path.startswith("/api/node/"):
            node_id = parsed.path.removeprefix("/api/node/")
            node = self.store.get_node(node_id)
            if node is None:
                self._json({"error": "node not found"}, status=404)
                return
            chunks = self.store.get_chunks_for_file(node.file_path, limit=12) if node.file_path else []
            self._json(
                {
                    "node": node.model_dump(),
                    "chunks": [chunk.model_dump() for chunk in chunks if chunk.node_id in {None, node.id}],
                    "provenance": self.store.provenance_for_entity(node.id),
                    "neighborhood": self.store.get_neighborhood([node.id], depth=1, limit=50),
                }
            )
            return
        if parsed.path == "/api/file-context":
            requested = parse_qs(parsed.query).get("path", [""])[0]
            safe_path = self._safe_relative_path(requested)
            if safe_path is None:
                self._json({"error": "invalid path"}, status=400)
                return
            nodes = self.store.nodes_for_files([safe_path])
            chunks = self.store.get_chunks_for_file(safe_path, limit=25)
            self._json(
                {
                    "file_path": safe_path,
                    "nodes": [node.model_dump() for node in nodes],
                    "chunks": [chunk.model_dump() for chunk in chunks],
                }
            )
            return
        if parsed.path.startswith("/api/provenance/"):
            entity_id = parsed.path.removeprefix("/api/provenance/")
            self._json({"provenance": self.store.provenance_for_entity(entity_id)})
            return
        if parsed.path == "/api/memories":
            kind = parse_qs(parsed.query).get("kind", [None])[0]
            self._json({"memories": self.store.list_memories(kind=kind)})
            return
        if parsed.path == "/api/snapshots":
            rows = self.store.connection.execute(
                "SELECT * FROM snapshots ORDER BY created_at DESC LIMIT 30"
            ).fetchall()
            self._json({"snapshots": [dict(row) for row in rows]})
            return
        if parsed.path == "/api/review-artifacts":
            self._json(self._review_artifacts())
            return
        if parsed.path == "/api/knowledge":
            self._json({"stale_docs": stale_docs(self.store)})
            return
        if self._serve_dashboard_asset(parsed.path):
            return
        if parsed.path in {"/", "/index.html"}:
            self._html(self._dashboard_shell())
            return
        super().do_GET()

    def _json(self, payload: object, status: int = 200) -> None:
        data = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(min(length, 1024 * 1024)).decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            self._json({"error": "invalid json"}, status=400)
            return
        if parsed.path == "/api/debug":
            self._json(DebugEngine(self.store).analyze(str(payload.get("issue", ""))))
            return
        if parsed.path == "/api/memories":
            content = str(payload.get("content", ""))
            kind = str(payload.get("kind", "note"))
            if not content:
                self._json({"error": "content is required"}, status=400)
                return
            self._json({"id": self.store.remember(kind=kind, content=content)})
            return
        self._json({"error": "not found"}, status=404)

    def _html(self, html: str) -> None:
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_dashboard_asset(self, request_path: str) -> bool:
        dist = self.root / "apps" / "dashboard" / "dist"
        if not dist.exists():
            return False
        relative = "index.html" if request_path in {"/", "/index.html"} else request_path.lstrip("/")
        target = (dist / relative).resolve()
        if not str(target).startswith(str(dist.resolve())) or not target.exists() or target.is_dir():
            return False
        data = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        return True

    def _safe_relative_path(self, value: str) -> str | None:
        if not value or "\x00" in value:
            return None
        candidate = (self.root / value).resolve()
        try:
            candidate.relative_to(self.root.resolve())
        except ValueError:
            return None
        return candidate.relative_to(self.root).as_posix()

    def _review_artifacts(self) -> dict[str, object]:
        reports = self.store.storage_path / "reports"
        payload: dict[str, object] = {}
        for name in ("review.md", "review.json"):
            path = reports / name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            payload[name] = json.loads(text) if name.endswith(".json") else text
        return payload

    @staticmethod
    def _dashboard_shell() -> str:
        return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>DevGraph OS</title>
    <style>
      body { margin: 0; font-family: system-ui, sans-serif; background: #f7f8fa; color: #181b20; }
      main { max-width: 1040px; margin: 0 auto; padding: 32px; }
      pre { background: white; border: 1px solid #d7dce2; padding: 16px; overflow: auto; }
      a { color: #0758a8; }
    </style>
  </head>
  <body>
    <main>
      <h1>DevGraph OS</h1>
      <p>The built dashboard app is not mounted here yet. API endpoints are available locally.</p>
      <ul>
        <li><a href="/api/status">/api/status</a></li>
        <li><a href="/api/graph">/api/graph</a></li>
        <li><a href="/api/communities">/api/communities</a></li>
      </ul>
    </main>
  </body>
</html>"""


def serve(root: Path, config: DevGraphConfig, store: GraphStore, port: int | None = None) -> str:
    handler = DevGraphHttpHandler
    handler.store = store
    handler.config = config
    handler.root = root
    address = ("127.0.0.1", port or config.dashboard.port)
    server = ThreadingHTTPServer(address, handler)
    url = f"http://{address[0]}:{address[1]}"
    print(f"DevGraph dashboard listening on {url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return url
