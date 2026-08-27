# ============================================================
# deploy.ps1 — Mwarokin Estates Full Production Deployment
# Run from the mwarokin-estates/ root directory
# Usage: powershell -File deploy.ps1
# Or: powershell -File deploy.ps1 -SkipSecrets -SkipMigration
# ============================================================
param(
  [switch]$SkipSecrets,
  [switch]$SkipMigration,
  [switch]$SkipFunctions,
  [switch]$SkipFrontend,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$PROJECT_REF = "spnerrqumefbuuscumhw"
$SUPABASE_URL = "https://spnerrqumefbuuscumhw.supabase.co"

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  MWAROKIN ESTATES — PRODUCTION DEPLOYMENT" -ForegroundColor Cyan
Write-Host "  Project: $PROJECT_REF" -ForegroundColor Cyan
Write-Host "============================================`n" -ForegroundColor Cyan

# ── Preflight checks ──
Write-Host "Preflight checks..." -ForegroundColor Yellow

try {
  $supabaseVersion = & supabase --version 2>&1
  Write-Host "  [OK] Supabase CLI: $supabaseVersion" -ForegroundColor Green
} catch {
  Write-Host "  [FAIL] Supabase CLI not installed. Run: npm i -g supabase" -ForegroundColor Red
  exit 1
}

try {
  $gitBranch = & git branch --show-current 2>&1
  Write-Host "  [OK] Git branch: $gitBranch" -ForegroundColor Green
} catch {
  Write-Host "  [WARN] Not in a git repo" -ForegroundColor DarkYellow
}

# Check for .env file
if (Test-Path ".env") {
  Write-Host "  [OK] .env file found" -ForegroundColor Green
} else {
  Write-Host "  [WARN] No .env file — secrets must be set manually" -ForegroundColor DarkYellow
}

Write-Host ""

# ═══════════════════════════════════════════════
# PHASE 1: DATABASE MIGRATION
# ═══════════════════════════════════════════════
if (-not $SkipMigration) {
  Write-Host "PHASE 1: Database Migration" -ForegroundColor Yellow
  Write-Host "  Migration file: supabase/migrations/20260826230000_production_payments_packaging.sql" -ForegroundColor Gray

  if ($DryRun) {
    Write-Host "  [DRY RUN] Would apply migration" -ForegroundColor DarkYellow
  } else {
    Write-Host "  Applying migration via Supabase SQL Editor..." -ForegroundColor Cyan
    Write-Host "  URL: https://supabase.com/dashboard/project/$PROJECT_REF/sql" -ForegroundColor Gray

    # Read the migration file
    $migrationFile = "supabase/migrations/20260826230000_production_payments_packaging.sql"
    if (Test-Path $migrationFile) {
      $sql = Get-Content $migrationFile -Raw
      Write-Host "  Migration SQL loaded ($(($sql.Length)) chars)" -ForegroundColor Green
      Write-Host "  >>> OPEN THE URL ABOVE AND PASTE THE SQL <<<" -ForegroundColor Yellow
      Write-Host "  >>> Then press Enter to continue <<<" -ForegroundColor Yellow
      Read-Host "  Press Enter when migration is applied"
    } else {
      Write-Host "  [FAIL] Migration file not found" -ForegroundColor Red
      exit 1
    }
  }
  Write-Host ""
}

# ═══════════════════════════════════════════════
# PHASE 2: SET EDGE FUNCTION SECRETS
# ═══════════════════════════════════════════════
if (-not $SkipSecrets) {
  Write-Host "PHASE 2: Edge Function Secrets" -ForegroundColor Yellow

  $secrets = @{
    # M-Pesa
    "MPESA_CONSUMER_KEY" = $null
    "MPESA_CONSUMER_SECRET" = $null
    "MPESA_SHORTCODE" = "174379"
    "MPESA_PASSKEY" = $null
    "MPESA_ENV" = "sandbox"
    "MPESA_CALLBACK_URL" = "$SUPABASE_URL/functions/v1/payment-webhook?provider=mpesa"

    # Airtel Money
    "AIRTEL_CLIENT_ID" = $null
    "AIRTEL_CLIENT_SECRET" = $null
    "AIRTEL_ENV" = "sandbox"
    "AIRTEL_CALLBACK_URL" = "$SUPABASE_URL/functions/v1/payment-webhook?provider=airtel"

    # Flutterwave
    "FLW_SECRET_KEY" = $null
    "FLW_WEBHOOK_HASH" = $null
    "FLW_ENV" = "sandbox"
  }

  # Try to load from .env
  if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
      if ($_ -match "^([^#=]+)=(.*)$") {
        $key = $matches[1].Trim()
        $val = $matches[2].Trim()
        if ($secrets.ContainsKey($key)) {
          $secrets[$key] = $val
        }
      }
    }
  }

  $setCount = 0
  $skipCount = 0

  foreach ($key in $secrets.Keys) {
    $value = $secrets[$key]
    if ($value -and $value -notmatch "^your_" -and $value -ne "null") {
      if ($DryRun) {
        Write-Host "  [DRY RUN] $key=***" -ForegroundColor DarkYellow
      } else {
        & supabase secrets set "$key=$value" --project-ref $PROJECT_REF 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
          Write-Host "  [OK] $key" -ForegroundColor Green
          $setCount++
        } else {
          Write-Host "  [FAIL] $key" -ForegroundColor Red
        }
      }
    } else {
      Write-Host "  [SKIP] $key — not set (fill in .env)" -ForegroundColor DarkYellow
      $skipCount++
    }
  }

  Write-Host "  Secrets: $setCount set, $skipCount skipped" -ForegroundColor Cyan
  if ($skipCount -gt 0) {
    Write-Host "  >>> Fill .env and re-run to set missing secrets <<<" -ForegroundColor Yellow
  }
  Write-Host ""
}

