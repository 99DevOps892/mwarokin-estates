# Mwarokin Estates — Production Deployment Guide

> **SyllogismTechnologyAfrica** · Updated 2026-08-26

---

## Architecture

```
User (Browser / AppMySite WebView / PWA)
        ↓
Frontend (HTML/JS/CSS)  ←→  Supabase Client (anon key)
        ↓
Supabase:
  - Auth (email + password)
  - PostgreSQL (30+ tables with RLS)
  - Storage (documents, images)
  - Edge Functions (7+ payment & utility functions)
        ↓
Payment Providers:
  - Safaricom Daraja (M-Pesa STK Push)
  - Airtel Africa API (Airtel Money)
  - Flutterwave (bank transfer + card)
        ↓
Callbacks → payment-webhook → update DB → notify users
```

## Edge Functions

| Function | Purpose | Auth |
|----------|---------|------|
| `/payments` | Create payment + initiate STK push | User JWT |
| `/mpesa-stk-push` | Direct M-Pesa STK push | User JWT |
| `/mpesa-callback` | M-Pesa callback (Safaricom → Supabase) | None (webhook) |
| `/airtel-money` | Airtel Money collection request | User JWT |
| `/flutterwave` | Flutterwave bank/card payment | User JWT |
| `/payment-webhook` | Unified webhook handler (all providers) | None (webhook) |
| `/currency` | Currency conversion | User JWT |
| `/translations` | i18n translations | Public |

## Payment Flow

### M-Pesa (Safaricom)
1. User enters phone + amount → calls `/payments`
2. Edge Function creates payment row + calls STK push
3. User gets M-Pesa prompt on phone
4. Safaricom calls `/payment-webhook?provider=mpesa`
5. Payment status updated → user sees confirmation

### Airtel Money
1. User enters phone + amount → calls `/airtel-money`
2. Edge Function creates payment + calls Airtel Collection API
3. User gets Airtel Money prompt
4. Airtel calls `/payment-webhook?provider=airtel`
5. Payment status updated

### Bank/Card (Flutterwave)
1. User enters amount → calls `/flutterwave`
2. Edge Function creates payment + gets Flutterwave payment link
3. User redirected to Flutterwave to complete payment
4. Flutterwave calls `/payment-webhook?provider=flutterwave`
5. Payment status updated

## Setup

### 1. Secrets (Supabase Edge Functions)
```bash
# Set all secrets from .env.supabase-secrets.example
supabase secrets set MPESA_ENV=production MPESA_CONSUMER_KEY=... --project-ref spnerrqumefbuuscumhw
```

### 2. Database Migration
```bash
# Apply the production payments packaging migration
# Via Supabase Dashboard > SQL Editor, run:
# supabase/migrations/20260826230000_production_payments_packaging.sql
```

### 3. Deploy Edge Functions
```bash
supabase functions deploy --project-ref spnerrqumefbuuscumhw
```

### 4. GitHub Secrets
| Secret | Purpose |
|--------|---------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Public anon key |
| `SUPABASE_ACCESS_TOKEN` | CLI access token |
| `SUPABASE_PROJECT_ID` | Project reference |

### 5. Deploy Frontend
Push to `main` branch — GitHub Actions handles deployment.

## Testing

### Sandbox Testing
1. Set `MPESA_ENV=sandbox` and test with Safaricom sandbox numbers
2. Set `FLW_ENV=sandbox` and test with Flutterwave test cards
3. Airtel sandbox for test transactions

### Test Card (Flutterwave)
- Card: `4187427415564246`
- CVV: `828`
- PIN: `3310`
- OTP: `12345`

## Go-Live Checklist

- [ ] All secrets rotated for production
- [ ] Daraja switched to production (sandbox → production)
- [ ] Flutterwave switched to production keys
- [ ] Airtel switched to production keys
- [ ] Domain + SSL verified
- [ ] RLS policies audited
- [ ] Payment success/failure UX polished
- [ ] Webhook URLs updated to production callbacks
- [ ] AppMySite builds tested on real devices
- [ ] Store listings ready
- [ ] Support channel live
- [ ] First real transaction tested with small amount
