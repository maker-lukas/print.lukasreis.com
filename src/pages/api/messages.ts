import type { APIRoute } from 'astro';

export const GET: APIRoute = async ({ locals }) => {
  const db = locals.runtime?.env?.DB;
  if (!db) {
    console.error('DB binding missing. locals.runtime:', JSON.stringify(locals.runtime));
    return new Response(JSON.stringify({ error: 'DB not available', runtime: !!locals.runtime }), { status: 500 });
  }

  const { results } = await db.prepare(
    'SELECT id, name, message, created_at FROM messages ORDER BY created_at DESC'
  ).all();
  
  return new Response(JSON.stringify(results), { 
    headers: { 'Content-Type': 'application/json' } 
  });
};

export const POST: APIRoute = async ({ request, locals }) => {
  const db = locals.runtime?.env?.DB;
  if (!db) {
    console.error('DB binding missing on POST');
    return new Response(JSON.stringify({ error: 'DB not available' }), { status: 500 });
  }

  const ip = request.headers.get('cf-connecting-ip') 
    || request.headers.get('x-forwarded-for')?.split(',')[0]?.trim()
    || 'unknown';

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
