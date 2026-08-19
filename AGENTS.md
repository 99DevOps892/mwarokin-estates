# Mwarokin Estates — AGENTS.md

Operating instructions for AI coding agents working in this repository.

## Project

- **Product**: Mwarokin Estates — property management & real estate platform by Syllogism Technology Africa (STA).
- **Stack**: Vanilla HTML/CSS/JS (no build step) + Supabase (Postgres, Auth, Realtime, Edge Functions) + GitHub Pages hosting.
- **Repo**: `99DevOps892/mwarokin-estates`. GitLab mirror is the "2nd brain".

## Layout

| Path | Purpose |
| --- | --- |
| `js/config.js` | Central config: Supabase URL, anon key, commission rate, languages, currencies, feature flags. |
| `js/supabase-client.js` | Single shared Supabase client + global helpers: `esc`, `fmtMoney`, `appPath`, `toast`. |
| `js/*.js` | Feature modules (auth, i18n, currency, properties, realtime, payments, dashboard, admin, profile, home, property). |
| `css/style.css` | Design system (tokens in `:root`). |
| `supabase/schema.sql` | Full schema — run first in Supabase SQL Editor. |
| `supabase/functions.sql` | RPCs, triggers, views — run second. |
| `supabase/policies.sql` | RLS policies + `is_admin`/`is_staff` helpers — run third. |
| `supabase/seed.sql` | Seed data (exchange rates, translations, sample properties) — run last. |
| `supabase/functions/*` | Deno Edge Functions (payments, mpesa, translations, currency, AI leads). |

## Business rules

- **Commission**: `js/config.js` → `commissionRate: 5`. The DB trigger `calculate_payment_split` splits each payment: 95% `landlord_amount`, 5% `platform_fee`. Keep both in sync.
- **Currencies**: KES is the base/ledger currency. UI converts via `exchange_rates` table.
- **Languages**: en, sw, fr, de, ar (ar is RTL). Translations live in the `translations` table; `i18n.js` falls back to a small built-in dict.

## Conventions

- NO build tools, NO npm install, NO frameworks. If a new dependency is truly required, it must be loaded via CDN like supabase-js v2 is.
- All JS modules are IIFEs exposing `window.MWAROKIN_*` namespaces; page scripts run after `DOMContentLoaded`.
- Use the shared helpers (`window.esc` for HTML escaping, `window.fmtMoney`, `window.appPath`, `window.toast`) instead of re-implementing.
- Supabase client is created once in `supabase-client.js`. Never create a second client.
- Edge Functions: Deno, `jsr:@supabase/supabase-js@2`, CORS headers on every response, secrets via `Deno.env.get`.

## Required commands (verify before finishing a task)

```powershell
# List the project tree
Get-ChildItem -Recurse -File | Select-Object FullName

# Node available? Quick syntax check of a JS file
node --check js\auth.js
```

No test framework exists. "Verification" = `node --check` each JS file + confirm all HTML `<script src>` targets exist.

## Git workflow

- GitHub is the source of truth; GitLab mirror is automatic via `.github/workflows/mirror-to-gitlab.yml`.
- Deploy to GitHub Pages is automatic via `.github/workflows/deploy.yml` (injects `SUPABASE_URL` + `SUPABASE_ANON_KEY` from repo secrets).
- Commit messages: short, imperative, prefixed by scope, e.g. `feat(payments): add mpesa stk push`, `fix(auth): redirect agents to admin`.
- NEVER commit secrets. The only secret-bearing file is `js/config.js` at build time (injected from CI secrets), and its committed form must keep placeholders.