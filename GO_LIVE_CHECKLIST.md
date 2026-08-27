# Go-Live Checklist — Mwarokin Estates Production

> **Date:** 2026-08-26 · **Status:** Pre-production
> **Owner:** OpenCode (engineering) + CEO (approval)

---

## Phase 1: Secrets & Credentials

- [ ] **M-Pesa Daraja:** Obtain production Consumer Key, Consumer Secret, Passkey, Shortcode
  - Portal: https://developer.safaricom.co.ke
  - Status: `___________` (fill when provisioned)
- [ ] **Airtel Money:** Obtain production Client ID, Client Secret
  - Portal: https://developers.airtel.africa
  - Status: `___________`
- [ ] **Flutterwave:** Obtain production Secret Key, Webhook Hash, Public Key
  - Portal: https://developer.flutterwave.com
  - Status: `___________`
- [ ] **Supabase:** Anon key confirmed, Service Role key confirmed
  - Status: `___________`
- [ ] **GitHub Secrets:** All 4 secrets set in repo
  - Status: `___________`

## Phase 2: Database

- [ ] Migration `20260826230000_production_payments_packaging.sql` applied
- [ ] `webhook_events` table created
- [ ] `payment_audit` table created
- [ ] RPCs created (`get_payment_by_idempotency`, `log_payment_audit`, `process_refund`)
- [ ] RLS policies verified on new tables
- [ ] Test data seeded (if needed)

## Phase 3: Edge Functions

- [ ] All 7 functions deployed to production
- [ ] `/payments` — tested with M-Pesa STK push
- [ ] `/mpesa-stk-push` — tested independently
- [ ] `/mpesa-callback` — callback URL registered with Safaricom
- [ ] `/airtel-money` — tested with Airtel sandbox
- [ ] `/flutterwave` — tested with Flutterwave test cards
- [ ] `/payment-webhook` — tested with all 3 providers
- [ ] Webhook URLs registered:
  - [ ] Safaricom callback: `https://spnerrqumefbuuscumhw.supabase.co/functions/v1/payment-webhook?provider=mpesa`
  - [ ] Airtel callback: `https://spnerrqumefbuuscumhw.supabase.co/functions/v1/payment-webhook?provider=airtel`
  - [ ] Flutterwave webhook: `https://spnerrqumefbuuscumhw.supabase.co/functions/v1/payment-webhook?provider=flutterwave`

## Phase 4: Frontend

- [ ] Supabase anon key injected via GitHub Actions
- [ ] `config.js` has correct production values
- [ ] `manifest.json` is valid (test at pwabuilder.com)
- [ ] `sw.js` registers without errors
- [ ] Payment UI works for all 3 methods
- [ ] Payment status polling works (Realtime + fallback)
- [ ] Auth flows tested on mobile browser
- [ ] Mobile responsive layout verified
- [ ] i18n works (English, Swahili)
- [ ] Currency switching works

## Phase 5: Hosting & CDN

- [ ] GitHub Pages deployment successful
- [ ] Custom domain configured (if applicable)
- [ ] SSL certificate active
- [ ] Cloudflare CDN configured (if applicable)
- [ ] DNS records pointing correctly

## Phase 6: AppMySite

- [ ] App created in AppMySite dashboard
- [ ] Production URL entered
- [ ] Branding configured (icon, splash, colors)
- [ ] Bottom navigation mapped
- [ ] Push notifications configured
- [ ] WebView settings verified
- [ ] Android build downloaded and tested
- [ ] iOS build downloaded and tested
- [ ] Push notifications tested on real device
- [ ] Payment flows tested in-app

## Phase 7: Store Submission

- [ ] Google Play Store listing ready
  - [ ] App description written
  - [ ] Screenshots captured (phone + tablet)
  - [ ] Feature graphic created
  - [ ] Privacy policy URL added
  - [ ] Content rating completed
  - [ ] AAB uploaded
- [ ] Apple App Store listing ready
  - [ ] App description written
  - [ ] Screenshots captured
  - [ ] Privacy policy URL added
  - [ ] Age rating completed
  - [ ] IPA uploaded

## Phase 8: Monitoring & Support

- [ ] Supabase Edge Function logs monitored
- [ ] Payment webhook delivery verified
- [ ] Error tracking configured (Sentry or similar)
- [ ] Support WhatsApp number (+254704919388) in app footer
- [ ] Privacy policy page live
- [ ] Terms of service page live

## Phase 9: Final Verification

- [ ] Complete payment flow: Register → Login → Pay → Confirmation
- [ ] M-Pesa payment with real sandbox number
- [ ] Flutterwave payment with test card
- [ ] Airtel Money with sandbox
- [ ] Failed payment handling (wrong PIN, timeout)
- [ ] Refund flow tested (admin)
- [ ] Notification delivery verified
- [ ] Performance: page load < 3s on 3G
- [ ] All pages accessible (no 404s)
- [ ] Cross-browser tested (Chrome, Safari, Firefox)

---

## Sign-Off

| Checkpoint | Approved By | Date | Notes |
|------------|------------|------|-------|
| Secrets provisioned | | | |
| Database migrated | | | |
| Edge functions live | | | |
| Frontend deployed | | | |
| AppMySite builds pass | | | |
| Store submission ready | | | |
| **PRODUCTION GO-LIVE** | | | |

---

> **CEO Approval Required (T2):** Before switching any payment provider from sandbox to production.
> WhatsApp: +254704919388
