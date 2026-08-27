# AppMySite Configuration — Mwarokin Estates

> **Status:** Ready for configuration
> **Production URL:** `https://99devops892.github.io/mwarokin-estates/`
> **Date:** 2026-08-26

---

## Pre-Configuration Checklist

- [ ] Production URL is live and accessible via HTTPS
- [ ] PWA manifest.json is valid (test at https://pwabuilder.com)
- [ ] Service worker registers without errors
- [ ] All payment flows work in mobile browser
- [ ] Auth flows (login, register, password reset) work on mobile
- [ ] Screenshots captured (mobile + desktop)

---

## AppMySite Setup Steps

### 1. Create App
1. Go to https://app.appmysite.com/app/create/
2. Select **"Web to App"**
3. Enter production URL: `https://99devops892.github.io/mwarokin-estates/`
4. Click **"Create App"**

### 2. Basic Information
| Field | Value |
|-------|-------|
| App Name | Mwarokin Estates |
| Package Name (Android) | `com.syllogismtechnology.mwarokin` |
| Bundle ID (iOS) | `com.syllogismtechnology.mwarokin` |
| Category | Business / Real Estate |
| Description | Premium property management & real estate platform. Browse properties, pay rent via M-Pesa/Airtel/Bank, track maintenance, and manage your tenancy — all in one app. |

### 3. Branding
| Element | Value |
|---------|-------|
| Primary Color | `#0b1f33` (brand-800) |
| Accent Color | `#e8a33d` (gold) |
| App Icon | Upload `img/pwa-192.png` (or custom 1024x1024) |
| Splash Screen | Use brand-800 background + centered "M" logo |
| Status Bar Style | Dark content on brand-800 background |
| Navigation Bar | Brand-800 background, white text |

### 4. Page Mapping (Bottom Navigation)
| Tab | Label | URL Path | Icon |
|-----|-------|----------|------|
| Home | Properties | `./index.html` | home |
| Dashboard | My Portal | `./dashboard.html` | grid |
| Payments | Pay Rent | `./dashboard.html#pay` | wallet |
| Profile | Account | `./profile.html` | user |

### 5. Push Notifications
- Enable push notifications
- Firebase Server Key: [Add from Firebase Console when ready]
- Notification topics:
  - `payment_confirmed` — Payment success alerts
  - `payment_failed` — Payment failure alerts
  - `maintenance_update` — Maintenance status changes
  - `lease_update` — Lease renewals and changes

### 6. WebView Settings
| Setting | Value |
|---------|-------|
| User Agent | (default — do not override) |
| JavaScript | Enabled |
| Cookies | Enabled |
| DOM Storage | Enabled |
| Cache | Enabled (for offline support) |
| External Links | Open in system browser |
| File Downloads | Enabled |
| Camera Access | Enabled (for profile photos) |

### 7. Hide Unwanted Elements
CSS selectors to hide in WebView (optional):
```css
/* Hide browser-specific elements that don't apply in app */
.nav-burger { display: none !important; }
```

### 8. Android Settings
| Setting | Value |
|---------|-------|
| Min SDK | 21 (Android 5.0) |
| Target SDK | 34 |
| Permissions | INTERNET, ACCESS_NETWORK_STATE, CAMERA, WRITE_EXTERNAL_STORAGE |
| Splash Screen Duration | 2000ms |
| Back Button | WebView back navigation |
| Hardware Acceleration | Enabled |

### 9. iOS Settings
| Setting | Value |
|---------|-------|
| Min iOS | 13.0 |
| Status Bar | Dark content, brand-800 background |
| Safe Area | Respect notch (notch-aware layout) |
| Splash Screen | Portrait only |

### 10. Build & Test
1. Click **"Build App"**
2. Wait for build completion (5-15 min)
3. Download APK (Android) for testing
4. Test on real Android device
5. Verify:
   - [ ] App launches with splash screen
   - [ ] Login/register works
   - [ ] Property listing loads
   - [ ] M-Pesa payment initiates STK push
   - [ ] Airtel Money flow initiates
   - [ ] Bank/card payment opens Flutterwave
   - [ ] Payment status updates in real-time
   - [ ] Push notifications arrive
   - [ ] Profile page works
   - [ ] Back button navigates correctly
   - [ ] Offline fallback shows cached content

### 11. Store Submission
1. **Google Play Store:**
   - Upload AAB from AppMySite
   - Add store listing (description, screenshots, category)
   - Set content rating
   - Add privacy policy URL
   - Submit for review

2. **Apple App Store:**
   - Upload IPA from AppMySite
   - Add store listing
   - Set age rating
   - Add privacy policy URL
   - Submit for review (allow 24-48h)

---

## Post-Launch Monitoring

- Monitor AppMySite analytics dashboard
- Check Supabase Edge Function logs for payment errors
- Verify payment webhook callbacks are received
- Monitor push notification delivery rates
- Track app installs and active users

---

## Rebuild Triggers

AppMySite auto-syncs with the production URL. Rebuild manually when:
- Major UI changes are deployed
- New pages are added
- PWA manifest is updated
- App icon or splash screen changes

---

## Support

- AppMySite Dashboard: https://app.appmysite.com
- STA Support: WhatsApp +254704919388
