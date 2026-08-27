/**
 * M-Pesa & Airtel Money — Payment Client
 * Drop-in module for Supabase + Daraja / Airtel Open API
 */

const SUPABASE_URL = "https://spnerrqumefbuuscumhw.supabase.co";
const SUPABASE_ANON_KEY = "YOUR_ANON_KEY"; // Replace with actual anon key

// ── Helpers ─────────────────────────────────────────────────

function createSupabaseClient() {
  if (typeof window !== "undefined" && window.supabase) {
    return window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
  }
  return null;
}

async function getAccessToken(supabase) {
  if (!supabase) return null;
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token || SUPABASE_ANON_KEY;
}

// ── M-Pesa STK Push ────────────────────────────────────────

async function initiateMpesaPayment({
  phone,
  amount,
  accountReference = "Payment",
  transactionDesc = "App Payment",
  supabase = null,
}) {
  supabase = supabase || createSupabaseClient();
  const token = await getAccessToken(supabase);

  const res = await fetch(`${SUPABASE_URL}/functions/v1/mpesa-stk`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ phone, amount, accountReference, transactionDesc }),
  });

  const result = await res.json();

  if (!result.success) {
    throw new Error(result.error || "Failed to initiate M-Pesa payment");
  }

  return {
    checkoutRequestId: result.checkoutRequestId,
    merchantRequestId: result.merchantRequestId,
    customerMessage: result.customerMessage,
    paymentId: result.paymentId,
  };
}

// ── Airtel Money Collection ────────────────────────────────

async function initiateAirtelPayment({
  phone,
  amount,
  accountReference = "Payment",
  transactionDesc = "App Payment",
  supabase = null,
}) {
  supabase = supabase || createSupabaseClient();
  const token = await getAccessToken(supabase);

  const res = await fetch(`${SUPABASE_URL}/functions/v1/airtel-money`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ phone, amount, accountReference, transactionDesc }),
  });

  const result = await res.json();

  if (!result.success) {
    throw new Error(result.error || "Failed to initiate Airtel payment");
  }

  return {
    transactionId: result.transactionId,
    airtelTransactionId: result.airtelTransactionId,
    message: result.message,
    paymentId: result.paymentId,
  };
}

// ── STK Query (Fallback Status Check) ─────────────────────

async function queryMpesaStatus(checkoutRequestId, supabase = null) {
  supabase = supabase || createSupabaseClient();
  const token = await getAccessToken(supabase);

  const res = await fetch(`${SUPABASE_URL}/functions/v1/mpesa-query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ checkoutRequestId }),
  });

  return await res.json();
}

// ── Payment Status Polling ─────────────────────────────────

function pollPaymentStatus(checkoutRequestId, supabase = null, options = {}) {
  const {
    intervalMs = 3000,
    maxDurationMs = 120000,
    onStatusChange = () => {},
    onSuccess = () => {},
    onFailure = () => {},
    onTimeout = () => {},
  } = options;

  supabase = supabase || createSupabaseClient();
  let elapsed = 0;

  const interval = setInterval(async () => {
    elapsed += intervalMs;

    try {
      const { data } = await supabase
        .from("payments")
        .select("status, mpesa_receipt, paid_amount")
        .eq("provider_ref", checkoutRequestId)
        .single();

      if (data) {
        onStatusChange(data);

        if (data.status === "success") {
          clearInterval(interval);
          onSuccess(data);
          return;
        }

        if (data.status === "failed" || data.status === "cancelled") {
          clearInterval(interval);
          onFailure(data);
          return;
        }
      }

      if (elapsed >= maxDurationMs) {
        clearInterval(interval);

        // Final fallback: query Daraja directly
        try {
          const queryResult = await queryMpesaStatus(checkoutRequestId, supabase);
          if (queryResult.status === "success") {
            onSuccess(queryResult);
          } else {
            onTimeout(queryResult);
          }
        } catch {
          onTimeout({ status: "timeout" });
        }
      }
    } catch (err) {
      console.error("Poll error:", err);
    }
  }, intervalMs);

  // Return cleanup function
  return () => clearInterval(interval);
}

// ── Realtime Subscription (alternative to polling) ─────────

function subscribeToPaymentStatus(paymentId, supabase, callbacks = {}) {
  supabase = supabase || createSupabaseClient();
  const { onInsert, onUpdate, onError } = callbacks;

  const channel = supabase
    .channel(`payment:${paymentId}`)
    .on(
      "postgres_changes",
      {
        event: "*",
        schema: "public",
        table: "payments",
        filter: `id=eq.${paymentId}`,
      },
      (payload) => {
        if (payload.eventType === "INSERT" && onInsert) {
          onInsert(payload.new);
        }
        if (payload.eventType === "UPDATE" && onUpdate) {
          onUpdate(payload.new);
        }
      }
    )
    .subscribe((err) => {
      if (err && onError) onError(err);
    });

  return () => supabase.removeChannel(channel);
}

// ── Result Code Mapping ────────────────────────────────────

const MPESA_RESULT_CODES = {
  0: { label: "Success", type: "success" },
  1: { label: "Insufficient balance", type: "error" },
  1032: { label: "Request cancelled", type: "cancelled" },
  1037: { label: "Timeout — PIN not entered", type: "timeout" },
  2001: { label: "Wrong PIN entered", type: "error" },
  2026: { label: "Debit limit exceeded", type: "error" },
  2027: { label: "Credit limit exceeded", type: "error" },
};

function interpretMpesaCode(code) {
  return (
    MPESA_RESULT_CODES[code] || {
      label: `Unknown code: ${code}`,
      type: "unknown",
    }
  );
}

// ── Exports ────────────────────────────────────────────────

window.MpesaPayment = {
  initiate: initiateMpesaPayment,
  queryStatus: queryMpesaStatus,
  pollStatus: pollPaymentStatus,
  subscribeStatus: subscribeToPaymentStatus,
  interpretCode: interpretMpesaCode,
};

window.AirtelPayment = {
  initiate: initiateAirtelPayment,
};

window.PaymentClient = {
  mpesa: window.MpesaPayment,
  airtel: window.AirtelPayment,
};
