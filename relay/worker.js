// Prod Manor instant relay (Cloudflare Worker, free plan).
//
// Telegram sends every tap/message here the moment it happens (webhook). The relay:
//   1. answers right away (button toast "Got it", or a 👀 reaction on your message),
//   2. keeps the update in KV until the agent has handled it,
//   3. starts the GitHub `tick` workflow so it's handled in about a minute, not at the next schedule.
// The tick reads updates from GET /updates instead of Telegram's getUpdates (which stops working once a webhook is set).
//
// Secrets: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, RELAY_SECRET, GH_TOKEN (fine-grained, Actions: read & write)
// Vars (wrangler.toml): GH_REPO, GH_WORKFLOW, GH_REF. KV binding: UPDATES.

const KEY = (id) => 'u:' + String(id).padStart(14, '0');

async function tg(env, method, body) {
  const r = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`, {
    method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body),
  });
  return r.json();
}

async function acknowledge(env, u) {
  if (u.callback_query) {
    return tg(env, 'answerCallbackQuery', { callback_query_id: u.callback_query.id, text: '⏳ Got it, working on it (about a minute)' });
  }
  if (u.message) {
    return tg(env, 'setMessageReaction', {
      chat_id: u.message.chat.id, message_id: u.message.message_id, reaction: [{ type: 'emoji', emoji: '👀' }],
    });
  }
}

async function startTick(env) {
  const r = await fetch(`https://api.github.com/repos/${env.GH_REPO}/actions/workflows/${env.GH_WORKFLOW}/dispatches`, {
    method: 'POST',
    headers: { authorization: `Bearer ${env.GH_TOKEN}`, accept: 'application/vnd.github+json', 'user-agent': 'prod-manor-relay' },
    body: JSON.stringify({ ref: env.GH_REF }),
  });
  if (r.status !== 204) console.log('dispatch failed', r.status, await r.text());
}

async function pending(env) {
  const keys = [];
  let cursor;
  do {
    const page = await env.UPDATES.list({ prefix: 'u:', cursor });
    keys.push(...page.keys.map((k) => k.name));
    cursor = page.list_complete ? null : page.cursor;
  } while (cursor);
  return keys.sort();
}

const json = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'content-type': 'application/json' } });

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);

    // Telegram webhook
    if (req.method === 'POST' && url.pathname === '/telegram') {
      if (req.headers.get('x-telegram-bot-api-secret-token') !== env.RELAY_SECRET) return new Response('forbidden', { status: 403 });
      const u = await req.json();
      const chat = u.message?.chat?.id ?? u.callback_query?.message?.chat?.id;
      if (String(chat) !== String(env.TELEGRAM_CHAT_ID)) return new Response('ignored'); // only the owner drives the bot
      await env.UPDATES.put(KEY(u.update_id), JSON.stringify(u), { expirationTtl: 14 * 86400 });
      ctx.waitUntil(Promise.allSettled([acknowledge(env, u), startTick(env)]));
      return new Response('ok');
    }

    if (req.headers.get('authorization') !== `Bearer ${env.RELAY_SECRET}`) return new Response('forbidden', { status: 403 });

    // the agent: updates not yet handled, oldest first
    if (req.method === 'GET' && url.pathname === '/updates') {
      const keys = await pending(env);
      const vals = await Promise.all(keys.map((k) => env.UPDATES.get(k, 'json')));
      return json({ ok: true, result: vals.filter(Boolean) });
    }

    // the agent: everything up to and including update_id `upto` is handled and saved
    if (req.method === 'POST' && url.pathname === '/ack') {
      const upto = KEY(Number(url.searchParams.get('upto') || 0));
      const done = (await pending(env)).filter((k) => k <= upto);
      await Promise.all(done.map((k) => env.UPDATES.delete(k)));
      return json({ ok: true, deleted: done.length });
    }

    // one-time: point the bot's webhook at this worker
    if (req.method === 'POST' && url.pathname === '/setup') {
      const res = await tg(env, 'setWebhook', {
        url: `${url.origin}/telegram`, secret_token: env.RELAY_SECRET, allowed_updates: ['message', 'callback_query'],
      });
      return json(res);
    }

    return new Response('not found', { status: 404 });
  },
};
