-- ============================================================================
-- MWAROKIN ESTATES — SUPABASE DATABASE SCHEMA
-- Run this in: Supabase Dashboard → SQL Editor
-- ============================================================================
-- This schema is the complete backend for the Mwarokin Estates platform:
-- properties, tenants, leases, payments (5% platform split), maintenance,
-- documents, communication (multi-channel), i18n, currency, analytics and
-- AI lead-generation for client onboarding.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. EXTENSIONS
-- ----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";      -- AI semantic search (pgvector)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ----------------------------------------------------------------------------
-- 2. PROFILES (extends auth.users)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name TEXT,
  phone TEXT,
  role TEXT NOT NULL DEFAULT 'tenant' CHECK (role IN ('admin', 'agent', 'landlord', 'caretaker', 'tenant')),
  company TEXT,
  profile_pic TEXT,
  bio TEXT,
  preferred_language TEXT NOT NULL DEFAULT 'en',
  preferred_currency TEXT NOT NULL DEFAULT 'KES',
  timezone TEXT NOT NULL DEFAULT 'Africa/Nairobi',
  notification_preferences JSONB NOT NULL DEFAULT '{
    "payment": true, "maintenance": true, "lease": true, "general": true
  }',
  is_verified BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name, phone, role)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'full_name', ''),
    COALESCE(NEW.raw_user_meta_data->>'phone', ''),
    COALESCE(NEW.raw_user_meta_data->>'role', 'tenant')
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ----------------------------------------------------------------------------
-- 3. PROPERTIES
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS properties (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  slug TEXT UNIQUE,
  description TEXT,
  property_type TEXT CHECK (property_type IN ('house','apartment','land','commercial','villa','bedsitter','bungalow')),
  status TEXT NOT NULL DEFAULT 'available' CHECK (status IN ('available','rented','under_maintenance','sold')),
  price DECIMAL(12,2) NOT NULL DEFAULT 0,
  deposit DECIMAL(12,2),
  bedrooms INTEGER DEFAULT 0,
  bathrooms INTEGER DEFAULT 0,
  area_sqft INTEGER,
  location TEXT NOT NULL,
  city TEXT,
  county TEXT,
  country TEXT NOT NULL DEFAULT 'Kenya',
  latitude DECIMAL(10,8),
  longitude DECIMAL(11,8),
  amenities JSONB NOT NULL DEFAULT '[]',
  images JSONB NOT NULL DEFAULT '[]',
  video_url TEXT,
  virtual_tour_url TEXT,
  agent_id UUID REFERENCES profiles(id),
  is_featured BOOLEAN NOT NULL DEFAULT false,
  views_count INTEGER NOT NULL DEFAULT 0,
  embedding vector(1536),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_properties_status ON properties(status);
CREATE INDEX IF NOT EXISTS idx_properties_price ON properties(price);
CREATE INDEX IF NOT EXISTS idx_properties_city ON properties(city);
CREATE INDEX IF NOT EXISTS idx_properties_agent ON properties(agent_id);
CREATE INDEX IF NOT EXISTS idx_properties_embedding ON properties USING ivfflat (embedding vector_cosine_ops);

-- ----------------------------------------------------------------------------
-- 4. TENANTS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  full_name TEXT NOT NULL,
  phone TEXT NOT NULL,
  email TEXT,
  id_number TEXT,
  date_of_birth DATE,
  occupation TEXT,
  emergency_contact_name TEXT,
  emergency_contact_phone TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ----------------------------------------------------------------------------
-- 5. LEASES
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS leases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  landlord_id UUID REFERENCES profiles(id),
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  rent_amount DECIMAL(12,2) NOT NULL,
  deposit_paid DECIMAL(12,2) NOT NULL DEFAULT 0,
  deposit_balance DECIMAL(12,2) NOT NULL DEFAULT 0,
  payment_frequency TEXT NOT NULL DEFAULT 'monthly' CHECK (payment_frequency IN ('monthly','quarterly','annually')),
  is_active BOOLEAN NOT NULL DEFAULT true,
  lease_document_url TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_leases_active ON leases(is_active);
CREATE INDEX IF NOT EXISTS idx_leases_property ON leases(property_id);

-- ----------------------------------------------------------------------------
-- 6. PAYMENTS (with 5% platform split)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS platform_settings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key TEXT UNIQUE NOT NULL,
  value JSONB NOT NULL,
  description TEXT,
  updated_by UUID REFERENCES profiles(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO platform_settings (key, value, description)
VALUES ('commission_rate', '{"percentage": 5.0, "min_amount": 50}', 'Mwarokin Estates platform commission on every payment')
ON CONFLICT (key) DO NOTHING;

CREATE TABLE IF NOT EXISTS payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lease_id UUID REFERENCES leases(id) ON DELETE CASCADE,
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  property_id UUID REFERENCES properties(id),
  landlord_id UUID REFERENCES profiles(id),
  amount DECIMAL(12,2) NOT NULL,
  landlord_amount DECIMAL(12,2) NOT NULL DEFAULT 0,   -- 95%
  platform_fee DECIMAL(12,2) NOT NULL DEFAULT 0,      -- 5%
  platform_fee_percentage DECIMAL(5,2) NOT NULL DEFAULT 5.0,
  payment_method TEXT CHECK (payment_method IN ('mpesa','airtel-money','bank-transfer','card','cash')),
  transaction_id TEXT UNIQUE,
  provider_reference TEXT,
  payment_date DATE NOT NULL,
  due_date DATE NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','completed','failed','refunded')),
  split_status TEXT NOT NULL DEFAULT 'pending' CHECK (split_status IN ('pending','processing','completed','failed')),
  metadata JSONB NOT NULL DEFAULT '{}',
  notes TEXT,
  receipt_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_tenant ON payments(tenant_id);
CREATE INDEX IF NOT EXISTS idx_payments_property ON payments(property_id);

-- Auto-calculate the 95/5 split on insert
CREATE OR REPLACE FUNCTION public.calculate_payment_split()
RETURNS TRIGGER AS $$
DECLARE
  commission DECIMAL(5,2);
BEGIN
  SELECT COALESCE((value->>'percentage')::DECIMAL, 5.0) INTO commission
  FROM public.platform_settings WHERE key = 'commission_rate';
  NEW.platform_fee_percentage := commission;
  NEW.platform_fee := ROUND(NEW.amount * (commission / 100), 2);
  NEW.landlord_amount := NEW.amount - NEW.platform_fee;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

DROP TRIGGER IF EXISTS trg_calculate_payment_split ON payments;
CREATE TRIGGER trg_calculate_payment_split
  BEFORE INSERT ON payments
  FOR EACH ROW EXECUTE FUNCTION public.calculate_payment_split();

-- ----------------------------------------------------------------------------
-- 7. MAINTENANCE REQUESTS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS maintenance_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id UUID REFERENCES properties(id) ON DELETE CASCADE,
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  request_type TEXT CHECK (request_type IN ('plumbing','electrical','structural','appliance','pest','other')),
  priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low','medium','high','emergency')),
  description TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','in_progress','completed','cancelled')),
  images JSONB NOT NULL DEFAULT '[]',
  technician_name TEXT,
  technician_phone TEXT,
  scheduled_date DATE,
  completed_date DATE,
  cost DECIMAL(12,2),
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ----------------------------------------------------------------------------
-- 8. DOCUMENTS (lease agreements, receipts, contracts)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id UUID REFERENCES properties(id) ON DELETE CASCADE,
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  lease_id UUID REFERENCES leases(id) ON DELETE CASCADE,
  document_type TEXT CHECK (document_type IN ('lease_agreement','identification','receipt','inspection','contract','other')),
  title TEXT NOT NULL,
  file_url TEXT NOT NULL,
  file_size INTEGER,
  file_type TEXT,
  uploaded_by UUID REFERENCES profiles(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ----------------------------------------------------------------------------
-- 9. COMMUNICATION (multi-channel: SMS, WhatsApp, Telegram, IG, TikTok, Snapchat)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS communication_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  phone VARCHAR(20),
  whatsapp_phone VARCHAR(20),
  telegram_username VARCHAR(100),
  instagram_handle VARCHAR(100),
  snapchat_username VARCHAR(100),
  tiktok_handle VARCHAR(100),
  preferred_channel TEXT NOT NULL DEFAULT 'whatsapp'
    CHECK (preferred_channel IN ('sms','whatsapp','telegram','instagram','email','in-app')),
  is_verified BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user_id)
);

CREATE TABLE IF NOT EXISTS message_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  channel TEXT NOT NULL CHECK (channel IN ('sms','whatsapp','telegram','instagram','snapchat','tiktok','in-app','email')),
  recipient_id UUID REFERENCES profiles(id),
  recipient_identifier TEXT NOT NULL,
  sender_id UUID REFERENCES profiles(id),
  subject TEXT,
  body TEXT NOT NULL,
  media_urls JSONB NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','sent','delivered','read','failed')),
  priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('low','normal','high','urgent')),
  scheduled_for TIMESTAMPTZ,
  sent_at TIMESTAMPTZ,
  delivered_at TIMESTAMPTZ,
  read_at TIMESTAMPTZ,
  metadata JSONB NOT NULL DEFAULT '{}',
  error_message TEXT,
  retry_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_message_queue_status ON message_queue(status);
