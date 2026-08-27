-- ============================================================
-- Migration: Multi-App Schema for STA Ecosystem
-- Adds tables for: STA Platform, Mali Access Union, SAICOS,
-- NOESIS, Financial Advisory
-- Project: spnerrqumefbuuscumhw
-- Date: 2026-08-26
-- ============================================================

-- ═══════════════════════════════════════════════
-- 1. STA PLATFORM (sta-001) — Subscriptions
-- ═══════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS sta_platform_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  plan TEXT NOT NULL CHECK (plan IN ('basic', 'standard', 'premium', 'enterprise')),
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'cancelled', 'expired', 'trial')),
  monthly_fee_ksh NUMERIC(10,2) NOT NULL,
  features JSONB DEFAULT '{}',
  apps_access TEXT[] DEFAULT '{}',
  current_period_start TIMESTAMPTZ DEFAULT now(),
  current_period_end TIMESTAMPTZ,
  cancel_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE sta_platform_subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users view own subscription" ON sta_platform_subscriptions
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users create own subscription" ON sta_platform_subscriptions
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_sta_sub_user ON sta_platform_subscriptions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_sta_sub_plan ON sta_platform_subscriptions(plan, status);

-- ═══════════════════════════════════════════════
-- 2. MALI ACCESS UNION (sta-003) — Groups & Savings
-- ═══════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS mau_groups (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  group_type TEXT CHECK (group_type IN ('chama', 'rosca', 'emergency', 'loan')),
  max_members INT DEFAULT 20,
  contribution_amount NUMERIC(10,2) NOT NULL,
  contribution_frequency TEXT DEFAULT 'monthly' CHECK (contribution_frequency IN ('weekly', 'biweekly', 'monthly')),
  currency TEXT DEFAULT 'KES',
  created_by UUID REFERENCES profiles(id),
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused', 'closed')),
  settings JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mau_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id UUID REFERENCES mau_groups(id) ON DELETE CASCADE,
  user_id UUID REFERENCES profiles(id),
  role TEXT DEFAULT 'member' CHECK (role IN ('admin', 'treasurer', 'secretary', 'member')),
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
  joined_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(group_id, user_id)
);

CREATE TABLE IF NOT EXISTS mau_contributions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id UUID REFERENCES mau_groups(id),
  member_id UUID REFERENCES mau_members(id),
  amount NUMERIC(10,2) NOT NULL,
  payment_method TEXT CHECK (payment_method IN ('mpesa', 'airtel-money', 'bank-transfer', 'cash')),
  transaction_id TEXT,
  cycle_number INT DEFAULT 1,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'late', 'missed')),
  confirmed_by UUID REFERENCES profiles(id),
  confirmed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mau_savings_pools (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id UUID REFERENCES mau_groups(id) ON DELETE CASCADE,
  total_balance NUMERIC(12,2) DEFAULT 0,
  total_contributions NUMERIC(12,2) DEFAULT 0,
  total_withdrawals NUMERIC(12,2) DEFAULT 0,
  interest_rate NUMERIC(5,2) DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mau_loans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id UUID REFERENCES mau_groups(id),
  borrower_id UUID REFERENCES mau_members(id),
  amount NUMERIC(10,2) NOT NULL,
  interest_rate NUMERIC(5,2) DEFAULT 0,
  term_months INT DEFAULT 3,
  purpose TEXT,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'disbursed', 'repaying', 'completed', 'defaulted')),
  approved_by UUID REFERENCES profiles(id),
  disbursed_at TIMESTAMPTZ,
  due_date DATE,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE mau_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE mau_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE mau_contributions ENABLE ROW LEVEL SECURITY;
