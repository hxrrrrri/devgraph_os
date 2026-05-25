import type { Request, Response } from 'express';

const users: { id: number; email: string }[] = [];

export function listUsers(_req: Request, res: Response) {
  res.json(users);
}

export function createUser(req: Request, res: Response) {
  const row = { id: users.length + 1, email: req.body.email };
  users.push(row);
  res.status(201).json(row);
}
