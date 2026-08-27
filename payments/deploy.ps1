# ============================================================
# deploy.ps1 — Deploy All Edge Functions
# Run from the supabase/ directory
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host "`n🚀 Deploying Payment Edge Functions to Supabase..." -ForegroundColor Cyan

# 1. Set secrets
Write-Host "`n📋 Setting Edge Function secrets..." -ForegroundColor Yellow

$secrets = @(
  "MPESA_CONSUMER_KEY",
  "MPESA_CONSUMER_SECRET",
  "MPESA_SHORTCODE",
  "MPESA_PASSKEY",
  "MPESA_ENV",
  "CALLBACK_URL",
  "AIRTEL_USER_ID",
  "AIRTEL_PASSWORD",
  "AIRTEL_SUBSCRIPTION_KEY",
  "AIRTEL_ENV",
  "AIRTEL_CALLBACK_URL"
)

foreach ($key in $secrets) {
  $value = [Environment]::GetEnvironmentVariable($key)
  if ($value) {
    Write-Host "  ✅ $key" -ForegroundColor Green
    & supabase secrets set "$key=$value"
  } else {
    Write-Host "  ⚠️  $key not found in local env — skipping" -ForegroundColor DarkYellow
  }
}

# 2. Deploy functions
Write-Host "`n🔧 Deploying functions..." -ForegroundColor Yellow

$functions = @(
  "mpesa-stk",
  "mpesa-callback",
  "mpesa-query",
  "airtel-money",
  "airtel-callback"
)

foreach ($fn in $functions) {
  Write-Host "  📦 Deploying $fn..." -ForegroundColor Cyan
  & supabase functions deploy $fn --project-ref spnerrqumefbuuscumhw
  if ($LASTEXITCODE -ne 0) {
    Write-Host "  ❌ Failed to deploy $fn" -ForegroundColor Red
    exit 1
  }
  Write-Host "  ✅ $fn deployed" -ForegroundColor Green
}

# 3. Run SQL migrations
Write-Host "`n🗄️  Running SQL migrations..." -ForegroundColor Yellow
Write-Host "  ⚠️  Run the SQL in supabase/sql/001_payments_table.sql manually via the Supabase Dashboard" -ForegroundColor DarkYellow
Write-Host "  Dashboard: https://supabase.com/dashboard/project/spnerrqumefbuuscumhw/sql" -ForegroundColor DarkYellow

Write-Host "`n✅ Deployment complete!" -ForegroundColor Green
Write-Host "   Test in sandbox first: https://developer.safaricom.co.ke/test-apis" -ForegroundColor Cyan
