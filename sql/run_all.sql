-- Jalankan dari ROOT proyek, setelah data mentah dimuat ke stg (automation/load_raw.py):
--   psql -h 127.0.0.1 -U ecom -d ecom_lumina -v ON_ERROR_STOP=1 -f sql/run_all.sql
-- (Setup sekali: 00 (superuser) dan 01. 02 & 03 idempoten.)
\set ON_ERROR_STOP on
-- 01_staging_ddl.sql sengaja TIDAK dijalankan di sini: ia membuat ulang tabel stg (kosong) dan mereset registri loader. Jalankan sekali saat setup / reset total.
\i sql/02_functions.sql
\i sql/03_core_ddl.sql
\i sql/04_dimensions.sql
\i sql/05_transform_orders.sql
\i sql/06_transform_ads_finance_monitor.sql
\i sql/07_marts_kpi.sql
\i sql/08_price_promo_compliance.sql
\i sql/09_bulk_order_detection.sql
\i sql/10_reconciliation_appeal.sql
\i sql/11_data_quality.sql
\i sql/12_etl_procedures.sql
\i sql/14_mart_dashboard.sql
\i sql/13_validate_answer_key.sql
