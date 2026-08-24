// ============================================================
// Mwarokin Estates — translations Edge Function
// GET /functions/v1/translations?language=sw&namespace=common
// Public: active translation strings for the i18n manager.
// ============================================================
import { serve } from 'https://deno.land/std@0.208.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { preflight, json, error } from '../_shared/cors.ts';

serve(async (req: Request) => {
  const pf = preflight(req);
  if (pf) return pf;
  if (req.method !== 'GET') return error('Method not allowed', 405);

  try {
    const url = new URL(req.url);
    const language = (url.searchParams.get('language') ?? 'en').slice(0, 5);
    const namespace = url.searchParams.get('namespace');

    const client = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_ANON_KEY') ?? '',
    );

    let query = client
      .from('translations')
      .select('key, value, namespace')
      .eq('language_code', language)
      .eq('is_active', true);
    if (namespace) query = query.eq('namespace', namespace);

    const { data, error: qErr } = await query;
    if (qErr) return error(qErr.message, 500);

    const dict: Record<string, string> = {};
    for (const row of data ?? []) {
      dict[`${row.namespace}.${row.key}`] = row.value;
    }
    return json({ success: true, language, translations: dict });
  } catch (err) {
    return error((err as Error).message, 500);
  }
});
