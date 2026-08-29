#!/bin/bash
# sync_private.sh — H8391001: copy index.html + data/ + reports/ to the PRIVATE repo + push
# B pilot (2026-08-29): dashboard + data 唔再喺 public repo；由 crons 喺 build 完成後 call
set -euo pipefail
SRC="${1:-/home/snkwok/H8391001-Inventory-Dashboard}"
DST=/home/snkwok/dashboard-private-data/H8391001
cd "$SRC"
mkdir -p "$DST/data" "$DST/reports"
# 只喺 index.html 係完整 dashboard（冇 dashFrame marker）先同步 —— loader 唔可以冚 private
if ! grep -q 'dashFrame' index.html 2>/dev/null; then
  cp -f index.html /tmp/h839_sync_index.html
  bash /home/snkwok/scripts/gate_strip_shared.sh /tmp/h839_sync_index.html H8391001 >/dev/null
  cp -f /tmp/h839_sync_index.html "$DST/index.html" 2>/dev/null || true
fi
cp -f data/*.csv data/*.json data/*.js "$DST/data/" 2>/dev/null || true
cp -rf reports/* "$DST/reports/" 2>/dev/null || true
cd "$DST"
if git status --short | grep -q .; then
  git add -A
  git -c user.email="hermes@fificheck.local" -c user.name="Hermes" commit -q -m "H8391001 daily update $(date '+%F %T')"
  git push origin main -q
  echo "✅ private repo synced ($(date '+%F %T'))"
else
  echo "ℹ️ 冇嘢改 — skip push"
fi
