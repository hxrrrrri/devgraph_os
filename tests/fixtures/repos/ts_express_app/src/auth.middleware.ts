import type { NextFunction, Request, Response } from 'express';

export function requireAuth(req: Request, _res: Response, next: NextFunction) {
  if (req.headers.authorization) {
    return next();
  }
  return _res.status(401).json({ error: 'unauthenticated' });
}
