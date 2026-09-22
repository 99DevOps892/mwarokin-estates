/**
 * Mwarokin Estates — Bot Gate Netlify Function
 * =============================================
 * Server-side verification for Cloudflare Turnstile + honeypot submissions.
 * Env (Netlify build env vars):
 *   TURNSTILE_SECRET_KEY  — secret from the Turnstile dashboard
 * Behaviour:
 *   - Rejects submissions carrying a filled honeypot field.
 *   - Verifies the Turnstile token against Cloudflare's siteverify endpoint.
 *   - Naive per-IP in-memory rate limit (auth endpoints).
 *   - Fails closed when the secret is not configured.
 * Response: { ok, message }
 */
const SITEVERIFY = 'https://challenges.cloudflare.com/turnstile/v0/siteverify';
const rate = new Map();

function allowed(key) {
  const now = Date.now();
  const hit = rate.get(key);
  if (!hit || now - hit.ts > 60000) {
    rate.set(key, { n: 1, ts: now });
    return true;
  }
  if (hit.n >= 5) return false;
  hit.n += 1;
  return true;
}

exports.handler = async function (event) {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: JSON.stringify({ ok: false, message: 'Method not allowed' }) };
  }
  const ip = (event.headers['x-forwarded-for'] || 'unknown').split(',')[0].trim();
  if (!allowed('ip:' + ip)) {
    return { statusCode: 429, body: JSON.stringify({ ok: false, message: 'Too many attempts. Try again shortly.' }) };
  }

  const secret = process.env.TURNSTILE_SECRET_KEY;
  if (!secret) {
    return { statusCode: 503, body: JSON.stringify({ ok: false, message: 'Bot protection not configured' }) };
  }

  const payload = JSON.parse(event.body || '{}');
  if (payload.honeypot && String(payload.honeypot).trim().length > 0) {
    return { statusCode: 400, body: JSON.stringify({ ok: false, message: 'Submission rejected.' }) };
  }

  try {
    const res = await fetch(SITEVERIFY, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ secret: secret, response: payload.token || '', remoteip: ip })
    });
    const data = await res.json();
    if (data.success === true) {
      return { statusCode: 200, body: JSON.stringify({ ok: true, message: 'verified' }) };
    }
    return { statusCode: 400, body: JSON.stringify({ ok: false, message: 'Bot check failed.' }) };
  } catch (e) {
    return { statusCode: 502, body: JSON.stringify({ ok: false, message: 'Verification service unavailable.' }) };
  }
};