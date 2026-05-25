from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/")
def list_users() -> list[dict[str, str]]:
    return [{"name": "alice"}, {"name": "bob"}]


@router.get("/{user_id}")
def get_user(user_id: int) -> dict[str, object]:
    return {"id": user_id, "name": "alice"}


@router.post("/")
def create_user(name: str) -> dict[str, str]:
    return {"name": name}
