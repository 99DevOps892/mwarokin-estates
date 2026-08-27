import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

serve(async (req) => {
  try {
    const body = await req.json();
    console.log("Airtel Callback:", JSON.stringify(body, null, 2));

    const transaction = body?.transaction;
    if (!transaction) {
      return new Response(
        JSON.stringify({ status: "error", message: "Invalid callback" }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    }

    const {
      transaction_id,
      reference,
      status_code,
      status_message,
      amount,
      msisdn,
    } = transaction;

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    let status = "failed";
    if (status_code === "200") status = "success";

    const { error } = await supabase
      .from("payments")
      .update({
        status,
        mpesa_receipt: transaction_id,
        paid_amount: amount,
        status_reason: status_message,
        updated_at: new Date().toISOString(),
        metadata: {
          airtelTransactionId: transaction_id,
          statusCode: status_code,
          statusMessage: status_message,
        },
      })
      .eq("provider_ref", reference);

    if (error) console.error("Update error:", error);

    // Always acknowledge
    return new Response(
      JSON.stringify({ status: "success", message: "Accepted" }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  } catch (err) {
    console.error(err);
    return new Response(
      JSON.stringify({ status: "error", message: "Internal error" }),
      { status: 200 }
    );
  }
});
