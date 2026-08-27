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
    const { phone, amount, accountReference, transactionDesc } =
      await req.json();

    if (!phone || !amount) {
      return new Response(
        JSON.stringify({ error: "phone and amount required" }),
        {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    // Normalize phone: 07XX -> 2547XX, 7XX -> 2547XX
    let normalizedPhone = phone.replace(/\D/g, "");
    if (normalizedPhone.startsWith("0"))
      normalizedPhone = "254" + normalizedPhone.slice(1);
    if (normalizedPhone.startsWith("7"))
      normalizedPhone = "254" + normalizedPhone;
    if (
      !normalizedPhone.startsWith("254") ||
      normalizedPhone.length !== 12
    ) {
      return new Response(
        JSON.stringify({ error: "Invalid Kenyan phone number" }),
        {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    const airtelUserId = Deno.env.get("AIRTEL_USER_ID")!;
    const airtelPassword = Deno.env.get("AIRTEL_PASSWORD")!;
    const airtelSubscriptionKey = Deno.env.get("AIRTEL_SUBSCRIPTION_KEY")!;
    const airtelEnv = Deno.env.get("AIRTEL_ENV") || "sandbox";
    const airtelCallbackUrl = Deno.env.get("AIRTEL_CALLBACK_URL")!;

    const baseUrl =
      airtelEnv === "production"
        ? "https://openapi.airtel.africa"
        : "https://sandbox.openapi.airtel.africa";

    // 1. Get Access Token (OAuth)
    const tokenRes = await fetch(
      `${baseUrl}/auth/oauth2/token`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          Authorization: `Basic ${btoa(`${airtelUserId}:${airtelPassword}`)}`,
        },
        body: new URLSearchParams({
          grant_type: "client_credentials",
        }),
      }
    );

    const tokenData = await tokenRes.json();
    if (!tokenData.access_token) {
      throw new Error("Airtel: Failed to get access token");
    }

    // 2. Initiate Collection (STK Push equivalent)
    const transactionId = `TX-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

    const payload = {
      reference: transactionId,
      subscriber: {
        country: "KE",
        msisdn: normalizedPhone,
      },
      transaction: {
        amount: Number(amount),
        country: "KE",
        currency: "KES",
        description: (transactionDesc || "Payment").slice(0, 128),
      },
      callback: {
        notificationUrl: airtelCallbackUrl,
      },
    };

    const collectionRes = await fetch(
      `${baseUrl}/merchant/v1/payments`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${tokenData.access_token}`,
          "Content-Type": "application/json",
          "X-Country": "KE",
          "X-Currency": "KES",
        },
        body: JSON.stringify(payload),
      }
    );

    const collectionData = await collectionRes.json();

    if (!collectionData.data || collectionData.data.responseCode !== "200") {
      return new Response(
        JSON.stringify({
          error:
            collectionData.data?.message ||
            collectionData.message ||
            "Airtel collection failed",
          details: collectionData,
        }),
        {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    // 3. Store pending payment
    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    const { data: payment, error } = await supabase
      .from("payments")
      .insert({
        amount: Number(amount),
        currency: "KES",
        method: "airtel",
        status: "pending",
        provider_ref: transactionId,
        phone: normalizedPhone,
        metadata: {
          airtelTransactionId: collectionData.data.transactionId,
          accountReference: accountReference || "Payment",
          airtelResponse: collectionData.data,
        },
      })
      .select()
      .single();

    if (error) console.error("DB insert error:", error);

    return new Response(
      JSON.stringify({
        success: true,
        transactionId,
        airtelTransactionId: collectionData.data.transactionId,
        message: collectionData.data.message,
        paymentId: payment?.id,
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
