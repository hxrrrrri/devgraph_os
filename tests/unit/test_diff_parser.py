from devgraph.update.diff_parser import parse_unified_diff


def test_parse_unified_diff_added_removed_lines() -> None:
    patch = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,2 +1,3 @@
 def main():
-    return False
+    value = True
+    return value
"""
    hunks = parse_unified_diff(patch)
    assert hunks[0].file_path == "app.py"
    assert hunks[0].changed_lines == [2, 2, 3]
