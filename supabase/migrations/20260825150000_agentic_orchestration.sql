-- ============================================================
-- STA Agentic Orchestration Hub — Database Schema
-- The central brain for all STA agents
-- ============================================================

-- 1. Agent Registry
CREATE TABLE IF NOT EXISTS public.agent_registry (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id TEXT UNIQUE NOT NULL,
  agent_name TEXT NOT NULL,
  agent_type TEXT NOT NULL CHECK (agent_type IN ('orchestrator','worker','monitor','advisory')),
  domain TEXT NOT NULL,
  model_used TEXT,
  endpoint_url TEXT,
  skills JSONB DEFAULT '[]',
  status TEXT DEFAULT 'idle' CHECK (status IN ('idle','busy','offline','error')),
  max_concurrent_tasks INT DEFAULT 5,
  current_task_count INT DEFAULT 0,
  total_tasks_completed INT DEFAULT 0,
  avg_response_time_ms INT DEFAULT 0,
  error_rate NUMERIC(5,2) DEFAULT 0,
  last_heartbeat TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2. Agent Tasks (Queue)
CREATE TABLE IF NOT EXISTS public.agent_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id TEXT UNIQUE NOT NULL,
  parent_task_id UUID REFERENCES public.agent_tasks(id),
  orchestrator_id TEXT,
  assigned_agent_id TEXT REFERENCES public.agent_registry(agent_id),
  domain TEXT NOT NULL,
  task_type TEXT NOT NULL,
  priority TEXT DEFAULT 'normal' CHECK (priority IN ('critical','high','normal','low','background')),
  input JSONB NOT NULL,
  output JSONB,
  context JSONB DEFAULT '{}',
  status TEXT DEFAULT 'created' CHECK (status IN ('created','queued','assigned','running','completed','failed','cancelled')),
  retry_count INT DEFAULT 0,
  max_retries INT DEFAULT 3,
  timeout_ms INT DEFAULT 30000,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  error_message TEXT,
  tokens_used INT DEFAULT 0,
  cost_ksh NUMERIC(10,4) DEFAULT 0,
  created_by TEXT DEFAULT 'system',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 3. Agent Events (Inter-Agent Communication Bus)
CREATE TABLE IF NOT EXISTS public.agent_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type TEXT NOT NULL,
  source_agent_id TEXT NOT NULL,
  target_agent_id TEXT,
  domain TEXT,
  payload JSONB NOT NULL,
  priority TEXT DEFAULT 'normal',
  delivered BOOLEAN DEFAULT false,
  processed BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 4. Agent Memory (Persistent)
CREATE TABLE IF NOT EXISTS public.agent_memory (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id TEXT NOT NULL,
  memory_type TEXT NOT NULL CHECK (memory_type IN ('episodic','semantic','procedural','ceo_briefing')),
  namespace TEXT DEFAULT 'default',
  content JSONB NOT NULL,
  embedding TEXT,
  importance NUMERIC(3,2) DEFAULT 0.5,
  access_count INT DEFAULT 0,
  last_accessed TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 5. CEO Briefings
CREATE TABLE IF NOT EXISTS public.ceo_briefings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  briefing_type TEXT NOT NULL CHECK (briefing_type IN ('daily','weekly','monthly','alert','kpi')),
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  kpis JSONB NOT NULL DEFAULT '{}',
  alerts JSONB DEFAULT '[]',
  recommendations JSONB DEFAULT '[]',
  revenue_summary JSONB,
  agent_performance JSONB,
  read_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 6. Agent Skills (Marketplace)
CREATE TABLE IF NOT EXISTS public.agent_skills (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  skill_id TEXT UNIQUE NOT NULL,
  skill_name TEXT NOT NULL,
  description TEXT,
  domain TEXT NOT NULL,
  input_schema JSONB NOT NULL,
  output_schema JSONB NOT NULL,
  edge_function TEXT,
  model_required TEXT,
  cost_per_use_ksh NUMERIC(10,4) DEFAULT 0,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 7. Scaling Rules
CREATE TABLE IF NOT EXISTS public.scaling_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id TEXT NOT NULL,
  metric TEXT NOT NULL,
  threshold_up NUMERIC(10,2) NOT NULL,
  threshold_down NUMERIC(10,2),
  action TEXT NOT NULL CHECK (action IN ('spawn','kill','notify','throttle')),
  cooldown_seconds INT DEFAULT 300,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_agent_registry_domain ON public.agent_registry(domain, status);
CREATE INDEX IF NOT EXISTS idx_agent_registry_status ON public.agent_registry(status);
CREATE INDEX IF NOT EXISTS idx_agent_registry_heartbeat ON public.agent_registry(last_heartbeat DESC);

CREATE INDEX IF NOT EXISTS idx_agent_tasks_status ON public.agent_tasks(status, priority, created_at);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_agent ON public.agent_tasks(assigned_agent_id, status);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_domain ON public.agent_tasks(domain, status);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_parent ON public.agent_tasks(parent_task_id);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_queued ON public.agent_tasks(status, created_at) WHERE status IN ('created','queued');

CREATE INDEX IF NOT EXISTS idx_agent_events_type ON public.agent_events(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_events_source ON public.agent_events(source_agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_events_target ON public.agent_events(target_agent_id, delivered) WHERE delivered = false;
CREATE INDEX IF NOT EXISTS idx_agent_events_unprocessed ON public.agent_events(processed, created_at) WHERE processed = false;

CREATE INDEX IF NOT EXISTS idx_agent_memory_agent ON public.agent_memory(agent_id, namespace);
CREATE INDEX IF NOT EXISTS idx_agent_memory_importance ON public.agent_memory(importance DESC, last_accessed DESC);
CREATE INDEX IF NOT EXISTS idx_agent_memory_expires ON public.agent_memory(expires_at) WHERE expires_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_ceo_briefings_type ON public.ceo_briefings(briefing_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ceo_briefings_unread ON public.ceo_briefings(read_at) WHERE read_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_agent_skills_domain ON public.agent_skills(domain, is_active);
CREATE INDEX IF NOT EXISTS idx_scaling_rules_agent ON public.scaling_rules(agent_id, is_active);

-- ============================================================
-- RLS
-- ============================================================

ALTER TABLE public.agent_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ceo_briefings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scaling_rules ENABLE ROW LEVEL SECURITY;

-- Agent registry: authenticated read, admin manage
CREATE POLICY "Agent registry read" ON public.agent_registry FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Agent registry manage" ON public.agent_registry FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
);

-- Tasks: authenticated read, agents manage own
CREATE POLICY "Tasks read" ON public.agent_tasks FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Tasks manage" ON public.agent_tasks FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
);

-- Events: authenticated read, agents manage own
CREATE POLICY "Events read" ON public.agent_events FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Events manage" ON public.agent_events FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
);

-- Memory: agent-scoped
CREATE POLICY "Memory read" ON public.agent_memory FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Memory manage" ON public.agent_memory FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
);

-- CEO briefings: CEO/admin only
CREATE POLICY "CEO briefings read" ON public.ceo_briefings FOR SELECT USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
);

-- Skills: public read, admin manage
CREATE POLICY "Skills read" ON public.agent_skills FOR SELECT USING (true);
CREATE POLICY "Skills manage" ON public.agent_skills FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
);