ALTER TABLE mau_savings_pools ENABLE ROW LEVEL SECURITY;
ALTER TABLE mau_loans ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Groups public read" ON mau_groups FOR SELECT USING (status = 'active');
CREATE POLICY "Group creators manage" ON mau_groups FOR ALL USING (auth.uid() = created_by);
CREATE POLICY "Members read own groups" ON mau_members FOR SELECT USING (
  user_id = auth.uid() OR group_id IN (SELECT group_id FROM mau_members WHERE user_id = auth.uid())
);
CREATE POLICY "Members insert own" ON mau_members FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "Contributions members read" ON mau_contributions FOR SELECT USING (
  member_id IN (SELECT id FROM mau_members WHERE user_id = auth.uid())
);
CREATE POLICY "Contributions members insert" ON mau_contributions FOR INSERT WITH CHECK (
  member_id IN (SELECT id FROM mau_members WHERE user_id = auth.uid())
);
CREATE POLICY "Savings pools group read" ON mau_savings_pools FOR SELECT USING (
  group_id IN (SELECT group_id FROM mau_members WHERE user_id = auth.uid())
);
CREATE POLICY "Loans members read" ON mau_loans FOR SELECT USING (
  borrower_id IN (SELECT id FROM mau_members WHERE user_id = auth.uid())
  OR group_id IN (SELECT group_id FROM mau_members WHERE user_id = auth.uid() AND role IN ('admin', 'treasurer'))
);

CREATE INDEX IF NOT EXISTS idx_mau_members_group ON mau_members(group_id, status);
CREATE INDEX IF NOT EXISTS idx_mau_members_user ON mau_members(user_id);
CREATE INDEX IF NOT EXISTS idx_mau_contributions_group ON mau_contributions(group_id, cycle_number);
CREATE INDEX IF NOT EXISTS idx_mau_loans_group ON mau_loans(group_id, status);
CREATE INDEX IF NOT EXISTS idx_mau_loans_borrower ON mau_loans(borrower_id);

-- ═══════════════════════════════════════════════
-- 3. SAICOS (sta-005) — Agent Registry & Events
-- ═══════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS saicos_agent_registry (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id TEXT UNIQUE NOT NULL,
  agent_name TEXT NOT NULL,
  domain TEXT NOT NULL,
  model TEXT NOT NULL,
  skills TEXT[] DEFAULT '{}',
  endpoint TEXT,
  rate_limit INT DEFAULT 100,
  timeout_ms INT DEFAULT 15000,
  status TEXT DEFAULT 'offline' CHECK (status IN ('online', 'offline', 'error', 'maintenance')),
  last_heartbeat TIMESTAMPTZ,
  metrics JSONB DEFAULT '{"tasks_completed": 0, "tasks_failed": 0, "avg_response_ms": 0}',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS saicos_agent_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type TEXT NOT NULL,
  source_agent_id TEXT,
  target_agent_id TEXT,
  payload JSONB DEFAULT '{}',
  severity TEXT DEFAULT 'info' CHECK (severity IN ('info', 'warning', 'error', 'critical')),
  processed BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS saicos_agent_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id TEXT NOT NULL,
  task_type TEXT NOT NULL,
  input JSONB NOT NULL,
  output JSONB,
  status TEXT DEFAULT 'queued' CHECK (status IN ('queued', 'assigned', 'running', 'completed', 'failed')),
  priority INT DEFAULT 5,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE saicos_agent_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE saicos_agent_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE saicos_agent_tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Agent registry admin read" ON saicos_agent_registry FOR SELECT USING (
  auth.uid() IN (SELECT id FROM profiles WHERE role IN ('admin', 'superadmin'))
);
CREATE POLICY "Agent events admin read" ON saicos_agent_events FOR SELECT USING (
  auth.uid() IN (SELECT id FROM profiles WHERE role IN ('admin', 'superadmin'))
);
CREATE POLICY "Agent tasks admin read" ON saicos_agent_tasks FOR SELECT USING (
  auth.uid() IN (SELECT id FROM profiles WHERE role IN ('admin', 'superadmin'))
);
CREATE POLICY "Agent tasks service insert" ON saicos_agent_tasks FOR INSERT WITH CHECK (auth.role() = 'service_role');

