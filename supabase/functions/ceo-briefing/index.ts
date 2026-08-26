import { serve } from "https://deno.land/std@0.177.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { corsHeaders, json, error, preflight } from "../_shared/cors.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const OLLAMA_URL = Deno.env.get("OLLAMA_URL") || "http://127.0.0.1:11434";

serve(async (req: Request) => {
  if (preflight(req)) return preflight(req);

  try {
    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);
    const body = await req.json();
    const { action } = body;

    switch (action) {
      case "daily": {
        const now = new Date();
        const yesterday = new Date(now.getTime() - 86400000);

        // Parallel data fetch
        const [properties, payments, tenants, tasks, agents, revenue, events] = await Promise.all([
          supabase.from("properties").select("id, status, property_type, price, county"),
          supabase.from("payments").select("id, amount, status, payment_method, created_at, platform_fee"),
          supabase.from("tenants").select("id, created_at"),
          supabase.from("agent_tasks").select("id, status, domain, task_type, tokens_used, cost_ksh").gte("created_at", yesterday.toISOString()),
          supabase.from("agent_registry").select("agent_id, agent_name, domain, status, total_tasks_completed, error_rate, last_heartbeat"),
          supabase.from("revenue_ledger").select("id, fee_amount, platform_revenue, domain, created_at").gte("created_at", yesterday.toISOString()),
          supabase.from("agent_events").select("id, event_type, created_at").gte("created_at", yesterday.toISOString()),
        ]);

        // Calculate KPIs
        const totalRevenue = payments.data?.filter((p: any) => p.status === "confirmed").reduce((s: number, p: any) => s + p.amount, 0) || 0;
        const platformFees = payments.data?.filter((p: any) => p.status === "confirmed").reduce((s: number, p: any) => s + (p.platform_fee || 0), 0) || 0;
        const pendingPayments = payments.data?.filter((p: any) => p.status === "pending").length || 0;
        const totalTasks = tasks.data?.length || 0;
        const completedTasks = tasks.data?.filter((t: any) => t.status === "completed").length || 0;
        const failedTasks = tasks.data?.filter((t: any) => t.status === "failed").length || 0;
        const activeAgents = agents.data?.filter((a: any) => a.status !== "offline").length || 0;
        const totalTokens = tasks.data?.reduce((s: number, t: any) => s + (t.tokens_used || 0), 0) || 0;
        const totalCost = tasks.data?.reduce((s: number, t: any) => s + (t.cost_ksh || 0), 0) || 0;

        // Revenue by domain
        const revenueByDomain: Record<string, number> = {};
        (revenue.data || []).forEach((r: any) => {
          revenueByDomain[r.domain] = (revenueByDomain[r.domain] || 0) + r.platform_revenue;
        });

        // Task breakdown by domain
        const tasksByDomain: Record<string, { total: number; completed: number; failed: number }> = {};
        (tasks.data || []).forEach((t: any) => {
          if (!tasksByDomain[t.domain]) tasksByDomain[t.domain] = { total: 0, completed: 0, failed: 0 };
          tasksByDomain[t.domain].total++;
          if (t.status === "completed") tasksByDomain[t.domain].completed++;
          if (t.status === "failed") tasksByDomain[t.domain].failed++;
        });

        // Agent performance
        const agentPerf = (agents.data || []).map((a: any) => ({
          id: a.agent_id,
          name: a.agent_name,
          domain: a.domain,
          status: a.status,
          tasks: a.total_tasks_completed,
          error_rate: a.error_rate,
          last_seen: a.last_heartbeat,
        }));

        // Alerts
        const alerts: any[] = [];
        if (pendingPayments > 10) alerts.push({ severity: "high", message: `${pendingPayments} pending payments need attention` });
        if (failedTasks > 5) alerts.push({ severity: "critical", message: `${failedTasks} tasks failed — check agent health` });
        if (activeAgents < agents.data!.length * 0.8) alerts.push({ severity: "medium", message: `${agents.data!.length - activeAgents} agents offline` });
        (agents.data || []).filter((a: any) => a.error_rate > 10).forEach((a: any) => {
          alerts.push({ severity: "high", message: `${a.agent_id} error rate ${a.error_rate}% — needs attention` });
        });

        // Recommendations
        const recs: any[] = [];
        if (totalRevenue < 50000) recs.push({ type: "revenue", message: "Revenue below target — consider increasing marketing outreach" });
        if (totalTasks > 0 && completedTasks / totalTasks < 0.8) recs.push({ type: "performance", message: `Task success rate ${(completedTasks / totalTasks * 100).toFixed(1)}% — optimize agent prompts` });
        if (totalCost > 1000) recs.push({ type: "cost", message: `AI cost KSh ${totalCost.toFixed(2)} — review model usage` });

        const briefing = {
          title: `Executive Daily Brief — ${now.toLocaleDateString("en-KE", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}`,
          summary: `Mwarokin generated KSh ${totalRevenue.toLocaleString()} from ${payments.data?.filter((p: any) => p.status === "confirmed").length || 0} payments. Platform earned KSh ${platformFees.toLocaleString()} in fees. ${completedTasks}/${totalTasks} AI tasks completed across ${activeAgents} active agents. ${pendingPayments} payments awaiting confirmation.`,
          kpis: {
            revenue: { total_ksh: totalRevenue, platform_fees_ksh: platformFees, payment_count: payments.data?.length || 0, pending: pendingPayments },
            properties: { active: properties.data?.filter((p: any) => p.status === "active").length || 0, total: properties.data?.length || 0 },
            tenants: { total: tenants.data?.length || 0 },
            agents: { active: activeAgents, total: agents.data?.length || 0, uptime_pct: agents.data?.length ? Number(((activeAgents / agents.data.length) * 100).toFixed(1)) : 0 },
            ai: { tasks_total: totalTasks, completed: completedTasks, failed: failedTasks, tokens_used: totalTokens, cost_ksh: totalCost, success_rate_pct: totalTasks > 0 ? Number(((completedTasks / totalTasks) * 100).toFixed(1)) : 100 },
            revenue_by_domain: revenueByDomain,
            tasks_by_domain: tasksByDomain,
          },
          alerts,
          recommendations: recs,
          agents: agentPerf,
          bank: {
            revenue_account: "Co-op Bank 01192643932500",
            ceo_account: "Equity Bank 0730178466611",
            ceo_monthly: "KSh 300,000",
          },
        };

        // Store briefing
        await supabase.from("ceo_briefings").insert({
          briefing_type: "daily",
          title: briefing.title,
          summary: briefing.summary,
          kpis: briefing.kpis,
          alerts: briefing.alerts,
          recommendations: briefing.recommendations,
          agent_performance: briefing.agents,
          revenue_summary: briefing.bank,
        });

        return json({ success: true, briefing });
      }

      case "list": {
        const limit = body.limit || 10;
        const type = body.type || null;

        let query = supabase
          .from("ceo_briefings")
          .select("*")
          .order("created_at", { ascending: false })
          .limit(limit);

        if (type) query = query.eq("briefing_type", type);

        const { data } = await query;
        return json({ success: true, briefings: data });
      }

      case "mark_read": {
        await supabase
          .from("ceo_briefings")
          .update({ read_at: new Date().toISOString() })
          .eq("id", body.id);
        return json({ success: true });
      }

      case "alert": {
        // Store alert and notify CEO
        const alertData = {
          briefing_type: "alert",
          title: `Alert: ${body.title || "System Alert"}`,
          summary: body.message || "No details",
          kpis: body.kpis || {},
          alerts: [{ severity: body.severity || "medium", message: body.message }],
        };

        await supabase.from("ceo_briefings").insert(alertData);

        // Emit event for notification agent
        await supabase.from("agent_events").insert({
          event_type: "alert.critical",
          source_agent_id: "ceo-001",
          target_agent_id: "ceo-002",
          domain: "sta",
          payload: alertData,
          priority: body.severity === "critical" ? "critical" : "high",
        });

        return json({ success: true, alert: alertData });
      }

      default:
        return json({ success: false, error: `Unknown action: ${action}` }, 400);
    }
  } catch (err) {
    return json({ success: false, error: err.message }, 500);
  }
});
