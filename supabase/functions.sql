-- ============================================================================
-- MWAROKIN ESTATES — DATABASE FUNCTIONS, TRIGGERS & VIEWS
-- Run AFTER schema.sql.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- AUTO-UPDATE updated_at on all core tables
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY['profiles','properties','tenants','leases','payments','maintenance_requests','communication_profiles','prospects','outreach_campaigns','outreach_threads']
  LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS trg_set_updated_at ON %I', t);
    EXECUTE format('CREATE TRIGGER trg_set_updated_at BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()', t);
  END LOOP;
END $$;

-- ----------------------------------------------------------------------------
-- Increment property view counter
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.increment_property_views(p_property_id UUID)
RETURNS void AS $$
BEGIN
  UPDATE properties SET views_count = views_count + 1 WHERE id = p_property_id;
  INSERT INTO property_views (property_id, view_count, last_viewed_at)
  VALUES (p_property_id, 1, now())
  ON CONFLICT (property_id)
  DO UPDATE SET view_count = property_views.view_count + 1, last_viewed_at = now();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- ----------------------------------------------------------------------------
-- Track user behavior (view/favorite/search)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.track_user_behavior(
  p_action TEXT,
  p_property_id UUID,
  p_search_query TEXT,
  p_filters JSONB
) RETURNS void AS $$
BEGIN
  INSERT INTO user_behavior (user_id, session_id, action_type, property_id, search_query, search_filters)
  VALUES (auth.uid(), COALESCE(current_setting('request.headers', true)::jsonb->>'x-session-id', 'anon'), p_action, p_property_id, p_search_query, p_filters);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- ----------------------------------------------------------------------------
-- Dashboard stats — single RPC for the whole dashboard
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.get_dashboard_stats()
RETURNS JSON AS $$
DECLARE
  result JSON;
BEGIN
  SELECT json_build_object(
    'total_properties',        (SELECT COUNT(*) FROM properties),
    'available_properties',    (SELECT COUNT(*) FROM properties WHERE status = 'available'),
    'rented_properties',       (SELECT COUNT(*) FROM properties WHERE status = 'rented'),
    'total_tenants',           (SELECT COUNT(*) FROM tenants),
    'active_leases',           (SELECT COUNT(*) FROM leases WHERE is_active = true),
    'pending_maintenance',     (SELECT COUNT(*) FROM maintenance_requests WHERE status = 'pending'),
    'total_payments',          (SELECT COUNT(*) FROM payments WHERE status = 'completed'),
    'monthly_revenue',         (SELECT COALESCE(SUM(amount),0) FROM payments WHERE status = 'completed' AND payment_date >= date_trunc('month', CURRENT_DATE)),
    'platform_fees',           (SELECT COALESCE(SUM(platform_fee),0) FROM payments WHERE status = 'completed'),
    'landlord_payouts',        (SELECT COALESCE(SUM(landlord_amount),0) FROM payments WHERE status = 'completed'),
    'overdue_payments',        (SELECT COUNT(*) FROM payments WHERE status IN ('pending','processing') AND due_date < CURRENT_DATE),
    'recent_properties',       (SELECT json_agg(json_build_object('id',id,'title',title,'price',price,'status',status)) FROM (SELECT * FROM properties ORDER BY created_at DESC LIMIT 5) p),
    'recent_payments',         (SELECT json_agg(json_build_object('id',id,'amount',amount,'platform_fee',platform_fee,'status',status,'payment_date',payment_date)) FROM (SELECT * FROM payments ORDER BY created_at DESC LIMIT 8) p)
  ) INTO result;
  RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- ----------------------------------------------------------------------------
-- Occupancy rate
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.get_occupancy_rate()
RETURNS TABLE (total_properties BIGINT, occupied_properties BIGINT, occupancy_rate DECIMAL(5,2)) AS $$
BEGIN
  RETURN QUERY
  SELECT
    COUNT(*)::BIGINT,
    COUNT(*) FILTER (WHERE status = 'rented')::BIGINT,
    ROUND(COUNT(*) FILTER (WHERE status = 'rented')::DECIMAL / NULLIF(COUNT(*),0) * 100, 2)
  FROM properties;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public;

-- ----------------------------------------------------------------------------
-- Approve / reject a bank-transfer payment (admin only)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.approve_payment(p_payment_id UUID)
RETURNS JSON AS $$
DECLARE
  v_payment RECORD;
BEGIN
  SELECT * INTO v_payment FROM payments WHERE id = p_payment_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'Payment not found'; END IF;

  UPDATE payments
  SET status = 'completed', split_status = 'completed', notes = COALESCE(notes,'') || ' | Approved by admin'
  WHERE id = p_payment_id;

  INSERT INTO audit_logs (user_id, action, table_name, record_id, new_data)
  VALUES (auth.uid(), 'payment_approved', 'payments', p_payment_id,
    jsonb_build_object('amount', v_payment.amount, 'landlord_amount', v_payment.landlord_amount, 'platform_fee', v_payment.platform_fee));

  RETURN jsonb_build_object('success', true, 'payment_id', p_payment_id);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

