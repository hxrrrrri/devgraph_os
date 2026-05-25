import {
  Controller,
  Get,
  Post,
  Patch,
  Delete,
  Param,
  Body,
} from '@nestjs/common';
import { UsersService } from './users.service';

@Controller('users')
export class UsersController {
  constructor(private readonly users: UsersService) {}

  @Get()
  list() {
    return this.users.findAll();
  }

  @Get(':id')
  one(@Param('id') id: string) {
    return this.users.findOne(id);
  }

  @Post()
  create(@Body() body: { email: string }) {
    return this.users.create(body.email);
  }

  @Patch(':id')
  update(@Param('id') id: string, @Body() body: { email: string }) {
    return this.users.update(id, body.email);
  }

  @Delete(':id')
  remove(@Param('id') id: string) {
    return this.users.remove(id);
  }
}
