-- ============================================================
-- PAYMENTS TABLE — Airtel / M-Pesa STK Push
-- Project: spnerrqumefbuuscumhw (Supabase)
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── ENUM types ──────────────────────────────────────────────
CREATE TYPE payment_method   AS ENUM ('mpesa', 'airtel', 'card', 'bank');
CREATE TYPE payment_status   AS ENUM ('pending', 'processing', 'success', 'failed', 'cancelled', 'expired', 'reversed');
CREATE TYPE payment_env      AS ENUM ('sandbox', 'production');

-- ── Main payments table ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS payments (
  id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

  -- Core fields
  amount           INTEGER      NOT NULL CHECK (amount > 0),
  currency         VARCHAR(3)   NOT NULL DEFAULT 'KES',
  method           payment_method NOT NULL,
  status           payment_status NOT NULL DEFAULT 'pending',

  -- Provider references
  provider_ref     TEXT         UNIQUE,              -- CheckoutRequestID (M-Pesa) or TransactionID (Airtel)
  mpesa_receipt    TEXT,                             -- M-Pesa receipt / Airtel receipt
  phone            VARCHAR(15)  NOT NULL,

  -- Amount tracking
  paid_amount      INTEGER,                          -- Actual amount debited
  status_reason    TEXT,

  -- Supabase auth link (nullable for guest payments)
  user_id          UUID         REFERENCES auth.users(id),

  -- Transaction context
  account_ref      VARCHAR(12)  DEFAULT 'Payment',
  transaction_desc VARCHAR(128) DEFAULT 'Payment',

  -- Environment
  env              payment_env  NOT NULL DEFAULT 'sandbox',

  -- Flexible metadata blob (provider-specific details)
  metadata         JSONB        DEFAULT '{}'::jsonb,

  -- Timestamps
  created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),

  -- Soft-delete / reversal tracking
  reversed_at      TIMESTAMPTZ,
  reversal_reason  TEXT
);

-- ── Indexes ─────────────────────────────────────────────────
CREATE INDEX idx_payments_status       ON payments (status);
CREATE INDEX idx_payments_user_id      ON payments (user_id);
CREATE INDEX idx_payments_phone        ON payments (phone);
CREATE INDEX idx_payments_provider_ref ON payments (provider_ref);
CREATE INDEX idx_payments_created_at   ON payments (created_at DESC);
CREATE INDEX idx_payments_method       ON payments (method);

-- ── Auto-update updated_at ──────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_payments_updated_at
  BEFORE UPDATE ON payments
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

-- ── Enable Row Level Security ───────────────────────────────
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;

-- Users can read their own payments
CREATE POLICY "users_read_own_payments"
  ON payments FOR SELECT
  USING (auth.uid() = user_id);

-- Service role can do everything (Edge Functions use service key)
CREATE POLICY "service_role_all_payments"
  ON payments FOR ALL
  USING (true)
  WITH CHECK (true);

-- ── Realtime publication ─────────────────────────────────────
ALTER PUBLICATION supabase_realtime ADD TABLE payments;

-- ============================================================
-- OPTIONAL: Transaction log (audit trail)
-- ============================================================
CREATE TABLE IF NOT EXISTS payment_events (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  payment_id   UUID NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
  event_type   TEXT NOT NULL,          -- 'initiated', 'callback_received', 'status_poll', 'reversed'
  payload      JSONB DEFAULT '{}'::jsonb,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_payment_events_payment_id ON payment_events (payment_id);
CREATE INDEX idx_payment_events_created_at ON payment_events (created_at DESC);

ALTER TABLE payment_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_all_events"
  ON payment_events FOR ALL
  USING (true)
  WITH CHECK (true);

-- ============================================================
-- Convenience view: active payments
-- ============================================================
CREATE OR REPLACE VIEW active_payments AS
SELECT
  id, amount, currency, method, status, provider_ref,
  mpesa_receipt, phone, paid_amount, user_id,
  account_ref, env, created_at, updated_at
FROM payments
WHERE status IN ('pending', 'processing')
ORDER BY created_at DESC;
