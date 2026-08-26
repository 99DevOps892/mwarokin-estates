#!/usr/bin/env python3
"""
Mwarokin Estates — CSV → Supabase Import Script
Production-ready data ingestion from Desktop/mwarokin_estates_database/csv/

Usage:
  1. Set environment variables:
     export SUPABASE_URL="https://spnerrqumefbuuscumhw.supabase.co"
     export SUPABASE_SERVICE_KEY="your-service-role-key"
  
  2. Run: python import_csv_to_supabase.py
  
  3. Or import specific table: python import_csv_to_supabase.py --table properties

Architecture:
  - Reads CSV files from csv/ folder (22 tables)
  - Imports in dependency order (parents before children)
  - Uses Supabase REST API with service-role key
  - Handles UUID generation, conflict resolution, error logging
  - Dry-run mode available (--dry-run)
"""

import os
import sys
import csv
import json
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library required. Install: pip install requests")
    sys.exit(1)

# ============================================================
# CONFIGURATION
# ============================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://spnerrqumefbuuscumhw.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
CSV_DIR = Path(os.environ.get("CSV_DIR", 
    Path.home() / "OneDrive" / "Desktop" / "mwarokin_estates_database" / "csv"
))

# Import order (parents before children)
IMPORT_ORDER = [
    "organizations",
    "users",
    "properties",
    "units",
    "owners",
    "property_owners",
    "tenants",
    "leases",
    "vendors",
    "staff",
    "leads",
    "viewings",
    "rent_payments",
    "expenses",
    "maintenance_requests",
    "utility_readings",
    "utility_charges",
    "property_documents",
    "property_images",
    "tasks",
    "notifications",
    "audit_logs",
]

# UUID columns that need generation
UUID_COLUMNS = {
    "organizations": ["id"],
    "users": ["id"],
    "properties": ["id"],
    "units": ["id"],
    "owners": ["id"],
    "property_owners": ["id"],
    "tenants": ["id"],
    "leases": ["id"],
    "rent_payments": ["id"],
    "expenses": ["id"],
    "maintenance_requests": ["id"],
    "vendors": ["id"],
    "property_documents": ["id"],
    "property_images": ["id"],
    "viewings": ["id"],
    "leads": ["id"],
    "utility_readings": ["id"],
    "utility_charges": ["id"],
    "staff": ["id"],
    "tasks": ["id"],
    "notifications": ["id"],
    "audit_logs": ["id"],
}

# Foreign key columns (for UUID conversion)
FK_COLUMNS = {
    "properties": ["organization_id"],
    "units": ["property_id"],
    "owners": ["organization_id"],
    "property_owners": ["property_id", "owner_id"],
    "tenants": ["organization_id"],
    "leases": ["unit_id", "tenant_id"],
    "rent_payments": ["lease_id", "tenant_id", "unit_id"],
    "expenses": ["property_id", "unit_id"],
    "maintenance_requests": ["property_id", "unit_id", "tenant_id"],
    "vendors": ["organization_id"],
    "property_documents": ["property_id", "unit_id"],
    "property_images": ["property_id", "unit_id"],
    "viewings": ["property_id", "unit_id"],
    "leads": ["organization_id", "property_id", "unit_id"],
    "utility_readings": ["unit_id"],
    "utility_charges": ["lease_id", "unit_id"],
    "staff": ["organization_id", "user_id"],
    "tasks": ["organization_id", "property_id", "unit_id", "assigned_to"],
    "notifications": ["user_id"],
    "audit_logs": ["organization_id", "user_id"],
}

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("import")

# ============================================================
# SUPABASE CLIENT
# ============================================================

class SupabaseClient:
    def __init__(self, url: str, service_key: str):
        self.url = url.rstrip("/")
        self.service_key = service_key
        self.rest_url = f"{self.url}/rest/v1"
        self.headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        }
    
    def upsert(self, table: str, data: list[dict], chunk_size: int = 500) -> dict:
        """Upsert data in chunks. Returns stats."""
        stats = {"total": len(data), "success": 0, "errors": 0, "error_details": []}
        
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            try:
                resp = requests.post(
                    f"{self.rest_url}/{table}",
                    headers=self.headers,
                    json=chunk,
                    timeout=30,
                )
                if resp.status_code in (200, 201, 204):
                    stats["success"] += len(chunk)
                    log.info(f"  [{table}] Upserted chunk {i//chunk_size + 1}: {len(chunk)} rows")
                else:
                    stats["errors"] += len(chunk)
                    error_msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    stats["error_details"].append(error_msg)
                    log.error(f"  [{table}] Chunk {i//chunk_size + 1} failed: {error_msg}")
            except Exception as e:
                stats["errors"] += len(chunk)
                stats["error_details"].append(str(e))
                log.error(f"  [{table}] Chunk {i//chunk_size + 1} exception: {e}")
            
            # Rate limit protection
            time.sleep(0.1)
        
        return stats
    
    def count(self, table: str) -> int:
        """Get row count for a table."""
        try:
            resp = requests.get(
                f"{self.rest_url}/{table}",
                headers={**self.headers, "Prefer": "count=exact"},
                params={"select": "id", "limit": "0"},
                timeout=10,
            )
            if resp.status_code == 200:
                return int(resp.headers.get("content-range", "*/0").split("/")[1])
        except Exception:
            pass
        return -1

