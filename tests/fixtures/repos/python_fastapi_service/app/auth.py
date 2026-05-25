import hashlib


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def login(username: str, password: str) -> dict[str, str]:
    return {"token": hash_password(f"{username}:{password}")}
