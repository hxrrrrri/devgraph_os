# python_fastapi_service

Minimal FastAPI service fixture used by DevGraph OS integration tests. Exercises:

- FastAPI route decorators (`@app.get`, `@app.post`, `@router.get`)
- APIRouter with prefix
- Cross-module imports / call graph
- SQL migration with index
- A test module

Tests read this fixture via `tests/integration/test_fastapi_fixture.py`.
