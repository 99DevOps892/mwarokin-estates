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
      case "store": {
        const { data, error } = await supabase
          .from("agent_memory")
          .insert({
            agent_id: body.agent_id,
            memory_type: body.memory_type || "episodic",
            namespace: body.namespace || "default",
            content: body.content,
            importance: body.importance || 0.5,
            expires_at: body.expires_at || null,
          })
          .select()
          .single();
        return json({ success: !error, memory: data, error: error?.message });
      }

      case "recall": {
        let query = supabase
          .from("agent_memory")
          .select("*")
          .eq("agent_id", body.agent_id);

        if (body.namespace) query = query.eq("namespace", body.namespace);
        if (body.memory_type) query = query.eq("memory_type", body.memory_type);

        // Filter out expired memories
        query = query.or(`expires_at.is.null,expires_at.gt.${new Date().toISOString()}`);

        // Order by importance and recency
        query = query.order("importance", { ascending: false })
          .order("created_at", { ascending: false })
          .limit(body.limit || 20);

        const { data, error } = await query;

        // Update access counts
        if (data && data.length > 0) {
          const ids = data.map(m => m.id);
          await supabase
            .from("agent_memory")
            .update({
              access_count: supabase.rpc ? undefined : undefined, // Will use SQL
              last_accessed: new Date().toISOString(),
            })
            .in("id", ids);
        }

        return json({ success: !error, memories: data, error: error?.message });
      }

      case "search": {
        // Semantic search via content text matching
        const { data, error } = await supabase
          .from("agent_memory")
          .select("*")
          .eq("agent_id", body.agent_id)
          .textSearch("content::text", body.query, { type: "websearch" })
          .order("importance", { ascending: false })
          .limit(body.limit || 10);

        // Fallback: JSON containment search
        if (!data || data.length === 0) {
          const { data: fallback } = await supabase
            .from("agent_memory")
            .select("*")
            .eq("agent_id", body.agent_id)
            .contains("content", { text: body.query })
            .order("importance", { ascending: false })
            .limit(body.limit || 10);

          return json({ success: true, memories: fallback || [], method: "fallback" });
        }

        return json({ success: !error, memories: data, method: "fulltext" });
      }

      case "forget": {
        if (body.memory_id) {
          await supabase.from("agent_memory").delete().eq("id", body.memory_id);
        } else if (body.agent_id && body.namespace) {
          await supabase
            .from("agent_memory")
            .delete()
            .eq("agent_id", body.agent_id)
            .eq("namespace", body.namespace);
        }
        return json({ success: true });
      }

      case "cleanup": {
        // Delete expired memories
        const { data, error } = await supabase
          .from("agent_memory")
          .delete()
          .lt("expires_at", new Date().toISOString())
          .not("expires_at", "is", null)
          .select();
        return json({ success: !error, deleted: data?.length || 0 });
      }

      case "stats": {
        const { data } = await supabase
          .from("agent_memory")
          .select("agent_id, memory_type, namespace");

        const stats = {
          total: data?.length || 0,
          by_agent: data?.reduce((acc: Record<string, number>, m) => {
            acc[m.agent_id] = (acc[m.agent_id] || 0) + 1;
            return acc;
          }, {}) || {},
          by_type: data?.reduce((acc: Record<string, number>, m) => {
            acc[m.memory_type] = (acc[m.memory_type] || 0) + 1;
            return acc;
          }, {}) || {},
          by_namespace: data?.reduce((acc: Record<string, number>, m) => {
            acc[m.namespace] = (acc[m.namespace] || 0) + 1;
            return acc;
          }, {}) || {},
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
