// ============================================================
// Mwarokin Estates — ai-lead-orchestrator Edge Function
// POST /functions/v1/ai-lead-orchestrator
// Auth: Bearer token of an ADMIN user.
// Body: { prospects: [{ name?, phone?, email?, source?, signals? }] }
// Rule-based lead scoring (transparent, no black-box claims):
//   phone present +20, email +15, source whatsapp/social +15,
//   budget signal >= 50k +25, urgency keywords +15, cap 100.
// High scorers (>= AI_MIN_SCORE, default 75) are marked 'qualified'.
// ============================================================
import { serve } from 'https://deno.land/std@0.208.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { preflight, json, error } from '../_shared/cors.ts';

interface IncomingProspect {
  name?: string;
  phone?: string;
  email?: string;
  source?: string;
  signals?: Record<string, unknown>;
}

function scoreLead(p: IncomingProspect): { leadScore: number; reasons: string[] } {
  let score = 10; // base interest
  const reasons: string[] = [];
  const text = JSON.stringify(p.signals ?? {}).toLowerCase();

  if (p.phone) { score += 20; reasons.push('phone provided'); }
  if (p.email) { score += 15; reasons.push('email provided'); }
  if (/whatsapp|social|referral/.test(String(p.source ?? '').toLowerCase())) {
    score += 15; reasons.push('high-intent channel');
  }
  const budget = Number((p.signals as { budget?: number })?.budget ?? 0);
  if (budget >= 50000) { score += 25; reasons.push('budget >= 50K'); }
  else if (budget >= 20000) { score += 12; reasons.push('budget >= 20K'); }
  if (/urgent|immediately|asap|now/.test(text)) { score += 15; reasons.push('urgency signal'); }

  return { leadScore: Math.min(score, 100), reasons };
}

serve(async (req: Request) => {
  const pf = preflight(req);
  if (pf) return pf;
  if (req.method !== 'POST') return error('Method not allowed', 405);

  try {
    const authHeader = req.headers.get('Authorization') ?? '';
    if (!authHeader.startsWith('Bearer ')) return error('Missing bearer token', 401);

    // Verify caller is authenticated AND an admin.
    const client = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_ANON_KEY') ?? '',
      { global: { headers: { Authorization: authHeader } } },
    );
    const { data: userData, error: userErr } = await client.auth.getUser();
    if (userErr || !userData?.user) return error('Invalid or expired token', 401);

    const { data: profile } = await client
      .from('profiles')
      .select('role')
      .eq('id', userData.user.id)
      .maybeSingle();
    if (profile?.role !== 'admin') return error('Admin access required', 403);

    const body = await req.json().catch(() => null);
    const incoming: IncomingProspect[] = Array.isArray(body?.prospects)
      ? body.prospects.slice(0, 200)
      : [];
    if (!incoming.length) return error('prospects array required');

    const minScore = Number(body?.minScore ?? Deno.env.get('AI_MIN_SCORE') ?? 75);

    const admin = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '',
    );

    const results = [];
    for (const p of incoming) {
      const { leadScore, reasons } = scoreLead(p);
      const status = leadScore >= minScore ? 'qualified' : 'new';
      const { data, error: insErr } = await admin
        .from('prospects')
        .insert({
          name: p.name ?? null,
          phone: p.phone ?? null,
          email: p.email ?? null,
          source: p.source ?? 'ai-orchestrator',
          lead_score: leadScore,
          status,
          metadata: { reasons, scored_by: 'ai-lead-orchestrator' },
        })
        .select('id, lead_score, status')
        .single();
      if (!insErr && data) results.push(data);
    }

    const qualified = results.filter((r) => r.status === 'qualified').length;
    return json({
      success: true,
      processed: results.length,
      qualified,
      minScore,
    });
  } catch (err) {
    return error((err as Error).message, 500);
  }
});
