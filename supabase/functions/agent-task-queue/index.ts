import { serve } from "https://deno.land/std@0.177.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { corsHeaders, json, preflight } from "../_shared/cors.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

serve(async (req: Request) => {
  if (preflight(req)) return preflight(req);

  try {
    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);
    const body = await req.json();
    const { action } = body;

    switch (action) {
      case "create": {
        const taskId = body.task_id || `TSK-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
        const { data, error } = await supabase
          .from("agent_tasks")
          .insert({
            task_id: taskId,
            parent_task_id: body.parent_task_id || null,
            orchestrator_id: body.orchestrator_id || "sta-hub-001",
            assigned_agent_id: body.assigned_agent_id || null,
            domain: body.domain,
            task_type: body.task_type,
            priority: body.priority || "normal",
            input: body.input || {},
            context: body.context || {},
            status: body.assigned_agent_id ? "assigned" : "queued",
            timeout_ms: body.timeout_ms || 30000,
            max_retries: body.max_retries || 3,
            created_by: body.created_by || "system",
          })
          .select()
          .single();
        return json({ success: !error, task: data, error: error?.message });
      }

      case "assign": {
        // Find best available task for an agent
        const { data: tasks } = await supabase
          .from("agent_tasks")
          .select("*")
          .eq("status", "queued")
          .eq("domain", body.domain)
          .order("priority", { ascending: true }) // critical first
          .order("created_at", { ascending: true })
          .limit(1);

        if (!tasks || tasks.length === 0) {
          return json({ success: true, task: null, message: "No queued tasks" });
        }

        const task = tasks[0];
        const { error } = await supabase
          .from("agent_tasks")
          .update({
            assigned_agent_id: body.agent_id,
            status: "assigned",
          })
          .eq("id", task.id);

        return json({ success: !error, task: { ...task, assigned_agent_id: body.agent_id, status: "assigned" } });
      }

      case "start": {
        const { error } = await supabase
          .from("agent_tasks")
          .update({
            status: "running",
            started_at: new Date().toISOString(),
          })
          .eq("id", body.task_id);
        return json({ success: !error });
      }

      case "complete": {
        const { error } = await supabase
          .from("agent_tasks")
          .update({
            status: "completed",
            output: body.output,
            completed_at: new Date().toISOString(),
            tokens_used: body.tokens_used || 0,
            cost_ksh: body.cost_ksh || 0,
          })
          .eq("id", body.task_id);
        return json({ success: !error });
      }

      case "fail": {
        const { data: task } = await supabase
          .from("agent_tasks")
          .select("retry_count, max_retries")
          .eq("id", body.task_id)
          .single();

        const shouldRetry = task && task.retry_count < task.max_retries;
        const newStatus = shouldRetry ? "queued" : "failed";

        const { error } = await supabase
          .from("agent_tasks")
          .update({
            status: newStatus,
            error_message: body.error_message,
            retry_count: (task?.retry_count || 0) + 1,
            assigned_agent_id: shouldRetry ? null : undefined,
          })
          .eq("id", body.task_id);

        // Emit failure event
        await supabase.from("agent_events").insert({
          event_type: shouldRetry ? "task.retry" : "task.failed",
          source_agent_id: body.agent_id || "unknown",
          domain: body.domain,
          payload: { task_id: body.task_id, error: body.error_message, retry: shouldRetry },
          priority: "high",
        });

        return json({ success: !error, retried: shouldRetry });
      }

      case "cancel": {
        const { error } = await supabase
          .from("agent_tasks")
          .update({ status: "cancelled" })
          .eq("id", body.task_id);
        return json({ success: !error });
      }

      case "get": {
        const { data, error } = await supabase
          .from("agent_tasks")
          .select("*")
          .eq("id", body.task_id)
          .single();
        return json({ success: !error, task: data, error: error?.message });
      }

      case "list": {
        let query = supabase.from("agent_tasks").select("*");
        if (body.status) query = query.eq("status", body.status);
        if (body.domain) query = query.eq("domain", body.domain);
        if (body.assigned_agent_id) query = query.eq("assigned_agent_id", body.assigned_agent_id);
        if (body.priority) query = query.eq("priority", body.priority);
        query = query.order("created_at", { ascending: false }).limit(body.limit || 50);
        const { data, error } = await query;
        return json({ success: !error, tasks: data, error: error?.message });
      }

      case "stats": {
        const { data: tasks } = await supabase
          .from("agent_tasks")
          .select("status, domain, priority, tokens_used, cost_ksh, created_at");

        const now = Date.now();
        const last24h = tasks?.filter(t => new Date(t.created_at).getTime() > now - 86400000) || [];

        const stats = {
          total: tasks?.length || 0,
          by_status: tasks?.reduce((acc: Record<string, number>, t) => {
            acc[t.status] = (acc[t.status] || 0) + 1;
            return acc;
          }, {}) || {},
          by_domain: tasks?.reduce((acc: Record<string, number>, t) => {
            acc[t.domain] = (acc[t.domain] || 0) + 1;
            return acc;
          }, {}) || {},
          last_24h: {
            total: last24h.length,
            completed: last24h.filter(t => t.status === "completed").length,
            failed: last24h.filter(t => t.status === "failed").length,
          },
          total_tokens: tasks?.reduce((s, t) => s + (t.tokens_used || 0), 0) || 0,
          total_cost_ksh: tasks?.reduce((s, t) => s + (t.cost_ksh || 0), 0) || 0,
        };

        return json({ success: true, stats });
      }

      default:
        return json({ success: false, error: `Unknown action: ${action}` }, 400);
    }
  } catch (err) {
    return json({ success: false, error: err.message }, 500);
  }
});
