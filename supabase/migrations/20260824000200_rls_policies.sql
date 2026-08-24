-- ============================================================
-- Mwarokin Estates — Row Level Security (migration 3 of 3)
-- Public property listings, owner-scoped private data,
-- admin full access via public.is_admin().
-- ============================================================

alter table agencies                enable row level security;
alter table landlords               enable row level security;
alter table tenants                 enable row level security;
alter table properties              enable row level security;
alter table leases                  enable row level security;
alter table payments                enable row level security;
alter table notifications           enable row level security;
alter table maintenance_requests    enable row level security;
alter table prospects               enable row level security;
alter table platform_settings       enable row level security;
alter table audit_logs              enable row level security;
alter table exchange_rates          enable row level security;
alter table translations            enable row level security;
alter table communication_profiles  enable row level security;
alter table profiles                enable row level security;

-- Profiles ----------------------------------------------------
create policy "profiles_select_own_or_admin"
  on profiles for select
  using (id = auth.uid() or public.is_admin());

create policy "profiles_update_own"
  on profiles for update
  using (id = auth.uid())
  with check (id = auth.uid() and role = public.my_role());

create policy "profiles_insert_self"
  on profiles for insert
  with check (id = auth.uid());

create policy "profiles_admin_all"
  on profiles for all
  using (public.is_admin())
  with check (public.is_admin());

-- Communication profiles --------------------------------------
create policy "commprofile_select_own"
  on communication_profiles for select
  using (user_id = auth.uid());

create policy "commprofile_write_own"
  on communication_profiles for insert
  with check (user_id = auth.uid());

create policy "commprofile_update_own"
  on communication_profiles for update
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

-- Agencies ----------------------------------------------------
create policy "agencies_read_all"
  on agencies for select using (true);

create policy "agencies_admin_write"
  on agencies for all
  using (public.is_admin())
  with check (public.is_admin());

-- Landlords --------------------------------------------------
create policy "landlords_select_own_or_admin"
  on landlords for select
  using (user_id = auth.uid() or public.is_admin());

create policy "landlords_write_own"
  on landlords for insert
  with check (user_id = auth.uid());

create policy "landlords_update_own"
  on landlords for update
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

create policy "landlords_admin_all"
  on landlords for all
  using (public.is_admin())
  with check (public.is_admin());

-- Tenants -----------------------------------------------------
create policy "tenants_select_own_or_admin"
  on tenants for select
  using (user_id = auth.uid() or public.is_admin());

create policy "tenants_write_self"
  on tenants for insert
  with check (user_id = auth.uid());

create policy "tenants_update_own"
  on tenants for update
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

create policy "tenants_admin_all"
  on tenants for all
  using (public.is_admin())
  with check (public.is_admin());

-- Properties: public read (marketing listings) -----------------
create policy "properties_read_public"
  on properties for select
  using (true);

create policy "properties_landlord_write"
  on properties for insert
  with check (
    exists (select 1 from landlords l where l.id = landlord_id and l.user_id = auth.uid())
    or public.is_admin()
  );

create policy "properties_landlord_update"
  on properties for update
  using (
    exists (select 1 from landlords l where l.id = properties.landlord_id and l.user_id = auth.uid())
    or public.is_admin()
  )
  with check (
    exists (select 1 from landlords l where l.id = properties.landlord_id and l.user_id = auth.uid())
    or public.is_admin()
  );

create policy "properties_admin_delete"
  on properties for delete
  using (public.is_admin());

-- Leases -------------------------------------------------------
create policy "leases_read_scoped"
  on leases for select
  using (
    exists (select 1 from tenants t where t.id = leases.tenant_id and t.user_id = auth.uid())
    or exists (select 1 from properties p join landlords l on l.id = p.landlord_id
               where p.id = leases.property_id and l.user_id = auth.uid())
    or public.is_admin()
  );

create policy "leases_admin_write"
  on leases for all
  using (public.is_admin())
  with check (public.is_admin());

-- Payments -----------------------------------------------------
create policy "payments_read_scoped"
  on payments for select
  using (
    exists (select 1 from tenants t where t.id = payments.tenant_id and t.user_id = auth.uid())
    or exists (select 1 from landlords l where l.id = payments.landlord_id and l.user_id = auth.uid())
    or public.is_admin()
  );

create policy "payments_tenant_create"
  on payments for insert
  with check (
    auth.uid() is not null
    and (
      tenant_id is null
      or exists (select 1 from tenants t where t.id = payments.tenant_id and t.user_id = auth.uid())
    )
  );

create policy "payments_admin_update"
  on payments for update
  using (public.is_admin())
  with check (public.is_admin());

-- Notifications: strictly own -----------------------------------
create policy "notifications_select_own"
  on notifications for select
  using (user_id = auth.uid());

create policy "notifications_update_own"
  on notifications for update
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

-- Maintenance requests -------------------------------------------
create policy "maint_read_scoped"
  on maintenance_requests for select
  using (
    exists (select 1 from tenants t where t.id = maintenance_requests.tenant_id and t.user_id = auth.uid())
    or public.is_admin()
  );

create policy "maint_tenant_create"
  on maintenance_requests for insert
  with check (
    auth.uid() is not null
    and (
      tenant_id is null
      or exists (select 1 from tenants t where t.id = maintenance_requests.tenant_id and t.user_id = auth.uid())
    )
  );

create policy "maint_admin_write"
  on maintenance_requests for all
  using (public.is_admin())
  with check (public.is_admin());

-- Prospects: admin only -------------------------------------------
create policy "prospects_admin_read"
  on prospects for select
  using (public.is_admin());

create policy "prospects_authenticated_insert"
  on prospects for insert
  with check (auth.role() = 'authenticated');

create policy "prospects_admin_write"
  on prospects for all
  using (public.is_admin())
  with check (public.is_admin());

-- Platform settings: public read ----------------------------------
create policy "settings_read_public"
  on platform_settings for select using (true);

create policy "settings_admin_write"
  on platform_settings for all
  using (public.is_admin())
  with check (public.is_admin());

-- Audit logs: admin only -------------------------------------------
create policy "audit_admin_read"
  on audit_logs for select
  using (public.is_admin());

-- Exchange rates & translations: public read ------------------------
create policy "rates_read_public"   on exchange_rates for select using (true);
create policy "rates_admin_write"   on exchange_rates for all
  using (public.is_admin()) with check (public.is_admin());
create policy "i18n_read_public"    on translations for select using (is_active);
create policy "i18n_admin_write"    on translations for all
  using (public.is_admin()) with check (public.is_admin());

-- ============================================================
-- Seed data
-- ============================================================

insert into platform_settings (key, value) values
  ('financial_distribution', '{"platform_percent": 5, "landlord_percent": 95}'),
  ('mpesa',  '{"enabled": true,  "environment": "sandbox"}'),
  ('airtel', '{"enabled": true,  "environment": "sandbox"}')
on conflict (key) do nothing;

insert into exchange_rates (base_currency, target_currency, rate) values
  ('KES','USD', 0.0077),
  ('KES','EUR', 0.0071),
  ('KES','GBP', 0.0061)
on conflict (base_currency, target_currency) do nothing;

insert into translations (language_code, namespace, key, value) values
  ('sw','common','welcome','Karibu Mwarokin Estates'),
  ('sw','common','pay_rent','Lipa Kodi'),
  ('fr','common','welcome','Bienvenue chez Mwarokin Estates'),
  ('de','common','welcome','Willkommen bei Mwarokin Estates'),
  ('ar','common','welcome','مرحباً بكم في Mwarokin Estates')
on conflict (language_code, namespace, key) do nothing;
