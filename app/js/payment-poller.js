/**
 * Mwarokin Estates — Payment Status Poller
 * Polls payment status via Supabase Realtime or fallback polling.
 * Used after STK push / Airtel / Flutterwave initiation.
 */
(function () {
  const sb = window.supabaseClient;
  if (!sb) return;

  const cfg = window.MWAROKIN_CONFIG || {};

  window.MWAROKIN_POLLER = {
    waitForPayment,
    subscribeToPayment,
    getPaymentStatus,
  };

  /**
   * Poll payment status by transaction_id.
   * @param {string} transactionId
   * @param {number} timeoutMs - max wait (default 60s)
   * @param {number} intervalMs - poll interval (default 3s)
   * @returns {Promise<object|null>} payment row or null on timeout
   */
  async function getPaymentStatus(transactionId) {
    const { data, error } = await sb
      .from('payments')
      .select('id, status, transaction_id, provider_reference, paid_at, amount, payment_method')
      .eq('transaction_id', transactionId)
      .maybeSingle();
    if (error) return null;
    return data;
  }

  /**
   * Subscribe to Realtime changes on payments table filtered by transaction_id.
   * Falls back to polling if Realtime is unavailable.
   */
  function subscribeToPayment(transactionId, onUpdate) {
    let resolved = false;

    try {
      const channel = sb
        .channel(`payment-${transactionId}`)
        .on(
          'postgres_changes',
          {
            event: 'UPDATE',
            schema: 'public',
            table: 'payments',
            filter: `transaction_id=eq.${transactionId}`,
          },
          (payload) => {
            if (!resolved) {
              resolved = true;
              onUpdate(payload.new);
              sb.removeChannel(channel);
            }
          },
        )
        .subscribe();

      return {
        unsubscribe: () => {
          resolved = true;
          sb.removeChannel(channel);
        },
      };
    } catch {
      return { unsubscribe: () => {} };
    }
  }

  /**
   * Wait for a payment to reach a terminal state.
   * Uses Realtime subscription with polling fallback.
   * @param {string} transactionId
   * @param {object} opts - { timeoutMs, intervalMs, onStatus }
   * @returns {Promise<object>} final payment row
   */
  function waitForPayment(transactionId, opts = {}) {
    const timeoutMs = opts.timeoutMs || 60000;
    const intervalMs = opts.intervalMs || 3000;
    const onStatus = opts.onStatus || (() => {});

    return new Promise((resolve) => {
      let settled = false;
      const finish = (payment) => {
        if (settled) return;
        settled = true;
        clearInterval(timer);
        sub?.unsubscribe?.();
        resolve(payment);
      };

      // Realtime subscription
      const sub = subscribeToPayment(transactionId, (payment) => {
        onStatus(payment.status);
        if (payment.status === 'completed' || payment.status === 'failed') {
          finish(payment);
        }
      });

      // Polling fallback
      const timer = setInterval(async () => {
        const payment = await getPaymentStatus(transactionId);
        if (payment) {
          onStatus(payment.status);
          if (payment.status === 'completed' || payment.status === 'failed') {
            finish(payment);
          }
        }
      }, intervalMs);

      // Timeout
      setTimeout(() => {
        finish(null);
      }, timeoutMs);
    });
  }

  // ── UI Helper: show payment status toast during processing ──
  window.MWAROKIN_PAYMENTS = window.MWAROKIN_PAYMENTS || {};
  const origCreatePayment = window.MWAROKIN_PAYMENTS.createPayment;

  if (origCreatePayment) {
    window.MWAROKIN_PAYMENTS.createPayment = async function (opts) {
      const result = await origCreatePayment(opts);
      if (result.success && result.data?.payment) {
        const payment = result.data.payment;
        if (payment.status === 'processing' && payment.transaction_id) {
          window.toast('Payment processing. Please wait...', 'info');
          waitForPayment(payment.transaction_id, {
            timeoutMs: 90000,
            intervalMs: 3000,
            onStatus: (status) => {
              if (status === 'completed') window.toast('Payment confirmed!', 'success');
              if (status === 'failed') window.toast('Payment failed. Please try again.', 'error');
            },
          });
        }
      }
      return result;
    };
  }
})();
