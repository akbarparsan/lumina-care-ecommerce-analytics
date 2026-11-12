#!/usr/bin/env python3
"""
load_raw.py - Loader mentah multi-platform -> PostgreSQL (schema stg). IDEMPOTEN & TANPA dependensi Python tambahan.

Cara kerja
  * Tiap file CSV di data/raw/** dipetakan ke satu tabel staging (lihat STREAMS).
  * Checksum SHA-256 file dicatat di etl.file_registry. File yang sama di-SKIP; file yang berubah di-RELOAD
    (baris lamanya dihapus berdasarkan _src_file). Cocok dijadwalkan harian (Task Scheduler / cron).
  * Memakai `psql \\copy` sehingga cukup ada psql di PATH (ikut terpasang bersama PostgreSQL / pgAdmin).

Contoh
  python automation/load_raw.py --host localhost --port 5432 --user postgres --db ecom_lumina
  python automation/load_raw.py --only orders_shopee            # hanya satu stream
  python automation/load_raw.py --truncate                      # kosongkan staging lalu load ulang semua
Password: set env PGPASSWORD (jangan ditulis di skrip) atau gunakan file pgpass.
"""
import argparse, glob, hashlib, os, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")

# (tabel staging, pola file, delimiter)
STREAMS = [
    ("orders_shopee", "orders/shopee/*.csv", ","),
    ("orders_tiktok", "orders/tiktok_tokopedia/*.csv", ","),
    ("orders_lazada", "orders/lazada/*.csv", ","),
    ("orders_blibli", "orders/blibli/*.csv", ";"),          # Blibli mengekspor dengan titik-koma
    ("ads", "ads/*.csv", ","),
    ("voucher_master", "voucher/*.csv", ","),
    ("campaign_calendar", "promo/*.csv", ","),
    ("jbp_agreement", "jbp/*.csv", ","),
    ("fee_contract", "contract/*.csv", ","),
    ("settlement_shopee", "settlement/raw_settlement_shopee.csv", ","),
    ("settlement_tiktok", "settlement/raw_settlement_tiktok_tokopedia.csv", ","),
    ("settlement_lazada", "settlement/raw_settlement_lazada.csv", ","),
    ("settlement_blibli", "settlement/raw_settlement_blibli.csv", ","),
    ("program_statement", "program/*.csv", ","),
    ("erp_sales", "erp/*.csv", ","),
    ("price_monitor", "monitoring/*.csv", ","),
    ("sku_master", "master/sku_master.csv", ","),
    ("listing_map", "master/listing_map.csv", ","),
    ("authorized_sellers", "master/authorized_sellers.csv", ","),
    ("ref_city_alias", "master/ref_city_alias.csv", ","),
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_psql(conn, *, command=None, script=None, tuples=False):
    cmd = ["psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-h", conn["host"], "-p", str(conn["port"]), "-U", conn["user"], "-d", conn["db"]]
    if tuples:
        cmd += ["-At", "-F", "|"]
    if command:
        cmd += ["-c", command]
    if script:
        cmd += ["-1", "-f", script]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"psql gagal: {r.stderr.strip()}")
    return r.stdout


def q(s):
    return "'" + s.replace("'", "''") + "'"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default=os.environ.get("PGHOST", "localhost"))
    ap.add_argument("--port", default=os.environ.get("PGPORT", "5432"))
    ap.add_argument("--user", default=os.environ.get("PGUSER", "postgres"))
    ap.add_argument("--db", default=os.environ.get("PGDATABASE", "ecom_lumina"))
    ap.add_argument("--only", help="nama stream tunggal, mis. orders_shopee")
    ap.add_argument("--truncate", action="store_true", help="kosongkan semua tabel staging + registry lebih dulu")
    a = ap.parse_args()
    conn = dict(host=a.host, port=a.port, user=a.user, db=a.db)

    if a.truncate:
        names = [s[0] for s in STREAMS if not a.only or s[0] == a.only]
        run_psql(conn, command="TRUNCATE " + ", ".join(f"stg.{n}" for n in names) + " RESTART IDENTITY; DELETE FROM etl.file_registry WHERE stream = ANY(ARRAY[" + ",".join(q(n) for n in names) + "]);")
        print("staging dikosongkan:", ", ".join(names))

    reg = {}
    for line in run_psql(conn, command="SELECT file_path, sha256 FROM etl.file_registry", tuples=True).splitlines():
        if line.strip():
            k, v = line.split("|")
            reg[k] = v

    total_rows = 0; t0 = time.time()
    print(f"{'stream':<20}{'file':<58}{'status':<10}{'baris':>9}")
    for stream, pattern, sep in STREAMS:
        if a.only and stream != a.only:
            continue
        cols = run_psql(conn, tuples=True, command=(
            "SELECT string_agg(column_name, ',' ORDER BY ordinal_position) FROM information_schema.columns "
            f"WHERE table_schema='stg' AND table_name={q(stream)} AND column_name NOT LIKE '\\_%'")).strip()
        for path in sorted(glob.glob(os.path.join(RAW, pattern))):
            rel = os.path.relpath(path, ROOT).replace("\\", "/")
            digest = sha256(path)
            if reg.get(rel) == digest:
                print(f"{stream:<20}{rel[-56:]:<58}{'SKIP':<10}{'':>9}")
                continue
            status = "RELOAD" if rel in reg else "LOAD"
            p = path.replace("\\", "/")
            sql = []
            if status == "RELOAD":
                sql.append(f"DELETE FROM stg.{stream} WHERE _src_file = {q(rel)};")
            sql.append(f"\\copy stg.{stream} ({cols}) FROM {q(p)} WITH (FORMAT csv, HEADER true, DELIMITER {q(sep)}, ENCODING 'UTF8')")
            sql.append(f"UPDATE stg.{stream} SET _src_file = {q(rel)} WHERE _src_file IS NULL;")
            sql.append("INSERT INTO etl.file_registry (file_path, stream, sha256, rows_loaded, loaded_at) "
                       f"SELECT {q(rel)}, {q(stream)}, {q(digest)}, count(*), now() FROM stg.{stream} WHERE _src_file = {q(rel)} "
                       "ON CONFLICT (file_path) DO UPDATE SET sha256 = EXCLUDED.sha256, rows_loaded = EXCLUDED.rows_loaded, loaded_at = EXCLUDED.loaded_at;")
            with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False, encoding="utf-8") as tf:
                tf.write("\n".join(sql) + "\n")
                tmp = tf.name
            try:
                run_psql(conn, script=tmp)
            finally:
                os.unlink(tmp)
            n = int(run_psql(conn, tuples=True, command=f"SELECT rows_loaded FROM etl.file_registry WHERE file_path = {q(rel)}").strip())
            total_rows += n
            print(f"{stream:<20}{rel[-56:]:<58}{status:<10}{n:>9}")
    print(f"selesai: {total_rows:,} baris baru dimuat dalam {time.time() - t0:.1f} detik")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        sys.exit(str(e))
