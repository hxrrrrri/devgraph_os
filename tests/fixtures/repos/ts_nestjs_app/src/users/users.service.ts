import { Injectable } from '@nestjs/common';

@Injectable()
export class UsersService {
  private readonly rows = new Map<string, { id: string; email: string }>();

  findAll() {
    return Array.from(this.rows.values());
  }

  findOne(id: string) {
    return this.rows.get(id) ?? null;
  }

  create(email: string) {
    const id = String(this.rows.size + 1);
    const row = { id, email };
    this.rows.set(id, row);
    return row;
  }

  update(id: string, email: string) {
    const existing = this.rows.get(id);
    if (!existing) return null;
    existing.email = email;
    return existing;
  }

  remove(id: string) {
    this.rows.delete(id);
    return { id };
  }
}
