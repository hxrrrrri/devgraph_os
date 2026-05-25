class AuthService:
    def login(self, username: str) -> bool:
        return validate_user(username)


def validate_user(username: str) -> bool:
    return bool(username)


def test_login() -> None:
    assert AuthService().login("alice")

