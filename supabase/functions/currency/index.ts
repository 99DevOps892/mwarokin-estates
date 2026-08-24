// ============================================================
// Mwarokin Estates — currency Edge Function
// GET /functions/v1/currency?base=KES
// Public: returns stored exchange rates; refreshes from an open
// API when EXCHANGE_RATE_API_KEY is configured (optional).
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
    const base = (url.searchParams.get('base') ?? 'KES').toUpperCase().slice(0, 3);

    const admin = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '',
    );

    const { data: rates } = await admin
      .from('exchange_rates')
      .select('target_currency, rate, fetched_at')
      .eq('base_currency', base);

    // Optional live refresh (only when a key is provisioned).
    const apiKey = Deno.env.get('EXCHANGE_RATE_API_KEY');
    if (apiKey) {
      try {
        const res = await fetch(`https://open.er-api.com/v6/latest/${base}`);
        if (res.ok) {
          const live = await res.json();
          const wanted = ['USD', 'EUR', 'GBP'];
          for (const target of wanted) {
            const rate = live?.rates?.[target];
            if (typeof rate === 'number' && rate > 0) {
              await admin.from('exchange_rates').upsert(
                { base_currency: base, target_currency: target, rate },
                { onConflict: 'base_currency,target_currency' },
              );
            }
          }
          const { data: fresh } = await admin
            .from('exchange_rates')
            .select('target_currency, rate, fetched_at')
            .eq('base_currency', base);
          return json({ success: true, base, source: 'live', rates: fresh });
        }
      } catch (_e) {
        /* fall through to stored rates */
      }
    }

    return json({ success: true, base, source: 'stored', rates: rates ?? [] });
  } catch (err) {
    return error((err as Error).message, 500);
  }
});
