# ============================================================
# NEXT STEPS — Complete Execution Playbook
# Mwarokin Estates → Production → AppMySite → Stores
# ============================================================
> **Status:** Ready to Execute
> **Date:** 2026-08-26
> **Project:** spnerrqumefbuuscumhw
> **Repo:** 99DevOps892/mwarokin-estates

---

## EXECUTION ORDER

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8
  Keys      SQL      Secrets    Deploy    Test     Go-Live   AppMySite  Stores
```

**Estimated total time:** 2-4 hours (excluding API approval wait times)

---

## PHASE 1: PROVISION API KEYS
> **Time:** 15-30 min active + 1-48h wait for approval
> **T2 Approval Required:** Yes (external API registration)

### Step 1.1 — M-Pesa Daraja (Safaricom)

**Go to:** https://developer.safaricom.co.ke

1. Click **"Create Account"** or **"Login"** if you have one
2. Create a new app:
   - App Name: `Mwarokin Estates`
   - Description: `Property management payment processing`
   - Category: `Payment Integration`
3. Once approved, you get:
   - **Consumer Key** — `________________________`
   - **Consumer Secret** — `________________________`
4. Go to **"My Apps" → your app → Production** tab:
   - **Shortcode** (Paybill): `________________________`
   - **Passkey** (Lipa Na M-Pesa Online): `________________________`
   - **Callback URL**: `https://spnerrqumefbuuscumhw.supabase.co/functions/v1/payment-webhook?provider=mpesa`

**Sandbox testing numbers:**
```
Phone: 254708374149
PIN: 1234
Amount: Any (max 1000 in sandbox)
```

### Step 1.2 — Airtel Money (Airtel Africa)

**Go to:** https://developers.airtel.africa

1. Click **"Register"** → fill company details
2. Create an app:
   - App Name: `Mwarokin Estates`
   - Products: `Collection` (receive payments)
3. Once approved, you get:
   - **Client ID** — `________________________`
   - **Client Secret** — `________________________`
4. Note the callback URL:
   - **Callback URL**: `https://spnerrqumefbuuscumhw.supabase.co/functions/v1/payment-webhook?provider=airtel`

**Sandbox testing:**
```
Airtel sandbox is enabled by default.
Use sandbox phone numbers from Airtel docs.
```

### Step 1.3 — Flutterwave (Bank + Card)

**Go to:** https://developer.flutterwave.com

1. Click **"Create Account"** → fill details
2. Once verified, go to **Settings → API Keys**:
   - **Public Key** (test) — `________________________`
   - **Secret Key** (test) — `________________________`
3. Go to **Settings → Webhooks**:
   - **Webhook Hash** — `________________________`
   - **Test Redirect URL**: `https://99devops892.github.io/mwarokin-estates/dashboard.html`
4. Test card details (for sandbox):
   ```
   Card: 4187427415564246
   CVV:  828
   PIN:  3310
   OTP:  12345
   ```

### Step 1.4 — Record All Keys

Create a local `.env` file (NEVER commit this):

```bash
# Copy the template
cp .env.example .env

# Edit .env with your actual keys:
MPESA_CONSUMER_KEY=xxxxxxxx
MPESA_CONSUMER_SECRET=xxxxxxxx
MPESA_SHORTCODE=174379
MPESA_PASSKEY=xxxxxxxx
MPESA_ENV=sandbox
MPESA_CALLBACK_URL=https://spnerrqumefbuuscumhw.supabase.co/functions/v1/payment-webhook?provider=mpesa

AIRTEL_CLIENT_ID=xxxxxxxx
AIRTEL_CLIENT_SECRET=xxxxxxxx
AIRTEL_ENV=sandbox
AIRTEL_CALLBACK_URL=https://spnerrqumefbuuscumhw.supabase.co/functions/v1/payment-webhook?provider=airtel

FLW_SECRET_KEY=FLWSECK_TEST-xxxxxxxx
FLW_WEBHOOK_HASH=xxxxxxxx
FLW_PUBLIC_KEY=FLWPUBK_TEST-xxxxxxxx
FLW_ENV=sandbox

SUPABASE_URL=https://spnerrqumefbuuscumhw.supabase.co
SUPABASE_ANON_KEY=xxxxxxxx
```

