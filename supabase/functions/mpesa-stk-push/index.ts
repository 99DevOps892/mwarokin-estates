import { createClient, SupabaseClient } from "jsr:@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

// Safaricom Daraja API credentials (set these in Supabase Edge Function secrets)
const MPESA_CONSUMER_KEY = Deno.env.get("MPESA_CONSUMER_KEY") ?? "";
const MPESA_CONSUMER_SECRET = Deno.env.get("MPESA_CONSUMER_SECRET") ?? "";
const MPESA_PASSKEY = Deno.env.get("MPESA_PASSKEY") ?? "";
const MPESA_SHORTCODE = Deno.env.get("MPESA_SHORTCODE") ?? "";
const MPESA_CALLBACK_URL = Deno.env.get("MPESA_CALLBACK_URL") ?? "";
const MPESA_ENV = Deno.env.get("MPESA_ENV") ?? "sandbox";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

/**
 * M-Pesa STK Push (Lipa na M-Pesa Online)
 * POST body: { phone (07xxxxxxxx), amount, payment_id, transaction_id }
 */
Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const supabase: SupabaseClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);
    const body = await req.json();

    if (!MPESA_CONSUMER_KEY || !MPESA_CONSUMER_SECRET || !MPESA_PASSKEY) {
      return json(
        { ok: false, error: "M-Pesa is not configured. Contact the platform administrator." },
        501,
        corsHeaders
      );
    }

    const phone = (body.phone || "").replace(/\D/g, "");
    const normalized = phone.length === 9 ? "254" + phone : phone.startsWith("0") ? "254" + phone.slice(1) : phone;
    const amount = Math.round(Number(body.amount));

    // 1. Get OAuth token
    const authRes = await fetch(
      "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
      {
        headers: {
          Authorization: "Basic " + btoa(`${MPESA_CONSUMER_KEY}:${MPESA_CONSUMER_SECRET}`),
        },
      }
    );
    const authData = await authRes.json();
    if (!authData.access_token) {
      return json({ ok: false, error: "Failed to get M-Pesa token" }, 500, corsHeaders);
    }

    // 2. Timestamp + password
    const ts = new Date()
      .toISOString()
      .replace(/[-T:Z.]/g, "")
      .slice(0, 14);
    const password = btoa(`${MPESA_SHORTCODE}${MPESA_PASSKEY}${ts}`);

    const base = MPESA_ENV === "production"
      ? "https://api.safaricom.co.ke"
      : "https://sandbox.safaricom.co.ke";

    // 3. Trigger STK push
    const stkRes = await fetch(`${base}/mpesa/stkpush/v1/processrequest`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${authData.access_token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        BusinessShortCode: MPESA_SHORTCODE,
        Password: password,
        Timestamp: ts,
        TransactionType: "CustomerPayBillOnline",
        Amount: amount,
        PartyA: normalized,
        PartyB: MPESA_SHORTCODE,
        PhoneNumber: normalized,
        CallBackURL: MPESA_CALLBACK_URL || `${SUPABASE_URL}/functions/v1/mpesa-callback`,
        AccountReference: body.transaction_id || `ME-${Date.now()}`,
        TransactionDesc: "Mwarokin Estates Rent",
      }),
    });
    const stkData = await stkRes.json();

    if (stkData.ResponseCode === "0") {
      // CheckoutRequestID received — store it so the callback can correlate
      await supabase
        .from("payments")
        .update({ metadata: { ...(body.metadata ?? {}), checkout_request_id: stkData.CheckoutRequestID } })
        .eq("id", body.payment_id)
        .catch(() => {});
      return json({ ok: true, checkout_request_id: stkData.CheckoutRequestID }, 200, corsHeaders);
    }

    return json({ ok: false, error: stkData.ResponseDescription || "STK push failed" }, 400, corsHeaders);
  } catch (e) {
    return json({ ok: false, error: e.message }, 500, corsHeaders);
  }
});

function json(body: unknown, status: number, headers: Record<string, string>) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}