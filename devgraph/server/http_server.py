"""Local HTTP server for dashboard data."""

from __future__ import annotations

import json
import mimetypes
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from devgraph.config import DevGraphConfig
from devgraph.core.graph_store import GraphStore
from devgraph.intelligence.communities import top_communities
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
        if self._serve_dashboard_asset(parsed.path):
            return
        if parsed.path in {"/", "/index.html"}:
            self._html(self._dashboard_shell())
            return
        super().do_GET()

    def _json(self, payload: object) -> None:
        data = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

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