CREATE INDEX IF NOT EXISTS idx_saicos_events_type ON saicos_agent_events(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_saicos_events_agent ON saicos_agent_events(source_agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_saicos_tasks_agent ON saicos_agent_tasks(agent_id, status);
CREATE INDEX IF NOT EXISTS idx_saicos_tasks_status ON saicos_agent_tasks(status, priority DESC);

-- Seed agent registry
INSERT INTO saicos_agent_registry (agent_id, agent_name, domain, model, skills, endpoint, rate_limit) VALUES
  ('mwarokin-001', 'Property Search Agent', 'mwarokin', 'qwen3:8b', ARRAY['property_search', 'location_match', 'price_filter'], '/functions/v1/agent-brain', 100),
  ('mwarokin-002', 'Tenant Screening Agent', 'mwarokin', 'gemma3:4b', ARRAY['credit_check', 'id_verify', 'reference_check'], '/functions/v1/agent-brain', 50),
  ('mwarokin-003', 'Payment Processing Agent', 'mwarokin', 'llama3.2:3b', ARRAY['mpesa_stk', 'payment_split', 'receipt_generate'], '/functions/v1/payments', 20),
  ('mwarokin-004', 'Maintenance Agent', 'mwarokin', 'qwen3:8b', ARRAY['ticket_routing', 'priority_scoring', 'technician_match'], '/functions/v1/agent-brain', 50),
  ('mwarokin-005', 'Document Agent', 'mwarokin', 'gemma3:4b', ARRAY['lease_gen', 'compliance_check', 'document_store'], '/functions/v1/agent-brain', 30),
  ('syllopay-001', 'Transaction Agent', 'syllopay', 'qwen3:8b', ARRAY['payment_routing', 'fee_calculation', 'settlement'], '/functions/v1/process-fee', 100),
  ('syllopay-002', 'Fraud Detection Agent', 'syllopay', 'gemma3:4b', ARRAY['anomaly_detection', 'risk_scoring', 'alert_generate'], '/functions/v1/agent-brain', 1000),
  ('saicos-001', 'Intelligence Agent', 'saicos', 'qwen3:8b', ARRAY['market_analysis', 'lead_scoring', 'trend_detect'], '/functions/v1/agent-brain', 10),
  ('saicos-002', 'Outreach Agent', 'saicos', 'llama3.2:3b', ARRAY['whatsapp_outreach', 'sms_send', 'email_send'], '/functions/v1/agent-brain', 10),
  ('noesis-001', 'Knowledge Agent', 'noesis', 'qwen3:8b', ARRAY['rag_search', 'context_injection', 'fact_check'], '/functions/v1/agent-brain', 200),
  ('noesis-002', 'Reasoning Agent', 'noesis', 'qwen3:8b', ARRAY['syllogistic_reasoning', 'chain_of_thought', 'logical_inference'], '/functions/v1/agent-brain', 50),
  ('ceo-001', 'Executive Summary Agent', 'sta', 'qwen3:8b', ARRAY['daily_brief', 'kpi_tracking', 'alert_generation'], '/functions/v1/ceo-briefing', 4),
  ('ceo-002', 'Notification Agent', 'sta', 'llama3.2:3b', ARRAY['whatsapp_ceo', 'email_alerts', 'sms_fallback'], NULL, 20)
ON CONFLICT (agent_id) DO NOTHING;

-- ═══════════════════════════════════════════════
-- 4. NOESIS (sta-006) — Knowledge Base
-- ═══════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS noesis_knowledge_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  namespace TEXT NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  source TEXT,
  tags TEXT[] DEFAULT '{}',
  importance NUMERIC(3,2) DEFAULT 0.5 CHECK (importance >= 0 AND importance <= 1),
  embedding TEXT,
  access_count INT DEFAULT 0,
  last_accessed TIMESTAMPTZ,
  ttl_days INT,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS noesis_reasoning_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id TEXT NOT NULL,
  major_premise TEXT NOT NULL,
  minor_premise TEXT NOT NULL,
  conclusion TEXT NOT NULL,
  confidence NUMERIC(3,2) DEFAULT 0.5,
  premises_used TEXT[] DEFAULT '{}',
  alternatives TEXT[] DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE noesis_knowledge_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE noesis_reasoning_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Knowledge entries admin read" ON noesis_knowledge_entries FOR SELECT USING (
  auth.uid() IN (SELECT id FROM profiles WHERE role IN ('admin', 'superadmin'))
);
CREATE POLICY "Knowledge entries service manage" ON noesis_knowledge_entries FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Reasoning logs admin read" ON noesis_reasoning_logs FOR SELECT USING (
  auth.uid() IN (SELECT id FROM profiles WHERE role IN ('admin', 'superadmin'))
);
CREATE POLICY "Reasoning logs service insert" ON noesis_reasoning_logs FOR INSERT WITH CHECK (auth.role() = 'service_role');

