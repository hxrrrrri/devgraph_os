export async function GET(_req: Request) {
  return Response.json({ ok: true });
}

export async function POST(_req: Request) {
  return Response.json({ acknowledged: true });
}