CREATE OR REPLACE FUNCTION public.reject_payment(p_payment_id UUID)
RETURNS JSON AS $$
BEGIN
  UPDATE payments SET status = 'failed', notes = 'Rejected by admin' WHERE id = p_payment_id;
  INSERT INTO audit_logs (user_id, action, table_name, record_id)
  VALUES (auth.uid(), 'payment_rejected', 'payments', p_payment_id);
  RETURN jsonb_build_object('success', true, 'payment_id', p_payment_id);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- ----------------------------------------------------------------------------
-- Mark overdue payments
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.check_overdue_payments()
RETURNS INTEGER AS $$
DECLARE
  updated INTEGER;
BEGIN
  UPDATE payments SET status = 'pending'
  WHERE status = 'processing' AND due_date < CURRENT_DATE;
  GET DIAGNOSTICS updated = ROW_COUNT;
  RETURN updated;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- ----------------------------------------------------------------------------
-- Create a notification + (optionally) an in-app message in one call
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.create_notification(
  p_user_id UUID,
  p_type TEXT,
  p_title TEXT,
  p_body TEXT,
  p_link TEXT DEFAULT NULL
) RETURNS void AS $$
BEGIN
  INSERT INTO notifications (user_id, type, title, body, link)
  VALUES (p_user_id, p_type, p_title, p_body, p_link);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- ----------------------------------------------------------------------------
-- AI Lead Scoring (agentic onboarding)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.calculate_lead_score(
  equity DECIMAL DEFAULT 0,
  years_owned INTEGER DEFAULT 0,
  property_value DECIMAL DEFAULT 0,
  intent_signals INTEGER DEFAULT 0,
  engagement INTEGER DEFAULT 0
) RETURNS INTEGER AS $$
BEGIN
  RETURN LEAST(100, GREATEST(0,
    (COALESCE(equity,0)::INT / 4) +
    (CASE WHEN years_owned > 10 THEN 20 ELSE years_owned END) +
    (CASE WHEN property_value > 20000000 THEN 15 ELSE 0 END) +
    (intent_signals * 5) +
    (engagement * 3)
  ));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ----------------------------------------------------------------------------
-- High-intent prospects for outreach campaigns
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.get_high_intent_prospects(min_score INTEGER DEFAULT 60, limit_count INTEGER DEFAULT 50)
RETURNS TABLE (id UUID, name TEXT, phone TEXT, email TEXT, lead_score INTEGER, property_address TEXT, estimated_value DECIMAL) AS $$
BEGIN
  RETURN QUERY
  SELECT p.id, p.name, p.phone, p.email, p.lead_score, p.property_address, p.estimated_value
  FROM prospects p
  WHERE p.lead_score >= min_score AND p.qualification_status NOT IN ('converted','hot')
  ORDER BY p.lead_score DESC
  LIMIT limit_count;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public;

-- ----------------------------------------------------------------------------
-- pgvector semantic property search (requires embedding column populated)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.search_properties_by_embedding(
  query_embedding vector(1536),
  match_threshold FLOAT DEFAULT 0.7,
  match_count INT DEFAULT 20
) RETURNS TABLE (id UUID, title TEXT, price DECIMAL, similarity FLOAT) AS $$
BEGIN
  RETURN QUERY
  SELECT p.id, p.title, p.price, 1 - (p.embedding <=> query_embedding) AS similarity
  FROM properties p
  WHERE p.status = 'available' AND p.embedding IS NOT NULL
    AND 1 - (p.embedding <=> query_embedding) > match_threshold
  ORDER BY p.embedding <=> query_embedding
  LIMIT match_count;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public;

-- ----------------------------------------------------------------------------
-- Views
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW public.v_communication_analytics AS
SELECT
  channel, status,
  COUNT(*) AS total_messages,
  ROUND(AVG(EXTRACT(EPOCH FROM (delivered_at - sent_at))), 2) AS avg_delivery_seconds
FROM message_queue
GROUP BY channel, status;

CREATE OR REPLACE VIEW public.v_payment_metrics AS
SELECT
  payment_method,
  COUNT(*) FILTER (WHERE status = 'completed') AS completed_count,
  COALESCE(SUM(amount) FILTER (WHERE status = 'completed'), 0) AS total_amount,
  COALESCE(SUM(platform_fee) FILTER (WHERE status = 'completed'), 0) AS total_platform_fees
FROM payments
GROUP BY payment_method;

CREATE OR REPLACE VIEW public.v_currency_dashboard AS
SELECT
  target_currency, rate, previous_rate, change_percentage, last_updated
FROM exchange_rates
WHERE base_currency = 'KES' AND target_currency <> 'KES'
ORDER BY change_percentage DESC;