CREATE INDEX IF NOT EXISTS idx_noesis_knowledge_namespace ON noesis_knowledge_entries(namespace, importance DESC);
CREATE INDEX IF NOT EXISTS idx_noesis_knowledge_tags ON noesis_knowledge_entries USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_noesis_knowledge_expiry ON noesis_knowledge_entries(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_noesis_reasoning_agent ON noesis_reasoning_logs(agent_id, created_at DESC);

-- ═══════════════════════════════════════════════
-- 5. FINANCIAL ADVISORY (sta-008) — Portfolios
-- ═══════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS fa_clients (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id),
  advisor_id UUID REFERENCES profiles(id),
  client_type TEXT DEFAULT 'individual' CHECK (client_type IN ('individual', 'joint', 'corporate', 'trust')),
  risk_profile TEXT DEFAULT 'moderate' CHECK (risk_profile IN ('conservative', 'moderate', 'aggressive', 'balanced')),
  kyc_status TEXT DEFAULT 'pending' CHECK (kyc_status IN ('pending', 'verified', 'rejected')),
  total_invested NUMERIC(14,2) DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fa_portfolios (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID REFERENCES fa_clients(id) ON DELETE CASCADE,
  portfolio_name TEXT NOT NULL,
  portfolio_type TEXT DEFAULT 'individual' CHECK (portfolio_type IN ('individual', 'joint', 'corporate', 'trust')),
  risk_profile TEXT DEFAULT 'moderate',
  currency TEXT DEFAULT 'KES',
  total_value NUMERIC(14,2) DEFAULT 0,
  total_returns NUMERIC(14,2) DEFAULT 0,
  inception_date DATE DEFAULT CURRENT_DATE,
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'frozen', 'closed')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fa_holdings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  portfolio_id UUID REFERENCES fa_portfolios(id) ON DELETE CASCADE,
  asset_type TEXT CHECK (asset_type IN ('equity', 'bond', 'fund', 'deposit', 'alternative', 'etf')),
  asset_name TEXT NOT NULL,
  ticker_symbol TEXT,
  quantity NUMERIC(12,4),
  purchase_price NUMERIC(12,2),
  current_price NUMERIC(12,2),
  market_value NUMERIC(14,2),
  unrealized_pnl NUMERIC(14,2) DEFAULT 0,
  weight_pct NUMERIC(5,2) DEFAULT 0,
  last_updated TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fa_trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  portfolio_id UUID REFERENCES fa_portfolios(id),
  holding_id UUID REFERENCES fa_holdings(id),
  trade_type TEXT CHECK (trade_type IN ('buy', 'sell', 'dividend', 'interest', 'deposit', 'withdrawal')),
  quantity NUMERIC(12,4),
  price NUMERIC(12,2),
  total_amount NUMERIC(14,2),
  commission NUMERIC(10,2) DEFAULT 0,
  tax NUMERIC(10,2) DEFAULT 0,
  trade_date TIMESTAMPTZ DEFAULT now(),
  status TEXT DEFAULT 'executed' CHECK (status IN ('pending', 'executed', 'settled', 'cancelled')),
  reference TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fa_financial_goals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID REFERENCES fa_clients(id) ON DELETE CASCADE,
  goal_name TEXT NOT NULL,
  target_amount NUMERIC(14,2) NOT NULL,
  current_amount NUMERIC(14,2) DEFAULT 0,
  target_date DATE,
  priority INT DEFAULT 5,
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'paused', 'cancelled')),
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE fa_clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE fa_portfolios ENABLE ROW LEVEL SECURITY;
ALTER TABLE fa_holdings ENABLE ROW LEVEL SECURITY;
ALTER TABLE fa_trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE fa_financial_goals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Clients view own" ON fa_clients FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "Clients create own" ON fa_clients FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "Portfolios client read" ON fa_portfolios FOR SELECT USING (
  client_id IN (SELECT id FROM fa_clients WHERE user_id = auth.uid())
);
CREATE POLICY "Holdings client read" ON fa_holdings FOR SELECT USING (
  portfolio_id IN (SELECT id FROM fa_portfolios WHERE client_id IN (SELECT id FROM fa_clients WHERE user_id = auth.uid()))
);
CREATE POLICY "Trades client read" ON fa_trades FOR SELECT USING (
  portfolio_id IN (SELECT id FROM fa_portfolios WHERE client_id IN (SELECT id FROM fa_clients WHERE user_id = auth.uid()))
);
CREATE POLICY "Goals client manage" ON fa_financial_goals FOR ALL USING (
  client_id IN (SELECT id FROM fa_clients WHERE user_id = auth.uid())
);

