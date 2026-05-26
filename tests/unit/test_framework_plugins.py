"""Unit tests for v1.2 framework plugins.

Covers: React, Spring Boot, Rails, Laravel, Prisma, SQLAlchemy/Alembic.
"""

from __future__ import annotations

from pathlib import Path

from devgraph.config import DevGraphConfig
from devgraph.extractors.code.frameworks import (
    laravel_migrations,
    laravel_models,
    parse_alembic_ops,
    parse_laravel_routes,
    parse_prisma_models,
    parse_rails_routes,
    parse_spring_routes,
    parse_sqlalchemy_models,
    rails_models,
    spring_class_kinds,
)
from devgraph.extractors.registry import ExtractorRegistry

# --- React ----------------------------------------------------------------


def test_react_components_and_hooks_tagged(tmp_path: Path) -> None:
    path = tmp_path / "Counter.tsx"
    path.write_text(
        "import { useState, useEffect } from 'react';\n"
        "export function Counter() {\n"
        "  const [n, setN] = useState(0);\n"
        "  useEffect(() => { setN(n + 1); }, []);\n"
        "  return <button>{n}</button>;\n"
        "}\n"
        "export function useDouble(value: number) {\n"
        "  return value * 2;\n"
        "}\n",
        encoding="utf-8",
    )
    result = ExtractorRegistry(DevGraphConfig()).extract(tmp_path, path)
    by_name = {node.name: node for node in result.nodes}
    counter = by_name.get("Counter")
    assert counter is not None
    assert counter.metadata.get("framework") == "react"
    assert counter.metadata.get("kind") == "component"
    assert "useState" in (counter.metadata.get("react_hooks") or [])
    assert "useEffect" in (counter.metadata.get("react_hooks") or [])
    hook = by_name.get("useDouble")
    assert hook is not None
    assert hook.metadata.get("kind") == "hook"


def test_react_not_tagged_when_no_react_import(tmp_path: Path) -> None:
    path = tmp_path / "Counter.tsx"
    path.write_text(
        "export function Counter() { return null; }\n",
        encoding="utf-8",
    )
    result = ExtractorRegistry(DevGraphConfig()).extract(tmp_path, path)
    counter = next((node for node in result.nodes if node.name == "Counter"), None)
    assert counter is not None
    assert counter.metadata.get("framework") != "react"


# --- Spring Boot ----------------------------------------------------------


def test_spring_routes_combine_class_prefix() -> None:
    text = (
        "@RestController\n"
        "@RequestMapping(\"/api/users\")\n"
        "public class UsersController {\n"
        "  @GetMapping\n"
        "  public List<User> list() { return null; }\n"
        "  @GetMapping(\"/{id}\")\n"
        "  public User one() { return null; }\n"
        "  @PostMapping\n"
        "  public User create() { return null; }\n"
        "}\n"
    )
    routes = {(m, p) for m, p, _ in parse_spring_routes(text)}
    assert ("GET", "/api/users") in routes
    assert ("GET", "/api/users/{id}") in routes
    assert ("POST", "/api/users") in routes


def test_spring_class_kinds_detected() -> None:
    text = (
        "@Service\npublic class UsersService {}\n"
        "@Repository\npublic class UsersRepository {}\n"
        "@Entity\npublic class User {}\n"
    )
    kinds = spring_class_kinds(text)
    assert kinds == {
        "UsersService": "service",
        "UsersRepository": "repository",
        "User": "entity",
    }


def test_spring_extraction_emits_route_and_kind(tmp_path: Path) -> None:
    path = tmp_path / "UsersController.java"
    path.write_text(
        "package x;\n"
        "@RestController\n"
        "@RequestMapping(\"/api/users\")\n"
        "public class UsersController {\n"
        "  @GetMapping\n"
        "  public Object list() { return null; }\n"
        "  @PostMapping\n"
        "  public Object create() { return null; }\n"
        "}\n",
        encoding="utf-8",
    )
    result = ExtractorRegistry(DevGraphConfig()).extract(tmp_path, path)
    endpoints = {
        (node.metadata.get("method"), node.metadata.get("path"), node.metadata.get("framework"))
        for node in result.nodes
        if node.type == "api_endpoint"
    }
    assert ("GET", "/api/users", "spring") in endpoints
    assert ("POST", "/api/users", "spring") in endpoints
    controller = next(
        (node for node in result.nodes if node.type == "class" and node.name == "UsersController"),
        None,
    )
    assert controller is not None
    assert controller.metadata.get("framework") == "spring"
    assert controller.metadata.get("kind") == "controller"


