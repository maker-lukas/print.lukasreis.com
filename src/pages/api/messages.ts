import type { APIRoute } from 'astro';

export const GET: APIRoute = async ({ locals }) => {
  const runtime = locals.runtime as { env?: { DB?: D1Database } } | undefined;
  const db = runtime?.env?.DB;
  if (!db) return new Response('DB not available', { status: 500 });

  const { results } = await db.prepare(
    'SELECT id, name, message, created_at FROM messages ORDER BY created_at DESC'
  ).all();
  
  return new Response(JSON.stringify(results), { 
    headers: { 'Content-Type': 'application/json' } 
  });
};

const RATE_LIMIT_MINUTES = 5;

export const POST: APIRoute = async ({ request, locals }) => {
  const runtime = locals.runtime as { env?: { DB?: D1Database } } | undefined;
  const db = runtime?.env?.DB;
  if (!db) return new Response('DB not available', { status: 500 });

  const ip = request.headers.get('cf-connecting-ip') 
    || request.headers.get('x-forwarded-for')?.split(',')[0]?.trim()
    || 'unknown';

  const recentMessage = await db.prepare(
    `SELECT created_at FROM messages 
     WHERE ip_address = ? AND created_at > datetime('now', ?)
     LIMIT 1`
  ).bind(ip, `-${RATE_LIMIT_MINUTES} minutes`).first();

  if (recentMessage) {
    return new Response(JSON.stringify({ 
      error: `Please wait ${RATE_LIMIT_MINUTES} minutes between messages` 
    }), { 
      status: 429,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  const { name, message } = await request.json() as { name?: string; message?: string };
  if (!message) {
    return new Response('Message is required', { status: 400 });
  }

  await db.prepare(
    'INSERT INTO messages (name, message, ip_address) VALUES (?, ?, ?)'
  ).bind(name || 'Anonymous', message, ip).run();

  return new Response(JSON.stringify({ success: true }), {
    headers: { 'Content-Type': 'application/json' }
  });
};