CREATE INDEX IF NOT EXISTS idx_message_queue_recipient ON message_queue(recipient_id);

CREATE TABLE IF NOT EXISTS notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  type TEXT NOT NULL DEFAULT 'general'
    CHECK (type IN ('payment_due','maintenance_update','lease_expiry','inspection','general','message')),
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  link TEXT,
  is_read BOOLEAN NOT NULL DEFAULT false,
  priority TEXT NOT NULL DEFAULT 'normal',
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  read_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read);

-- ----------------------------------------------------------------------------
-- 10. i18n — LANGUAGES & TRANSLATIONS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS supported_languages (
  code TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  native_name TEXT NOT NULL,
  flag TEXT,
  is_rtl BOOLEAN NOT NULL DEFAULT false,
  is_active BOOLEAN NOT NULL DEFAULT true
);

INSERT INTO supported_languages (code, name, native_name, flag, is_rtl) VALUES
  ('en', 'English',  'English',   'GB', false),
  ('sw', 'Swahili',  'Kiswahili', 'KE', false),
  ('fr', 'French',   'Français',  'FR', false),
  ('de', 'German',   'Deutsch',   'DE', false),
  ('ar', 'Arabic',   'العربية',    'AE', true)
ON CONFLICT (code) DO NOTHING;

CREATE TABLE IF NOT EXISTS translations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  language_code TEXT NOT NULL REFERENCES supported_languages(code),
  namespace TEXT NOT NULL DEFAULT 'common',
  key TEXT NOT NULL,
  value TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(language_code, namespace, key)
);

