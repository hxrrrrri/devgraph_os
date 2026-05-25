"""FastAPI/Flask/Django route extraction tests."""

from __future__ import annotations

from pathlib import Path

from devgraph.config import DevGraphConfig
from devgraph.extractors.registry import ExtractorRegistry


def test_fastapi_decorator_routes(tmp_path: Path) -> None:
    path = tmp_path / "api.py"
    path.write_text(
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n"
        "@app.get('/users')\n"
        "def list_users():\n    return []\n"
        "@app.post('/users')\n"
        "async def create_user(): return {}\n"
        "@app.websocket('/ws')\n"
        "async def ws(): pass\n",
        encoding="utf-8",
    )
    result = ExtractorRegistry(DevGraphConfig()).extract(tmp_path, path)
    endpoints = {
        (node.metadata.get("method"), node.metadata.get("path"))
        for node in result.nodes
        if node.type == "api_endpoint"
    }
    assert ("GET", "/users") in endpoints
    assert ("POST", "/users") in endpoints
    assert ("WEBSOCKET", "/ws") in endpoints


def test_flask_route_methods(tmp_path: Path) -> None:
    path = tmp_path / "flask_app.py"
    path.write_text(
        "from flask import Flask\n"
        "app = Flask(__name__)\n"
        "@app.route('/login', methods=['POST'])\n"
        "def login(): return 'ok'\n"
        "@app.route('/health')\n"
        "def health(): return 'ok'\n",
        encoding="utf-8",
    )
    result = ExtractorRegistry(DevGraphConfig()).extract(tmp_path, path)
    endpoints = {
        (node.metadata.get("method"), node.metadata.get("path"))
        for node in result.nodes
        if node.type == "api_endpoint"
    }
    assert ("POST", "/login") in endpoints
    assert ("GET", "/health") in endpoints


def test_django_urls(tmp_path: Path) -> None:
    path = tmp_path / "urls.py"
    path.write_text(
        "from django.urls import path\n"
        "from . import views\n"
        "urlpatterns = [\n"
        "    path('users/', views.user_list),\n"
        "    path('users/<int:id>/', views.user_detail),\n"
        "]\n",
        encoding="utf-8",
    )
    result = ExtractorRegistry(DevGraphConfig()).extract(tmp_path, path)
    endpoints = {
        (node.metadata.get("method"), node.metadata.get("path"))
        for node in result.nodes
        if node.type == "api_endpoint"
    }
    assert ("ANY", "users/") in endpoints
    assert ("ANY", "users/<int:id>/") in endpoints
