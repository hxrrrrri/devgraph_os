from pathlib import Path

from devgraph.config import DevGraphConfig
from devgraph.extractors.registry import ExtractorRegistry


def test_go_rust_java_vue_svelte_basic_extraction(tmp_path: Path) -> None:
    samples = {
        "main.go": 'import "fmt"\nfunc Serve() {}\n',
        "lib.rs": "use std::fmt;\npub struct User;\npub fn login() {}\n",
        "User.java": "import java.util.*; public class User { public void login() {} }\n",
        "App.vue": "<script>import x from './x'</script><template><main /></template>",
        "App.svelte": "<script>import x from './x'</script><main />",
    }
    registry = ExtractorRegistry(DevGraphConfig())
    for name, text in samples.items():
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        result = registry.extract(tmp_path, path)
        assert any(node.type in {"module", "class", "function", "type"} for node in result.nodes)
