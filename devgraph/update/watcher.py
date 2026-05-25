"""Watch mode implementation."""

from __future__ import annotations

import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from devgraph.config import DevGraphConfig
from devgraph.core.graph_store import GraphStore
from devgraph.update.incremental import update_graph


class DevGraphEventHandler(FileSystemEventHandler):
    def __init__(self, root: Path, config: DevGraphConfig, store: GraphStore) -> None:
        self.root = root
        self.config = config
        self.store = store
        self._last_run = 0.0

    def on_any_event(self, event: object) -> None:
        now = time.time()
        if now - self._last_run < 1.0:
            return
        self._last_run = now
        update_graph(self.root, self.config, self.store)


def watch(root: Path, config: DevGraphConfig, store: GraphStore) -> None:
    observer = Observer()
    handler = DevGraphEventHandler(root, config, store)
    observer.schedule(handler, str(root), recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()
