#!/usr/bin/env python3
"""H8391001 Access Gate — approve/deny: add/remove email in data/access_allowlist.json + commit + push.
Usage: python3 approve_allowlist.py <email> [approve|deny]
"""
import json
import subprocess
import sys
import time

REPO = '/home/snkwok/H8391001-Inventory-Dashboard'
ALLOWLIST = REPO + '/data/access_allowlist.json'


def git(cmd):
    return subprocess.run(['git', '-C', REPO] + cmd, capture_output=True, text=True, timeout=60)


def main():
    if len(sys.argv) < 2:
        sys.exit('usage: approve_allowlist.py <email> [approve|deny]')
    email = sys.argv[1].strip().lower()
    action = sys.argv[2].strip().lower() if len(sys.argv) > 2 else 'approve'

    with open(ALLOWLIST, encoding='utf-8') as f:
        lst = json.load(f)
    lst = [str(e).strip().lower() for e in lst]

    if action == 'approve':
        if email not in lst:
            lst.append(email)
            print(f'✅ ADDED {email}')
        else:
            print(f'ℹ️ already approved: {email}')
    elif action == 'deny':
        if email in lst:
            lst.remove(email)
            print(f'❌ REMOVED {email}')
        else:
            print(f'ℹ️ not in allowlist: {email}')
    else:
        sys.exit('unknown action: ' + action)

    lst = sorted(set(lst))
    with open(ALLOWLIST, 'w', encoding='utf-8') as f:
        json.dump(lst, f, ensure_ascii=False, indent=2)

    git(['add', 'data/access_allowlist.json'])
    git(['commit', '-m', f'🔓 Access gate: {action} {email} ({time.strftime("%Y-%m-%d %H:%M")})'])
    git(['pull', '--rebase'])
    r = git(['push'])
    if r.returncode == 0:
        print('PUSHED')
    else:
        print('WARN: push failed — ' + r.stderr[-200:])


if __name__ == '__main__':
    main()