-- ----------------------------------------------------------------------------
-- 11. CURRENCY & EXCHANGE RATES
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS supported_currencies (
  code TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  symbol TEXT NOT NULL,
  decimal_places INTEGER NOT NULL DEFAULT 2,
  is_active BOOLEAN NOT NULL DEFAULT true
);

INSERT INTO supported_currencies (code, name, symbol, decimal_places) VALUES
  ('KES', 'Kenyan Shilling', 'KSh', 2),
  ('USD', 'US Dollar',       '$',   2),
  ('EUR', 'Euro',            '€',   2),
  ('GBP', 'British Pound',   '£',   2)
ON CONFLICT (code) DO NOTHING;

CREATE TABLE IF NOT EXISTS exchange_rates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  base_currency TEXT NOT NULL REFERENCES supported_currencies(code),
  target_currency TEXT NOT NULL REFERENCES supported_currencies(code),
  rate DECIMAL(20,8) NOT NULL,
  previous_rate DECIMAL(20,8),
  change_percentage DECIMAL(8,4) NOT NULL DEFAULT 0,
  source TEXT,
  last_updated TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(base_currency, target_currency)
);

-- Insert base 1:1 row for KES
INSERT INTO exchange_rates (base_currency, target_currency, rate)
VALUES ('KES','KES',1) ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS property_price_localization (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  currency_code TEXT NOT NULL REFERENCES supported_currencies(code),
  localized_price DECIMAL(12,2) NOT NULL,
  exchange_rate_used DECIMAL(20,8) NOT NULL,
  last_calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(property_id, currency_code)
);

-- ----------------------------------------------------------------------------
-- 12. ANALYTICS & AUDIT
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  action TEXT NOT NULL,
  table_name TEXT,
  record_id UUID,
  old_data JSONB,
  new_data JSONB,
  ip_address INET,
  user_agent TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_behavior (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id),
  session_id TEXT,
  action_type TEXT CHECK (action_type IN ('view','favorite','share','search','inquiry')),
  property_id UUID REFERENCES properties(id),
  search_query TEXT,
  search_filters JSONB,
  time_spent INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS property_views (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  view_count INTEGER NOT NULL DEFAULT 0,
  unique_viewers INTEGER NOT NULL DEFAULT 0,
  last_viewed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ----------------------------------------------------------------------------
-- 13. AI LEAD-GENERATION (agentic onboarding)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prospects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT,
  name TEXT,
  phone TEXT,
  email TEXT,
  address TEXT,
  property_address TEXT,
  property_type TEXT,
  estimated_value DECIMAL(12,2),
  lead_score INTEGER NOT NULL DEFAULT 0,
  qualification_status TEXT NOT NULL DEFAULT 'new'
    CHECK (qualification_status IN ('new','qualified','hot','nurture','converted')),
  intent_signals JSONB NOT NULL DEFAULT '[]',
  preferred_channels JSONB NOT NULL DEFAULT '[]',
  notes TEXT,
  discovered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS outreach_campaigns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  target_criteria JSONB NOT NULL DEFAULT '{}',
  channels JSONB NOT NULL DEFAULT '["whatsapp","sms"]',
  message_template_id UUID,
  schedule_config JSONB,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','active','paused','completed')),
  total_reached INTEGER NOT NULL DEFAULT 0,
  total_converted INTEGER NOT NULL DEFAULT 0,
  created_by UUID REFERENCES profiles(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS outreach_threads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prospect_id UUID REFERENCES prospects(id) ON DELETE CASCADE,
  campaign_id UUID REFERENCES outreach_campaigns(id) ON DELETE CASCADE,
  channel TEXT NOT NULL,
  external_thread_id TEXT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','awaiting_response','converted','closed')),
  last_message_at TIMESTAMPTZ,
  engagement_score INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- done — see functions.sql, policies.sql and seed.sql next.
-- ============================================================================
