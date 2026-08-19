import { createClient, SupabaseClient } from "jsr:@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
};

/**
 * Translations Edge Function
 * POST { language_code } => full dictionary for a language (cached).
 * POST { language_code, key, namespace, value } => upsert a translation.
 */
Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  const supabase: SupabaseClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

  if (req.method === "GET") {
    const lang = new URL(req.url).searchParams.get("language_code") || "en";
    const { data, error } = await supabase
      .from("translations")
      .select("namespace, key, value")
      .eq("language_code", lang)
      .eq("is_active", true);
    if (error) return json({ error: error.message }, 500, corsHeaders);
    const dict: Record<string, string> = {};
    data.forEach((t) => { dict[`${t.namespace}.${t.key}`] = t.value; });
    return json({ language_code: lang, translations: dict }, 200, corsHeaders);
  }

  try {
    const body = await req.json();
    if (body.key && body.language_code) {
      const { error } = await supabase.from("translations").upsert({
        language_code: body.language_code,
        namespace: body.namespace || "common",
        key: body.key,
        value: body.value,
      }, { onConflict: "language_code,namespace,key" });
      if (error) return json({ error: error.message }, 500, corsHeaders);
      return json({ ok: true }, 200, corsHeaders);
    }
    return json({ error: "language_code and key are required" }, 400, corsHeaders);
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