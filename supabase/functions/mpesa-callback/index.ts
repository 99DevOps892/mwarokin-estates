// ============================================================
// Mwarokin Estates — mpesa-callback Edge Function
// POST /functions/v1/mpesa-callback   (called by Safaricom Daraja)
// No user auth: Daraja servers call this endpoint. Updates the
// matching payment by CheckoutRequestID, notifies tenant + landlord,
// writes an audit trail, and always ACKs with ResultCode 0.
// ============================================================
import { serve } from 'https://deno.land/std@0.208.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { preflight, json } from '../_shared/cors.ts';

interface StkCallbackItem { Name: string; Value?: unknown }
interface StkCallback {
  Body?: {
    stkCallback?: {
      MerchantRequestID?: string;
      CheckoutRequestID?: string;
      ResultCode?: number;
      ResultDesc?: string;
      CallbackMetadata?: { Item?: StkCallbackItem[] };
    };
  };
}

serve(async (req: Request) => {
  const pf = preflight(req);
  if (pf) return pf;
  if (req.method !== 'POST') return json({ ResultCode: 0, ResultDesc: 'Accepted' });

  try {
    const admin = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '',
    );

    const payload = (await req.json()) as StkCallback;
    const cb = payload?.Body?.stkCallback;
    const checkoutId = cb?.CheckoutRequestID;
    if (!checkoutId) return json({ ResultCode: 0, ResultDesc: 'No checkout id — ignored' });

    const success = cb?.ResultCode === 0;

    // Extract metadata items on success.
    let mpesaReceipt: string | null = null;
    let amount: number | null = null;
    let phone: string | null = null;
    if (success) {
      for (const item of cb!.CallbackMetadata?.Item ?? []) {
        if (item.Name === 'MpesaReceiptNumber') mpesaReceipt = String(item.Value);
        if (item.Name === 'Amount') amount = Number(item.Value);
        if (item.Name === 'PhoneNumber') phone = String(item.Value);
      }
    }

    const updates = success
      ? {
          status: 'completed',
          paid_at: new Date().toISOString(),
          provider_reference: mpesaReceipt,
          metadata: { resultDesc: cb?.ResultDesc, callbackAmount: amount },
        }
      : {
          status: 'failed',
          metadata: { resultCode: cb?.ResultCode, resultDesc: cb?.ResultDesc },
        };

    const { data: payment } = await admin
      .from('payments')
      .update(updates)
      .eq('checkout_request_id', checkoutId)
      .select('id, transaction_id, amount, tenant_id, landlord_id')
      .single();

    if (payment) {
      // Notify the tenant's login account.
      if (payment.tenant_id) {
        const { data: t } = await admin
          .from('tenants')
          .select('user_id')
          .eq('id', payment.tenant_id)
          .maybeSingle();
        if (t?.user_id) {
          await admin.from('notifications').insert({
            user_id: t.user_id,
            type: 'payment',
            title: success ? 'Payment received' : 'Payment failed',
            body: success
              ? `Payment of ${payment.amount} confirmed. M-Pesa receipt ${mpesaReceipt}.`
              : `Payment of ${payment.amount} failed: ${cb?.ResultDesc ?? 'unknown reason'}.`,
          });
        }
      }

      // Notify the landlord.
      if (payment.landlord_id) {
        const { data: l } = await admin
          .from('landlords')
          .select('user_id')
          .eq('id', payment.landlord_id)
          .maybeSingle();
        if (l?.user_id) {
          await admin.from('notifications').insert({
            user_id: l.user_id,
            type: 'payment',
            title: success ? 'Rent received' : 'Tenant payment failed',
            body: success
              ? `Payment ${payment.transaction_id} settled. Your share is credited after the platform fee.`
              : `Payment ${payment.transaction_id} failed at M-Pesa.`,
          });
        }
      }

      await admin.from('audit_logs').insert({
        action: success ? 'payment.mpesa_confirmed' : 'payment.mpesa_failed',
        table_name: 'payments',
        record_id: payment.id,
        new_data: { checkoutId, mpesaReceipt },
      });
    }

    // Daraja requires a 200 ACK regardless of our processing result.
    return json({ ResultCode: 0, ResultDesc: 'Accepted' });
  } catch (_err) {
    return json({ ResultCode: 0, ResultDesc: 'Accepted' });
  }
});
