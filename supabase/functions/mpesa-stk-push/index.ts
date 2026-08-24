// ============================================================
// Mwarokin Estates — mpesa-stk-push Edge Function
// POST /functions/v1/mpesa-stk-push
// Auth: Bearer <supabase access token>
// Body: { phone, amount, accountReference?, description? }
// Direct Daraja STK push; result returned to caller.
// ============================================================
import { serve } from 'https://deno.land/std@0.208.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { preflight, json, error } from '../_shared/cors.ts';
import { stkPush } from '../_shared/mpesa.ts';

serve(async (req: Request) => {
  const pf = preflight(req);
  if (pf) return pf;
  if (req.method !== 'POST') return error('Method not allowed', 405);

  try {
    const authHeader = req.headers.get('Authorization') ?? '';
    if (!authHeader.startsWith('Bearer ')) return error('Missing bearer token', 401);

    const userClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_ANON_KEY') ?? '',
      { global: { headers: { Authorization: authHeader } } },
    );
    const { error: userErr } = await userClient.auth.getUser();
    if (userErr) return error('Invalid or expired token', 401);

    const body = await req.json().catch(() => null);
    if (!body?.phone || !(Number(body.amount) > 0)) {
      return error('phone and positive amount required');
    }

    const result = await stkPush({
      phone: String(body.phone),
      amount: Number(body.amount),
      accountReference: String(body.accountReference ?? 'MWAROKIN'),
      description: body.description,
    });

    return json(result, result.ok ? 200 : 502);
  } catch (err) {
    return error((err as Error).message, 500);
  }
});
