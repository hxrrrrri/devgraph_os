from service import AuthService


def main() -> None:
    service = AuthService()
    service.login("alice")


if __name__ == "__main__":
    main()