**Checkpoint:** All keys recorded in `.env` → proceed to Phase 2

---

## PHASE 2: APPLY DATABASE MIGRATION
> **Time:** 5 minutes
> **T2 Approval Required:** No

### Step 2.1 — Open Supabase SQL Editor

**Go to:** https://supabase.com/dashboard/project/spnerrqumefbuuscumhw/sql

### Step 2.2 — Run the Migration

1. Open the file `supabase/migrations/20260826230000_production_payments_packaging.sql`
2. Copy the ENTIRE contents
3. Paste into the SQL Editor
4. Click **"Run"** (or Ctrl+Enter)

### Step 2.3 — Verify

Run this query to confirm:

```sql
-- Check new columns exist
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'payments'
AND column_name IN ('provider', 'idempotency_key', 'webhook_verified', 'refund_status')
ORDER BY column_name;
```

Expected: 4 rows returned (provider, idempotency_key, refund_status, webhook_verified)

```sql
-- Check new tables exist
SELECT table_name FROM information_schema.tables
WHERE table_name IN ('webhook_events', 'payment_audit')
ORDER BY table_name;
```

Expected: 2 rows returned

```sql
-- Check RPCs exist
SELECT routine_name FROM information_schema.routines
WHERE routine_name IN ('get_payment_by_idempotency', 'log_payment_audit', 'process_refund')
ORDER BY routine_name;
```

Expected: 3 rows returned

**Checkpoint:** Migration applied, tables verified → proceed to Phase 3

---

## PHASE 3: SET EDGE FUNCTION SECRETS
> **Time:** 5 minutes
> **T2 Approval Required:** No (secrets are sandbox)

### Option A: One-command (if .env is filled)

```powershell
powershell -File deploy.ps1
```

This reads `.env` and sets all secrets automatically.

### Option B: Manual secrets set

```bash
# M-Pesa
supabase secrets set MPESA_CONSUMER_KEY=your_key --project-ref spnerrqumefbuuscumhw
supabase secrets set MPESA_CONSUMER_SECRET=your_secret --project-ref spnerrqumefbuuscumhw
supabase secrets set MPESA_SHORTCODE=174379 --project-ref spnerrqumefbuuscumhw
supabase secrets set MPESA_PASSKEY=your_passkey --project-ref spnerrqumefbuuscumhw
supabase secrets set MPESA_ENV=sandbox --project-ref spnerrqumefbuuscumhw
supabase secrets set "MPESA_CALLBACK_URL=https://spnerrqumefbuuscumhw.supabase.co/functions/v1/payment-webhook?provider=mpesa" --project-ref spnerrqumefbuuscumhw

# Airtel Money
supabase secrets set AIRTEL_CLIENT_ID=your_client_id --project-ref spnerrqumefbuuscumhw
supabase secrets set AIRTEL_CLIENT_SECRET=your_client_secret --project-ref spnerrqumefbuuscumhw
supabase secrets set AIRTEL_ENV=sandbox --project-ref spnerrqumefbuuscumhw
supabase secrets set "AIRTEL_CALLBACK_URL=https://spnerrqumefbuuscumhw.supabase.co/functions/v1/payment-webhook?provider=airtel" --project-ref spnerrqumefbuuscumhw

# Flutterwave
supabase secrets set FLW_SECRET_KEY=your_secret_key --project-ref spnerrqumefbuuscumhw
supabase secrets set FLW_WEBHOOK_HASH=your_hash --project-ref spnerrqumefbuuscumhw
supabase secrets set FLW_ENV=sandbox --project-ref spnerrqumefbuuscumhw
```

### Verify secrets:

```bash
supabase secrets list --project-ref spnerrqumefbuuscumhw
```

Expected: all secrets listed with masked values.

**Checkpoint:** All secrets set → proceed to Phase 4

---

## PHASE 4: DEPLOY EDGE FUNCTIONS
> **Time:** 5-10 minutes
> **T2 Approval Required:** No

### Option A: Full deploy script

```powershell
powershell -File deploy.ps1 -SkipSecrets -SkipMigration
```

### Option B: Manual deploy

