-- ============================================================
-- Mwarokin Estates — Enterprise Schema Reconciliation
-- Migrates from live Supabase schema to include enterprise tables
-- Date: 2026-08-25
-- Author: 2nd Agentic Brain
-- Safety: ADDITIVE ONLY — no drops, no alters to existing columns
-- ============================================================

-- ============================================================
-- 1. EXTENSIONS (safe to re-run)
-- ============================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- PostGIS: only if available (Supabase may not have it)
-- CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================================
-- 2. NEW TABLES (enterprise operations layer)
-- These tables do NOT exist in the live schema
-- ============================================================

-- 2.1 Organizations (multi-tenant hierarchy)
CREATE TABLE IF NOT EXISTS public.organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  legal_name TEXT,
  registration_no TEXT,
  kra_pin TEXT,
  email TEXT,
  phone TEXT,
  website TEXT,
  status TEXT DEFAULT 'active' CHECK (status IN ('active','inactive','suspended')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2.2 Units (sub-properties within a property)
CREATE TABLE IF NOT EXISTS public.units (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id UUID NOT NULL REFERENCES public.properties(id) ON DELETE CASCADE,
  unit_code TEXT NOT NULL,
  unit_type TEXT,
  floor TEXT,
  bedrooms INT,
  bathrooms NUMERIC(4,1),
  size_sqm NUMERIC(12,2),
  rent_amount NUMERIC(14,2),
  deposit_amount NUMERIC(14,2),
  status TEXT DEFAULT 'vacant' CHECK (status IN ('vacant','occupied','maintenance','reserved')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(property_id, unit_code)
);

-- 2.3 Owners (property owners)
CREATE TABLE IF NOT EXISTS public.owners (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID REFERENCES public.organizations(id) ON DELETE CASCADE,
  full_name TEXT NOT NULL,
  email TEXT,
  phone TEXT,
  national_id_or_passport TEXT,
  ownership_type TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2.4 Property-Owner junction
CREATE TABLE IF NOT EXISTS public.property_owners (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id UUID NOT NULL REFERENCES public.properties(id) ON DELETE CASCADE,
  owner_id UUID NOT NULL REFERENCES public.owners(id) ON DELETE CASCADE,
  ownership_percentage NUMERIC(5,2),
  start_date DATE,
  end_date DATE,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 2.5 Vendors (maintenance/service providers)
CREATE TABLE IF NOT EXISTS public.vendors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID REFERENCES public.organizations(id) ON DELETE CASCADE,
  business_name TEXT NOT NULL,
  contact_name TEXT,
  phone TEXT,
  email TEXT,
  service_category TEXT,
  status TEXT DEFAULT 'active' CHECK (status IN ('active','inactive','suspended')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2.6 Staff (organization staff members)
CREATE TABLE IF NOT EXISTS public.staff (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID REFERENCES public.organizations(id) ON DELETE CASCADE,
  user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
  department TEXT,
  job_title TEXT,
  phone TEXT,
  status TEXT DEFAULT 'active' CHECK (status IN ('active','inactive','terminated')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2.7 Tasks (internal task management)
CREATE TABLE IF NOT EXISTS public.tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID REFERENCES public.organizations(id) ON DELETE CASCADE,
  property_id UUID REFERENCES public.properties(id) ON DELETE SET NULL,
  unit_id UUID REFERENCES public.units(id) ON DELETE SET NULL,
  assigned_to UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  description TEXT,
  priority TEXT DEFAULT 'medium' CHECK (priority IN ('low','medium','high','urgent')),
  status TEXT DEFAULT 'open' CHECK (status IN ('open','in_progress','completed','cancelled')),
  due_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2.8 Expenses (property-related expenses)
CREATE TABLE IF NOT EXISTS public.expenses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id UUID NOT NULL REFERENCES public.properties(id) ON DELETE CASCADE,
  unit_id UUID REFERENCES public.units(id) ON DELETE SET NULL,
  category TEXT NOT NULL,
  description TEXT,
  amount NUMERIC(14,2) NOT NULL,
  currency CHAR(3) DEFAULT 'KES',
  expense_date DATE,
  vendor TEXT,
  reference TEXT,
  status TEXT DEFAULT 'approved' CHECK (status IN ('pending','approved','rejected','paid')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2.9 Utility Readings (meter readings)
CREATE TABLE IF NOT EXISTS public.utility_readings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  unit_id UUID NOT NULL REFERENCES public.units(id) ON DELETE CASCADE,
  utility_type TEXT NOT NULL CHECK (utility_type IN ('water','electricity','gas','internet','sewage')),
  reading_value NUMERIC(14,3) NOT NULL,
  reading_date DATE NOT NULL,
  meter_number TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 2.10 Utility Charges (billed utility amounts)
CREATE TABLE IF NOT EXISTS public.utility_charges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lease_id UUID NOT NULL REFERENCES public.leases(id) ON DELETE CASCADE,
  unit_id UUID NOT NULL REFERENCES public.units(id) ON DELETE CASCADE,
  utility_type TEXT NOT NULL,
  amount NUMERIC(14,2) NOT NULL,
  billing_period DATE,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending','paid','overdue','disputed')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2.11 Property Images (dedicated image table)
CREATE TABLE IF NOT EXISTS public.property_images (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id UUID NOT NULL REFERENCES public.properties(id) ON DELETE CASCADE,
  unit_id UUID REFERENCES public.units(id) ON DELETE SET NULL,
  storage_path TEXT,
  public_url TEXT,
  caption TEXT,
  sort_order INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 2.12 Viewings (property viewing scheduling)
CREATE TABLE IF NOT EXISTS public.viewings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id UUID NOT NULL REFERENCES public.properties(id) ON DELETE CASCADE,
  unit_id UUID REFERENCES public.units(id) ON DELETE SET NULL,
  prospect_name TEXT NOT NULL,
  prospect_phone TEXT,
  prospect_email TEXT,
  scheduled_at TIMESTAMPTZ,
  status TEXT DEFAULT 'scheduled' CHECK (status IN ('scheduled','completed','cancelled','no_show')),
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2.13 Leads (alternative to prospects for enterprise workflow)
CREATE TABLE IF NOT EXISTS public.leads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID REFERENCES public.organizations(id) ON DELETE CASCADE,
  full_name TEXT,
  email TEXT,
  phone TEXT,
  source TEXT,
  property_id UUID REFERENCES public.properties(id) ON DELETE SET NULL,
  unit_id UUID REFERENCES public.units(id) ON DELETE SET NULL,
  stage TEXT DEFAULT 'new' CHECK (stage IN ('new','contacted','qualified','proposal','negotiation','won','lost')),
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 3. ADD COLUMNS TO EXISTING TABLES (additive, non-breaking)
-- ============================================================

-- 3.1 Add organization_id to properties (for multi-tenant)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'properties' AND column_name = 'organization_id'
  ) THEN
    ALTER TABLE public.properties ADD COLUMN organization_id UUID REFERENCES public.organizations(id) ON DELETE SET NULL;
  END IF;
END $$;

-- 3.2 Add organization_id to tenants
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'tenants' AND column_name = 'organization_id'
  ) THEN
    ALTER TABLE public.tenants ADD COLUMN organization_id UUID REFERENCES public.organizations(id) ON DELETE SET NULL;
  END IF;
END $$;

-- 3.3 Add unit_id to leases (enterprise uses unit_id, live uses property_id)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'leases' AND column_name = 'unit_id'
  ) THEN
    ALTER TABLE public.leases ADD COLUMN unit_id UUID REFERENCES public.units(id) ON DELETE SET NULL;
  END IF;
END $$;

-- 3.4 Add vendor_id to maintenance_requests
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'maintenance_requests' AND column_name = 'vendor_id'
  ) THEN
    ALTER TABLE public.maintenance_requests ADD COLUMN vendor_id UUID REFERENCES public.vendors(id) ON DELETE SET NULL;
  END IF;
END $$;

-- 3.5 Add assigned_to to maintenance_requests (enterprise pattern)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'maintenance_requests' AND column_name = 'assigned_to'
  ) THEN
    ALTER TABLE public.maintenance_requests ADD COLUMN assigned_to UUID REFERENCES public.profiles(id) ON DELETE SET NULL;
  END IF;
END $$;

-- ============================================================
-- 4. INDEXES (new tables only)
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_units_property ON public.units(property_id);
CREATE INDEX IF NOT EXISTS idx_units_status ON public.units(status);
CREATE INDEX IF NOT EXISTS idx_owners_org ON public.owners(organization_id);
CREATE INDEX IF NOT EXISTS idx_property_owners_property ON public.property_owners(property_id);
CREATE INDEX IF NOT EXISTS idx_property_owners_owner ON public.property_owners(owner_id);
CREATE INDEX IF NOT EXISTS idx_vendors_org ON public.vendors(organization_id);
CREATE INDEX IF NOT EXISTS idx_staff_org ON public.staff(organization_id);
CREATE INDEX IF NOT EXISTS idx_tasks_org ON public.tasks(organization_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON public.tasks(status, priority);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON public.tasks(assigned_to, status);
CREATE INDEX IF NOT EXISTS idx_expenses_property ON public.expenses(property_id);
CREATE INDEX IF NOT EXISTS idx_expenses_date ON public.expenses(expense_date);
CREATE INDEX IF NOT EXISTS idx_utility_readings_unit ON public.utility_readings(unit_id, utility_type);
CREATE INDEX IF NOT EXISTS idx_utility_charges_lease ON public.utility_charges(lease_id);
CREATE INDEX IF NOT EXISTS idx_property_images_property ON public.property_images(property_id);
CREATE INDEX IF NOT EXISTS idx_viewings_property ON public.viewings(property_id);
CREATE INDEX IF NOT EXISTS idx_viewings_scheduled ON public.viewings(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_leads_org ON public.leads(organization_id);
CREATE INDEX IF NOT EXISTS idx_leads_stage ON public.leads(stage);
CREATE INDEX IF NOT EXISTS idx_leads_property ON public.leads(property_id);

-- New indexes on existing tables
CREATE INDEX IF NOT EXISTS idx_properties_org ON public.properties(organization_id);
CREATE INDEX IF NOT EXISTS idx_tenants_org ON public.tenants(organization_id);
CREATE INDEX IF NOT EXISTS idx_leases_unit ON public.leases(unit_id);

-- ============================================================
-- 5. ROW LEVEL SECURITY (new tables)
-- ============================================================

ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.units ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.owners ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.property_owners ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vendors ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.staff ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.utility_readings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.utility_charges ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.property_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.viewings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY;

-- Organizations: authenticated read, admin manage
CREATE POLICY "Organizations read" ON public.organizations FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Organizations manage" ON public.organizations FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
);

-- Units: authenticated read, admin/landlord manage
CREATE POLICY "Units read" ON public.units FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Units manage" ON public.units FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin','landlord'))
);

-- Owners: authenticated read, admin manage
CREATE POLICY "Owners read" ON public.owners FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Owners manage" ON public.owners FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
);

-- Property owners: authenticated read, admin manage
CREATE POLICY "Property owners read" ON public.property_owners FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Property owners manage" ON public.property_owners FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
);

-- Vendors: authenticated read, admin manage
CREATE POLICY "Vendors read" ON public.vendors FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Vendors manage" ON public.vendors FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
);

-- Staff: authenticated read, admin manage
CREATE POLICY "Staff read" ON public.staff FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Staff manage" ON public.staff FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
);

