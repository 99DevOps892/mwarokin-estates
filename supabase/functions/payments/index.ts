import { createClient, SupabaseClient } from "jsr:@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

/**
 * Payments Edge Function
 * POST /payments — records a rent payment. The DB trigger computes the
 * 95% landlord / 5% platform split. If method is mpesa, an STK push is
 * attempted via the mpesa-stk-push function (when configured).
 *
 * Body: { amount, payment_method, payment_date, due_date, tenant_id,
 *         property_id, lease_id, landlord_id, transaction_id, metadata }
 */
Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const supabase: SupabaseClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);
    const body = await req.json();

    const amount = Number(body.amount);
    if (!amount || amount <= 0) {
      return json({ error: "A valid amount is required" }, 400, corsHeaders);
    }

    const method = body.payment_method || "bank-transfer";

    // 1. Create the payment record (split computed server-side by trigger)
    const { data: payment, error: insertError } = await supabase
      .from("payments")
      .insert([{
        amount,
        payment_method: method,
        payment_date: body.payment_date || new Date().toISOString().slice(0, 10),
        due_date: body.due_date || new Date().toISOString().slice(0, 10),
        tenant_id: body.tenant_id ?? null,
        property_id: body.property_id ?? null,
        lease_id: body.lease_id ?? null,
        landlord_id: body.landlord_id ?? null,
        transaction_id: body.transaction_id || `ME-${Date.now()}`,
        status: method === "bank-transfer" ? "pending" : "processing",
        metadata: body.metadata ?? {},
      }])
      .select()
      .single();

    if (insertError) {
      return json({ error: insertError.message }, 500, corsHeaders);
    }

    // 2. For M-Pesa: attempt STK push (best-effort, async fire-and-forget)
    if (method === "mpesa" && body.phone) {
      try {
        await fetch(`${SUPABASE_URL}/functions/v1/mpesa-stk-push`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${SUPABASE_SERVICE_KEY}`,
          },
          body: JSON.stringify({
            phone: body.phone,
            amount,
            payment_id: payment.id,
            transaction_id: payment.transaction_id,
          }),
        });
      } catch (e) {
        console.warn("STK push failed:", e.message);
      }
    }

    // 3. Notify relevant parties
    const notifyTargets: Array<{ user_id: string; title: string; body: string }> = [];
    if (payment.landlord_id) {
      notifyTargets.push({
        user_id: payment.landlord_id,
        title: "Rent payment received",
        body: `A payment of KES ${amount.toLocaleString()} was received via ${method}.`,
      });
    }
    for (const n of notifyTargets) {
      await supabase.from("notifications").insert([n]).select().single().catch(() => {});
    }

    return json({ ok: true, payment }, 200, corsHeaders);
  } catch (e) {
    return json({ error: e.message }, 500, corsHeaders);
  }
});

function json(body: unknown, status: number, headers: Record<string, string>) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}