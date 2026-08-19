-- ============================================================================
-- MWAROKIN ESTATES — ROW LEVEL SECURITY POLICIES
-- Run AFTER schema.sql and functions.sql.
-- Security model:
--   anon          → can read available properties only
--   authenticated → can read/write their own records, manage their own data
--   admin/agent/landlord/caretaker → role-based management via helper
-- ============================================================================

-- Helper: is the current user an admin?
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'
  );
$$ LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public;

-- Helper: is the current user admin or agent?
CREATE OR REPLACE FUNCTION public.is_staff()
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM profiles WHERE id = auth.uid() AND role IN ('admin','agent')
  );
$$ LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public;

-- Helper: is the current user admin, agent, landlord or caretaker?
CREATE OR REPLACE FUNCTION public.is_staff_landlord()
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM profiles WHERE id = auth.uid() AND role IN ('admin','agent','landlord','caretaker')
  );
$$ LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public;

-- ============================================================================
-- ENABLE RLS
-- ============================================================================
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE leases ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE communication_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_behavior ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE prospects ENABLE ROW LEVEL SECURITY;
ALTER TABLE outreach_campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE outreach_threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE translations ENABLE ROW LEVEL SECURITY;
ALTER TABLE exchange_rates ENABLE ROW LEVEL SECURITY;
ALTER TABLE supported_languages ENABLE ROW LEVEL SECURITY;
ALTER TABLE supported_currencies ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- PROFILES
-- ============================================================================
DROP POLICY IF EXISTS "profiles_select" ON profiles;
CREATE POLICY "profiles_select" ON profiles FOR SELECT
  TO authenticated USING (true);

DROP POLICY IF EXISTS "profiles_update_own" ON profiles;
CREATE POLICY "profiles_update_own" ON profiles FOR UPDATE
  TO authenticated USING (auth.uid() = id) WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "profiles_insert_own" ON profiles;
CREATE POLICY "profiles_insert_own" ON profiles FOR INSERT
  TO authenticated WITH CHECK (auth.uid() = id);

-- ============================================================================
-- PROPERTIES
-- ============================================================================
DROP POLICY IF EXISTS "properties_public_read" ON properties;
CREATE POLICY "properties_public_read" ON properties FOR SELECT
  TO anon, authenticated
  USING (status = 'available' OR is_staff_landlord());

DROP POLICY IF EXISTS "properties_staff_write" ON properties;
CREATE POLICY "properties_staff_write" ON properties FOR ALL
  TO authenticated
  USING (is_staff()) WITH CHECK (is_staff());

-- ============================================================================
-- TENANTS
-- ============================================================================
DROP POLICY IF EXISTS "tenants_select_own" ON tenants;
CREATE POLICY "tenants_select_own" ON tenants FOR SELECT
  TO authenticated
  USING (user_id = auth.uid() OR is_staff_landlord());

DROP POLICY IF EXISTS "tenants_write_staff" ON tenants;
CREATE POLICY "tenants_write_staff" ON tenants FOR ALL
  TO authenticated
  USING (is_staff()) WITH CHECK (is_staff());

-- ============================================================================
-- LEASES
-- ============================================================================
DROP POLICY IF EXISTS "leases_select" ON leases;
CREATE POLICY "leases_select" ON leases FOR SELECT
  TO authenticated
  USING (landlord_id = auth.uid()
      OR tenant_id IN (SELECT id FROM tenants WHERE user_id = auth.uid())
      OR is_staff());

DROP POLICY IF EXISTS "leases_write_staff" ON leases;
CREATE POLICY "leases_write_staff" ON leases FOR ALL
  TO authenticated
  USING (is_staff() OR landlord_id = auth.uid()) WITH CHECK (is_staff() OR landlord_id = auth.uid());

-- ============================================================================
-- PAYMENTS
-- ============================================================================
DROP POLICY IF EXISTS "payments_select" ON payments;
CREATE POLICY "payments_select" ON payments FOR SELECT
  TO authenticated
  USING (tenant_id IN (SELECT id FROM tenants WHERE user_id = auth.uid())
      OR landlord_id = auth.uid()
      OR is_staff());

DROP POLICY IF EXISTS "payments_insert_self" ON payments;
CREATE POLICY "payments_insert_self" ON payments FOR INSERT
  TO authenticated
  WITH CHECK (true); -- amount & split are validated server-side by trigger + RLS on update

DROP POLICY IF EXISTS "payments_update_staff" ON payments;
CREATE POLICY "payments_update_staff" ON payments FOR UPDATE
  TO authenticated
  USING (is_staff()) WITH CHECK (is_staff());

-- ============================================================================
-- MAINTENANCE REQUESTS
-- ============================================================================
DROP POLICY IF EXISTS "maintenance_insert_tenant" ON maintenance_requests;
CREATE POLICY "maintenance_insert_tenant" ON maintenance_requests FOR INSERT
  TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "maintenance_select" ON maintenance_requests;
