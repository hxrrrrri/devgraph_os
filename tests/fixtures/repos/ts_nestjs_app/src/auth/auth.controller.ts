import { Controller, Post, Body } from '@nestjs/common';

@Controller('auth')
export class AuthController {
  @Post('login')
  login(@Body() body: { email: string; password: string }) {
    return { token: `t-${body.email}` };
  }

  @Post('logout')
  logout() {
    return { ok: true };
  }
}
