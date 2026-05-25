from devgraph.intelligence.debug import parse_stack_trace


def test_parse_python_and_node_stack_traces() -> None:
    python_trace = 'Traceback:\n  File "src/app.py", line 3, in main\nValueError: bad\n'
    node_trace = "TypeError: bad\n    at login (src/auth.ts:10:5)\n"
    assert parse_stack_trace(python_trace)[0]["file_path"] == "src/app.py"
    assert parse_stack_trace(node_trace)[0]["file_path"] == "src/auth.ts"
