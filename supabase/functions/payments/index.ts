// ============================================================
// Mwarokin Estates — payments Edge Function
// POST /functions/v1/payments
// Auth: Bearer <supabase access token>
// Body: payment payload (same shape as app/js/payments.js)
// Flow: verify JWT -> insert payment (95/5 split via DB trigger)
//       -> if mpesa + phone: initiate STK push and store checkout id
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

    // User-scoped client: verifies the caller's JWT.
    const userClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_ANON_KEY') ?? '',
      { global: { headers: { Authorization: authHeader } } },
    );
    const { data: userData, error: userErr } = await userClient.auth.getUser();
    if (userErr || !userData?.user) return error('Invalid or expired token', 401);
    const user = userData.user;

    // Service-role client: trusted writes after authentication.
    const admin = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '',
    );

    const body = await req.json().catch(() => null);
    if (!body || !(Number(body.amount) > 0)) return error('Valid amount required');
    const amount = Number(body.amount);

    const method = String(body.payment_method ?? 'mpesa').toLowerCase();
    const transactionId =
      body.transaction_id ?? `ME-${Date.now()}-${user.id.slice(0, 8)}`;

    // Resolve tenant for the caller when not supplied.
    let tenantId: string | null = body.tenant_id ?? null;
    if (!tenantId) {
      const { data: t } = await admin
        .from('tenants')
        .select('id')
        .eq('user_id', user.id)
        .maybeSingle();
      tenantId = t?.id ?? null;
    }

    const insertRow = {
      amount,
      payment_method: method,
      payment_date: body.payment_date ?? new Date().toISOString().slice(0, 10),
      due_date: body.due_date ?? new Date().toISOString().slice(0, 10),
      tenant_id: tenantId,
      property_id: body.property_id ?? null,
      lease_id: body.lease_id ?? null,
      landlord_id: body.landlord_id ?? null,
      transaction_id: transactionId,
      status: method === 'bank-transfer' ? 'pending' : 'processing',
      // Live schema has no phone column — payer phone lives in metadata.
      metadata: { ...(body.metadata ?? {}), phone: body.phone ?? null },
    };

    const { data: payment, error: payErr } = await admin
      .from('payments')
      .insert(insertRow)
      .select()
      .single();
    if (payErr) return error(payErr.message, 500);

    await admin.from('audit_logs').insert({
      user_id: user.id,
      action: 'payment.created',
      table_name: 'payments',
      record_id: payment.id,
      new_data: { amount, method, via: 'edge-function' },
    });

    // M-Pesa: fire Daraja STK push when a phone is present.
    // Airtel Money is handled by the dedicated airtel-money function
    // (Airtel Collection API) — it must NOT use the Safaricom Daraja rail.
    let stk: unknown = null;
    if (method === 'mpesa' && body.phone) {
      try {
        const result = await stkPush({
          phone: body.phone,
          amount,
          accountReference: String(transactionId).slice(-12),
          description: 'Mwarokin rent',
        });
        if (result.ok && result.checkoutRequestId) {
          await admin
            .from('payments')
            .update({ checkout_request_id: result.checkoutRequestId })
            .eq('id', payment.id);
          payment.checkout_request_id = result.checkoutRequestId;
        }
        stk = result;
      } catch (stkErr) {
        // Payment row stands; STK failure is reported, not swallowed.
        stk = { ok: false, error: (stkErr as Error).message };
      }
    }

    return json({ success: true, payment, stk });
  } catch (err) {
    return error((err as Error).message, 500);
  }
});
