export class AuthService {
  login(username: string): boolean {
    return username.length > 0;
  }
}
