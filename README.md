# Mwarokin Estates

Premium property management & real estate platform by **Syllogism Technology Africa (STA)** — built for Mwarokin.

- Multi-language UI (English, Kiswahili, Français, Deutsch, العربية with RTL)
- Multi-currency display (KES base → USD/EUR/GBP)
- Rent payments via **M-Pesa STK push**, **Airtel Money**, and **bank transfer** with automatic **95% landlord / 5% platform** split
- Maintenance requests, notifications, and realtime updates
- Admin panel with property CRUD, payment approval, AI lead scoring, and audit log
- AI lead-gen orchestration with a rule-based intent model + message queue
- Hosted on **GitHub Pages**, backend on **Supabase**, mirrored to **GitLab** (2nd brain)

## Tech

| Layer | Technology |
| --- | --- |
| Frontend | Vanilla HTML/CSS/JS + supabase-js v2 (CDN) |
| Backend | Supabase (Postgres, Auth, Realtime, Edge Functions) |
| Payments | Safaricom Daraja (M-Pesa STK push), Airtel Money, manual bank |
| Hosting | GitHub Pages |
| CI/CD | GitHub Actions (deploy + GitLab mirror), GitLab CI failsafe |

## Live setup — 10 minutes

### 1. GitHub

1. Push this repo to `99DevOps892/mwarokin-estates` (branch `main`).
2. In **Settings → Secrets and variables → Actions**, add:
   - `SUPABASE_URL` = `https://spnerrqumefbuuscumhw.supabase.co`
   - `SUPABASE_ANON_KEY` = your Supabase anon key (below)
   - `GITLAB_URL` (optional) = e.g. `gitlab.com/yourgroup/mwarokin-estates.git`
   - `GITLAB_TOKEN` (optional) = GitLab personal access token with `write_repository`
3. In **Settings → Pages**: Source = "GitHub Actions". The site URL will be `https://99devops892.github.io/mwarokin-estates/`.

### 2. Supabase

1. Open your project → **SQL Editor** and run the files **in order**:
   1. `supabase/schema.sql`
   2. `supabase/functions.sql`
   3. `supabase/policies.sql`
   4. `supabase/seed.sql`
2. Copy the **anon / public** key from **Settings → API**.
3. **Authentication → URL Configuration**:
   - Site URL: `https://99devops892.github.io`
   - Redirect URLs: `https://99devops892.github.io/mwarokin-estates/*`
4. **Authentication → Providers → Email**: leave enabled (confirmation email will be sent on sign-up).

### 3. Local `js/config.js` (if running without CI)

Open `js/config.js` and replace `YOUR_SUPABASE_ANON_PUBLIC_KEY_HERE` with your anon key.

### 4. Edge Functions (optional — payments via M-Pesa)

```bash
supabase login
supabase link --project-ref spnerrqumefbuuscumhw
supabase functions deploy payments mpesa-stk-push mpesa-callback translations currency ai-lead-orchestrator
```

Set secrets in **Edge Functions → Secrets**:
`MPESA_CONSUMER_KEY`, `MPESA_CONSUMER_SECRET`, `MPESA_PASSKEY`, `MPESA_SHORTCODE`, `MPESA_CALLBACK_URL` (your deployed callback URL), `MPESA_ENV=sandbox` until go-live.

> Until the functions are deployed the frontend gracefully falls back to direct inserts, so the UI works end-to-end without them.

## Project structure

```
mwarokin-estates/
├─ index.html            Home + property search
├─ login.html / register.html / profile.html
├─ dashboard.html        Tenant dashboard (pay rent, maintenance, notifications)
├─ admin.html            Admin panel (properties, payments, leads, audit)
├─ property.html         Property detail
├─ css/style.css         Design system
├─ js/                   Modules (see AGENTS.md for dependency order)
├─ supabase/
│  ├─ schema.sql / functions.sql / policies.sql / seed.sql
│  └─ functions/*        Deno edge functions
└─ .github/workflows/    Deploy + GitLab mirror
```

## Roles & access

| Role | Access |
| --- | --- |
| admin | Everything (incl. admin panel, payment approval) |
| agent | Admin panel (properties, leads), no payment approval |
| landlord | Dashboard, own properties & payouts |
| caretaker | Maintenance management |
| tenant | Dashboard: pay rent, request maintenance |

## Security notes

- All tables are locked down with **RLS**; client writes go through per-role policies in `supabase/policies.sql`.
- Payments split is computed by a DB trigger with `SECURITY DEFINER` — never trust a client-sent split.
- `AGENTS.md` documents agent operating rules — read it before making changes.

## License

Proprietary — © Syllogism Technology Africa (STA). All rights reserved.