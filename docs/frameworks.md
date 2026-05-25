# Framework Plugins (v1.2)

Every framework plugin sets `metadata.framework = "<name>"` on the nodes it
emits. Routes are emitted as `api_endpoint` nodes with `metadata.method`,
`metadata.path`, and `metadata.framework`. Models / controllers / migrations
are tagged on the existing `class`, `function`, or `schema` nodes.

| Framework | What is extracted | What is NOT |
|---|---|---|
| **FastAPI** | `@app.get/post/...`, `@router.*`, `@app.websocket` decorators (method, path, line). | Mounted prefixes that depend on `APIRouter(prefix=...)` inferred at runtime. |
| **Flask** | `@app.route('/x', methods=[...])` with explicit method lists; defaults to GET when missing. | `Blueprint(prefix=...)` resolution; converters in paths. |
| **Django** | `path()`, `re_path()`, `url()` entries in `urls.py`. | Class-based view method detection. |
| **Express** | `app.get/post/put/patch/delete('/x', ...)`. `framework="express"`. | Router middleware ordering. |
| **NestJS** | `@Controller('prefix')` paired with `@Get/@Post/@Put/@Patch/@Delete/@Options/@Head/@All('subpath')`. Combines prefix + sub-path; no args means root. | Versioning via `@Version()`; dynamic modules. |
| **Next.js** | Files under `app/` (`page`, `route` with `export GET/POST/...`) and `pages/` (including `pages/api/*`). Route groups `(name)` are stripped. `_app`, `_document`, `_error` are skipped. | Middleware-driven dynamic routing; server actions resolution. |
| **React** | Function components (capitalized name, file imports `react`) and hooks (`useX`). Components carry `metadata.kind = "component"` plus any `useState` / `useEffect` / custom-hook calls in `metadata.react_hooks`. | Prop-type inference; JSX dependency tracing. |
| **Spring Boot** | `@RestController`, `@Controller`, `@Service`, `@Component`, `@Repository`, `@Entity`, `@Configuration` annotations on classes. Routes from `@RequestMapping("/prefix")` + `@GetMapping/@PostMapping/...`. | `@PathVariable` typing; method-level `@RequestMapping`. |
| **Rails** | `routes.rb` DSL (`get`, `post`, ...) plus `resources :name` (expanded to GET/POST + member CRUD). `ApplicationRecord` subclasses tagged as models with `has_many` / `belongs_to` / `has_one` associations. | Engine mount points; nested resources. |
| **Laravel** | `Route::get/post/...` plus `Route::resource` and `Route::apiResource`. Eloquent models (`extends Model`) and migration classes (`extends Migration`). | Route groups with middleware closures. |
| **Prisma** | `model X { ... }` blocks with field name/type/attributes. Emits `schema` node per model and a `database_table` synonym. | `enum`, `view`, `datasource`. |
| **SQLAlchemy** | Classes inheriting `Base` / `DeclarativeBase` / `Model` / `db.Model`. Captures `__tablename__`, `Column` / `mapped_column` columns, `relationship` targets. | Composite types; hybrid_property. |
| **Alembic** | `op.create_table / drop_table / add_column / drop_column / alter_column / create_index / drop_index / rename_table / create_foreign_key / drop_constraint` calls. Emits `schema` node per op. | DSL `with_variant`; offline scripts. |

## Provenance

All framework-emitted nodes still inherit the original parser provenance
(`metadata.parser`) — `tree-sitter`, `python-ast`, or the language-specific
regex parser. The framework overlay only adds metadata; it never overrides the
original `parser` field.

## Confidence

Regex-based plugins (NestJS, Next.js, Spring, Rails, Laravel, Prisma,
SQLAlchemy, Alembic) emit nodes at confidence tier `extracted`. The framework
attribution itself is heuristic — verify by checking `metadata.framework`
together with the file path / nearest tree-sitter symbol.

## Known limits

- Routes that depend on runtime metaprogramming (Django CBV decorators,
  Rails engines, Laravel route groups with middleware closures) are missed.
- Prisma `view` and `enum` blocks are not extracted yet.
- React component detection assumes the file imports `react`. Pure-JSX files
  without that import are not tagged.
- Spring class-level `@RequestMapping` only picks the first string value;
  arrays (`{"/a", "/b"}`) only contribute to the prefix once.

## Adding a framework plugin

1. Add detector functions to `devgraph/extractors/code/frameworks.py`. Keep
   them regex-only; tree-sitter is the primary path for symbol extraction.
2. Wire them into `_apply_static_framework_overlays`,
   `_with_python_framework_overlays`, or the JS/TS pipeline in
   `tree_sitter_parser.py` depending on the host language.
3. Add unit tests under `tests/unit/test_framework_plugins.py` asserting both
   the parser output and the `framework=` metadata on the emitted node.
4. If the plugin needs a new fixture repo, add it under
   `tests/fixtures/repos/<name>/` and write an integration test under
   `tests/integration/test_<name>_fixture.py`.
