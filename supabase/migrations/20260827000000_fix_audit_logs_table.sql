-- ============================================================
-- Mwarokin Estates — Fix: audit_logs (plural) table
-- ------------------------------------------------------------
-- Edge functions (payments, mpesa-callback, etc.) write audit rows to
-- `public.audit_logs` (plural) with columns: user_id, action, table_name,
-- record_id, new_data. The earlier migration created `public.audit_log`
-- (singular) with different columns, so function inserts could 500.
-- This additive migration creates the table the functions actually use.
-- Additive only: CREATE ... IF NOT EXISTS. Safe to re-run.
-- ============================================================

CREATE TABLE IF NOT EXISTS public.audit_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    action      TEXT NOT NULL,
    table_name  TEXT,
    record_id   UUID,
    new_data    JSONB DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user   ON public.audit_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON public.audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_record ON public.audit_logs(record_id);

ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- Audit rows are written by edge functions (service role); admins may read.
CREATE POLICY "Audit logs admin read" ON public.audit_logs
    FOR SELECT USING (
        auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
    );

-- Service role bypasses RLS; only allow admins to insert via normal JWT.
CREATE POLICY "Audit logs admin write" ON public.audit_logs
    FOR INSERT WITH CHECK (
        auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
    );