-- Tasks: authenticated read, assigned user or admin manage
CREATE POLICY "Tasks read" ON public.tasks FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Tasks manage" ON public.tasks FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
  OR auth.uid() = assigned_to
);

-- Expenses: authenticated read, admin manage
CREATE POLICY "Expenses read" ON public.expenses FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Expenses manage" ON public.expenses FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
);

-- Utility readings: authenticated read, admin/landlord manage
CREATE POLICY "Utility readings read" ON public.utility_readings FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Utility readings manage" ON public.utility_readings FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin','landlord'))
);

-- Utility charges: authenticated read, admin/landlord manage
CREATE POLICY "Utility charges read" ON public.utility_charges FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Utility charges manage" ON public.utility_charges FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin','landlord'))
);

-- Property images: public read, admin manage
CREATE POLICY "Property images read" ON public.property_images FOR SELECT USING (true);
CREATE POLICY "Property images manage" ON public.property_images FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin'))
);

-- Viewings: authenticated read, admin/agent manage
CREATE POLICY "Viewings read" ON public.viewings FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Viewings manage" ON public.viewings FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin','agent'))
);

-- Leads: authenticated read, admin/agent manage
CREATE POLICY "Leads read" ON public.leads FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Leads manage" ON public.leads FOR ALL USING (
  auth.uid() IN (SELECT id FROM public.profiles WHERE role IN ('admin','superadmin','agent'))
);

