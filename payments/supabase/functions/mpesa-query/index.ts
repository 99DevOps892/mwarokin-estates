import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
};

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const { checkoutRequestId } = await req.json();

    if (!checkoutRequestId) {
      return new Response(
        JSON.stringify({ error: "checkoutRequestId required" }),
        {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    const consumerKey = Deno.env.get("MPESA_CONSUMER_KEY")!;
    const consumerSecret = Deno.env.get("MPESA_CONSUMER_SECRET")!;
    const shortcode = Deno.env.get("MPESA_SHORTCODE")!;
    const env = Deno.env.get("MPESA_ENV") || "sandbox";

    const baseUrl =
      env === "production"
        ? "https://api.safaricom.co.ke"
        : "https://sandbox.safaricom.co.ke";

    // 1. Get Access Token
    const auth = btoa(`${consumerKey}:${consumerSecret}`);
    const tokenRes = await fetch(
      `${baseUrl}/oauth/v1/generate?grant_type=client_credentials`,
      { headers: { Authorization: `Basic ${auth}` } }
    );
    const tokenData = await tokenRes.json();
    if (!tokenData.access_token) {
      throw new Error("Failed to get access token");
    }

    // 2. Query STK Status
    const timestamp = new Date()
      .toISOString()
      .replace(/[^0-9]/g, "")
      .slice(0, 14);

    const password = btoa(`${shortcode}${Deno.env.get("MPESA_PASSKEY")!}${timestamp}`);

    const queryPayload = {
      BusinessShortCode: shortcode,
      Password: password,
      Timestamp: timestamp,
      CheckoutRequestID: checkoutRequestId,
    };

    const queryRes = await fetch(
      `${baseUrl}/mpesa/stkpushquery/v1/query`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${tokenData.access_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(queryPayload),
      }
    );

    const queryData = await queryRes.json();

    // 3. Map ResultCode to status
    let status = "pending";
    const resultCode = String(queryData.ResultCode);

    if (resultCode === "0") {
      status = "success";
    } else if (["1032", "1037", "2001"].includes(resultCode)) {
      status = "failed";
    } else if (resultCode === "1") {
      status = "failed";
    }

    // 4. Update DB if status changed from pending
    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    const { data: existing } = await supabase
      .from("payments")
      .select("status")
      .eq("provider_ref", checkoutRequestId)
      .single();

    if (existing && existing.status === "pending") {
      const updateData: Record<string, unknown> = {
        status,
        status_reason: queryData.ResultDesc,
        updated_at: new Date().toISOString(),
      };

      await supabase
        .from("payments")
        .update(updateData)
        .eq("provider_ref", checkoutRequestId);
    }

    // 5. Log the event
    const { data: payment } = await supabase
      .from("payments")
      .select("id")
      .eq("provider_ref", checkoutRequestId)
      .single();

    if (payment) {
      await supabase.from("payment_events").insert({
        payment_id: payment.id,
        event_type: "status_poll",
        payload: queryData,
      });
    }

    return new Response(
      JSON.stringify({
        success: true,
        status,
        resultCode: queryData.ResultCode,
        resultDesc: queryData.ResultDesc,
      }),
      {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      }
    );
  } catch (err) {
    console.error(err);
    return new Response(
      JSON.stringify({ error: err.message }),
      {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      }
    );
  }
});
