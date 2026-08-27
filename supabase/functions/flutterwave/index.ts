// ============================================================
// Mwarokin Estates — Flutterwave Edge Function
// POST /functions/v1/flutterwave
// Auth: Bearer <supabase access token>
// Body: { amount, phone?, email?, method: 'bank'|'card', lease_id, ... }
// Flow: Initiate Flutterwave payment -> return payment link
// Required secrets:
//   FLW_SECRET_KEY (production or test)
//   FLW_WEBHOOK_HASH (for webhook verification)
//   FLW_ENV=sandbox|production
// ============================================================
import { serve } from 'https://deno.land/std@0.208.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { preflight, json, error } from '../_shared/cors.ts';

const FLW_BASES: Record<string, string> = {
  sandbox: 'https://api.flutterwave.com/v3',
  production: 'https://api.flutterwave.com/v3',
};

function getBaseUrl(): string {
  const env = (Deno.env.get('FLW_ENV') ?? 'sandbox').toLowerCase();
  return FLW_BASES[env] ?? FLW_BASES.sandbox;
}

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
    const { data: userData, error: userErr } = await userClient.auth.getUser();
    if (userErr || !userData?.user) return error('Invalid or expired token', 401);
    const user = userData.user;

    const admin = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '',
    );

    const body = await req.json().catch(() => null);
    if (!body || !(Number(body.amount) > 0)) return error('Valid amount required');

    const amount = Number(body.amount);
    const method = String(body.payment_method ?? 'card').toLowerCase();
    const txRef = `MW-${Date.now()}-${user.id.slice(0, 8)}`;

    // Determine payment method for Flutterwave
    let fwMethod: string;
    if (method === 'bank-transfer' || method === 'bank') {
      fwMethod = 'banktransfer';
    } else if (method === 'card') {
      fwMethod = 'card';
    } else {
      fwMethod = 'card';
    }

    // Insert pending payment
    const { data: payment, error: payErr } = await admin
      .from('payments')
      .insert({
        amount,
        payment_method: fwMethod === 'banktransfer' ? 'bank-transfer' : 'card',
        payment_date: new Date().toISOString().slice(0, 10),
        due_date: body.due_date ?? new Date().toISOString().slice(0, 10),
        tenant_id: body.tenant_id ?? null,
        property_id: body.property_id ?? null,
        lease_id: body.lease_id ?? null,
        landlord_id: body.landlord_id ?? null,
        transaction_id: txRef,
        provider: 'flutterwave',
        status: 'processing',
        metadata: { email: body.email, phone: body.phone, fwMethod },
      })
      .select()
      .single();
    if (payErr) return error(payErr.message, 500);

    // Initiate Flutterwave payment
    let paymentLink: string | null = null;
    let flwRef: string | null = null;
    try {
      const secretKey = Deno.env.get('FLW_SECRET_KEY');
      if (!secretKey) throw new Error('Flutterwave credentials not configured');

      const baseUrl = getBaseUrl();
      const redirectUrl = body.redirect_url ?? `${Deno.env.get('SUPABASE_URL')?.replace('.supabase.co', '.vercel.app')}/dashboard.html`;

      const fwPayload: Record<string, unknown> = {
        tx_ref: txRef,
        amount,
        currency: 'KES',
        redirect_url: redirectUrl,
        payment_options: fwMethod,
        customer: {
          email: body.email ?? `${user.id}@mwarokin.app`,
          phone_number: body.phone ?? undefined,
          name: body.full_name ?? 'Mwarokin Tenant',
        },
        customizations: {
          title: 'Mwarokin Estates',
          description: `Payment for ${body.description ?? 'rent'}`,
          logo: '',
        },
        meta: { payment_id: payment.id },
      };

      const fwRes = await fetch(`${baseUrl}/payments`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${secretKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(fwPayload),
      });

      const fwData = await fwRes.json().catch(() => null);
      if (fwRes.ok && fwData?.status === 'success') {
        paymentLink = fwData.data?.link ?? null;
        flwRef = fwData.data?.id ? String(fwData.data.id) : null;
        if (flwRef) {
          await admin
            .from('payments')
            .update({ provider_reference: flwRef, metadata: { ...payment.metadata, flwRef } })
            .eq('id', payment.id);
        }
      } else {
        await admin
          .from('payments')
          .update({ status: 'failed', metadata: { ...payment.metadata, error: fwData } })
          .eq('id', payment.id);
      }
    } catch (fwErr) {
      await admin
        .from('payments')
        .update({ status: 'failed', metadata: { ...payment.metadata, error: (fwErr as Error).message } })
        .eq('id', payment.id);
    }

    return json({
      success: true,
      payment,
      flutterwave: { link: paymentLink, reference: flwRef, status: paymentLink ? 'initiated' : 'failed' },
    });
  } catch (err) {
    return error((err as Error).message, 500);
  }
});
