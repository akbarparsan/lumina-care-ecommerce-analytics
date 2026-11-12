#!/usr/bin/env bash
# Pipeline harian end-to-end: muat file mentah baru -> transformasi -> mart -> DQ.
# Contoh cron (setiap jam, menit 5):  5 * * * * cd /path/ecom_portfolio && PGPASSWORD=*** ./automation/run_pipeline.sh >> logs/pipeline.log 2>&1
# Windows: jalankan lewat Task Scheduler (Git Bash / WSL).
set -euo pipefail
cd "$(dirname "$0")/.."
export PGHOST="${PGHOST:-127.0.0.1}" PGUSER="${PGUSER:-ecom}" PGDATABASE="${PGDATABASE:-ecom_lumina}"
echo "[$(date -Is)] load raw (idempoten: file yang sudah dimuat dilewati lewat sha256)"
python3 automation/load_raw.py --host "$PGHOST" --user "$PGUSER" --db "$PGDATABASE"
echo "[$(date -Is)] transform + mart + ops"
psql -v ON_ERROR_STOP=1 -q -f sql/run_all.sql
echo "[$(date -Is)] selesai"
