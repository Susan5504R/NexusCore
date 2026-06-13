"""Quick diagnostic: check what's in the pending_deployments table."""
import asyncio
import hashlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import get_settings
from app.services.ledger import _normalize_dsn

RAW_KEY = "nx_core_x2BlzGyAs8UEfNOweRC3_VYY74lTV1KOAqsebm2mcPU"

async def main():
    import asyncpg
    
    settings = get_settings()
    db_url = settings.supabase_db_url
    if not db_url:
        print("ERROR: No SUPABASE_DB_URL configured")
        return
    
    conn = await asyncpg.connect(_normalize_dsn(db_url), statement_cache_size=0)
    
    # 1. Check what namespace this API key maps to
    key_hash = hashlib.sha256(RAW_KEY.encode("utf-8")).hexdigest()
    row = await conn.fetchrow("SELECT namespace, revoked FROM api_keys WHERE key_hash = $1", key_hash)
    if row:
        print(f"API Key namespace: '{row['namespace']}' (revoked={row['revoked']})")
    else:
        print("ERROR: API key not found in database!")
        await conn.close()
        return
    
    daemon_namespace = row["namespace"]
    
    # 2. Check ALL pending_deployments
    rows = await conn.fetch(
        "SELECT patch_id, namespace, status, target_file, created_at FROM pending_deployments ORDER BY created_at DESC LIMIT 15"
    )
    print(f"\nAll pending_deployments ({len(rows)} rows):")
    for r in rows:
        match = "✅ MATCH" if r["namespace"] == daemon_namespace else "❌ MISMATCH"
        print(f"  [{r['status']:12}] ns='{r['namespace']}' {match} | file={r['target_file']} | {r['created_at']}")
    
    # 3. Check specifically for 'pending' status with daemon's namespace
    pending = await conn.fetch(
        "SELECT patch_id FROM pending_deployments WHERE namespace = $1 AND status = 'pending'",
        daemon_namespace
    )
    print(f"\nPending patches for namespace '{daemon_namespace}': {len(pending)}")
    
    await conn.close()

asyncio.run(main())
