import { AuthService } from "./auth";

export function startServer() {
  const auth = new AuthService();
  return auth.login("alice");
}

router.get("/login", startServer);