-- Scaling rules: admin only
CREATE POLICY "Scaling admin" ON public.scaling_rules FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
);

-- ============================================================
-- REALTIME
-- ============================================================

ALTER PUBLICATION supabase_realtime ADD TABLE public.agent_events;
ALTER PUBLICATION supabase_realtime ADD TABLE public.agent_tasks;
ALTER PUBLICATION supabase_realtime ADD TABLE public.agent_registry;

-- ============================================================
-- SEED: Default Agent Registry
-- ============================================================

INSERT INTO public.agent_registry (agent_id, agent_name, agent_type, domain, model_used, skills, status)
VALUES
  ('mwarokin-001', 'Property Search Agent', 'worker', 'mwarokin', 'qwen3:8b', '["property_search","location_match","price_filter"]', 'idle'),
  ('mwarokin-002', 'Tenant Screening Agent', 'worker', 'mwarokin', 'gemma3:4b', '["credit_check","id_verify","reference_check"]', 'idle'),
  ('mwarokin-003', 'Payment Processing Agent', 'worker', 'mwarokin', 'llama3.2:3b', '["mpesa_stk","payment_split","receipt_generate"]', 'idle'),
  ('mwarokin-004', 'Maintenance Agent', 'worker', 'mwarokin', 'qwen3:8b', '["ticket_routing","priority_scoring","technician_match"]', 'idle'),
  ('mwarokin-005', 'Document Agent', 'worker', 'mwarokin', 'gemma3:4b', '["lease_gen","compliance_check","document_store"]', 'idle'),
  ('syllopay-001', 'Transaction Agent', 'worker', 'syllopay', 'qwen3:8b', '["payment_routing","fee_calculation","settlement"]', 'idle'),
  ('syllopay-002', 'Fraud Detection Agent', 'monitor', 'syllopay', 'gemma3:4b', '["anomaly_detection","risk_scoring","alert_generate"]', 'idle'),
  ('saicos-001', 'Intelligence Agent', 'worker', 'saicos', 'qwen3:8b', '["market_analysis","lead_scoring","trend_detect"]', 'idle'),
  ('saicos-002', 'Outreach Agent', 'worker', 'saicos', 'llama3.2:3b', '["whatsapp_outreach","sms_send","email_send"]', 'idle'),
  ('noesis-001', 'Knowledge Agent', 'worker', 'noesis', 'qwen3:8b', '["rag_search","context_injection","fact_check"]', 'idle'),
  ('noesis-002', 'Reasoning Agent', 'worker', 'noesis', 'qwen3:8b', '["syllogistic_reasoning","chain_of_thought","logical_inference"]', 'idle'),
  ('mali-001', 'Savings Agent', 'worker', 'maliaccessunion', 'gemma3:4b', '["chama_management","savings_tracking","dividend_calc"]', 'idle'),
  ('mali-002', 'Loan Agent', 'worker', 'maliaccessunion', 'qwen3:8b', '["credit_scoring","loan_distribution","repayment_track"]', 'idle'),
  ('financial-001', 'Advisory Agent', 'advisory', 'financial_advisory', 'qwen3:8b', '["portfolio_analysis","risk_assessment","recommender"]', 'idle'),
  ('financial-002', 'Report Agent', 'worker', 'financial_advisory', 'llama3.2:3b', '["report_generation","dashboard_update","export_pdf"]', 'idle'),
  ('ceo-001', 'Executive Summary Agent', 'orchestrator', 'sta', 'qwen3:8b', '["daily_brief","kpi_tracking","alert_generation","trend_analysis"]', 'idle'),
  ('ceo-002', 'Notification Agent', 'worker', 'sta', 'llama3.2:3b', '["whatsapp_ceo","email_alerts","sms_fallback"]', 'idle'),
  ('sta-hub-001', 'Orchestrator Agent', 'orchestrator', 'sta', 'qwen3:8b', '["task_decomposition","routing","load_balancing","conflict_resolution"]', 'idle')
