import { createClient, SupabaseClient } from "jsr:@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
};

/**
 * Currency Edge Function
 * GET  /currency?base=KES  => exchange rates
 * POST /currency           => upsert a rate { base_currency, target_currency, rate }
 */
Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  const supabase: SupabaseClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

  if (req.method === "GET") {
    const base = new URL(req.url).searchParams.get("base") || "KES";
    const { data, error } = await supabase
      .from("exchange_rates")
      .select("target_currency, rate")
      .eq("base_currency", base);
    if (error) return json({ error: error.message }, 500, corsHeaders);
    const rates: Record<string, number> = { [base]: 1 };
    data.forEach((r) => { rates[r.target_currency] = r.rate; });
    return json({ base_currency: base, rates }, 200, corsHeaders);
  }

  try {
    const body = await req.json();
    const { error } = await supabase.from("exchange_rates").upsert({
      base_currency: body.base_currency || "KES",
      target_currency: body.target_currency,
      rate: body.rate,
    }, { onConflict: "base_currency,target_currency" });
    if (error) return json({ error: error.message }, 500, corsHeaders);
    return json({ ok: true }, 200, corsHeaders);
  } catch (e) {
    return json({ error: e.message }, 500, corsHeaders);
  }
});

function json(body: unknown, status: number, headers: Record<string, string>) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}