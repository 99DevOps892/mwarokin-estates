-- ============================================================
-- Mwarokin Estates — Core Schema (migration 1 of 3)
-- Aligned to: Mwarokin DB Schema docs + app/js frontend contract
-- Tables: agencies, landlords, tenants, properties, leases,
--         payments, notifications, maintenance_requests,
--         prospects, platform_settings, audit_logs,
--         exchange_rates, translations, communication_profiles
-- ============================================================

-- Extensions -------------------------------------------------
create extension if not exists pgcrypto;

-- Helpers ----------------------------------------------------
create schema if not exists public;

-- Role helper used by RLS policies (SECURITY DEFINER avoids recursion)
create or replace function public.is_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from profiles
    where id = auth.uid() and role = 'admin'
  );
$$;

-- Caller's own role, read through a definer barrier so policies on
-- `profiles` can reference it without self-recursion.
create or replace function public.my_role()
returns text
language sql
stable
security definer
set search_path = public
as $$
  select role from profiles where id = auth.uid();
$$;

-- Agencies ---------------------------------------------------
create table if not exists agencies (
  id          uuid primary key default gen_random_uuid(),
  name        varchar(120) not null,
  phone       varchar(20),
  email       varchar(120),
  address     text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- Landlords -------------------------------------------------
create table if not exists landlords (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid unique references auth.users(id) on delete set null,
  first_name      varchar(60) not null,
  last_name       varchar(60) not null,
  phone           varchar(20),
  email           varchar(120),
  bank_account    varchar(60),
  id_passport     varchar(40),
  profile_picture text,
  agency_id       uuid references agencies(id) on delete set null,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

-- Tenants ----------------------------------------------------
create table if not exists tenants (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid unique references auth.users(id) on delete set null,
  first_name      varchar(60) not null,
  last_name       varchar(60) not null,
  phone           varchar(20),
  email           varchar(120),
  gender          varchar(10),
  id_passport     varchar(40),
  profile_picture text,
  balance         numeric(12,2) not null default 0 check (balance >= 0),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create index if not exists idx_tenants_user on tenants(user_id);

-- Properties -------------------------------------------------
-- NOTE: `title` and `status` are required by app/js/properties.js
create table if not exists properties (
  id            uuid primary key default gen_random_uuid(),
  title         varchar(160) not null,
  description   text,
  property_type varchar(40) not null default 'apartment',
  status        varchar(20) not null default 'available'
                check (status in ('available','occupied','maintenance','inactive')),
  house_no      varchar(30),
  address       text not null,
  amenities     jsonb not null default '{}'::jsonb,
  images        text[] not null default '{}',
  rent_amount   numeric(12,2) not null default 0 check (rent_amount >= 0),
  bedrooms      int,
  bathrooms     int,
  is_featured   boolean not null default false,
  views         int not null default 0,
  landlord_id   uuid not null references landlords(id) on delete restrict,
  agency_id     uuid references agencies(id) on delete set null,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create index if not exists idx_properties_landlord on properties(landlord_id);
create index if not exists idx_properties_status   on properties(status);
create index if not exists idx_properties_featured on properties(is_featured);

-- Leases -----------------------------------------------------
create table if not exists leases (
  id          uuid primary key default gen_random_uuid(),
  property_id uuid not null references properties(id) on delete cascade,
  tenant_id   uuid not null references tenants(id) on delete cascade,
  start_date  date not null,
  end_date    date,
  rent_amount numeric(12,2) not null,
  deposit     numeric(12,2),
  status      varchar(20) not null default 'active'
              check (status in ('active','expired','terminated')),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create index if not exists idx_leases_property on leases(property_id);
create index if not exists idx_leases_tenant   on leases(tenant_id);
create index if not exists idx_leases_status   on leases(status);

-- Payments ---------------------------------------------------
-- Columns match app/js/payments.js payload exactly.
-- platform_amount / landlord_amount are filled by trigger (95/5 split).
create table if not exists payments (
  id                 uuid primary key default gen_random_uuid(),
  lease_id           uuid references leases(id) on delete set null,
  tenant_id          uuid references tenants(id) on delete set null,
  property_id        uuid references properties(id) on delete set null,
  landlord_id        uuid references landlords(id) on delete set null,
  amount             numeric(12,2) not null check (amount > 0),
  platform_amount    numeric(12,2) not null default 0,
  landlord_amount    numeric(12,2) not null default 0,
  payment_method     varchar(30) not null default 'mpesa',
  payment_date       date not null default current_date,
  due_date           date,
  transaction_id     varchar(80) unique,
  checkout_request_id varchar(120),
  mpesa_receipt      varchar(60),
  phone              varchar(20),
  status             varchar(20) not null default 'processing'
                     check (status in ('pending','processing','paid','approved','rejected','failed')),
  metadata           jsonb not null default '{}'::jsonb,
  approved_by        uuid references auth.users(id) on delete set null,
  paid_at            timestamptz,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);

create index if not exists idx_payments_tenant    on payments(tenant_id);
create index if not exists idx_payments_landlord  on payments(landlord_id);
create index if not exists idx_payments_status    on payments(status);
create index if not exists idx_payments_lease     on payments(lease_id);
create index if not exists idx_payments_checkout  on payments(checkout_request_id);

-- Notifications ----------------------------------------------
-- Uses user_id + is_read + read_at per app/js/dashboard.js
create table if not exists notifications (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid references auth.users(id) on delete cascade,
  type       varchar(40) not null default 'general',
  title      varchar(160),
  message    text not null,
  is_read    boolean not null default false,
  read_at    timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists idx_notifications_user on notifications(user_id, created_at desc);

-- Maintenance requests ---------------------------------------
create table if not exists maintenance_requests (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid references tenants(id) on delete set null,
  property_id  uuid references properties(id) on delete set null,
  request_type varchar(40) not null default 'general',
  priority     varchar(20) not null default 'medium'
               check (priority in ('low','medium','high','urgent')),
  description  text,
  status       varchar(20) not null default 'open'
               check (status in ('open','in_progress','resolved','closed')),
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

-- Prospects (AI lead pipeline) -------------------------------
create table if not exists prospects (
  id           uuid primary key default gen_random_uuid(),
  name         varchar(160),
  phone        varchar(20),
  email        varchar(120),
  source       varchar(60) not null default 'manual',
  lead_score   int not null default 50 check (lead_score between 0 and 100),
  intent_score int,
  status       varchar(20) not null default 'new'
               check (status in ('new','contacted','qualified','onboarded','lost')),
  metadata     jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

create index if not exists idx_prospects_score on prospects(lead_score desc);

-- Platform settings (key/value) ------------------------------
create table if not exists platform_settings (
  key        varchar(80) primary key,
  value      jsonb not null,
  updated_at timestamptz not null default now()
);

-- Audit logs -------------------------------------------------
create table if not exists audit_logs (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users(id) on delete set null,
  action      varchar(80) not null,
  entity_type varchar(40),
  entity_id   uuid,
  details     jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now()
);

create index if not exists idx_audit_created on audit_logs(created_at desc);

-- Exchange rates (multi-currency) ----------------------------
create table if not exists exchange_rates (
  id             uuid primary key default gen_random_uuid(),
  base_currency  varchar(3) not null default 'KES',
  target_currency varchar(3) not null,
  rate           numeric(14,6) not null check (rate > 0),
  fetched_at     timestamptz not null default now(),
  unique (base_currency, target_currency)
);

-- Translations (i18n) ----------------------------------------
create table if not exists translations (
  id            uuid primary key default gen_random_uuid(),
  language_code varchar(5) not null,
  namespace     varchar(60) not null default 'common',
  key           varchar(160) not null,
  value         text not null,
  is_active     boolean not null default true,
  unique (language_code, namespace, key)
);

-- Communication profiles (channel preferences) ---------------
create table if not exists communication_profiles (
  user_id         uuid primary key references auth.users(id) on delete cascade,
  email_enabled   boolean not null default true,
  sms_enabled     boolean not null default true,
  whatsapp_enabled boolean not null default false,
  push_enabled    boolean not null default true,
  language        varchar(5) not null default 'en',
  updated_at      timestamptz not null default now()
);

-- Profiles (auth mirror) --------------------------------------
create table if not exists profiles (
  id                 uuid primary key references auth.users(id) on delete cascade,
  full_name          varchar(160) not null default '',
  phone              varchar(20) not null default '',
  role               varchar(20) not null default 'tenant'
                     check (role in ('tenant','landlord','admin')),
  preferred_language varchar(5) not null default 'en',
  preferred_currency varchar(3) not null default 'KES',
  avatar_url         text,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);

-- Auto-create profile + communication row for every new auth user
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, full_name, phone)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'full_name', ''),
    coalesce(new.raw_user_meta_data->>'phone', '')
  )
  on conflict (id) do nothing;

  insert into public.communication_profiles (user_id)
  values (new.id)
  on conflict (user_id) do nothing;

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- updated_at touch trigger ------------------------------------
create or replace function public.touch_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

do $$
declare t text;
begin
  foreach t in array array[
    'agencies','landlords','tenants','properties','leases',
    'payments','maintenance_requests','prospects','profiles'
  ]
  loop
    execute format('drop trigger if exists trg_touch_%1$s on %1$s;', t);
    execute format(
      'create trigger trg_touch_%1$s before update on %1$s
       for each row execute function public.touch_updated_at();', t);
  end loop;
end $$;
