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
      case "register": {
        const { data, error } = await supabase
          .from("agent_registry")
          .upsert({
            agent_id: body.agent_id,
            agent_name: body.agent_name,
            agent_type: body.agent_type || "worker",
            domain: body.domain,
            model_used: body.model_used,
            endpoint_url: body.endpoint_url,
            skills: body.skills || [],
            status: "idle",
            max_concurrent_tasks: body.max_concurrent_tasks || 5,
          }, { onConflict: "agent_id" })
          .select()
          .single();
        return json({ success: !error, agent: data, error: error?.message });
      }

      case "heartbeat": {
        const { error } = await supabase
          .from("agent_registry")
          .update({
            last_heartbeat: new Date().toISOString(),
            status: body.status || "idle",
          })
          .eq("agent_id", body.agent_id);
        return json({ success: !error });
      }

      case "get": {
        const { data, error } = await supabase
          .from("agent_registry")
          .select("*")
          .eq("agent_id", body.agent_id)
          .single();
        return json({ success: !error, agent: data, error: error?.message });
      }

      case "list": {
        let query = supabase.from("agent_registry").select("*");
        if (body.domain) query = query.eq("domain", body.domain);
        if (body.status) query = query.eq("status", body.status);
        if (body.agent_type) query = query.eq("agent_type", body.agent_type);
        query = query.order("agent_id");
        const { data, error } = await query;
        return json({ success: !error, agents: data, error: error?.message });
      }

      case "update_status": {
        const updates: Record<string, unknown> = { status: body.status };
        if (body.current_task_count !== undefined) updates.current_task_count = body.current_task_count;
        if (body.error_rate !== undefined) updates.error_rate = body.error_rate;
        if (body.avg_response_time_ms !== undefined) updates.avg_response_time_ms = body.avg_response_time_ms;
        const { error } = await supabase
          .from("agent_registry")
          .update(updates)
          .eq("agent_id", body.agent_id);
        return json({ success: !error });
      }

      case "increment_completed": {
        const { data: agent } = await supabase
          .from("agent_registry")
          .select("total_tasks_completed, current_task_count")
          .eq("agent_id", body.agent_id)
          .single();
        if (agent) {
          await supabase
            .from("agent_registry")
            .update({
              total_tasks_completed: (agent.total_tasks_completed || 0) + 1,
              current_task_count: Math.max(0, (agent.current_task_count || 1) - 1),
              last_heartbeat: new Date().toISOString(),
            })
            .eq("agent_id", body.agent_id);
        }
        return json({ success: true });
      }

      case "stats": {
        const { data: agents } = await supabase
          .from("agent_registry")
          .select("agent_id, status, domain, total_tasks_completed, error_rate, last_heartbeat");

        const stats = {
          total: agents?.length || 0,
          idle: agents?.filter(a => a.status === "idle").length || 0,
          busy: agents?.filter(a => a.status === "busy").length || 0,
          offline: agents?.filter(a => a.status === "offline").length || 0,
          error: agents?.filter(a => a.status === "error").length || 0,
          total_tasks_completed: agents?.reduce((s, a) => s + (a.total_tasks_completed || 0), 0) || 0,
          avg_error_rate: agents?.length ? (agents.reduce((s, a) => s + (a.error_rate || 0), 0) / agents.length).toFixed(2) : 0,
          by_domain: agents?.reduce((acc: Record<string, number>, a) => {
            acc[a.domain] = (acc[a.domain] || 0) + 1;
            return acc;
          }, {}) || {},
        };

        return json({ success: true, stats, agents });
      }

      default:
        return json({ success: false, error: `Unknown action: ${action}` }, 400);
    }
  } catch (err) {
    return json({ success: false, error: err.message }, 500);
  }
});
