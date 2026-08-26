-- ============================================================
-- Mwarokin Estates — Add Missing Tables from DATABASE_SCHEMA.md
-- Production already has: profiles, properties, units, tenants,
--   leases, payments, landlords, caretakers (with RLS + RPCs)
-- This migration adds: fee_config, revenue_ledger, bank_accounts,
--   cash_flow, coop_groups, subscriptions, sta_subscriptions,
--   ai_tasks, knowledge_entries, campaigns, analytics_events,
--   compliance_items, audit_log, and update_updated_at trigger
-- ============================================================

-- 0. Helper: updated_at trigger function
CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 1. Fee Configuration (1-5-10 KSh tiers)
CREATE TABLE IF NOT EXISTS public.fee_config (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain TEXT NOT NULL CHECK (domain IN ('mwarokin','maliaccessunion','sta','financial_advisory')),
  tier TEXT NOT NULL CHECK (tier IN ('basic','standard','premium','enterprise','coop','financial')),
  transaction_type TEXT NOT NULL,
  min_fee_ksh NUMERIC(10,2) NOT NULL,
  max_fee_ksh NUMERIC(10,2) NOT NULL,
  platform_pct NUMERIC(5,2) NOT NULL DEFAULT 0,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 2. Revenue Ledger
CREATE TABLE IF NOT EXISTS public.revenue_ledger (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain TEXT NOT NULL,
  transaction_id UUID REFERENCES public.payments(id),
  fee_amount NUMERIC(10,2) NOT NULL,
  settlement_amount NUMERIC(10,2) NOT NULL,
  landlord_account TEXT,
  platform_revenue NUMERIC(10,2) NOT NULL,
  bank_name TEXT DEFAULT 'Co-op Bank',
  bank_account TEXT DEFAULT '01192643932500',
  account_holder TEXT DEFAULT 'Robin B. Mwarema',
  reconciliation_status TEXT DEFAULT 'pending',
  reconciled_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TRIGGER update_revenue_ledger_updated_at
  BEFORE UPDATE ON public.revenue_ledger
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- 3. Bank Accounts (seeded with Co-op + Equity)
CREATE TABLE IF NOT EXISTS public.bank_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_name TEXT NOT NULL,
  bank_name TEXT NOT NULL,
  bank_url TEXT,
  account_number TEXT NOT NULL,
  account_holder TEXT NOT NULL,
  account_type TEXT CHECK (account_type IN ('business','settlement','operating','savings','personal')),
  domain TEXT NOT NULL,
  is_primary BOOLEAN DEFAULT false,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

INSERT INTO public.bank_accounts (account_name, bank_name, bank_url, account_number, account_holder, account_type, domain, is_primary)
VALUES
  ('STA Revenue Account', 'Co-op Bank', 'https://www.co-opbank.co.ke/', '01192643932500', 'Robin B. Mwarema', 'business', 'sta', true),
  ('CEO Personal Account', 'Equity Bank', 'https://equitygroupholdings.com/ke/', '0730178466611', 'Robin Mwarema', 'personal', 'sta', false)
ON CONFLICT DO NOTHING;

-- 4. Cash Flow
CREATE TABLE IF NOT EXISTS public.cash_flow (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bank_account_id UUID REFERENCES public.bank_accounts(id),
  flow_type TEXT CHECK (flow_type IN ('inbound','outbound','transfer')),
  amount NUMERIC(12,2) NOT NULL,
  currency TEXT DEFAULT 'KES',
  reference TEXT NOT NULL,
  description TEXT,
  linked_transaction_id UUID,
  reconciliation_status TEXT DEFAULT 'pending',
  reconciled_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 5. Co-op Groups (Mali Access Union)
CREATE TABLE IF NOT EXISTS public.coop_groups (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  group_name TEXT NOT NULL,
  domain TEXT DEFAULT 'maliaccessunion',
  member_count INT DEFAULT 0,
  total_savings NUMERIC(12,2) DEFAULT 0,
  group_type TEXT CHECK (group_type IN ('chama','rosca','emergency','loan')),
  bank_account_id UUID REFERENCES public.bank_accounts(id),
  status TEXT DEFAULT 'active',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 6. Subscriptions (domain-specific)
CREATE TABLE IF NOT EXISTS public.subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.profiles(id),
  domain TEXT NOT NULL,
  tier TEXT NOT NULL,
  monthly_fee_ksh NUMERIC(10,2) NOT NULL,
  features JSONB DEFAULT '{}',
  status TEXT DEFAULT 'active' CHECK (status IN ('active','expired','cancelled','pending')),
  billing_cycle TEXT DEFAULT 'monthly',
  next_billing_date DATE,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TRIGGER update_subscriptions_updated_at
  BEFORE UPDATE ON public.subscriptions
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- 7. STA Internal Subscriptions (hosting, licenses, services)
CREATE TABLE IF NOT EXISTS public.sta_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  service_name TEXT NOT NULL,
  service_category TEXT CHECK (service_category IN ('internal','customer')),
  billing_cycle TEXT CHECK (billing_cycle IN ('monthly','annual','one-time')),
  amount_ksh NUMERIC(10,2),
  currency TEXT DEFAULT 'KES',
  account_reference TEXT,
  next_billing_date DATE,
  last_billing_date DATE,
  status TEXT DEFAULT 'active',
  auto_renew BOOLEAN DEFAULT false,
  alert_days_before INT DEFAULT 7,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TRIGGER update_sta_subscriptions_updated_at
  BEFORE UPDATE ON public.sta_subscriptions
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- 8. AI Tasks
CREATE TABLE IF NOT EXISTS public.ai_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_name TEXT NOT NULL,
  task_type TEXT NOT NULL,
  input JSONB NOT NULL,
  output JSONB,
  model_used TEXT,
  tokens_used INT,
  execution_time_ms INT,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending','running','completed','failed')),
  created_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ
);

-- 9. Knowledge Entries
CREATE TABLE IF NOT EXISTS public.knowledge_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  category TEXT NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  source TEXT,
  tags TEXT[] DEFAULT '{}',
  confidence NUMERIC(3,2) DEFAULT 0.5,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TRIGGER update_knowledge_entries_updated_at
  BEFORE UPDATE ON public.knowledge_entries
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- 10. Marketing Campaigns
CREATE TABLE IF NOT EXISTS public.campaigns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  channel TEXT CHECK (channel IN ('email','social','whatsapp','sms','ads')),
  template TEXT,
  target_audience JSONB,
  status TEXT DEFAULT 'draft' CHECK (status IN ('draft','scheduled','sent','cancelled')),
  sent_count INT DEFAULT 0,
  open_count INT DEFAULT 0,
  click_count INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 11. Analytics Events
CREATE TABLE IF NOT EXISTS public.analytics_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type TEXT NOT NULL,
  domain TEXT,
  user_id UUID,
  properties JSONB DEFAULT '{}',
  session_id TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 12. Compliance Items
CREATE TABLE IF NOT EXISTS public.compliance_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_type TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending','in_progress','completed','overdue')),
  priority TEXT DEFAULT 'medium' CHECK (priority IN ('critical','high','medium','low')),
  due_date DATE,
  completed_at TIMESTAMPTZ,
  document_url TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 13. Audit Log
CREATE TABLE IF NOT EXISTS public.audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID,
  action TEXT NOT NULL,
  resource_type TEXT,
  resource_id UUID,
  old_value JSONB,
  new_value JSONB,
  ip_address TEXT,
  user_agent TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- INDEXES
-- ============================================================

-- Fee config
CREATE INDEX IF NOT EXISTS idx_fee_config_lookup ON public.fee_config(domain, tier, transaction_type) WHERE is_active = true;

-- Revenue
CREATE INDEX IF NOT EXISTS idx_revenue_date ON public.revenue_ledger(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_revenue_domain ON public.revenue_ledger(domain, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_revenue_bank ON public.revenue_ledger(bank_account, reconciliation_status);

-- Cash flow
CREATE INDEX IF NOT EXISTS idx_cash_flow_account ON public.cash_flow(bank_account_id, created_at);
CREATE INDEX IF NOT EXISTS idx_cash_flow_recon ON public.cash_flow(reconciliation_status);

-- Co-op groups
CREATE INDEX IF NOT EXISTS idx_coop_groups_domain ON public.coop_groups(domain, status);

-- Subscriptions
CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON public.subscriptions(user_id, domain);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON public.subscriptions(status, next_billing_date);
CREATE INDEX IF NOT EXISTS idx_sta_sub_status ON public.sta_subscriptions(status, next_billing_date);

-- AI
CREATE INDEX IF NOT EXISTS idx_ai_tasks_agent ON public.ai_tasks(agent_name, status);
CREATE INDEX IF NOT EXISTS idx_knowledge_category ON public.knowledge_entries(category, confidence DESC);

-- Analytics
CREATE INDEX IF NOT EXISTS idx_analytics_type ON public.analytics_events(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_domain ON public.analytics_events(domain, created_at DESC);

-- Audit
CREATE INDEX IF NOT EXISTS idx_audit_user ON public.audit_log(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON public.audit_log(resource_type, resource_id);

-- ============================================================
-- ROW-LEVEL SECURITY (RLS)
-- ============================================================

ALTER TABLE public.fee_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.revenue_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bank_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cash_flow ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.coop_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sta_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.compliance_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;

-- Fee config: public read
CREATE POLICY "Fee config read" ON public.fee_config FOR SELECT USING (true);

-- Revenue: admin only
CREATE POLICY "Revenue admin" ON public.revenue_ledger FOR SELECT USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
);

-- Bank accounts: admin only
CREATE POLICY "Bank admin" ON public.bank_accounts FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
);

-- Cash flow: admin only
CREATE POLICY "Cash flow admin" ON public.cash_flow FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
);

-- Co-op groups: authenticated read, manage by members
CREATE POLICY "Coop read" ON public.coop_groups FOR SELECT USING (auth.role() = 'authenticated');

-- Subscriptions: users read own
CREATE POLICY "Subscriptions own read" ON public.subscriptions FOR SELECT USING (
  auth.uid() = user_id
);

-- STA subscriptions: admin only
CREATE POLICY "STA sub admin" ON public.sta_subscriptions FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
);

-- AI tasks: admin only
CREATE POLICY "AI tasks admin" ON public.ai_tasks FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
);

-- Knowledge: authenticated read
CREATE POLICY "Knowledge read" ON public.knowledge_entries FOR SELECT USING (auth.role() = 'authenticated');

-- Campaigns: admin only
CREATE POLICY "Campaigns admin" ON public.campaigns FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
);

-- Analytics: admin only
CREATE POLICY "Analytics admin" ON public.analytics_events FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
);