```powershell
# From mwarokin-estates/ root
supabase functions deploy payments --project-ref spnerrqumefbuuscumhw
supabase functions deploy mpesa-stk-push --project-ref spnerrqumefbuuscumhw
supabase functions deploy mpesa-callback --project-ref spnerrqumefbuuscumhw
supabase functions deploy airtel-money --project-ref spnerrqumefbuuscumhw
supabase functions deploy flutterwave --project-ref spnerrqumefbuuscumhw
supabase functions deploy payment-webhook --project-ref spnerrqumefbuuscumhw
supabase functions deploy currency --project-ref spnerrqumefbuuscumhw
supabase functions deploy translations --project-ref spnerrqumefbuuscumhw
```

### Verify functions are live:

```powershell
# Public endpoints (no auth needed)
curl https://spnerrqumefbuuscumhw.supabase.co/functions/v1/mpesa-callback
# Should return: {"ResultCode":0,"ResultDesc":"Accepted"} or similar

curl https://spnerrqumefbuuscumhw.supabase.co/functions/v1/payment-webhook
# Should return: {"status":"ok"}

# Auth-required endpoints (should return 401)
curl https://spnerrqumefbuuscumhw.supabase.co/functions/v1/payments
# Should return: 401 Unauthorized

curl https://spnerrqumefbuuscumhw.supabase.co/functions/v1/airtel-money
# Should return: 401 Unauthorized

curl https://spnerrqumefbuuscumhw.supabase.co/functions/v1/flutterwave
# Should return: 401 Unauthorized
```

### JWT Configuration Summary

| Function | verify_jwt | Who calls it |
|----------|-----------|--------------|
| `/payments` | **true** | User (needs login) |
| `/mpesa-stk-push` | **true** | User (needs login) |
| `/mpesa-callback` | **false** | Safaricom servers |
| `/airtel-money` | **true** | User (needs login) |
| `/flutterwave` | **true** | User (needs login) |
| `/payment-webhook` | **false** | All providers (public) |

**Checkpoint:** Functions deployed, endpoints verified → proceed to Phase 5

---

## PHASE 5: FRONTEND DEPLOYMENT & UI TESTING
> **Time:** 10-15 minutes
> **T2 Approval Required:** No

### Step 5.1 — Push to GitHub (triggers CI/CD)

```powershell
cd C:\Users\Administrator\OneDrive\Documents\Default Project\mwarokin-estates

git add .
git commit -m "Production: payment integration complete (M-Pesa + Airtel + Flutterwave)"
git push origin main
```

### Step 5.2 — Wait for GitHub Actions

1. Go to: https://github.com/99DevOps892/mwarokin-estates/actions
2. Watch the "Deploy" workflow complete
3. Verify it injects Supabase keys from secrets

### Step 5.3 — Open index.html to Test UI

**Local testing (no server needed):**

```powershell
# From the mwarokin-estates/ root
start app\index.html
```

Or directly:
```
file:///C:/Users/Administrator/OneDrive/Documents/Default Project/mwarokin-estates/app/index.html
```

**What to verify:**
- [ ] Page loads without console errors
- [ ] Supabase client initializes (check console for `[supabase-client]` logs)
- [ ] Login/Register forms work
- [ ] Property grid loads (if data exists)
- [ ] Language selector works
- [ ] Currency selector works
- [ ] Mobile responsive layout

### Step 5.4 — Test Payment UI

1. Login with a test account
2. Go to Dashboard
3. Click "Pay Rent"
4. Verify the payment modal shows:
   - Amount input
   - Method selector (M-Pesa / Airtel Money / Bank Transfer)
   - Phone number field (visible for M-Pesa/Airtel, hidden for bank)
   - Split preview (95% landlord / 5% platform)

### Step 5.5 — Test on Mobile Browser

1. Get your local IP: `ipconfig`
2. Open `http://YOUR-IP:PORT/app/index.html` on phone
3. Or use the GitHub Pages URL after deployment

**Checkpoint:** Frontend loads, UI works → proceed to Phase 6

---

## PHASE 6: SANDBOX TESTING (All 3 Payment Methods)
> **Time:** 20-30 minutes
> **T2 Approval Required:** No (sandbox only)

