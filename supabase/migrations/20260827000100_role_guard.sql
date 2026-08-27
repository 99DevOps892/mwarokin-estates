-- ============================================================
-- Mwarokin Estates — Server-side role enforcement
-- ------------------------------------------------------------
-- 1. Trigger: block non-admins from setting/adopting a privileged role
--    ('agent','admin','superadmin') on profiles via direct client writes.
-- 2. RPC promote_user_role: the ONLY way to elevate a user. Guarded to
--    existing admins/superadmins. Callable from the admin console.
-- Additive + idempotent. Safe to re-run.
-- ============================================================

-- Guard trigger
CREATE OR REPLACE FUNCTION public.guard_profile_role()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  caller_role TEXT;
BEGIN
  -- Determine the caller's current role from their profile.
  SELECT role INTO caller_role
  FROM public.profiles
  WHERE id = auth.uid();

  -- Privileged roles require an existing admin/superadmin.
  IF NEW.role IN ('agent', 'admin', 'superadmin') THEN
    IF caller_role IS NULL OR caller_role NOT IN ('admin', 'superadmin') THEN
      RAISE EXCEPTION 'Not authorized to assign privileged role';
    END IF;
  END IF;

  -- A non-admin may never escalate themselves upward.
  IF caller_role IS NULL OR caller_role NOT IN ('admin', 'superadmin') THEN
    IF OLD.role IN ('agent', 'admin', 'superadmin') THEN
      RAISE EXCEPTION 'Cannot modify privileged role';
    END IF;
    IF NEW.role IN ('agent', 'admin', 'superadmin')
       AND NEW.role <> OLD.role THEN
      RAISE EXCEPTION 'Cannot escalate role without admin';
    END IF;
  END IF;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_profiles_guard_role ON public.profiles;
CREATE TRIGGER trg_profiles_guard_role
  BEFORE INSERT OR UPDATE OF role ON public.profiles
  FOR EACH ROW
  EXECUTE FUNCTION public.guard_profile_role();

-- Admin-only promotion RPC
CREATE OR REPLACE FUNCTION public.promote_user_role(p_user_id UUID, p_role TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  caller_role TEXT;
BEGIN
  SELECT role INTO caller_role FROM public.profiles WHERE id = auth.uid();
  IF caller_role IS NULL OR caller_role NOT IN ('admin', 'superadmin') THEN
    RAISE EXCEPTION 'Only an admin can promote roles';
  END IF;
  IF p_role NOT IN ('tenant', 'landlord', 'caretaker', 'agent', 'admin') THEN
    RAISE EXCEPTION 'Invalid role';
  END IF;
  UPDATE public.profiles SET role = p_role WHERE id = p_user_id;
  RETURN FOUND;
END;
$$;

REVOKE ALL ON FUNCTION public.promote_user_role(UUID, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.promote_user_role(UUID, TEXT) TO authenticated;