# --- Rails ----------------------------------------------------------------


def test_rails_routes_dsl_and_resources() -> None:
    text = (
        "Rails.application.routes.draw do\n"
        "  get '/health', to: 'health#show'\n"
        "  post '/login', to: 'sessions#create'\n"
        "  resources :users\n"
        "end\n"
    )
    routes = {(m, p) for m, p, _ in parse_rails_routes(text)}
    assert ("GET", "/health") in routes
    assert ("POST", "/login") in routes
    assert ("GET", "/users") in routes
    assert ("POST", "/users") in routes
    assert ("DELETE", "/users/:id") in routes


def test_rails_models_with_associations(tmp_path: Path) -> None:
    text = (
        "class User < ApplicationRecord\n"
        "  has_many :posts\n"
        "  has_one :profile\n"
        "  belongs_to :team\n"
        "end\n"
    )
    models = rails_models(text)
    assert "User" in models
    associations = {(kind, target) for kind, target in models["User"]}
    assert ("has_many", "posts") in associations
    assert ("has_one", "profile") in associations
    assert ("belongs_to", "team") in associations


def test_rails_extraction_emits_route_and_model_metadata(tmp_path: Path) -> None:
    routes_file = tmp_path / "routes.rb"
    routes_file.write_text(
        "Rails.application.routes.draw do\n"
        "  resources :posts\n"
        "end\n",
        encoding="utf-8",
    )
    model_file = tmp_path / "user.rb"
    model_file.write_text(
        "class User < ApplicationRecord\n"
        "  has_many :posts\n"
        "end\n",
        encoding="utf-8",
    )
    registry = ExtractorRegistry(DevGraphConfig())
    routes_result = registry.extract(tmp_path, routes_file)
    endpoints = {
        (node.metadata.get("method"), node.metadata.get("path"), node.metadata.get("framework"))
        for node in routes_result.nodes
        if node.type == "api_endpoint"
    }
    assert ("GET", "/posts", "rails") in endpoints
    assert ("DELETE", "/posts/:id", "rails") in endpoints

    model_result = registry.extract(tmp_path, model_file)
    user = next(
        (node for node in model_result.nodes if node.type == "class" and node.name == "User"),
        None,
    )
    assert user is not None
    assert user.metadata.get("framework") == "rails"
    assert user.metadata.get("kind") == "model"


# --- Laravel --------------------------------------------------------------


def test_laravel_routes_and_resource_expansion() -> None:
    text = (
        "<?php\n"
        "Route::get('/health', [HealthController::class, 'show']);\n"
        "Route::post('/login', [SessionController::class, 'create']);\n"
        "Route::resource('users', UsersController::class);\n"
    )
    routes = {(m, p) for m, p, _ in parse_laravel_routes(text)}
    assert ("GET", "/health") in routes
    assert ("POST", "/login") in routes
    assert ("GET", "/users") in routes
    assert ("DELETE", "/users/{id}") in routes


def test_laravel_models_and_migrations() -> None:
    text = (
        "<?php\n"
        "class User extends Model {}\n"
        "class CreateUsersTable extends Migration {\n"
        "  public function up() {}\n"
        "}\n"
    )
    assert laravel_models(text) == ["User"]
    assert laravel_migrations(text) == ["CreateUsersTable"]


def test_laravel_extraction_emits_route_and_model(tmp_path: Path) -> None:
    routes_file = tmp_path / "web.php"
    routes_file.write_text(
        "<?php\n"
        "Route::get('/ping', [PingController::class, 'show']);\n",
        encoding="utf-8",
    )
    model_file = tmp_path / "User.php"
    model_file.write_text(
        "<?php\n"
        "class User extends Model {\n"
        "  protected $fillable = ['email'];\n"
        "}\n",
        encoding="utf-8",
    )
    registry = ExtractorRegistry(DevGraphConfig())
    endpoints = {
        (node.metadata.get("method"), node.metadata.get("path"), node.metadata.get("framework"))
        for node in registry.extract(tmp_path, routes_file).nodes
        if node.type == "api_endpoint"
    }
    assert ("GET", "/ping", "laravel") in endpoints

    user = next(
        (
            node
            for node in registry.extract(tmp_path, model_file).nodes
            if node.type == "class" and node.name == "User"
        ),
        None,
    )
    assert user is not None
    assert user.metadata.get("framework") == "laravel"
    assert user.metadata.get("kind") == "eloquent_model"


# --- Prisma ---------------------------------------------------------------


