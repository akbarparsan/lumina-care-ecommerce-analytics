-- =====================================================================================
-- 00_create_database.sql
-- Jalankan SEKALI sebagai superuser (mis. postgres) dari database 'postgres':
--     psql -U postgres -f sql/00_create_database.sql
-- Membuat database, ekstensi, dan skema kerja.
--   stg   : landing mentah (semua TEXT, apa adanya dari ekspor platform)
--   etl   : fungsi parsing, registri file, tabel perantara
--   dwh   : model bersih (dimensi + fakta) -> sumber Power BI
--   mart  : view/materialized view KPI siap-dashboard
--   ops   : monitoring kepatuhan, deteksi order mencurigakan, rekonsiliasi, DQ, quarantine
--   qa    : (opsional) kunci jawaban untuk menguji akurasi aturan deteksi Anda
-- =====================================================================================
SELECT 'CREATE DATABASE ecom_lumina ENCODING ''UTF8'' TEMPLATE template0'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'ecom_lumina')\gexec

\connect ecom_lumina

CREATE EXTENSION IF NOT EXISTS pg_trgm;       -- pencocokan teks fuzzy (nama kota salah ketik)

CREATE SCHEMA IF NOT EXISTS stg;
CREATE SCHEMA IF NOT EXISTS etl;
CREATE SCHEMA IF NOT EXISTS dwh;
CREATE SCHEMA IF NOT EXISTS mart;
CREATE SCHEMA IF NOT EXISTS ops;
CREATE SCHEMA IF NOT EXISTS qa;

COMMENT ON SCHEMA stg  IS 'Landing mentah: semua kolom TEXT, jangan dimodifikasi';
COMMENT ON SCHEMA etl  IS 'Fungsi parsing & registri file';
COMMENT ON SCHEMA dwh  IS 'Model bersih (star schema) untuk Power BI';
COMMENT ON SCHEMA mart IS 'KPI siap dashboard';
COMMENT ON SCHEMA ops  IS 'Kepatuhan, deteksi anomali, rekonsiliasi, data quality';
COMMENT ON SCHEMA qa   IS 'Kunci jawaban latihan (opsional)';