CREATE POLICY "maintenance_select" ON maintenance_requests FOR SELECT
  TO authenticated
  USING (tenant_id IN (SELECT id FROM tenants WHERE user_id = auth.uid()) OR is_staff_landlord());

DROP POLICY IF EXISTS "maintenance_update_staff" ON maintenance_requests;
CREATE POLICY "maintenance_update_staff" ON maintenance_requests FOR UPDATE
  TO authenticated
  USING (is_staff_landlord()) WITH CHECK (is_staff_landlord());

-- ============================================================================
-- DOCUMENTS
-- ============================================================================
DROP POLICY IF EXISTS "documents_select" ON documents;
CREATE POLICY "documents_select" ON documents FOR SELECT
  TO authenticated
  USING (tenant_id IN (SELECT id FROM tenants WHERE user_id = auth.uid())
      OR uploaded_by = auth.uid() OR is_staff());

DROP POLICY IF EXISTS "documents_write" ON documents;
CREATE POLICY "documents_write" ON documents FOR ALL
  TO authenticated
  USING (uploaded_by = auth.uid() OR is_staff()) WITH CHECK (uploaded_by = auth.uid() OR is_staff());

-- ============================================================================
-- COMMUNICATION PROFILES
-- ============================================================================
DROP POLICY IF EXISTS "comm_profiles_select_own" ON communication_profiles;
CREATE POLICY "comm_profiles_select_own" ON communication_profiles FOR SELECT
  TO authenticated USING (user_id = auth.uid());

DROP POLICY IF EXISTS "comm_profiles_write_own" ON communication_profiles;
CREATE POLICY "comm_profiles_write_own" ON communication_profiles FOR ALL
  TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

-- ============================================================================
-- MESSAGE QUEUE
-- ============================================================================
DROP POLICY IF EXISTS "message_queue_select" ON message_queue;
CREATE POLICY "message_queue_select" ON message_queue FOR SELECT
  TO authenticated USING (recipient_id = auth.uid() OR sender_id = auth.uid());

DROP POLICY IF EXISTS "message_queue_insert" ON message_queue;
CREATE POLICY "message_queue_insert" ON message_queue FOR INSERT
  TO authenticated WITH CHECK (true);

-- ============================================================================
-- NOTIFICATIONS
-- ============================================================================
DROP POLICY IF EXISTS "notifications_select" ON notifications;
CREATE POLICY "notifications_select" ON notifications FOR SELECT
  TO authenticated USING (user_id = auth.uid());

DROP POLICY IF EXISTS "notifications_update" ON notifications;
CREATE POLICY "notifications_update" ON notifications FOR UPDATE
  TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

-- ============================================================================
-- USER BEHAVIOR
-- ============================================================================
DROP POLICY IF EXISTS "behavior_insert_own" ON user_behavior;
CREATE POLICY "behavior_insert_own" ON user_behavior FOR INSERT
  TO authenticated WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "behavior_select_own" ON user_behavior;
CREATE POLICY "behavior_select_own" ON user_behavior FOR SELECT
  TO authenticated USING (user_id = auth.uid());

-- ============================================================================
-- AUDIT LOGS
-- ============================================================================
DROP POLICY IF EXISTS "audit_insert" ON audit_logs;
CREATE POLICY "audit_insert" ON audit_logs FOR INSERT
  TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "audit_select_staff" ON audit_logs;
CREATE POLICY "audit_select_staff" ON audit_logs FOR SELECT
  TO authenticated USING (is_admin());

-- ============================================================================
-- AI LEADS / OUTREACH
-- ============================================================================
DROP POLICY IF EXISTS "prospects_staff" ON prospects;
CREATE POLICY "prospects_staff" ON prospects FOR ALL
  TO authenticated USING (is_staff()) WITH CHECK (is_staff());

DROP POLICY IF EXISTS "campaigns_staff" ON outreach_campaigns;
CREATE POLICY "campaigns_staff" ON outreach_campaigns FOR ALL
  TO authenticated USING (is_staff()) WITH CHECK (is_staff());

DROP POLICY IF EXISTS "threads_staff" ON outreach_threads;
CREATE POLICY "threads_staff" ON outreach_threads FOR ALL
  TO authenticated USING (is_staff()) WITH CHECK (is_staff());

-- ============================================================================
-- i18n & CURRENCY (public read)
-- ============================================================================
DROP POLICY IF EXISTS "langs_public" ON supported_languages;
CREATE POLICY "langs_public" ON supported_languages FOR SELECT TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "currencies_public" ON supported_currencies;
CREATE POLICY "currencies_public" ON supported_currencies FOR SELECT TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "translations_public" ON translations;
CREATE POLICY "translations_public" ON translations FOR SELECT TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "rates_public" ON exchange_rates;
CREATE POLICY "rates_public" ON exchange_rates FOR SELECT TO anon, authenticated USING (true);
