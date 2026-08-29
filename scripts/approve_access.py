#!/usr/bin/env python3
"""H8391001 Access Gate — approve/deny an access request.
Inserts email into access_approved + updates access_requests status.

Usage: python3 approve_access.py <email> [approve|deny]
"""
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone

SUPABASE_URL = 'https://mbeftbvpeqfmyxvbpmcy.supabase.co'
CONFIG = '/home/snkwok/todo-dashboard-supabase/config.js'


def get_key():
    txt = open(CONFIG, encoding='utf-8').read()
    m = re.search(r"CONFIG_SUPABASE_ANON_KEY\s*=\s*'([^']+)'", txt)
    if not m:
        sys.exit('ERROR: anon key not found')
    return m.group(1)


def api(path, key, method='GET', body=None):
    url = SUPABASE_URL.rstrip('/') + path
    headers = {'apikey': key, 'Authorization': 'Bearer ' + key}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers['Content-Type'] = 'application/json'
        headers['Prefer'] = 'return=minimal'
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read().decode()
        return r.status, (json.loads(raw) if raw else None)


def main():
    if len(sys.argv) < 2:
        sys.exit('usage: approve_access.py <email> [approve|deny]')
    email = sys.argv[1].strip().lower()
    action = sys.argv[2].strip().lower() if len(sys.argv) > 2 else 'approve'
    key = get_key()
    now = datetime.now(timezone.utc).isoformat()

    if action == 'approve':
        # 1) upsert into access_approved (idempotent)
        st, _ = api('/rest/v1/access_approved', key, method='POST',
                    body={'email': email, 'approved_at': now})
        if st not in (200, 201):
            sys.exit(f'ERROR: insert access_approved failed {st}')
        # 2) update any pending request rows to approved
        st2, _ = api('/rest/v1/access_requests?email=eq.' + email + '&status=eq.pending',
                     key, method='PATCH',
                     body={'status': 'approved', 'decided_at': now})
        print(f'✅ APPROVED {email}')
    elif action == 'deny':
        st2, _ = api('/rest/v1/access_requests?email=eq.' + email + '&status=eq.pending',
                     key, method='PATCH',
                     body={'status': 'denied', 'decided_at': now})
        print(f'❌ DENIED {email}')
    else:
        sys.exit('unknown action: ' + action)


if __name__ == '__main__':
    main()