# ═══════════════════════════════════════════════
# PHASE 3: DEPLOY EDGE FUNCTIONS
# ═══════════════════════════════════════════════
if (-not $SkipFunctions) {
  Write-Host "PHASE 3: Deploy Edge Functions" -ForegroundColor Yellow

  $functions = @(
    "payments",
    "mpesa-stk-push",
    "mpesa-callback",
    "airtel-money",
    "flutterwave",
    "payment-webhook",
    "currency",
    "translations"
  )

  $deployed = 0
  $failed = 0

  foreach ($fn in $functions) {
    if ($DryRun) {
      Write-Host "  [DRY RUN] Deploy $fn" -ForegroundColor DarkYellow
      continue
    }

    Write-Host "  Deploying $fn..." -ForegroundColor Cyan -NoNewline
    & supabase functions deploy $fn --project-ref $PROJECT_REF 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
      Write-Host " [OK]" -ForegroundColor Green
      $deployed++
    } else {
      Write-Host " [FAIL]" -ForegroundColor Red
      $failed++
    }
  }

  Write-Host "  Functions: $deployed deployed, $failed failed" -ForegroundColor Cyan
  Write-Host ""
}

# ═══════════════════════════════════════════════
# PHASE 4: VERIFY DEPLOYMENT
# ═══════════════════════════════════════════════
Write-Host "PHASE 4: Verify Deployment" -ForegroundColor Yellow

$endpoints = @(
  @{ Name = "payments";          Auth = $true },
  @{ Name = "mpesa-stk-push";    Auth = $true },
  @{ Name = "mpesa-callback";    Auth = $false },
  @{ Name = "airtel-money";      Auth = $true },
  @{ Name = "flutterwave";       Auth = $true },
  @{ Name = "payment-webhook";   Auth = $false },
  @{ Name = "currency";          Auth = $true },
  @{ Name = "translations";      Auth = $false }
)

foreach ($ep in $endpoints) {
  $url = "$SUPABASE_URL/functions/v1/$($ep.Name)"
  try {
    $response = Invoke-WebRequest -Uri $url -Method GET -TimeoutSec 10 -ErrorAction Stop
    Write-Host "  [OK] $($ep.Name) — HTTP $($response.StatusCode)" -ForegroundColor Green
  } catch {
    $status = $_.Exception.Response.StatusCode.value__
    if ($status -eq 404) {
      Write-Host "  [WARN] $($ep.Name) — 404 (function may not exist yet)" -ForegroundColor DarkYellow
    } elseif ($status -eq 401 -and $ep.Auth) {
      Write-Host "  [OK] $($ep.Name) — 401 (auth required, function is live)" -ForegroundColor Green
    } elseif ($status -eq 401 -and -not $ep.Auth) {
      Write-Host "  [WARN] $($ep.Name) — 401 (should be public, check verify_jwt)" -ForegroundColor DarkYellow
    } else {
      Write-Host "  [INFO] $($ep.Name) — HTTP $status" -ForegroundColor Gray
    }
  }
}
Write-Host ""

# ═══════════════════════════════════════════════
# PHASE 5: DEPLOY FRONTEND (GitHub Pages)
# ═══════════════════════════════════════════════
if (-not $SkipFrontend) {
  Write-Host "PHASE 5: Frontend Deployment" -ForegroundColor Yellow
  Write-Host "  Frontend is deployed via GitHub Actions on push to main." -ForegroundColor Gray
  Write-Host "  To deploy:" -ForegroundColor Cyan
  Write-Host "    git add ." -ForegroundColor Gray
  Write-Host "    git commit -m 'Production deployment'" -ForegroundColor Gray
  Write-Host "    git push origin main" -ForegroundColor Gray
  Write-Host ""
  Write-Host "  GitHub Pages URL: https://99devops892.github.io/mwarokin-estates/" -ForegroundColor Gray
  Write-Host ""
}

# ═══════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  DEPLOYMENT SUMMARY" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Dashboard:    https://supabase.com/dashboard/project/$PROJECT_REF" -ForegroundColor Gray
Write-Host "  Edge Funcs:   https://supabase.com/dashboard/project/$PROJECT_REF/functions" -ForegroundColor Gray
Write-Host "  SQL Editor:   https://supabase.com/dashboard/project/$PROJECT_REF/sql" -ForegroundColor Gray
Write-Host "  Frontend:     https://99devops892.github.io/mwarokin-estates/" -ForegroundColor Gray
Write-Host ""
Write-Host "  Callback URLs (register with providers):" -ForegroundColor Yellow
Write-Host "    M-Pesa:     $SUPABASE_URL/functions/v1/payment-webhook?provider=mpesa" -ForegroundColor Gray
Write-Host "    Airtel:     $SUPABASE_URL/functions/v1/payment-webhook?provider=airtel" -ForegroundColor Gray
Write-Host "    Flutterwave: $SUPABASE_URL/functions/v1/payment-webhook?provider=flutterwave" -ForegroundColor Gray
Write-Host ""
Write-Host "  Next: Test in sandbox before going live!" -ForegroundColor Yellow
Write-Host ""
