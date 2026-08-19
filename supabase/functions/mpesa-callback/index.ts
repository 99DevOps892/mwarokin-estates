import { createClient, SupabaseClient } from "jsr:@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

/**
 * M-Pesa Callback
 * Safaricom calls this endpoint with the STK push result. We match the
 * CheckoutRequestID stored on the payment and mark it completed/failed.
 * The DB trigger then releases the landlord share (95%) / platform fee (5%).
 */
Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const supabase: SupabaseClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);
    const body = await req.json();

    const stk = body?.Body?.stkCallback;
    if (!stk) {
      return json({ ok: false, error: "Malformed callback" }, 400, corsHeaders);
    }

    const checkoutId = stk.CheckoutRequestID;
    const resultCode = stk.ResultCode; // 0 = success
    const amount = stk.CallbackMetadata?.Item?.find((i: any) => i.Name === "Amount")?.Value;
    const mpesaReceipt = stk.CallbackMetadata?.Item?.find((i: any) => i.Name === "MpesaReceiptNumber")?.Value;
    const phone = stk.CallbackMetadata?.Item?.find((i: any) => i.Name === "PhoneNumber")?.Value;

    // Find the payment by CheckoutRequestID
    const { data: payments } = await supabase
      .from("payments")
      .select("id, tenant_id, landlord_id, property_id")
      .filter("metadata->>checkout_request_id", "eq", checkoutId);

    if (!payments || payments.length === 0) {
      return json({ ok: false, error: "Payment not found" }, 404, corsHeaders);
    }

    const payment = payments[0];
    const status = resultCode === 0 ? "completed" : "failed";

    const { data, error } = await supabase
      .from("payments")
      .update({
        status,
        transaction_id: mpesaReceipt || payment.transaction_id || `MPESA-${checkoutId.slice(0, 8)}`,
        payment_date: new Date().toISOString().slice(0, 10),
        metadata: { ...(payment.metadata ?? {}), mpesa_receipt: mpesaReceipt ?? null, result_code: resultCode },
      })
      .eq("id", payment.id)
      .select()
      .single();

    if (error) {
      return json({ ok: false, error: error.message }, 500, corsHeaders);
    }

    if (payment.landlord_id && resultCode === 0) {
      await supabase.from("notifications").insert([{
        user_id: payment.landlord_id,
        title: "Rent payment confirmed",
        body: `M-Pesa payment of KES ${(amount ?? 0).toLocaleString()} confirmed.`,
      }]).catch(() => {});
    }

    return json({ ok: true, status, receipt: mpesaReceipt }, 200, corsHeaders);
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