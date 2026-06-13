import asyncio
import asyncpg
import hashlib

db_url = 'postgresql://postgres:iE+,n8MU4+h/$5t@db.ovsaltdetqpklorussws.supabase.co:5432/postgres'

async def run():
    # Pass password explicitly so it doesn't get messed up in URL parsing
    conn = await asyncpg.connect(
        host="db.ovsaltdetqpklorussws.supabase.co",
        port=5432,
        user="postgres",
        password="iE+,n8MU4+h/$5t",
        database="postgres",
        statement_cache_size=0
    )
    key = hashlib.sha256('nx_core_x2BlzGyAs8UEfNOweRC3_VYY74lTV1KOAqsebm2mcPU'.encode()).hexdigest()
    ns = await conn.fetchrow('SELECT namespace FROM api_keys WHERE key_hash=$1', key)
    print(f'API Key Namespace: {ns["namespace"] if ns else "NOT FOUND"}')
    
    patches = await conn.fetch('SELECT patch_id, namespace, status FROM pending_deployments ORDER BY created_at DESC LIMIT 10')
    for p in patches:
        print(f'Patch: ns={p["namespace"]} status={p["status"]}')
        
    await conn.close()

asyncio.run(run())