-- Compliance: admin only
CREATE POLICY "Compliance admin" ON public.compliance_items FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
);

-- Audit: admin only
CREATE POLICY "Audit admin" ON public.audit_log FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
);

-- ============================================================
-- SEED: Default fee configuration (1-5-10 KSh tiers)
-- ============================================================

INSERT INTO public.fee_config (domain, tier, transaction_type, min_fee_ksh, max_fee_ksh, platform_pct)
VALUES
  -- Mwarokin Estates
  ('mwarokin', 'basic', 'rent_payment', 1, 5, 2.5),
  ('mwarokin', 'standard', 'rent_payment', 5, 10, 2.0),
  ('mwarokin', 'premium', 'rent_payment', 10, 50, 1.5),
  ('mwarokin', 'basic', 'booking', 1, 5, 3.0),
  ('mwarokin', 'standard', 'booking', 5, 10, 2.5),
  ('mwarokin', 'premium', 'booking', 10, 50, 2.0),

  -- Mali Access Union
  ('maliaccessunion', 'basic', 'savings', 1, 5, 1.0),
  ('maliaccessunion', 'standard', 'savings', 5, 10, 1.5),
  ('maliaccessunion', 'coop', 'loan', 1, 5, 2.0),

  -- STA Platform
  ('sta', 'basic', 'subscription', 1, 5, 5.0),
  ('sta', 'standard', 'subscription', 5, 10, 4.0),
  ('sta', 'premium', 'subscription', 10, 50, 3.0),

  -- Financial Advisory
  ('financial_advisory', 'basic', 'advisory', 1, 5, 10.0),
  ('financial_advisory', 'financial', 'advisory', 5, 10, 8.0),
  ('financial_advisory', 'enterprise', 'advisory', 10, 50, 5.0)
ON CONFLICT DO NOTHING;
