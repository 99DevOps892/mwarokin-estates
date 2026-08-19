import { createClient, SupabaseClient } from "jsr:@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

/**
 * AI Lead Orchestrator
 * POST { action: "score" | "campaign", min_score?, limit? }
 *
 * score    — re-scores existing prospects with a rule-based intent model and
 *            persists lead_score + qualification_status to the DB.
 * campaign — pulls high-intent prospects and creates one message_queue row per
 *            prospect so the comms workers (WhatsApp/SMS/Email) can pick them up.
 */
Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const supabase: SupabaseClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);
    const body = await req.json();
    const action = body.action || "score";

    if (action === "score") {
      const { data: prospects, error } = await supabase
        .from("prospects")
        .select("*")
        .limit(body.limit || 100);
      if (error) return json({ error: error.message }, 500, corsHeaders);

      let updated = 0;
      for (const p of prospects || []) {
        const score = computeLeadScore(p);
        const status = score >= 70 ? "hot" : score >= 45 ? "warm" : "cold";
        const { error: upErr } = await supabase
          .from("prospects")
          .update({ lead_score: score, qualification_status: status })
          .eq("id", p.id);
        if (!upErr) updated++;
      }
      return json({ ok: true, action: "score", processed: updated }, 200, corsHeaders);
    }

    if (action === "campaign") {
      const minScore = body.min_score || 60;
      const limit = body.limit || 20;

      const { data: prospects, error } = await supabase
        .from("prospects")
        .select("*")
        .gte("lead_score", minScore)
        .order("lead_score", { ascending: false })
        .limit(limit);
      if (error) return json({ error: error.message }, 500, corsHeaders);

      let queued = 0;
      for (const p of prospects || []) {
        if (!p.phone && !p.email) continue;
        const { error: qErr } = await supabase.from("message_queue").insert([{
          channel: p.phone ? "whatsapp" : "email",
          recipient: p.phone ? p.phone : p.email,
          template_key: "lead_intro",
          status: "pending",
          scheduled_for: new Date().toISOString(),
          metadata: { prospect_id: p.id, property_address: p.property_address },
        }]);
        if (!qErr) queued++;
      }
      return json({ ok: true, action: "campaign", queued }, 200, corsHeaders);
    }

    return json({ error: `Unknown action "${action}"` }, 400, corsHeaders);
  } catch (e) {
    return json({ error: e.message }, 500, corsHeaders);
  }
});

/**
 * Rule-based intent model.
 * Signals can arrive from the outreach worker (social posts, DMs, form fills).
 * We weight recency, engagement, response speed, and property-match signals.
 */
function computeLeadScore(p: any): number {
  const signals = p.intent_signals || [];
  if (!Array.isArray(signals) || signals.length === 0) return 30;

  let score = 30;
  const now = Date.now();
  for (const s of signals) {
    const t = typeof s.timestamp === "string" ? Date.parse(s.timestamp) : now;
    const ageDays = (now - t) / 86400000;
    const recency = ageDays <= 1 ? 20 : ageDays <= 3 ? 12 : ageDays <= 7 ? 6 : 1;
    score += recency;

    switch (s.type) {
      case "instagram_dm": score += 8; break;
      case "whatsapp_reply": score += 10; break;
      case "property_page_view": score += 6; break;
      case "viewing_request": score += 15; break;
      case "booking_request": score += 20; break;
      case "property_enquiry": score += 12; break;
      case "form_fill": score += 9; break;
      case "social_like": score += 3; break;
      case "social_comment": score += 4; break;
      default: score += 2;
    }
  }
  return Math.min(100, score);
}

function json(body: unknown, status: number, headers: Record<string, string>) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}