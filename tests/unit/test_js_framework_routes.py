"""NestJS and Next.js framework route extraction tests."""

from __future__ import annotations

from pathlib import Path

from devgraph.config import DevGraphConfig
from devgraph.extractors.code.routes import (
    parse_nestjs_routes,
    parse_nextjs_routes_for_path,
)
from devgraph.extractors.registry import ExtractorRegistry


def test_nestjs_controller_prefix_combined_with_methods() -> None:
    text = (
        "import { Controller, Get, Post, Patch, Delete } from '@nestjs/common';\n"
        "@Controller('users')\n"
        "export class UsersController {\n"
        "  @Get()\n"
        "  list() { return []; }\n"
        "  @Get(':id')\n"
        "  one() { return {}; }\n"
        "  @Post()\n"
        "  create() { return {}; }\n"
        "  @Patch(':id')\n"
        "  update() { return {}; }\n"
        "  @Delete(':id')\n"
        "  remove() { return {}; }\n"
        "}\n"
    )
    routes = {(method, path) for method, path, _ in parse_nestjs_routes(text)}
    assert ("GET", "/users") in routes
    assert ("GET", "/users/:id") in routes
    assert ("POST", "/users") in routes
    assert ("PATCH", "/users/:id") in routes
    assert ("DELETE", "/users/:id") in routes


def test_nestjs_controller_without_prefix_uses_root() -> None:
    text = (
        "@Controller()\n"
        "export class HealthController {\n"
        "  @Get('health')\n"
        "  ping() { return 'ok'; }\n"
        "}\n"
    )
    routes = {(method, path) for method, path, _ in parse_nestjs_routes(text)}
    assert ("GET", "/health") in routes


def test_nestjs_extraction_emits_api_endpoint_nodes(tmp_path: Path) -> None:
    path = tmp_path / "users.controller.ts"
    path.write_text(
        "import { Controller, Get, Post } from '@nestjs/common';\n"
        "@Controller('users')\n"
        "export class UsersController {\n"
        "  @Get()\n"
        "  list() { return []; }\n"
        "  @Post()\n"
        "  create() { return {}; }\n"
        "}\n",
        encoding="utf-8",
    )
    result = ExtractorRegistry(DevGraphConfig()).extract(tmp_path, path)
    endpoints = {
        (node.metadata.get("method"), node.metadata.get("path"), node.metadata.get("framework"))
        for node in result.nodes
        if node.type == "api_endpoint"
    }
    assert ("GET", "/users", "nestjs") in endpoints
    assert ("POST", "/users", "nestjs") in endpoints


def test_nextjs_app_page_routes_from_path() -> None:
    routes = parse_nextjs_routes_for_path("app/users/page.tsx", "export default function Page() {}\n")
    assert routes == [("GET", "/users", 1)]
    nested = parse_nextjs_routes_for_path(
        "app/users/[id]/page.tsx", "export default function Page() {}\n"
    )
    assert nested == [("GET", "/users/[id]", 1)]
    root = parse_nextjs_routes_for_path("app/page.tsx", "export default function Page() {}\n")
    assert root == [("GET", "/", 1)]


def test_nextjs_app_route_handler_exports_http_methods() -> None:
    text = (
        "export async function GET(req: Request) { return Response.json([]); }\n"
        "export async function POST(req: Request) { return Response.json({}); }\n"
    )
    routes = {(method, path) for method, path, _ in parse_nextjs_routes_for_path(
        "app/api/users/route.ts", text
    )}
    assert ("GET", "/api/users") in routes
    assert ("POST", "/api/users") in routes


def test_nextjs_route_groups_are_stripped() -> None:
    routes = parse_nextjs_routes_for_path(
        "app/(marketing)/pricing/page.tsx", "export default function Page() {}\n"
    )
    assert routes == [("GET", "/pricing", 1)]


def test_nextjs_pages_dir_routes_and_api() -> None:
    page = parse_nextjs_routes_for_path("pages/index.tsx", "export default function Home() {}\n")
    assert page == [("GET", "/", 1)]
    nested_page = parse_nextjs_routes_for_path(
        "pages/users/[id].tsx", "export default function User() {}\n"
    )
    assert nested_page == [("GET", "/users/[id]", 1)]
    api = parse_nextjs_routes_for_path(
        "pages/api/health.ts", "export default function handler() {}\n"
    )
    assert api == [("ANY", "/api/health", 1)]
    skipped = parse_nextjs_routes_for_path("pages/_app.tsx", "export default function App() {}\n")
    assert skipped == []


def test_nextjs_extraction_emits_api_endpoint_nodes(tmp_path: Path) -> None:
    app_dir = tmp_path / "app" / "products"
    app_dir.mkdir(parents=True)
    page = app_dir / "page.tsx"
    page.write_text("export default function Products() { return null; }\n", encoding="utf-8")
    result = ExtractorRegistry(DevGraphConfig()).extract(tmp_path, page)
    endpoints = {
        (node.metadata.get("method"), node.metadata.get("path"), node.metadata.get("framework"))
        for node in result.nodes
        if node.type == "api_endpoint"
    }
    assert ("GET", "/products", "nextjs") in endpoints
