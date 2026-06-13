import requests
import json
headers = {'Authorization': 'Bearer nx_core_x2BlzGyAs8UEfNOweRC3_VYY74lTV1KOAqsebm2mcPU'}
try:
    r = requests.get('https://nexuscore-rdc1.onrender.com/api/v1/ledger/logs', headers=headers, timeout=15)
    data = r.json()
    for e in data:
        if e.get('agent_action') == 'autonomous_repair':
            print(f"Status: {e.get('execution_status')} | Latency: {e.get('compute_latency_ms')}ms")
            payload = e.get('execution_payload', '')
            import re
            err = re.search(r"sandbox_stderr.*?([\w\W]*)", payload)
            if err:
                print(err.group(1)[:500])
            print("-" * 40)
except Exception as e:
    print(f'Error: {e}')