# ============================================================
# CSV PROCESSING
# ============================================================

def read_csv(filepath: Path) -> list[dict]:
    """Read CSV file and return list of dicts with proper type conversion."""
    rows = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            processed = {}
            for key, value in row.items():
                if key is None:
                    continue
                key = key.strip()
                value = value.strip() if value else None
                
                # Convert empty strings to None
                if value == "" or value is None:
                    processed[key] = None
                # Convert UUIDs (keep as strings, Supabase handles them)
                elif key in ("id",) + tuple(FK_COLUMNS.get(filepath.stem, [])):
                    processed[key] = value
                # Convert numbers
                elif key in ("amount", "rent_amount", "deposit_amount", "deposit", "price",
                            "estimated_cost", "actual_cost", "cost", "size_sqm",
                            "ownership_percentage", "reading_value", "platform_fee",
                            "landlord_amount", "platform_fee_percentage", "deposit_paid",
                            "deposit_balance", "lead_score", "engagement_score"):
                    try:
                        processed[key] = float(value) if value else None
                    except ValueError:
                        processed[key] = None
                elif key in ("bedrooms", "bathrooms", "floor", "sort_order", "view_count",
                            "unique_viewers", "retry_count", "file_size"):
                    try:
                        processed[key] = int(value) if value else None
                    except ValueError:
                        processed[key] = None
                # Convert booleans
                elif key in ("is_active", "is_featured", "is_verified", "is_read", "is_rtl"):
                    processed[key] = value.lower() in ("true", "1", "yes")
                # Convert JSON fields
                elif key in ("metadata", "notification_preferences", "amenities", "images",
                            "search_filters", "intent_signals", "preferred_channels",
                            "target_criteria", "channels", "schedule_config"):
                    try:
                        processed[key] = json.loads(value) if value else None
                    except (json.JSONDecodeError, TypeError):
                        processed[key] = None
                # Convert timestamps
                elif key.endswith("_at") or key.endswith("_date"):
                    if value and value not in ("", "NULL", "null"):
                        processed[key] = value
                    else:
                        processed[key] = None
                else:
                    processed[key] = value
            
            rows.append(processed)
    
    return rows

def validate_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        import uuid
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError):
        return False

def process_table(table_name: str, rows: list[dict]) -> list[dict]:
    """Process rows: ensure UUIDs are valid, handle FK references."""
    processed = []
    uuid_cols = UUID_COLUMNS.get(table_name, [])
    fk_cols = FK_COLUMNS.get(table_name, [])
    
    for row in rows:
        # Skip rows with invalid UUIDs in primary key
        if "id" in row and row["id"] and not validate_uuid(row["id"]):
            log.warning(f"  [{table_name}] Skipping row with invalid UUID: {row['id']}")
            continue
        
        # Skip rows where required FK references are invalid
        skip = False
        for fk_col in fk_cols:
            if fk_col in row and row[fk_col] and not validate_uuid(row[fk_col]):
                log.warning(f"  [{table_name}] Skipping row with invalid FK {fk_col}: {row[fk_col]}")
                skip = True
                break
        
        if not skip:
            processed.append(row)
    
    return processed

# ============================================================
# MAIN IMPORT
# ============================================================

