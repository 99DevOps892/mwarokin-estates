-- ============================================================
-- Mwarokin Estates — Business Logic (migration 2 of 3)
-- 95/5 split trigger, dashboard stats, approve/reject payment,
-- property view counter, high-intent prospects.
-- ============================================================

-- 95/5 revenue split -----------------------------------------
-- Reads platform commission % from platform_settings
-- ('financial_distribution' -> {"platform_percent": 5}); falls back to 5%.
create or replace function public.apply_payment_split()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  v_percent numeric := 5.0;
begin
  begin
    select coalesce((value->>'platform_percent')::numeric, 5.0)
      into v_percent
      from platform_settings
     where key = 'financial_distribution';
  exception when others then
    v_percent := 5.0;
  end;

  new.platform_amount := round(new.amount * v_percent / 100.0, 2);
  new.landlord_amount := new.amount - new.platform_amount;
  return new;
end;
$$;

drop trigger if exists trg_payment_split on payments;
create trigger trg_payment_split
  before insert on payments
  for each row execute function public.apply_payment_split();

-- Dashboard stats (used by dashboard.js + payments.js) --------
create or replace function public.get_dashboard_stats()
returns jsonb
language sql
stable
security definer
set search_path = public
as $$
  select jsonb_build_object(
    'total_properties',     (select count(*) from properties),
    'available_properties', (select count(*) from properties where status = 'available'),
    'active_leases',        (select count(*) from leases where status = 'active'),
    'monthly_revenue',      coalesce((
       select sum(amount) from payments
        where status in ('paid','approved')
          and payment_date >= date_trunc('month', current_date)::date), 0),
    'platform_fees',        coalesce((
       select sum(platform_amount) from payments
        where status in ('paid','approved')
          and payment_date >= date_trunc('month', current_date)::date), 0),
    'landlord_payouts',     coalesce((
       select sum(landlord_amount) from payments
        where status in ('paid','approved')
          and payment_date >= date_trunc('month', current_date)::date), 0),
    'pending',              (select count(*) from payments where status in ('pending','processing'))
  );
$$;

revoke all on function public.get_dashboard_stats() from public;
grant execute on function public.get_dashboard_stats() to anon, authenticated;

-- Approve / reject payment (admin or owning landlord only) ----
create or replace function public.approve_payment(p_payment_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  p            payments;
  v_role       text;
  v_tenant_uid uuid;
begin
  select * into p from payments where id = p_payment_id;
  if not found then
    raise exception 'Payment not found';
  end if;

  if p.status not in ('pending','processing') then
    raise exception 'Payment is not in an approvable state (%).', p.status;
  end if;

  select role into v_role from profiles where id = auth.uid();
  if coalesce(v_role,'') <> 'admin' then
    if p.landlord_id is null or not exists (
      select 1 from landlords l
       where l.id = p.landlord_id and l.user_id = auth.uid()
    ) then
      raise exception 'Not authorized to approve this payment';
    end if;
  end if;

  update payments
     set status = 'approved', approved_by = auth.uid(), paid_at = now()
   where id = p_payment_id
   returning * into p;

  select user_id into v_tenant_uid from tenants where id = p.tenant_id;

  insert into notifications (user_id, type, title, message)
  values (v_tenant_uid, 'payment',
          'Payment confirmed',
          'Your payment of ' || p.amount::text || ' was received and confirmed. Receipt: '
          || coalesce(p.transaction_id, p.id::text));

  insert into audit_logs (user_id, action, entity_type, entity_id, details)
  values (auth.uid(), 'payment.approved', 'payments', p.id,
          jsonb_build_object('amount', p.amount, 'method', p.payment_method));

  return to_jsonb(p);
end;
$$;

create or replace function public.reject_payment(p_payment_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  p        payments;
  v_role   text;
begin
  select * into p from payments where id = p_payment_id;
  if not found then
    raise exception 'Payment not found';
  end if;

  select role into v_role from profiles where id = auth.uid();

  if coalesce(v_role,'') <> 'admin' then
    if p.landlord_id is null or not exists (
      select 1 from landlords l
       where l.id = p.landlord_id and l.user_id = auth.uid()
    ) then
      raise exception 'Not authorized to reject this payment';
    end if;
  end if;

  update payments set status = 'rejected' where id = p_payment_id returning * into p;

  insert into audit_logs (user_id, action, entity_type, entity_id, details)
  values (auth.uid(), 'payment.rejected', 'payments', p.id,
          jsonb_build_object('amount', p.amount));

  return to_jsonb(p);
end;
$$;

revoke all on function public.approve_payment(uuid), public.reject_payment(uuid) from public;
grant execute on function public.approve_payment(uuid), public.reject_payment(uuid) to authenticated;

-- Property view counter (public marketing site) ---------------
create or replace function public.increment_property_views(p_property_id uuid)
returns void
language sql
security definer
set search_path = public
as $$
  update properties set views = views + 1 where id = p_property_id;
$$;

revoke all on function public.increment_property_views(uuid) from public;
grant execute on function public.increment_property_views(uuid) to anon, authenticated;

-- High-intent prospects (admin campaign runner) ---------------
create or replace function public.get_high_intent_prospects(
  min_score   int default 60,
  limit_count int default 20
)
returns setof prospects
language sql
stable
security definer
set search_path = public
as $$
  select *
    from prospects
   where lead_score >= min_score
     and status in ('new','contacted')
   order by lead_score desc
   limit greatest(limit_count, 1);
$$;

revoke all on function public.get_high_intent_prospects(int, int) from public;
grant execute on function public.get_high_intent_prospects(int, int) to authenticated;

-- Tenant balance helper (kept for API completeness) -----------
create or replace function public.update_tenant_balance(
  p_tenant_id uuid,
  p_delta     numeric
)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  update tenants
     set balance = greatest(balance + p_delta, 0)
   where id = p_tenant_id;
end;
$$;
