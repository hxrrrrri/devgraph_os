"""Tests for the public API and route contract compatibility diff."""

from __future__ import annotations

from devgraph.core.schema import Node
from devgraph.intelligence.compat import diff_public_api, diff_routes


def _snapshot(nodes: list[dict]) -> dict[str, object]:
    return {"nodes": nodes, "edges": [], "files": []}


def _function_node(
    qn: str,
    *,
    params: str = "()",
    return_type: str = "",
    visibility: str = "public",
) -> dict[str, object]:
    return {
        "type": "function",
        "name": qn.rsplit(".", 1)[-1],
        "qualified_name": qn,
        "file_path": "src/api.py",
        "metadata": {
            "signature": f"def {qn.rsplit('.', 1)[-1]}{params}",
            "parameters": params,
            "return_type": return_type,
            "visibility": visibility,
        },
    }


def _endpoint_node(method: str, path: str, framework: str = "fastapi") -> dict[str, object]:
    return {
        "type": "api_endpoint",
        "name": f"{method} {path}",
        "qualified_name": f"routes::{method} {path}",
        "file_path": "src/routes.py",
        "metadata": {"method": method, "path": path, "framework": framework},
    }


def _current_function(
    qn: str,
    *,
    params: str = "()",
    return_type: str = "",
    visibility: str = "public",
) -> Node:
    return Node(
        id=f"function:{qn}",
        type="function",
        name=qn.rsplit(".", 1)[-1],
        qualified_name=qn,
        file_path="src/api.py",
        metadata={
            "signature": f"def {qn.rsplit('.', 1)[-1]}{params}",
            "parameters": params,
            "return_type": return_type,
            "visibility": visibility,
        },
    )


def _current_endpoint(method: str, path: str, framework: str = "fastapi") -> Node:
    return Node(
        id=f"api_endpoint:{method}:{path}",
        type="api_endpoint",
        name=f"{method} {path}",
        qualified_name=f"routes::{method} {path}",
        file_path="src/routes.py",
        metadata={"method": method, "path": path, "framework": framework},
    )


def test_removed_public_symbol_emits_high_severity() -> None:
    previous = _snapshot([_function_node("app.api.list_users")])
    warnings = diff_public_api(previous, [])
    assert any(w["code"] == "removed_public_symbol" and w["severity"] == "high" for w in warnings)


def test_added_required_parameter_flagged() -> None:
    previous = _snapshot([_function_node("app.api.create_user", params="(email)")])
    current = [_current_function("app.api.create_user", params="(email, role)")]
    warnings = diff_public_api(previous, current)
    assert any(w["code"] == "required_parameter_added" for w in warnings)


def test_default_removed_flagged() -> None:
    previous = _snapshot([_function_node("app.api.create_user", params="(email, role='user')")])
    current = [_current_function("app.api.create_user", params="(email, role)")]
    warnings = diff_public_api(previous, current)
    codes = {w["code"] for w in warnings}
    # Either "default_removed" OR "required_parameter_added" — required count went 1 -> 2.
    assert "required_parameter_added" in codes or "default_removed" in codes


def test_return_type_change_flagged() -> None:
    previous = _snapshot([_function_node("app.api.fetch", return_type="-> dict")])
    current = [_current_function("app.api.fetch", return_type="-> list")]
    warnings = diff_public_api(previous, current)
    assert any(w["code"] == "return_type_changed" for w in warnings)


def test_visibility_downgrade_flagged() -> None:
    previous = _snapshot([_function_node("App.helper", visibility="public")])
    current = [_current_function("App.helper", visibility="private")]
    warnings = diff_public_api(previous, current)
    assert any(w["code"] == "visibility_downgrade" and w["severity"] == "high" for w in warnings)


def test_private_symbols_ignored() -> None:
    previous = _snapshot([_function_node("app.api._internal")])
    warnings = diff_public_api(previous, [])
    assert not warnings


def test_route_removed_and_added() -> None:
    previous = _snapshot([_endpoint_node("GET", "/users"), _endpoint_node("POST", "/users")])
    current = [_current_endpoint("GET", "/users"), _current_endpoint("DELETE", "/users")]
    warnings = diff_routes(previous, current)
    codes = {(w["code"], w["method"], w["path"]) for w in warnings}
    assert ("route_removed", "POST", "/users") in codes
    assert ("route_added", "DELETE", "/users") in codes
