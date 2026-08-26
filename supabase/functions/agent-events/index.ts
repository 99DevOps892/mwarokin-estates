import { serve } from "https://deno.land/std@0.177.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { corsHeaders, json, preflight } from "../_shared/cors.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

serve(async (req: Request) => {
  if (preflight(req)) return preflight(req);

  try {
    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);
    const body = await req.json();
    const { action } = body;

    switch (action) {
      case "emit": {
        const event = {
          event_type: body.event_type,
          source_agent_id: body.source_agent_id,
          target_agent_id: body.target_agent_id || null,
          domain: body.domain || null,
          payload: body.payload || {},
          priority: body.priority || "normal",
        };

        const { data } = await supabase.from("agent_events").insert(event).select().single();
        return json({ success: true, event: data });
      }

      case "poll": {
        // Poll for undelivered events targeting a specific agent
        const { data: events } = await supabase
          .from("agent_events")
          .select("*")
          .or(`target_agent_id.eq.${body.agent_id},target_agent_id.is.null`)
          .eq("delivered", false)
          .order("created_at", { ascending: true })
          .limit(body.limit || 20);

        if (events && events.length > 0) {
          const ids = events.map((e: any) => e.id);
          await supabase
            .from("agent_events")
            .update({ delivered: true })
            .in("id", ids);
        }

        return json({ success: true, events: events || [] });
      }

      case "process": {
        // Mark event as processed
        await supabase
          .from("agent_events")
          .update({ processed: true })
          .eq("id", body.event_id);
        return json({ success: true });
      }

      case "history": {
        const { data: events } = await supabase
          .from("agent_events")
          .select("*")
          .eq("source_agent_id", body.agent_id || "")
          .order("created_at", { ascending: false })
          .limit(body.limit || 50);

        return json({ success: true, events: events || [] });
      }

      case "stats": {
        const { data: stats } = await supabase.rpc("get_agent_event_stats");
        return json({ success: true, stats });
      }

      default:
        return json({ success: false, error: `Unknown action: ${action}` }, 400);
    }
  } catch (err) {
    return json({ success: false, error: err.message }, 500);
  }
});
