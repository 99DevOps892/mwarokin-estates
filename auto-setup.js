#!/usr/bin/env node
// ============================================================
// Mwarokin Estates — Setup & Readiness Validator
// Usage:  node auto-setup.js [--verify]
//
// Replaces the broken generator script with an honest validator:
//   - checks Node version
//   - checks .env presence and required variables
//   - checks app/js/config.js anon key is no longer a placeholder
//   - pings the Supabase REST endpoint
//   - reports migration/function/deploy next steps
// Writes NO secrets anywhere. Zero dependencies (Node 18+).
// ============================================================

import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.dirname(fileURLToPath(import.meta.url));
const verifyOnly = process.argv.includes('--verify');
let failures = 0;

function check(label, ok, hint = '') {
  const icon = ok ? '[OK]  ' : '[FAIL]';
  console.log(`${icon} ${label}${ok || !hint ? '' : `\n      -> ${hint}`}`);
  if (!ok) failures++;
}

console.log('\n=== Mwarokin Estates — Setup Check ===\n');

// 1. Node version -------------------------------------------------
const nodeOk = Number(process.versions.node.split('.')[0]) >= 18;
check(`Node.js >= 18 (found ${process.versions.node})`, nodeOk,
  'Install Node.js 18 or newer: https://nodejs.org');

// 2. Environment file ---------------------------------------------
const envPath = path.join(root, '.env');
let envVars = {};
if (existsSync(envPath)) {
  for (const line of readFileSync(envPath, 'utf8').split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$/);
    if (m) envVars[m[1]] = m[2];
  }
}
check('.env file exists', existsSync(envPath),
  'Copy .env.example -> .env and fill in your keys.');

for (const v of ['SUPABASE_URL', 'SUPABASE_ANON_KEY']) {
  const val = envVars[v];
  check(`${v} is set`, Boolean(val && !/^your-/.test(val ?? '')),
    `Set ${v} in .env`);
}
check('SUPABASE_SERVICE_ROLE_KEY is set (server-side only)',
  Boolean(envVars.SUPABASE_SERVICE_ROLE_KEY && !/^your-/.test(envVars.SUPABASE_SERVICE_ROLE_KEY)),
  'Get it from Supabase Dashboard -> Settings -> API. NEVER ship it to the frontend or commit it.');

// 3. Frontend anon key --------------------------------------------
const configPath = path.join(root, 'app', 'js', 'config.js');
const configSrc = existsSync(configPath) ? readFileSync(configPath, 'utf8') : '';
check('app/js/config.js has real anon key',
  /SUPABASE_ANON_KEY\s*=\s*'(?!\s*YOUR_)/.test(configSrc),
  "Open app/js/config.js and replace 'YOUR_SUPABASE_ANON_PUBLIC_KEY_HERE'.");

// 4. Supabase project reachability --------------------------------
const supabaseUrl = envVars.SUPABASE_URL;
if (supabaseUrl && /^https?:\/\//.test(supabaseUrl)) {
  try {
    const res = await fetch(`${supabaseUrl.replace(/\/$/, '')}/rest/v1/?apikey=${envVars.SUPABASE_ANON_KEY}`, {
      headers: { apikey: envVars.SUPABASE_ANON_KEY },
      signal: AbortSignal.timeout(8000),
    });
    check('Supabase REST endpoint reachable', res.status === 200 || res.status === 401,
      `HTTP ${res.status}`);
  } catch (e) {
    check('Supabase REST endpoint reachable', false, e.message);
  }
}

// 5. Repo structure ------------------------------------------------
for (const rel of [
  'supabase/migrations/20260824000000_core_schema.sql',
  'supabase/migrations/20260824000100_functions_triggers.sql',
  'supabase/migrations/20260824000200_rls_policies.sql',
  'supabase/functions/payments/index.ts',
  'supabase/functions/mpesa-stk-push/index.ts',
  'supabase/functions/mpesa-callback/index.ts',
  'netlify.toml',
]) {
  check(`repo file: ${rel}`, existsSync(path.join(root, rel)));
}

// Report -----------------------------------------------------------
console.log('\n=== Next steps ===');
console.log(`
 1. npx supabase login
 2. npx supabase link --project-ref spnerrqumefbuuscumhw
 3. npx supabase db push                      # applies the 3 migrations
 4. npx supabase secrets set --env-file .env.supabase-secrets
 5. npm run functions:deploy                  # deploys all 6 edge functions
 6. Netlify: connect repo 99DevOps892/mwarokin-estates
       build command: (none)   publish dir: app
    OR: npm i -D netlify-cli && npm run deploy:netlify

 Production M-Pesa checklist:
   - MPESA_ENV=production + live credentials + verified shortcode
   - MPESA_CALLBACK_URL points at deployed mpesa-callback function
`);

if (verifyOnly) {
  console.log(failures === 0 ? 'ALL CHECKS PASSED\n' : `${failures} CHECK(S) FAILED\n`);
  process.exit(failures === 0 ? 0 : 1);
}
