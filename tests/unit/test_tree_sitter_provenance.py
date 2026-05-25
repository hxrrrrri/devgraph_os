"""Assert tree-sitter is the real provenance for languages with a packaged grammar.

Names matching tree-sitter-language-pack grammars must extract via tree-sitter,
not fall back to regex. A regression in `TREE_SITTER_LANGUAGE_NAMES` or in the
semantic analyzer must turn this red.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from devgraph.config import DevGraphConfig
from devgraph.extractors.registry import ExtractorRegistry

pytest.importorskip("tree_sitter_language_pack")


SAMPLES = {
    "python": ("auth.py", "import os\n\nclass Auth:\n    def login(self):\n        return helper()\n\ndef helper():\n    return True\n"),
    "javascript": ("app.js", "export function add(a, b) { return a + b; }\n"),
    "typescript": ("app.ts", "export class Auth { login(): boolean { return true; } }\n"),
    "go": ("main.go", 'package main\nimport "fmt"\nfunc Serve() { fmt.Println(\"hi\") }\n'),
    "rust": ("lib.rs", "pub struct User;\npub fn login() -> bool { true }\n"),
    "java": ("User.java", "public class User { public void login() {} }\n"),
    "c": ("main.c", "#include <stdio.h>\nint main(void) { return 0; }\n"),
    "cpp": ("main.cpp", "class Auth { public: void login(); };\nvoid Auth::login() {}\n"),
    "csharp": ("Auth.cs", "public class Auth { public void Login() {} }\n"),
    "ruby": ("auth.rb", "class Auth\n  def login\n    true\n  end\nend\n"),
    "php": ("Auth.php", "<?php\nclass Auth { public function login() { return true; } }\n"),
    "kotlin": ("Auth.kt", "class Auth { fun login(): Boolean = true }\n"),
    "swift": ("Auth.swift", "class Auth { func login() -> Bool { return true } }\n"),
    "scala": ("Auth.scala", "class Auth { def login(): Boolean = true }\n"),
    "bash": ("deploy.sh", "#!/bin/bash\nfunction deploy() { echo go; }\ndeploy\n"),
}


@pytest.mark.parametrize("language,sample", list(SAMPLES.items()))
def test_tree_sitter_is_real_parser(tmp_path: Path, language: str, sample: tuple[str, str]) -> None:
    filename, source = sample
    path = tmp_path / filename
    path.write_text(source, encoding="utf-8")
    result = ExtractorRegistry(DevGraphConfig()).extract(tmp_path, path)

    parsers = {node.metadata.get("parser") for node in result.nodes if node.metadata}
    assert "tree-sitter" in parsers, (
        f"{language}: expected tree-sitter provenance, got {parsers}. "
        "Either the grammar is missing or the semantic analyzer regressed."
    )

    symbol_nodes = [
        node for node in result.nodes
        if node.type in {"class", "function", "type", "test"}
    ]
    assert symbol_nodes, f"{language}: tree-sitter produced no symbol nodes from {filename}"
