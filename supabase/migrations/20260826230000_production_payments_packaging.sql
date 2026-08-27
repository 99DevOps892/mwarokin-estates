-- ============================================================
-- Migration: Production Payment Packaging
-- Adds Airtel Money + Flutterwave (bank/card) support,
-- payment idempotency, webhook audit trail, and refund tracking.
-- Project: spnerrqumefbuuscumhw
-- Date: 2026-08-26
-- ============================================================

-- 1. Extend payment_method CHECK to include airtel-money and card
ALTER TABLE payments DROP CONSTRAINT IF EXISTS payments_payment_method_check;
ALTER TABLE payments ADD CONSTRAINT payments_payment_method_check
  CHECK (payment_method IN ('mpesa','airtel-money','bank-transfer','card','cash'));

-- 2. Add columns for multi-provider support
ALTER TABLE payments ADD COLUMN IF NOT EXISTS provider TEXT DEFAULT 'internal';
ALTER TABLE payments ADD COLUMN IF NOT EXISTS idempotency_key TEXT UNIQUE;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS webhook_verified BOOLEAN DEFAULT false;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS refund_status TEXT DEFAULT 'none'
  CHECK (refund_status IN ('none','requested','processing','completed','failed'));
ALTER TABLE payments ADD COLUMN IF NOT EXISTS refund_reference TEXT;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS refund_amount NUMERIC(12,2);
ALTER TABLE payments ADD COLUMN IF NOT EXISTS refund_date TIMESTAMPTZ;

-- 3. Index for idempotency lookups
CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_idempotency
  ON payments(idempotency_key) WHERE idempotency_key IS NOT NULL;

-- 4. Webhook audit trail
CREATE TABLE IF NOT EXISTS webhook_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  payment_id UUID REFERENCES payments(id),
  processed BOOLEAN DEFAULT false,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE webhook_events ENABLE ROW LEVEL SECURITY;

-- Only service role can access webhook events
CREATE POLICY "Webhook events admin only" ON webhook_events
  FOR ALL USING (auth.role() = 'service_role');

CREATE INDEX IF NOT EXISTS idx_webhook_events_provider
  ON webhook_events(provider, event_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_webhook_events_payment
  ON webhook_events(payment_id) WHERE payment_id IS NOT NULL;

-- 5. Payment audit log (replaces ad-hoc audit_logs inserts for payments)
CREATE TABLE IF NOT EXISTS payment_audit (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  payment_id UUID REFERENCES payments(id) ON DELETE CASCADE,
  action TEXT NOT NULL,
  old_status TEXT,
  new_status TEXT,
  actor TEXT DEFAULT 'system',
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE payment_audit ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Payment audit admin" ON payment_audit
  FOR SELECT USING (
    auth.uid() IN (SELECT id FROM profiles WHERE role IN ('admin','superadmin'))
  );

CREATE INDEX IF NOT EXISTS idx_payment_audit_payment
  ON payment_audit(payment_id, created_at DESC);

-- 6. RPC: get payment by idempotency key (prevents duplicates)
CREATE OR REPLACE FUNCTION get_payment_by_idempotency(p_key TEXT)
RETURNS payments AS $$
  SELECT * FROM payments WHERE idempotency_key = p_key LIMIT 1;
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- 7. RPC: log payment audit entry
CREATE OR REPLACE FUNCTION log_payment_audit(
  p_payment_id UUID,
  p_action TEXT,
  p_old_status TEXT DEFAULT NULL,
  p_new_status TEXT DEFAULT NULL,
  p_actor TEXT DEFAULT 'system',
  p_metadata JSONB DEFAULT '{}'
)
RETURNS VOID AS $$
BEGIN
  INSERT INTO payment_audit (payment_id, action, old_status, new_status, actor, metadata)
  VALUES (p_payment_id, p_action, p_old_status, p_new_status, p_actor, p_metadata);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 8. RPC: process refund (updates payment + creates audit entry)
CREATE OR REPLACE FUNCTION process_refund(
  p_payment_id UUID,
  p_refund_reference TEXT,
  p_refund_amount NUMERIC(12,2)
)
RETURNS VOID AS $$
DECLARE
  v_old_status TEXT;
BEGIN
  SELECT status INTO v_old_status FROM payments WHERE id = p_payment_id;
  UPDATE payments SET
    refund_status = 'completed',
    refund_reference = p_refund_reference,
    refund_amount = p_refund_amount,
    refund_date = now(),
    updated_at = now()
  WHERE id = p_payment_id;

  PERFORM log_payment_audit(
    p_payment_id, 'refund.completed', v_old_status, 'refunded', 'system',
    jsonb_build_object('refund_reference', p_refund_reference, 'refund_amount', p_refund_amount)
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
