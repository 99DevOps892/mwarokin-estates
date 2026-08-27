# M-Pesa & Airtel Money — STK Push Integration

Production-ready mobile money integration for your Supabase + frontend stack.

## Architecture

```
Frontend (HTML/JS)
    │
    ├─► mpesa-stk (Edge Function)
    │       │
    │       ├─► Safaricom OAuth → Access Token
    │       ├─► STK Push → Customer phone
    │       └─► INSERT payments (status: pending)
    │
    ├─► airtel-money (Edge Function)
    │       │
    │       ├─► Airtel OAuth → Access Token
    │       ├─► Collection Request → Customer phone
    │       └─► INSERT payments (status: pending)
    │
    ├─► Polling / Realtime ← payments table
    │
    └─► mpesa-callback / airtel-callback ← Provider POST
            │
            └─► UPDATE payments (status: success/failed)
```

## Setup

### 1. Run SQL Migration

Go to [Supabase Dashboard → SQL Editor](https://supabase.com/dashboard/project/spnerrqumefbuuscumhw/sql) and run:

```
supabase/sql/001_payments_table.sql
```

### 2. Set Secrets

```bash
supabase secrets set \
  MPESA_CONSUMER_KEY=xxx \
  MPESA_CONSUMER_SECRET=xxx \
  MPESA_SHORTCODE=174379 \
  MPESA_PASSKEY=xxx \
  MPESA_ENV=sandbox \
  CALLBACK_URL=https://spnerrqumefbuuscumhw.supabase.co/functions/v1/mpesa-callback \
  AIRTEL_USER_ID=xxx \
  AIRTEL_PASSWORD=xxx \
  AIRTEL_SUBSCRIPTION_KEY=xxx \
  AIRTEL_ENV=sandbox \
  AIRTEL_CALLBACK_URL=https://spnerrqumefbuuscumhw.supabase.co/functions/v1/airtel-callback
```

### 3. Deploy Functions

```bash
cd payments/supabase
powershell -File ../deploy.ps1
```

Or manually:

```bash
supabase functions deploy mpesa-stk --project-ref spnerrqumefbuuscumhw
supabase functions deploy mpesa-callback --project-ref spnerrqumefbuuscumhw
supabase functions deploy mpesa-query --project-ref spnerrqumefbuuscumhw
supabase functions deploy airtel-money --project-ref spnerrqumefbuuscumhw
supabase functions deploy airtel-callback --project-ref spnerrqumefbuuscumhw
```

### 4. Frontend

Drop `payment-client.js` and `index.html` into your project. The client exposes:

```js
// M-Pesa
const result = await MpesaPayment.initiate({ phone, amount });
MpesaPayment.pollStatus(result.checkoutRequestId, null, {
  onSuccess: (data) => console.log("Receipt:", data.mpesa_receipt),
  onFailure: (data) => console.log("Failed:", data.status_reason),
  onTimeout: () => console.log("Timed out"),
});

// Airtel
const result = await AirtelPayment.initiate({ phone, amount });
```

## Key Files

| File | Purpose |
|------|---------|
| `sql/001_payments_table.sql` | Payments + events tables, RLS, realtime |
| `supabase/functions/mpesa-stk/index.ts` | STK Push initiation |
| `supabase/functions/mpesa-callback/index.ts` | Safaricom callback handler |
| `supabase/functions/mpesa-query/index.ts` | STK status query fallback |
| `supabase/functions/airtel-money/index.ts` | Airtel collection initiation |
| `supabase/functions/airtel-callback/index.ts` | Airtel callback handler |
| `js/payment-client.js` | Frontend SDK (polling, realtime, initiate) |
| `index.html` | Premium payment UI component |
| `deploy.ps1` | One-command deployment script |

## Production Checklist

- [ ] Switch `MPESA_ENV=production` + `AIRTEL_ENV=production`
- [ ] Replace sandbox credentials with live ones
- [ ] Verify callback URLs are whitelisted with providers
- [ ] Enable RLS policies as needed for your auth model
- [ ] Set up webhook logging / alerts
- [ ] Test end-to-end with real phones before go-live

## Common M-Pesa Result Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Insufficient balance |
| 1032 | User cancelled |
| 1037 | PIN timeout |
| 2001 | Wrong PIN |