### Step 6.1 — M-Pesa Sandbox Test

1. Login to the app
2. Go to Dashboard → Pay Rent
3. Enter:
   - Amount: `100`
   - Method: `M-Pesa`
   - Phone: `254708374149` (Safaricom sandbox number)
4. Click "Pay"
5. Expected: STK push prompt on the sandbox phone
6. Enter PIN: `1234`
7. Expected: Payment status updates from "processing" → "completed"
8. Check: `payments` table in Supabase shows new row with status `completed`

**If STK push fails:**
- Check Edge Function logs: https://supabase.com/dashboard/project/spnerrqumefbuuscumhw/functions
- Common errors:
  - "M-Pesa credentials not configured" → secrets not set
  - "Invalid Kenyan phone number" → wrong phone format
  - "Daraja OAuth failed" → wrong Consumer Key/Secret

### Step 6.2 — Airtel Money Sandbox Test

1. Same flow as M-Pesa but select "Airtel Money"
2. Use sandbox phone number from Airtel docs
3. Expected: Airtel Money prompt
4. Complete the payment
5. Check: payment status updates

### Step 6.3 — Flutterwave Sandbox Test (Bank/Card)

1. Login → Dashboard → Pay Rent
2. Enter:
   - Amount: `500`
   - Method: `Bank Transfer` or `Card`
3. Click "Pay"
4. Expected: Redirect to Flutterwave payment page
5. Test card:
   ```
   Card: 4187427415564246
   CVV: 828
   PIN: 3310
   OTP: 12345
   ```
6. Complete payment
7. Expected: Redirect back to dashboard, payment confirmed
8. Check: webhook received, payment status updated

### Step 6.4 — Verify Webhook Events

```sql
-- In Supabase SQL Editor
SELECT provider, event_type, processed, created_at
FROM webhook_events
ORDER BY created_at DESC
LIMIT 10;
```

### Step 6.5 — Verify Payment Audit Trail

```sql
SELECT payment_id, action, new_status, actor, created_at
FROM payment_audit
ORDER BY created_at DESC
LIMIT 10;
```

### Step 6.6 — Test Idempotency

Try creating the same payment twice with the same `idempotency_key`:
```sql
-- Should fail (unique constraint)
INSERT INTO payments (idempotency_key, amount, payment_method, transaction_id)
VALUES ('test-idempotency-1', 100, 'mpesa', 'TEST-1');
INSERT INTO payments (idempotency_key, amount, payment_method, transaction_id)
VALUES ('test-idempotency-1', 100, 'mpesa', 'TEST-2');
-- Second insert should fail with unique violation
```

**Checkpoint:** All 3 payment methods work in sandbox → proceed to Phase 7

---

## PHASE 7: GO-LIVE (Switch to Production)
> **Time:** 30-60 minutes
> **T2 Approval Required:** YES — CEO must approve before switching providers

### Step 7.1 — CEO Approval

```
T2 APPROVAL REQUIRED:

Switch payment providers from sandbox → production.

Impact: Real money transactions will be processed.
Risk: Medium (can revert to sandbox by changing MPESA_ENV)

Providers to switch:
1. M-Pesa Daraja (Safaricom)
2. Airtel Money (Airtel Africa)
3. Flutterwave (bank + card)

CEO WhatsApp: +254704919388
```

### Step 7.2 — Update Secrets to Production

```bash
# M-Pesa PRODUCTION
supabase secrets set MPESA_ENV=production --project-ref spnerrqumefbuuscumhw
supabase secrets set MPESA_CONSUMER_KEY=PROD_KEY --project-ref spnerrqumefbuuscumhw
supabase secrets set MPESA_CONSUMER_SECRET=PROD_SECRET --project-ref spnerrqumefbuuscumhw
supabase secrets set MPESA_SHORTCODE=PROD_SHORTCODE --project-ref spnerrqumefbuuscumhw
supabase secrets set MPESA_PASSKEY=PROD_PASSKEY --project-ref spnerrqumefbuuscumhw

# Airtel PRODUCTION
supabase secrets set AIRTEL_ENV=production --project-ref spnerrqumefbuuscumhw
supabase secrets set AIRTEL_CLIENT_ID=PROD_ID --project-ref spnerrqumefbuuscumhw
supabase secrets set AIRTEL_CLIENT_SECRET=PROD_SECRET --project-ref spnerrqumefbuuscumhw

# Flutterwave PRODUCTION
supabase secrets set FLW_ENV=production --project-ref spnerrqumefbuuscumhw
supabase secrets set FLW_SECRET_KEY=FLWSECK-PROD --project-ref spnerrqumefbuuscumhw
supabase secrets set FLW_WEBHOOK_HASH=PROD_HASH --project-ref spnerrqumefbuuscumhw
```