CREATE INDEX IF NOT EXISTS idx_fa_portfolios_client ON fa_portfolios(client_id, status);
CREATE INDEX IF NOT EXISTS idx_fa_holdings_portfolio ON fa_holdings(portfolio_id, asset_type);
CREATE INDEX IF NOT EXISTS idx_fa_trades_portfolio ON fa_trades(portfolio_id, trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_fa_trades_status ON fa_trades(status, trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_fa_goals_client ON fa_financial_goals(client_id, status);

-- ═══════════════════════════════════════════════
-- 6. RPCs for Multi-App Operations
-- ═══════════════════════════════════════════════

-- Get agent registry (for SAICOS dashboard)
CREATE OR REPLACE FUNCTION get_agent_registry()
RETURNS SETOF saicos_agent_registry AS $$
  SELECT * FROM saicos_agent_registry ORDER BY domain, agent_id;
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- Get agent metrics
CREATE OR REPLACE FUNCTION get_agent_metrics()
RETURNS TABLE (
  total_agents BIGINT,
  online_agents BIGINT,
  total_tasks BIGINT,
  completed_tasks BIGINT,
  failed_tasks BIGINT,
  avg_response_ms NUMERIC
) AS $$
  SELECT
    (SELECT count(*) FROM saicos_agent_registry),
    (SELECT count(*) FROM saicos_agent_registry WHERE status = 'online'),
    (SELECT count(*) FROM saicos_agent_tasks),
    (SELECT count(*) FROM saicos_agent_tasks WHERE status = 'completed'),
    (SELECT count(*) FROM saicos_agent_tasks WHERE status = 'failed'),
    (SELECT COALESCE(avg(extract(epoch from (completed_at - started_at)) * 1000), 0)
     FROM saicos_agent_tasks WHERE status = 'completed' AND started_at IS NOT NULL);
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- Get knowledge base stats (for NOESIS dashboard)
CREATE OR REPLACE FUNCTION get_knowledge_stats()
RETURNS TABLE (
  namespace TEXT,
  entry_count BIGINT,
  avg_importance NUMERIC,
  last_updated TIMESTAMPTZ
) AS $$
  SELECT
    n.namespace,
    count(*) as entry_count,
    COALESCE(avg(n.importance), 0) as avg_importance,
    max(n.updated_at) as last_updated
  FROM noesis_knowledge_entries n
  GROUP BY n.namespace
  ORDER BY entry_count DESC;
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- Get Mali Access Union group stats
CREATE OR REPLACE FUNCTION get_group_stats(p_group_id UUID)
RETURNS TABLE (
  member_count BIGINT,
  total_contributions NUMERIC,
  pool_balance NUMERIC,
  active_loans BIGINT,
  completion_pct NUMERIC
) AS $$
  SELECT
    (SELECT count(*) FROM mau_members WHERE group_id = p_group_id AND status = 'active'),
    (SELECT COALESCE(sum(amount), 0) FROM mau_contributions WHERE group_id = p_group_id AND status = 'confirmed'),
    (SELECT COALESCE(total_balance, 0) FROM mau_savings_pools WHERE group_id = p_group_id),
    (SELECT count(*) FROM mau_loans WHERE group_id = p_group_id AND status IN ('approved', 'disbursed', 'repaying')),
    CASE
      WHEN (SELECT max_members FROM mau_groups WHERE id = p_group_id) > 0
      THEN (SELECT count(*)::numeric FROM mau_members WHERE group_id = p_group_id AND status = 'active')
           * 100.0 / (SELECT max_members FROM mau_groups WHERE id = p_group_id)
      ELSE 0
    END;
$$ LANGUAGE sql SECURITY DEFINER STABLE;
