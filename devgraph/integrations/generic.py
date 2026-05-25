"""Slash-command integration instructions."""

from __future__ import annotations

PLATFORM_TARGETS = {
    "claude": "CLAUDE.md",
    "codex": "AGENTS.md",
    "cursor": ".cursor/rules/devgraph.mdc",
    "copilot": ".github/copilot-instructions.md",
    "gemini": "GEMINI.md",
    "generic": "DEVGRAPH_AGENT.md",
}


def platform_instruction_targets() -> dict[str, str]:
    return dict(PLATFORM_TARGETS)


def render_platform_instructions(platform: str) -> str:
    name = platform.title()
    return f"""# DevGraph OS Instructions for {name}

Use DevGraph OS before reading large parts of this repository.

## Slash Commands

- `/devgraph build` - build or refresh the local knowledge graph.
- `/devgraph update` - incrementally update changed files.
- `/devgraph status` - inspect graph health and freshness.
- `/devgraph ask <question>` - get graph-grounded project context.
- `/devgraph explain <file-or-symbol>` - explain a file, symbol, module, or flow.
- `/devgraph review` - review current changes with blast radius and risk.
- `/devgraph debug <issue-or-stack-trace>` - build focused debug context.
- `/devgraph onboard` - generate a guided project tour.
- `/devgraph handoff` - write compact handoff context before stopping work.

## Agent Policy

- Always check DevGraph before broad codebase questions.
- Use `get_context` before reading many files manually.
- Use `review_changes` for PR or code review work.
- Use `debug_issue` for bugs, stack traces, or symptoms.
- Use `handoff_session` before ending a long session.
- Prefer graph-grounded context over raw grep when the task touches architecture,
  dependencies, flows, tests, or blast radius.
- Treat confidence tiers carefully: `extracted` facts are deterministic, `inferred`
  facts are indirect, `llm` facts are model-generated, `ambiguous` facts need review,
  and `user` facts are manually approved.
"""

