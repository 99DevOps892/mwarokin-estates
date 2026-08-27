// ============================================================
// Mwarokin Estates — Unified Payment Webhook Handler
// POST /functions/v1/payment-webhook?provider=mpesa|airtel|flutterwave
// No user auth: called by external payment providers.
// Handles callbacks from M-Pesa (via mpesa-callback), Airtel Money,
// and Flutterwave. Verifies signatures where possible, updates
// payment status, notifies users, and writes audit trail.
// Always returns 200 to provider to prevent retries.
// ============================================================
import { serve } from 'https://deno.land/std@0.208.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { preflight, json } from '../_shared/cors.ts';

interface FlutterwaveEvent {
  event: string;
  data: {
    id: number;
    tx_ref: string;
    flw_ref: string;
    amount: number;
    currency: string;
    status: string;
    payment_type: string;
    customer: { email?: string; phone_number?: string };
    meta?: { payment_id?: string };
  };
}

interface AirtelCallback {
  transaction: {
    id: string;
    status: string;
    amount: number;
    reference_id: string;
  };
}

serve(async (req: Request) => {
  const pf = preflight(req);
  if (pf) return pf;
  if (req.method !== 'POST') return json({ status: 'ok' });

  const url = new URL(req.url);
  const provider = url.searchParams.get('provider') ?? 'unknown';

  const admin = createClient(
    Deno.env.get('SUPABASE_URL') ?? '',
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '',
  );

  let payload: unknown;
  try {
    payload = await req.json();
  } catch {
    payload = null;
  }

  const rawBody = JSON.stringify(payload);
  const headers: Record<string, string> = {};
  req.headers.forEach((v, k) => { headers[k.toLowerCase()] = v; });

  try {
    let paymentId: string | null = null;
    let txRef: string | null = null;
    let newStatus = 'pending';
    let providerRef: string | null = null;
    let meta: Record<string, unknown> = {};

    // ── Flutterwave ──
    if (provider === 'flutterwave') {
      const event = payload as FlutterwaveEvent;

      // Verify webhook hash (signature)
      const expectedHash = Deno.env.get('FLW_WEBHOOK_HASH');
      const receivedHash = headers['verif-hash'];
      if (expectedHash && receivedHash !== expectedHash) {
        await admin.from('webhook_events').insert({
          provider: 'flutterwave', event_type: event.event,
          payload, processed: false, error_message: 'Invalid webhook hash',
        });
        return json({ status: 'ignored', reason: 'invalid_hash' });
      }

      if (event.event === 'charge.completed' && event.data) {
        txRef = event.data.tx_ref;
        providerRef = String(event.data.flw_ref);
        newStatus = event.data.status === 'successful' ? 'completed' : 'failed';
        meta = { flwEvent: event.event, fwRef: event.data.flw_ref };
      }
    }

    // ── Airtel Money ──
    else if (provider === 'airtel') {
      const cb = payload as AirtelCallback;
      if (cb?.transaction) {
        txRef = cb.transaction.reference_id;
        providerRef = cb.transaction.id;
        newStatus = cb.transaction.status === 'SUCCESSFUL' ? 'completed' : 'failed';
        meta = { airtelStatus: cb.transaction.status };
      }
    }

    // ── M-Pesa (redirect from mpesa-callback) ──
    else if (provider === 'mpesa') {
      const body = payload as Record<string, unknown>;
      const cb = (body as Record<string, Record<string, Record<string, unknown>>>)?.Body?.stkCallback;
      const checkoutId = cb?.CheckoutRequestID as string;
      const resultCode = cb?.ResultCode as number;

      if (checkoutId) {
        const { data: existing } = await admin
          .from('payments')
          .select('id, transaction_id')
          .eq('checkout_request_id', checkoutId)
          .maybeSingle();

        if (existing) {
          paymentId = existing.id;
          txRef = existing.transaction_id;
          newStatus = resultCode === 0 ? 'completed' : 'failed';
          meta = { mpesaCheckoutId: checkoutId, resultCode };

          if (resultCode === 0) {
            const items = (cb?.CallbackMetadata as Record<string, unknown>)?.Item as Array<Record<string, unknown>> | undefined;
            if (items) {
              for (const item of items) {
                if (item.Name === 'MpesaReceiptNumber') providerRef = String(item.Value);
                if (item.Name === 'Amount') meta.callbackAmount = item.Value;
              }
            }
          }
        }
      }
    }

    // ── Update payment by tx_ref if not found by checkout_id ──
    if (!paymentId && txRef) {
      const { data: existing } = await admin
        .from('payments')
        .select('id')
        .eq('transaction_id', txRef)
        .maybeSingle();
      paymentId = existing?.id ?? null;
    }

    // ── Idempotency: check if already processed ──
    if (paymentId) {
      const { data: current } = await admin
        .from('payments')
        .select('status')
        .eq('id', paymentId)
        .maybeSingle();
      if (current?.status === 'completed') {
        return json({ status: 'already_processed' });
      }
    }

    // ── Apply update ──
    if (paymentId) {
      const updates: Record<string, unknown> = {
        status: newStatus,
        webhook_verified: true,
        updated_at: new Date().toISOString(),
      };
      if (providerRef) updates.provider_reference = providerRef;
      if (newStatus === 'completed') updates.paid_at = new Date().toISOString();
      updates.metadata = { ...(meta as Record<string, unknown>) };

      const { error: updateErr } = await admin
        .from('payments')
        .update(updates)
        .eq('id', paymentId);

      if (updateErr) {
        await admin.from('webhook_events').insert({
          provider, event_type: `${provider}_callback`,
          payload, processed: false, error_message: updateErr.message,
        });
        return json({ status: 'error', message: updateErr.message });
      }

      // ── Notifications ──
      const { data: payment } = await admin
        .from('payments')
        .select('id, transaction_id, amount, tenant_id, landlord_id')
        .eq('id', paymentId)
        .maybeSingle();

      if (payment) {
        if (payment.tenant_id) {
          const { data: t } = await admin
            .from('tenants').select('user_id').eq('id', payment.tenant_id).maybeSingle();
          if (t?.user_id) {
            await admin.from('notifications').insert({
              user_id: t.user_id,
              type: 'payment',
              title: newStatus === 'completed' ? 'Payment received' : 'Payment failed',
              body: newStatus === 'completed'
                ? `KES ${payment.amount} confirmed. Ref: ${providerRef ?? payment.transaction_id}.`
                : `Payment of KES ${payment.amount} failed.`,
            });
          }
        }
        if (payment.landlord_id && newStatus === 'completed') {
          const { data: l } = await admin
            .from('landlords').select('user_id').eq('id', payment.landlord_id).maybeSingle();
          if (l?.user_id) {
            await admin.from('notifications').insert({
              user_id: l.user_id,
              type: 'payment',
              title: 'Rent received',
              body: `Payment ${payment.transaction_id} settled via ${provider}.`,
            });
          }
        }

        // ── Audit trail ──
        await admin.from('payment_audit').insert({
          payment_id: paymentId,
          action: `${provider}.${newStatus === 'completed' ? 'confirmed' : 'failed'}`,
          new_status: newStatus,
          actor: `webhook:${provider}`,
          metadata: { providerRef, ...meta },
        });
      }

      // ── Webhook event log ──
      await admin.from('webhook_events').insert({
        provider, event_type: `${provider}_callback`,
        payload, payment_id: paymentId, processed: true,
      });
    }

    // ── Always ACK to prevent provider retries ──
    return json({ status: 'ok' });
  } catch (err) {
    // Log but still ACK — provider retries are worse than silent errors
    try {
      await admin.from('webhook_events').insert({
        provider, event_type: `${provider}_error`,
        payload, processed: false, error_message: (err as Error).message,
      });
    } catch { /* best effort */ }
    return json({ status: 'ok' });
  }
});