def import_table(client: SupabaseClient, table_name: str, dry_run: bool = False) -> dict:
    """Import a single table from CSV."""
    csv_path = CSV_DIR / f"{table_name}.csv"
    
    if not csv_path.exists():
        log.warning(f"CSV not found: {csv_path}")
        return {"table": table_name, "status": "skipped", "reason": "csv_not_found"}
    
    log.info(f"Reading {csv_path}...")
    try:
        rows = read_csv(csv_path)
    except Exception as e:
        log.error(f"Failed to read {csv_path}: {e}")
        return {"table": table_name, "status": "error", "reason": str(e)}
    
    if not rows:
        log.info(f"  [{table_name}] No rows to import")
        return {"table": table_name, "status": "empty", "rows": 0}
    
    log.info(f"  [{table_name}] Processing {len(rows)} rows...")
    rows = process_table(table_name, rows)
    log.info(f"  [{table_name}] {len(rows)} rows after validation")
    
    if dry_run:
        log.info(f"  [{table_name}] DRY RUN — would upsert {len(rows)} rows")
        return {"table": table_name, "status": "dry_run", "rows": len(rows)}
    
    # Get existing count before import
    before_count = client.count(table_name)
    
    # Upsert
    stats = client.upsert(table_name, rows)
    
    # Get count after import
    after_count = client.count(table_name)
    
    result = {
        "table": table_name,
        "status": "success" if stats["errors"] == 0 else "partial",
        "csv_rows": len(rows),
        "before_count": before_count,
        "after_count": after_count,
        "upserted": stats["success"],
        "errors": stats["errors"],
    }
    
    if stats["error_details"]:
        result["error_details"] = stats["error_details"][:5]  # First 5 errors
    
    return result

def main():
    parser = argparse.ArgumentParser(description="Import CSV data to Supabase")
    parser.add_argument("--table", help="Import specific table only")
    parser.add_argument("--dry-run", action="store_true", help="Preview without importing")
    parser.add_argument("--order", action="store_true", help="Show import order and exit")
    parser.add_argument("--csv-dir", help="Override CSV directory path")
    args = parser.parse_args()
    
    global CSV_DIR
    if args.csv_dir:
        CSV_DIR = Path(args.csv_dir)
    
    if args.order:
        print("Import order (parents before children):")
        for i, table in enumerate(IMPORT_ORDER, 1):
            csv_path = CSV_DIR / f"{table}.csv"
            exists = "✓" if csv_path.exists() else "✗"
            print(f"  {i:2d}. {exists} {table}")
        return
    
    # Validate environment
    if not SUPABASE_SERVICE_KEY:
        log.error("SUPABASE_SERVICE_KEY not set. Export it first:")
        log.error("  export SUPABASE_SERVICE_KEY='your-service-role-key'")
        sys.exit(1)
    
    if not CSV_DIR.exists():
        log.error(f"CSV directory not found: {CSV_DIR}")
        sys.exit(1)
    
    client = SupabaseClient(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    # Determine tables to import
    if args.table:
        tables = [args.table]
    else:
        tables = IMPORT_ORDER
    
    log.info("=" * 60)
    log.info("Mwarokin Estates — CSV → Supabase Import")
    log.info(f"Supabase: {SUPABASE_URL}")
    log.info(f"CSV Dir:  {CSV_DIR}")
    log.info(f"Mode:     {'DRY RUN' if args.dry_run else 'LIVE IMPORT'}")
    log.info(f"Tables:   {len(tables)}")
    log.info("=" * 60)
    
    results = []
    total_success = 0
    total_errors = 0
    
    for table_name in tables:
        log.info(f"\n--- {table_name} ---")
        result = import_table(client, table_name, dry_run=args.dry_run)
        results.append(result)
        
        if "upserted" in result:
            total_success += result["upserted"]
        if "errors" in result:
            total_errors += result["errors"]
    
    # Summary
    log.info("\n" + "=" * 60)
    log.info("IMPORT SUMMARY")
    log.info("=" * 60)
    
    for r in results:
        status_icon = {"success": "✓", "partial": "~", "error": "✗", "skipped": "-", "empty": "○", "dry_run": "?"}.get(r["status"], "?")
        rows_info = r.get("csv_rows", r.get("rows", "N/A"))
        log.info(f"  {status_icon} {r['table']:30s} {rows_info:>6} rows  [{r['status']}]")
    
    log.info(f"\n  Total upserted: {total_success}")
    log.info(f"  Total errors:   {total_errors}")
    log.info("=" * 60)
    
    # Write results to file
    results_file = CSV_DIR.parent / f"import_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "supabase_url": SUPABASE_URL,
            "csv_dir": str(CSV_DIR),
            "dry_run": args.dry_run,
            "results": results,
            "total_success": total_success,
            "total_errors": total_errors,
        }, f, indent=2)
    
    log.info(f"\nResults saved to: {results_file}")
    
    if total_errors > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