ON CONFLICT (agent_id) DO NOTHING;

-- ============================================================
-- SEED: Default Skills
-- ============================================================

INSERT INTO public.agent_skills (skill_id, skill_name, description, domain, input_schema, output_schema, edge_function)
VALUES
  ('search-property', 'Property Search', 'Search properties by location, price, type', 'mwarokin',
   '{"location":"text","min_price":"number","max_price":"number","property_type":"text"}',
   '{"properties":"array","total":"number"}',
   'agent-brain'),
  ('process-payment', 'Process Payment', 'Initiate M-Pesa STK push and track', 'syllopay',
   '{"phone":"text","amount":"number","reference":"text"}',
   '{"checkout_id":"text","status":"text"}',
   'agent-brain'),
  ('screen-tenant', 'Screen Tenant', 'Verify tenant identity and creditworthiness', 'mwarokin',
   '{"phone":"text","id_number":"text","employer":"text"}',
   '{"score":"number","approved":"boolean","reasons":"array"}',
   'agent-brain'),
  ('generate-briefing', 'CEO Briefing', 'Generate executive daily summary', 'sta',
   '{"period":"text","include_kpis":"boolean","include_alerts":"boolean"}',
   '{"title":"text","summary":"text","kpis":"object","alerts":"array"}',
   'ceo-briefing'),
  ('detect-fraud', 'Fraud Detection', 'Analyze transaction for suspicious patterns', 'syllopay',
   '{"transaction_id":"text","amount":"number","phone":"text","location":"text"}',
   '{"risk_score":"number","flagged":"boolean","reasons":"array"}',
   'agent-brain')
ON CONFLICT (skill_id) DO NOTHING;

-- ============================================================
-- SEED: Default Scaling Rules
-- ============================================================

INSERT INTO public.scaling_rules (agent_id, metric, threshold_up, threshold_down, action, cooldown_seconds)
VALUES
  ('mwarokin-003', 'queue_depth', 10, 2, 'spawn', 300),
  ('mwarokin-003', 'error_rate', 10.0, 1.0, 'notify', 60),
  ('syllopay-002', 'error_rate', 5.0, 0.5, 'notify', 120),
  ('ceo-001', 'queue_depth', 5, 1, 'notify', 600)
ON CONFLICT DO NOTHING;
