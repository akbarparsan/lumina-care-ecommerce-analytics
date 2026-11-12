# Pipeline harian untuk Windows (PowerShell). Jalankan dari mana saja:
#   powershell -ExecutionPolicy Bypass -File C:\lumina\ecom_portfolio\automation\run_pipeline.ps1
# Prasyarat: psql dan python ada di PATH. Ubah kata sandi di bawah bila Anda memakai kata sandi lain untuk pengguna ecom.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PGPASSWORD = "ecom"
$h = "127.0.0.1"; $u = "ecom"; $d = "ecom_lumina"

Write-Host "[$(Get-Date -Format s)] muat file mentah (idempoten: file yang sama dilewati)"
python automation/load_raw.py --host $h --user $u --db $d
if ($LASTEXITCODE -ne 0) { throw "load_raw gagal" }

Write-Host "[$(Get-Date -Format s)] transformasi + mart + ops"
psql -h $h -U $u -d $d -v ON_ERROR_STOP=1 -q -f sql/run_all.sql
if ($LASTEXITCODE -ne 0) { throw "run_all gagal" }

Write-Host "[$(Get-Date -Format s)] selesai"
