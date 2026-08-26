-- ============================================================
-- Mwarokin Estates — Add Indexes Matching ACTUAL Production Schema
-- Discovered via information_schema query on spnerrqumefbuuscumhw
-- ============================================================

-- Properties (actual columns: title, slug, agent_id, county, property_type, status, is_featured)
CREATE INDEX IF NOT EXISTS idx_properties_agent ON public.properties(agent_id);
CREATE INDEX IF NOT EXISTS idx_properties_county ON public.properties(county);
CREATE INDEX IF NOT EXISTS idx_properties_type ON public.properties(property_type);
CREATE INDEX IF NOT EXISTS idx_properties_status ON public.properties(status);
CREATE INDEX IF NOT EXISTS idx_properties_featured ON public.properties(is_featured) WHERE is_featured = true;
CREATE INDEX IF NOT EXISTS idx_properties_slug ON public.properties(slug);

-- Tenants (actual columns: phone, id_number, user_id)
CREATE INDEX IF NOT EXISTS idx_tenants_phone ON public.tenants(phone);
CREATE INDEX IF NOT EXISTS idx_tenants_id_number ON public.tenants(id_number);
CREATE INDEX IF NOT EXISTS idx_tenants_user ON public.tenants(user_id);

-- Leases (actual columns: property_id, tenant_id, landlord_id, is_active, start_date, end_date, rent_amount)
CREATE INDEX IF NOT EXISTS idx_leases_property ON public.leases(property_id);
CREATE INDEX IF NOT EXISTS idx_leases_tenant ON public.leases(tenant_id);
CREATE INDEX IF NOT EXISTS idx_leases_landlord ON public.leases(landlord_id);
CREATE INDEX IF NOT EXISTS idx_leases_active ON public.leases(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_leases_dates ON public.leases(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_leases_expiring ON public.leases(end_date) WHERE is_active = true;

-- Payments (actual columns: transaction_id, provider_reference, payment_date, status, lease_id, tenant_id, property_id, landlord_id, payment_method, split_status)
CREATE INDEX IF NOT EXISTS idx_payments_pending ON public.payments(status, payment_date) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_payments_transaction ON public.payments(transaction_id);
CREATE INDEX IF NOT EXISTS idx_payments_provider_ref ON public.payments(provider_reference);
CREATE INDEX IF NOT EXISTS idx_payments_lease ON public.payments(lease_id, payment_date);
CREATE INDEX IF NOT EXISTS idx_payments_tenant ON public.payments(tenant_id);
CREATE INDEX IF NOT EXISTS idx_payments_property ON public.payments(property_id);
CREATE INDEX IF NOT EXISTS idx_payments_landlord ON public.payments(landlord_id);
CREATE INDEX IF NOT EXISTS idx_payments_method ON public.payments(payment_method, status);
CREATE INDEX IF NOT EXISTS idx_payments_split ON public.payments(split_status);
CREATE INDEX IF NOT EXISTS idx_payments_checkout ON public.payments(checkout_request_id) WHERE checkout_request_id IS NOT NULL;

-- Notifications
CREATE INDEX IF NOT EXISTS idx_notifications_user ON public.notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON public.notifications(type, created_at DESC);

-- Documents
CREATE INDEX IF NOT EXISTS idx_documents_property ON public.documents(property_id);
CREATE INDEX IF NOT EXISTS idx_documents_tenant ON public.documents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_documents_lease ON public.documents(lease_id);

-- Maintenance
CREATE INDEX IF NOT EXISTS idx_maintenance_property ON public.maintenance_requests(property_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_status ON public.maintenance_requests(status, priority);

-- Prospects
CREATE INDEX IF NOT EXISTS idx_prospects_score ON public.prospects(lead_score DESC);
CREATE INDEX IF NOT EXISTS idx_prospects_source ON public.prospects(source, discovered_at DESC);

-- Outreach
CREATE INDEX IF NOT EXISTS idx_outreach_campaign ON public.outreach_campaigns(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_outreach_threads ON public.outreach_threads(campaign_id, status);

-- Message queue
CREATE INDEX IF NOT EXISTS idx_message_queue_status ON public.message_queue(status, scheduled_for);
CREATE INDEX IF NOT EXISTS idx_message_queue_channel ON public.message_queue(channel, status);

-- Translations
CREATE INDEX IF NOT EXISTS idx_translations_lookup ON public.translations(language_code, namespace, key);

-- Exchange rates
CREATE INDEX IF NOT EXISTS idx_exchange_rates_pair ON public.exchange_rates(base_currency, target_currency);

-- User behavior
CREATE INDEX IF NOT EXISTS idx_behavior_user ON public.user_behavior(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_behavior_property ON public.user_behavior(property_id, action_type);

-- Communication profiles
CREATE INDEX IF NOT EXISTS idx_comm_profiles_user ON public.communication_profiles(user_id);

-- Property views
CREATE INDEX IF NOT EXISTS idx_property_views ON public.property_views(property_id, view_count DESC);

-- Platform settings
CREATE INDEX IF NOT EXISTS idx_platform_settings_key ON public.platform_settings(key);

-- Audit log (we created this table)
CREATE INDEX IF NOT EXISTS idx_audit_log_user ON public.audit_log(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_resource ON public.audit_log(resource_type, resource_id);
