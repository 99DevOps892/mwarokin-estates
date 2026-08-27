// ============================================================
// Mwarokin Estates — Airtel Money Edge Function
// POST /functions/v1/airtel-money
// Auth: Bearer <supabase access token>
// Body: { phone, amount, accountReference?, description? }
// Flow: OAuth token -> Collection API -> store pending payment
// Required secrets:
//   AIRTEL_CLIENT_ID, AIRTEL_CLIENT_SECRET
//   AIRTEL_ENV=sandbox|production
//   AIRTEL_CALLBACK_URL
// ============================================================
import { serve } from 'https://deno.land/std@0.208.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { preflight, json, error } from '../_shared/cors.ts';

const AIRTEL_BASES: Record<string, string> = {
  sandbox: 'https://openapi.ng.africastalking.com/v1',
  production: 'https://openapi.airtel.africa/v1',
};

function getBaseUrl(): string {
  const env = (Deno.env.get('AIRTEL_ENV') ?? 'sandbox').toLowerCase();
  return env === 'production'
    ? 'https://openapi.airtel.africa/v1'
    : AIRTEL_BASES.sandbox;
}

function normalizePhone(input: string): string {
  const digits = input.replace(/\D/g, '');
  if (digits.startsWith('254')) return digits.slice(0, 12);
  if (digits.startsWith('0')) return '254' + digits.slice(1, 10);
  if (digits.startsWith('7') || digits.startsWith('1')) return '254' + digits.slice(0, 9);
  return digits;
}

async function getAccessToken(): Promise<string> {
  const clientId = Deno.env.get('AIRTEL_CLIENT_ID');
  const clientSecret = Deno.env.get('AIRTEL_CLIENT_SECRET');
  if (!clientId || !clientSecret) throw new Error('Airtel credentials not configured');

  const base = getBaseUrl();
  const res = await fetch(`${base}/merchant/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      client_id: clientId,
      client_secret: clientSecret,
      lang: 'en',
    }),
  });

  if (!res.ok) throw new Error(`Airtel OAuth failed (${res.status})`);
  const data = await res.json();
  return data.access_token as string;
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
    if (!body?.phone || !(Number(body.amount) > 0)) {
      return error('phone and positive amount required');
    }

    const phone = normalizePhone(body.phone);
    if (!/^254(7|1)\d{8}$/.test(phone)) return error('Invalid Kenyan phone number');

    const amount = Math.round(Number(body.amount));
    const accountRef = String(body.accountReference ?? 'MWAROKIN').slice(0, 12);
    const transactionId = `MA-${Date.now()}-${user.id.slice(0, 8)}`;

    // Insert pending payment
    const { data: payment, error: payErr } = await admin
      .from('payments')
      .insert({
        amount,
        payment_method: 'airtel-money',
        payment_date: new Date().toISOString().slice(0, 10),
        due_date: body.due_date ?? new Date().toISOString().slice(0, 10),
        tenant_id: body.tenant_id ?? null,
        property_id: body.property_id ?? null,
        lease_id: body.lease_id ?? null,
        landlord_id: body.landlord_id ?? null,
        transaction_id: transactionId,
        provider: 'airtel',
        status: 'processing',
        metadata: { phone, accountRef },
      })
      .select()
      .single();
    if (payErr) return error(payErr.message, 500);

    // Initiate Airtel Collection
    let airtelRef: string | null = null;
    try {
      const token = await getAccessToken();
      const base = getBaseUrl();
      const callbackUrl = Deno.env.get('AIRTEL_CALLBACK_URL') ?? '';

      const airtelRes = await fetch(`${base}/merchant/v1/collection/request`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
          'X-Reference-Id': transactionId,
          'X-Target-Environment': Deno.env.get('AIRTEL_ENV') ?? 'sandbox',
        },
        body: JSON.stringify({
          amount,
          currency: 'KES',
          externalId: transactionId,
          payer: { partyIdType: 'MSISDN', partyId: phone },
          payerMessage: body.description ?? 'Mwarokin rent payment',
          payeeNote: `Payment for ${accountRef}`,
        }),
      });

      const airtelData = await airtelRes.json().catch(() => null);
      if (airtelRes.ok && airtelData?.status === 'QUEUED') {
        airtelRef = transactionId;
        await admin
          .from('payments')
          .update({ provider_reference: transactionId })
          .eq('id', payment.id);
      } else {
        await admin
          .from('payments')
          .update({ status: 'failed', metadata: { error: airtelData } })
          .eq('id', payment.id);
      }
    } catch (airtelErr) {
      await admin
        .from('payments')
        .update({ status: 'failed', metadata: { error: (airtelErr as Error).message } })
        .eq('id', payment.id);
    }

    return json({
      success: true,
      payment,
      airtel: { reference: airtelRef, status: airtelRef ? 'queued' : 'failed' },
    });
  } catch (err) {
    return error((err as Error).message, 500);
  }
});
