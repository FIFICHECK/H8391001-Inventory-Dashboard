#!/usr/bin/env python3
"""H8391001 Access Gate — poll pending access requests.
- Queries Supabase access_requests where status=pending
- Prints NEW pending requests (not yet notified) as JSON lines for the cron agent
- Marks them notified_at=now() so each request notifies once

Usage: python3 poll_access_requests.py [--dry-run]
"""
import json
import os
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
        print('ERROR: anon key not found', file=sys.stderr)
        sys.exit(1)
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
    dry = '--dry-run' in sys.argv
    key = get_key()
    # 1) fetch pending + not-yet-notified requests
    st, rows = api('/rest/v1/access_requests?status=eq.pending&notified_at=is.null&select=id,email,created_at&order=created_at.asc', key)
    if st != 200 or not rows:
        print('SILENT')
        return
    # 2) print new requests for the cron agent
    out = []
    for r in rows:
        out.append({'id': r['id'], 'email': r['email'],
                    'created_at': r.get('created_at', '')})
    print(json.dumps(out, ensure_ascii=False))
    # 3) mark notified (unless dry-run)
    if not dry:
        for r in rows:
            api('/rest/v1/access_requests?id=eq.' + str(r['id']),
                key, method='PATCH',
                body={'notified_at': datetime.now(timezone.utc).isoformat()})


if __name__ == '__main__':
    main()
