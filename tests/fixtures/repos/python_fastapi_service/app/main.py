from fastapi import FastAPI

from .auth import login
from .users import router as users_router

app = FastAPI(title="Sample Service")
app.include_router(users_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/login")
def login_route(username: str, password: str) -> dict[str, str]:
    return login(username, password)