### Step 7.3 — Register Production Callback URLs with Providers

**M-Pesa (Safaricom):**
- Go to Daraja Portal → your app → Production tab
- Set Callback URL: `https://spnerrqumefbuuscumhw.supabase.co/functions/v1/payment-webhook?provider=mpesa`

**Airtel Money:**
- Go to Airtel Developer Portal → your app → Settings
- Set Callback URL: `https://spnerrqumefbuuscumhw.supabase.co/functions/v1/payment-webhook?provider=airtel`

**Flutterwave:**
- Go to Flutterwave Dashboard → Settings → Webhooks
- Set Webhook URL: `https://spnerrqumefbuuscumhw.supabase.co/functions/v1/payment-webhook?provider=flutterwave`
- Set Redirect URL: `https://99devops892.github.io/mwarokin-estates/dashboard.html`

### Step 7.4 — Test with Real (Small) Amount

```bash
# Test M-Pesa with KES 1
# Use your real phone number
# Amount: 1
# Verify: payment completes, receipt received
```

### Step 7.5 — Verify Production

```sql
-- Check production payments are being recorded
SELECT transaction_id, amount, payment_method, status, provider, created_at
FROM payments
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;
```

**Checkpoint:** Production payments working → proceed to Phase 8

---

## PHASE 8: APPMYSITE — Configure, Build, Submit to Stores
> **Time:** 1-2 hours
> **T2 Approval Required:** Yes (store submissions)

### Step 8.1 — Create AppMySite Account

1. Go to: https://app.appmysite.com
2. Sign up / Login
3. Click **"Create New App"**

### Step 8.2 — Configure App

| Setting | Value |
|---------|-------|
| **App Type** | Web to App |
| **Website URL** | `https://99devops892.github.io/mwarokin-estates/` |
| **App Name** | Mwarokin Estates |
| **Package Name** | `com.syllogismtechnology.mwarokin` |
| **Category** | Business > Real Estate |
| **Description** | Premium property management platform. Browse properties, pay rent via M-Pesa, Airtel Money, or bank transfer. Track maintenance and manage your tenancy. |

### Step 8.3 — Branding

| Element | Value |
|---------|-------|
| **Primary Color** | `#0b1f33` |
| **Accent Color** | `#e8a33d` |
| **App Icon** | Upload `img/pwa-192.png` |
| **Splash Background** | `#0b1f33` |
| **Splash Logo** | White "M" on dark background |

### Step 8.4 — Navigation Tabs

| Tab | Label | URL | Icon |
|-----|-------|-----|------|
| 1 | Properties | `./index.html` | home |
| 2 | Dashboard | `./dashboard.html` | grid |
| 3 | Pay Rent | `./dashboard.html#pay` | wallet |
| 4 | Account | `./profile.html` | user |

### Step 8.5 — Push Notifications

1. Enable push notifications
2. (Optional) Set up Firebase for Android push
3. Topics: `payment_confirmed`, `payment_failed`, `maintenance_update`

### Step 8.6 — WebView Settings

- JavaScript: **Enabled**
- Cookies: **Enabled**
- DOM Storage: **Enabled**
- Cache: **Enabled**
- External Links: **Open in browser**
- File Downloads: **Enabled**

### Step 8.7 — Build & Test

1. Click **"Build App"**
2. Wait 5-15 minutes
3. Download **APK** (Android)
4. Install on real Android device
5. Test all flows:
   - [ ] App launches with splash screen
   - [ ] Login works
   - [ ] Property listing loads
   - [ ] Payment modal opens
   - [ ] M-Pesa payment initiates
   - [ ] Profile page loads
   - [ ] Bottom navigation works
   - [ ] Back button navigates correctly
   - [ ] Push notification test