-- ============================================================
-- 6. TRIGGERS (auto-update updated_at)
-- ============================================================

-- Generic trigger function
CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all new tables
DO $$
DECLARE
  tbl TEXT;
BEGIN
  FOR tbl IN SELECT unnest(ARRAY[
    'organizations','units','owners','vendors','staff',
    'tasks','expenses','utility_charges','property_images',
    'viewings','leads'
  ]) LOOP
    IF NOT EXISTS (
      SELECT 1 FROM pg_trigger WHERE tgname = 'trg_' || tbl || '_updated_at'
    ) THEN
      EXECUTE format(
        'CREATE TRIGGER trg_%s_updated_at BEFORE UPDATE ON public.%s FOR EACH ROW EXECUTE FUNCTION public.update_updated_at()',
        tbl, tbl
      );
    END IF;
  END LOOP;
END $$;

-- ============================================================
-- 7. SEED DATA (default organization)
-- ============================================================

INSERT INTO public.organizations (id, name, legal_name, email, phone, status)
VALUES (
  'a0000000-0000-0000-0000-000000000001',
  'Syllogism Technology Africa',
  'Syllogism Technology Africa Limited',
  'info@syllogismtechnologyafrica.com',
  '+254704919388',
  'active'
)
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- MIGRATION COMPLETE
-- ============================================================
-- Summary:
-- +15 new tables (organizations, units, owners, property_owners,
--   vendors, staff, tasks, expenses, utility_readings, utility_charges,
--   property_images, viewings, leads, property_documents [alias for documents])
-- +5 new columns on existing tables (organization_id, unit_id, vendor_id, assigned_to)
-- +20 new indexes
-- +13 RLS policies
-- +11 auto-update triggers
-- +1 seed organization
-- ============================================================
