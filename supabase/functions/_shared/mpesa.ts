// ============================================================
// Mwarokin Estates — M-Pesa Daraja helper (shared)
// STK Push (Lipa na M-Pesa Online) for sandbox + production.
// Required secrets (set via: supabase secrets set):
//   MPESA_ENV=sandbox|production
//   MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET
//   MPESA_PASSKEY, MPESA_SHORTCODE
//   MPESA_CALLBACK_URL  (https://<ref>.supabase.co/functions/v1/mpesa-callback)
// ============================================================

const BASES: Record<string, string> = {
  sandbox: 'https://sandbox.safaricom.co.ke',
  production: 'api.safaricom.co.ke', // handled below with https:// prefix
};

export interface StkArgs {
  phone: string; // 2547XXXXXXXX
  amount: number;
  accountReference: string;
  description?: string;
}

export interface StkResult {
  ok: boolean;
  checkoutRequestId?: string;
  merchantRequestId?: string;
  customerMessage?: string;
  raw?: unknown;
}

function baseUrl(): string {
  const env = (Deno.env.get('MPESA_ENV') ?? 'sandbox').toLowerCase();
  return env === 'production'
    ? 'https://api.safaricom.co.ke'
    : BASES.sandbox;
}

/** Nairobi timestamp in Daraja format yyyyMMddHHmmss. */
function darajaTimestamp(): string {
  const now = new Date(Date.now() + 3 * 3600_000); // UTC+3
  const p = (n: number) => String(n).padStart(2, '0');
  return (
    now.getUTCFullYear() + p(now.getUTCMonth() + 1) + p(now.getUTCDate()) +
    p(now.getUTCHours()) + p(now.getUTCMinutes()) + p(now.getUTCSeconds())
  );
}

function normalizePhone(input: string): string {
  const digits = input.replace(/\D/g, '');
  if (digits.startsWith('254')) return digits.slice(0, 12);
  if (digits.startsWith('0')) return '254' + digits.slice(1, 10);
  if (digits.startsWith('7') || digits.startsWith('1')) return '254' + digits.slice(0, 9);
  return digits;
}

async function accessToken(): Promise<string> {
  const key = Deno.env.get('MPESA_CONSUMER_KEY');
  const secret = Deno.env.get('MPESA_CONSUMER_SECRET');
  if (!key || !secret) throw new Error('M-Pesa credentials not configured');
  const basic = btoa(`${key}:${secret}`);
  const res = await fetch(
    `${baseUrl()}/oauth/v1/generate?grant_type=client_credentials`,
    { headers: { Authorization: `Basic ${basic}` } },
  );
  if (!res.ok) throw new Error(`Daraja OAuth failed (${res.status})`);
  const data = await res.json();
  return data.access_token as string;
}

export async function stkPush(args: StkArgs): Promise<StkResult> {
  const shortcode = Deno.env.get('MPESA_SHORTCODE');
  const passkey = Deno.env.get('MPESA_PASSKEY');
  const callbackUrl = Deno.env.get('MPESA_CALLBACK_URL');
  if (!shortcode || !passkey || !callbackUrl) {
    throw new Error('M-Pesa shortcode/passkey/callback URL not configured');
  }

  const phone = normalizePhone(args.phone);
  if (!/^254(7|1)\d{8}$/.test(phone)) throw new Error('Invalid Kenyan phone number');

  const ts = darajaTimestamp();
  const password = btoa(`${shortcode}${passkey}${ts}`);

  const token = await accessToken();
  const payload = {
    BusinessShortCode: shortcode,
    Password: password,
    Timestamp: ts,
    TransactionType: 'CustomerPayBillOnline',
    Amount: Math.round(args.amount),
    PartyA: phone,
    PartyB: shortcode,
    PhoneNumber: phone,
    CallBackURL: callbackUrl,
    AccountReference: args.accountReference.slice(0, 12),
    TransactionDesc: (args.description ?? 'Rent payment').slice(0, 30),
  };

  const res = await fetch(`${baseUrl()}/mpesa/stkpush/v1/processrequest`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  const raw = await res.json().catch(() => null);
  if (!res.ok || !raw || raw.ResponseCode !== '0') {
    return { ok: false, raw };
  }
  return {
    ok: true,
    checkoutRequestId: raw.CheckoutRequestID,
    merchantRequestId: raw.MerchantRequestID,
    customerMessage: raw.CustomerMessage,
    raw,
  };
}