### Step 8.8 — Store Submission

**Google Play Store:**
1. Go to: https://play.google.com/console
2. Create new app listing
3. Upload AAB from AppMySite
4. Fill store listing:
   - Title: `Mwarokin Estates`
   - Short description: `Premium property management & rent payment platform`
   - Full description: (see APPMYSITE_CONFIG.md)
   - Category: Business > Real Estate
   - Screenshots: (capture from AppMySite preview)
   - Feature graphic: 1024x500
5. Set content rating
6. Add privacy policy URL
7. Submit for review (24-72h)

**Apple App Store:**
1. Go to: https://appstoreconnect.apple.com
2. Create new app
3. Upload IPA from AppMySite
4. Fill store listing
5. Set age rating
6. Add privacy policy URL
7. Submit for review (24-48h)

### Step 8.9 — Post-Launch

- [ ] Monitor AppMySite analytics
- [ ] Check Supabase Edge Function logs daily
- [ ] Verify webhook delivery rates
- [ ] Track app installs
- [ ] Respond to store reviews
- [ ] Push updates via AppMySite (auto-syncs with website)

---

## ROLLBACK PROCEDURE

If anything goes wrong:

### Revert to Sandbox
```bash
supabase secrets set MPESA_ENV=sandbox --project-ref spnerrqumefbuuscumhw
supabase secrets set AIRTEL_ENV=sandbox --project-ref spnerrqumefbuuscumhw
supabase secrets set FLW_ENV=sandbox --project-ref spnerrqumefbuuscumhw
```

### Redeploy Previous Edge Functions
```bash
git checkout HEAD~1
powershell -File deploy.ps1 -SkipSecrets -SkipMigration
git checkout main
```

### Emergency Contact
```
CEO WhatsApp: +254704919388
Message: "EMERGENCY: Payment system rollback needed. [describe issue]"
```

---

## QUICK REFERENCE

### Command Summary
```powershell
# Full deploy (reads .env, sets secrets, deploys functions)
powershell -File deploy.ps1

# Deploy only functions (skip secrets/migration)
powershell -File deploy.ps1 -SkipSecrets -SkipMigration

# Deploy only frontend
powershell -File deploy.ps1 -SkipSecrets -SkipMigration -SkipFunctions

# Dry run (no changes)
powershell -File deploy.ps1 -DryRun

# Set a single secret
supabase secrets set KEY=VALUE --project-ref spnerrqumefbuuscumhw

# Deploy a single function
supabase functions deploy FUNCTION_NAME --project-ref spnerrqumefbuuscumhw

# List all secrets
supabase secrets list --project-ref spnerrqumefbuuscumhw
```

### URLs
| Service | URL |
|---------|-----|
| Supabase Dashboard | https://supabase.com/dashboard/project/spnerrqumefbuuscumhw |
| Edge Functions | https://supabase.com/dashboard/project/spnerrqumefbuuscumhw/functions |
| SQL Editor | https://supabase.com/dashboard/project/spnerrqumefbuuscumhw/sql |
| GitHub Pages | https://99devops892.github.io/mwarokin-estates/ |
| GitHub Actions | https://github.com/99DevOps892/mwarokin-estates/actions |
| AppMySite | https://app.appmysite.com |
| M-Pesa Portal | https://developer.safaricom.co.ke |
| Airtel Portal | https://developers.airtel.africa |
| Flutterwave | https://developer.flutterwave.com |

### Callback URLs (Register with Providers)
| Provider | Callback URL |
|----------|-------------|
| M-Pesa | `https://spnerrqumefbuuscumhw.supabase.co/functions/v1/payment-webhook?provider=mpesa` |
| Airtel | `https://spnerrqumefbuuscumhw.supabase.co/functions/v1/payment-webhook?provider=airtel` |
| Flutterwave | `https://spnerrqumefbuuscumhw.supabase.co/functions/v1/payment-webhook?provider=flutterwave` |

---

> **This document is your execution roadmap. Follow it phase by phase.
> Never skip a checkpoint. Never switch to production without CEO approval.
> Every command is copy-paste ready.**
