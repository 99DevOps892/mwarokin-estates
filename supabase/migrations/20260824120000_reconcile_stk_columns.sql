-- ============================================================
-- Mwarokin Estates — Reconcile with live schema (2026-08-24)
-- The production DB already contains the full schema: tables, RLS,
-- split trigger (calculate_payment_split), RPCs (get_dashboard_stats,
-- approve/reject_payment, increment_property_views,
-- get_high_intent_prospects, create_notification), seeds.
-- This migration ONLY adds what the M-Pesa STK flow requires:
--   payments.checkout_request_id  (Daraja callback matching)
--   payments.paid_at              (accurate settlement timestamp)
-- Everything else is intentionally left untouched.
-- ============================================================

alter table public.payments
  add column if not exists checkout_request_id text;

alter table public.payments
  add column if not exists paid_at timestamptz;

create index if not exists idx_payments_checkout_request
  on public.payments (checkout_request_id)
  where checkout_request_id is not null;