def test_prisma_model_parsing() -> None:
    text = (
        "model User {\n"
        "  id    Int    @id @default(autoincrement())\n"
        "  email String @unique\n"
        "  posts Post[]\n"
        "}\n"
        "model Post {\n"
        "  id    Int    @id\n"
        "  title String\n"
        "  user  User   @relation(fields: [userId], references: [id])\n"
        "  userId Int\n"
        "}\n"
    )
    models = parse_prisma_models(text)
    names = {name for name, _, _ in models}
    assert names == {"User", "Post"}


def test_prisma_extractor_emits_schema_and_database_table(tmp_path: Path) -> None:
    path = tmp_path / "schema.prisma"
    path.write_text(
        "model User {\n"
        "  id    Int    @id\n"
        "  email String @unique\n"
        "}\n",
        encoding="utf-8",
    )
    result = ExtractorRegistry(DevGraphConfig()).extract(tmp_path, path)
    schema = next((node for node in result.nodes if node.type == "schema"), None)
    assert schema is not None
    assert schema.metadata.get("framework") == "prisma"
    fields = {field["name"] for field in (schema.metadata.get("fields") or [])}
    assert {"id", "email"}.issubset(fields)
    assert any(node.type == "database_table" and node.name == "User" for node in result.nodes)


# --- SQLAlchemy / Alembic -------------------------------------------------


def test_sqlalchemy_models_detected() -> None:
    text = (
        "from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship\n"
        "class Base(DeclarativeBase):\n    pass\n"
        "class User(Base):\n"
        "    __tablename__ = 'users'\n"
        "    id: Mapped[int] = mapped_column(primary_key=True)\n"
        "    email: Mapped[str] = mapped_column()\n"
        "    posts = relationship('Post', back_populates='user')\n"
        "class Post(Base):\n"
        "    __tablename__ = 'posts'\n"
        "    id: Mapped[int] = mapped_column(primary_key=True)\n"
        "    user = relationship('User', back_populates='posts')\n"
    )
    models = parse_sqlalchemy_models(text)
    by_name = {str(model["name"]): model for model in models}
    assert "User" in by_name
    assert by_name["User"]["tablename"] == "users"
    user_columns = by_name["User"]["columns"]
    assert "id" in user_columns
    assert "email" in user_columns
    user_rels = [tuple(rel) for rel in by_name["User"]["relationships"]]
    assert ("posts", "Post") in user_rels


def test_alembic_ops_detected() -> None:
    text = (
        "def upgrade():\n"
        "    op.create_table('users')\n"
        "    op.add_column('users', sa.Column('email', sa.String))\n"
        "    op.create_index('ix_users_email', 'users', ['email'])\n"
        "    op.alter_column('users', 'email', nullable=False)\n"
    )
    ops = {(op, target) for op, target, _ in parse_alembic_ops(text)}
    assert ("create_table", "users") in ops
    assert ("add_column", "users") in ops
    assert ("create_index", "ix_users_email") in ops
    assert ("alter_column", "users") in ops


def test_sqlalchemy_extraction_emits_metadata(tmp_path: Path) -> None:
    path = tmp_path / "models.py"
    path.write_text(
        "from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column\n"
        "class Base(DeclarativeBase):\n    pass\n"
        "class User(Base):\n"
        "    __tablename__ = 'users'\n"
        "    id: Mapped[int] = mapped_column(primary_key=True)\n",
        encoding="utf-8",
    )
    result = ExtractorRegistry(DevGraphConfig()).extract(tmp_path, path)
    user = next((node for node in result.nodes if node.name == "User"), None)
    assert user is not None
    assert user.metadata.get("framework") == "sqlalchemy"
    assert user.metadata.get("tablename") == "users"


def test_alembic_extraction_emits_schema_nodes(tmp_path: Path) -> None:
    path = tmp_path / "20240101_init.py"
    path.write_text(
        "from alembic import op\n"
        "import sqlalchemy as sa\n"
        "def upgrade():\n"
        "    op.create_table('users')\n"
        "    op.add_column('users', sa.Column('email', sa.String))\n",
        encoding="utf-8",
    )
    result = ExtractorRegistry(DevGraphConfig()).extract(tmp_path, path)
    schema_ops = {
        (node.metadata.get("operation"), node.metadata.get("target"), node.metadata.get("framework"))
        for node in result.nodes
        if node.type == "schema" and node.metadata.get("framework") == "alembic"
    }
    assert ("create_table", "users", "alembic") in schema_ops
    assert ("add_column", "users", "alembic") in schema_ops
