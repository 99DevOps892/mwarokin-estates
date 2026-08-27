-- ============================================================
-- CEO Daily Briefing — Cron Setup Reference
-- ============================================================
-- The daily CEO briefing is triggered by an external cron job:
--
-- URL:  https://spnerrqumefbuuscumhw.supabase.co/functions/v1/ceo-briefing
-- Method: POST
-- Header: Content-Type: application/json
-- Body: {"action": "daily"}
-- Schedule: Daily at 6:00 AM EAT (0 3 * * * UTC)
--
-- Setup options:
-- 1. cron-job.org (free tier) — create account, add job
-- 2. GitHub Actions — scheduled workflow
-- 3. Supabase Dashboard — SQL editor with pg_cron
-- 4. Hostinger VPS — system crontab
--
-- The briefing auto-generates and stores in ceo_briefings table.
-- CEO is notified via the agent-dashboard.html real-time feed.
-- ============================================================

-- Verify ceo_briefings table exists
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'ceo_briefings') THEN
    RAISE NOTICE 'ceo_briefings table does not exist — run agentic_orchestration migration first';
  ELSE
    RAISE NOTICE 'ceo_briefings table exists — cron setup ready';
  END IF;
END $$;
