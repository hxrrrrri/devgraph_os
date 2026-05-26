import express from 'express';
import { listUsers, createUser } from './users.controller';

const app = express();
app.use(express.json());

app.get('/health', (_req, res) => res.json({ ok: true }));
app.get('/users', listUsers);
app.post('/users', createUser);

export default app;
