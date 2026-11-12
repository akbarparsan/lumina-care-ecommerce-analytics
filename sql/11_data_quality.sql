-- =====================================================================================
-- 11_data_quality.sql : pemeriksaan integritas & akurasi data. Hasil disimpan di ops.dq_result (tren per run).
--   CRITICAL gagal -> tahan publikasi dashboard ; WARNING -> tinjau ; INFO -> konteks
-- Setiap pemeriksaan: nilai metrik, ambang, pembanding ('<=' atau '>='), status PASS/FAIL (INFO tidak dinilai)
-- =====================================================================================
CREATE SEQUENCE IF NOT EXISTS ops.dq_run_seq;

CREATE OR REPLACE VIEW ops.v_dq_checks AS
WITH asof AS (SELECT max(order_date) AS d FROM dwh.fact_order), dates AS (SELECT min(order_date) AS d0, max(order_date) AS d1 FROM dwh.fact_order)
-- ---------- INTEGRITAS ORDER
SELECT 'ORD01_GMV_HEADER_EQ_LINES' AS check_code, 'ORDERS' AS domain, 'CRITICAL' AS severity,
       abs((SELECT sum(gmv_placed) FROM dwh.fact_order) - (SELECT sum(line_gmv) FROM dwh.fact_order_line))::numeric AS metric, 0::numeric AS threshold, '<=' AS cmp,
       'Total GMV header order harus sama dengan total GMV baris' AS detail
UNION ALL SELECT 'ORD02_UNITS_HEADER_EQ_LINES', 'ORDERS', 'CRITICAL', abs((SELECT sum(units) FROM dwh.fact_order) - (SELECT sum(qty) FROM dwh.fact_order_line)), 0, '<=', 'Total unit header = total qty baris'
UNION ALL SELECT 'ORD03_ORPHAN_LINES', 'ORDERS', 'CRITICAL', (SELECT count(*) FROM dwh.fact_order_line l LEFT JOIN dwh.fact_order o USING (platform_code, order_id) WHERE o.order_id IS NULL), 0, '<=', 'Baris tanpa header'
UNION ALL SELECT 'ORD04_NULL_SKU', 'ORDERS', 'CRITICAL', (SELECT count(*) FROM dwh.fact_order_line WHERE sku IS NULL), 0, '<=', 'SKU kosong setelah recovery'
UNION ALL SELECT 'ORD05_SKU_NOT_IN_MASTER', 'ORDERS', 'CRITICAL', (SELECT count(*) FROM dwh.fact_order_line l LEFT JOIN dwh.dim_sku k USING (sku) WHERE k.sku IS NULL), 0, '<=', 'SKU tidak ada di master'
UNION ALL SELECT 'ORD06_NONPOSITIVE_QTY_OR_PRICE', 'ORDERS', 'CRITICAL', (SELECT count(*) FROM dwh.fact_order_line WHERE qty <= 0 OR unit_sell_price <= 0), 0, '<=', 'Qty/harga tidak positif'
UNION ALL SELECT 'ORD07_SELL_ABOVE_LIST', 'ORDERS', 'WARNING', (SELECT count(*) FROM dwh.fact_order_line WHERE unit_sell_price > unit_list_price + 1), 0, '<=', 'Harga jual di atas harga list'
UNION ALL SELECT 'ORD08_UNRESOLVED_CITY', 'ORDERS', 'WARNING', (SELECT count(*) FROM dwh.fact_order WHERE city IS NULL), 0, '<=', 'Kota tidak ter-resolve'
UNION ALL SELECT 'ORD09_UNKNOWN_VOUCHER_CODE', 'ORDERS', 'WARNING', (SELECT count(*) FROM dwh.fact_order o WHERE (seller_voucher_code IS NOT NULL AND NOT EXISTS (SELECT 1 FROM dwh.dim_voucher v WHERE v.voucher_code = o.seller_voucher_code))
                                                                                         OR (platform_voucher_code IS NOT NULL AND NOT EXISTS (SELECT 1 FROM dwh.dim_voucher v WHERE v.voucher_code = o.platform_voucher_code))), 0, '<=', 'Kode voucher di order tidak ada di master'
UNION ALL SELECT 'ORD10_NET_SALES_IDENTITY', 'ORDERS', 'CRITICAL', (SELECT count(*) FROM dwh.fact_order WHERE abs(net_sales_after_seller_voucher - (gmv_placed - seller_voucher_amt)) > 1), 0, '<=', 'Net sales = GMV - voucher penjual'
UNION ALL SELECT 'ORD11_ZERO_ORDER_DAYS', 'ORDERS', 'WARNING',
       (SELECT count(*) FROM dwh.dim_platform p CROSS JOIN dwh.dim_date d, dates WHERE d.date BETWEEN dates.d0 AND dates.d1
          AND NOT EXISTS (SELECT 1 FROM dwh.fact_order o WHERE o.platform_code = p.platform_code AND o.order_date = d.date)), 0, '<=', 'Hari tanpa order pada platform (indikasi file ekspor hilang)'
UNION ALL SELECT 'ORD12_QUARANTINE_RATE', 'ORDERS', 'WARNING',
       round(100.0 * (SELECT count(*) FROM ops.quarantine_row WHERE domain = 'ORDERS') / NULLIF((SELECT count(*) FROM ops.quarantine_row WHERE domain = 'ORDERS') + (SELECT count(*) FROM dwh.fact_order_line), 0), 3), 2, '<=', 'Persen baris order yang dikarantina (%)'
UNION ALL SELECT 'ORD13_STATUS_UNMAPPED', 'ORDERS', 'WARNING', (SELECT count(*) FROM dwh.fact_order WHERE status IS NULL OR status NOT IN ('COMPLETED','CANCELLED','RETURNED','SHIPPED','TO_SHIP')), 0, '<=', 'Status di luar kamus status'
-- ---------- ADS
UNION ALL SELECT 'ADS01_RELIABLE_SPEND_PCT', 'ADS', 'WARNING', round(100.0 * count(*) FILTER (WHERE spend_reliable) / count(*), 2), 98, '>=', 'Persen baris iklan dengan spend andal (%)' FROM dwh.fact_ads_daily
UNION ALL SELECT 'ADS02_CLICKS_GT_IMPRESSIONS_RAW', 'ADS', 'INFO', (SELECT count(*) FROM dwh.fact_ads_daily WHERE dq_flag LIKE '%CLICKS%'), NULL, NULL, 'Baris dengan klik > impresi (dikoreksi)'
UNION ALL SELECT 'ADS03_MISSING_AD_DAYS', 'ADS', 'WARNING',
       (SELECT count(*) FROM dwh.dim_platform p CROSS JOIN dwh.dim_date d, dates WHERE d.date BETWEEN dates.d0 AND dates.d1
          AND NOT EXISTS (SELECT 1 FROM dwh.fact_ads_daily a WHERE a.platform_code = p.platform_code AND a.ad_date = d.date)), 0, '<=', 'Hari tanpa data iklan pada platform'
UNION ALL SELECT 'ADS04_NEGATIVE_SPEND', 'ADS', 'CRITICAL', (SELECT count(*) FROM dwh.fact_ads_daily WHERE spend < 0), 0, '<=', 'Spend negatif setelah koreksi tanda'
UNION ALL SELECT 'ADS05_AD_GMV_GT_PLATFORM_GMV', 'ADS', 'WARNING',
       (SELECT count(*) FROM (SELECT a.platform_code, a.ad_date FROM dwh.fact_ads_daily a JOIN (SELECT platform_code, order_date, sum(gmv_placed) g FROM dwh.fact_order GROUP BY 1, 2) o
                               ON o.platform_code = a.platform_code AND o.order_date = a.ad_date GROUP BY 1, 2, o.g HAVING sum(a.ad_gmv) > o.g * 1.0) z), 0, '<=', 'Hari ketika GMV atribusi iklan melebihi GMV platform (mustahil)'
-- ---------- FINANCE
UNION ALL SELECT 'FIN01_SETTLEMENT_IDENTITY_BREAKS', 'SETTLEMENT', 'WARNING', (SELECT count(*) FROM dwh.fact_settlement WHERE dup_rank = 1 AND NOT net_identity_ok), 0, '<=', 'Net payout tidak sama gross-potongan pada data platform'
UNION ALL SELECT 'FIN02_SETTLEMENT_ON_NONCOMPLETED', 'SETTLEMENT', 'WARNING', (SELECT count(*) FROM dwh.fact_settlement s JOIN dwh.fact_order o USING (platform_code, order_id) WHERE NOT o.is_completed), 0, '<=', 'Settlement pada order tidak selesai'
UNION ALL SELECT 'FIN03_ORPHAN_SETTLEMENT', 'SETTLEMENT', 'INFO', (SELECT count(*) FROM ops.v_settlement_audit WHERE discrepancy_type = 'ORPHAN_SETTLEMENT'), NULL, NULL, 'Settlement tanpa order (sebagian akibat ID TikTok rusak yang dikarantina)'
UNION ALL SELECT 'FIN04_ERP_DUP_DOCS', 'ERP', 'WARNING', (SELECT count(*) - count(DISTINCT erp_doc_no) FROM dwh.fact_erp_sales), 0, '<=', 'Nomor dokumen ERP ganda'
UNION ALL SELECT 'FIN05_PROGRAM_STATEMENTS_UNMATCHED', 'PROGRAM', 'WARNING', (SELECT count(*) FROM dwh.fact_program_statement s LEFT JOIN ops.v_program_expected e USING (platform_code, program_code, period_label) WHERE e.platform_code IS NULL), 0, '<=', 'Statement yang tidak punya dasar perhitungan expected'
-- ---------- MONITORING HARGA
UNION ALL SELECT 'MON01_COVERAGE_PCT', 'MONITOR', 'WARNING', round(100.0 * avg(coverage), 2), 90, '>=', 'Rata-rata cakupan snapshot harga (%)' FROM ops.v_monitor_coverage
UNION ALL SELECT 'MON02_NULL_OR_ZERO_PRICE', 'MONITOR', 'INFO', (SELECT count(*) FROM ops.quarantine_row WHERE domain = 'MONITOR' AND reason LIKE 'PRICE%'), NULL, NULL, 'Snapshot dikarantina karena harga kosong/nol'
UNION ALL SELECT 'MON03_STALE_HOURS', 'MONITOR', 'WARNING', round(extract(epoch FROM (now()::timestamp - (SELECT max(snapshot_ts) FROM dwh.fact_price_snapshot))) / 3600), 24, '<=', 'Umur snapshot terakhir (jam) - pada data latihan wajar gagal'
-- ---------- KARANTINA (konteks)
UNION ALL SELECT 'QRN_' || domain || '_' || reason, domain, 'INFO', count(*), NULL, NULL, 'Baris dikarantina' FROM ops.quarantine_row GROUP BY domain, reason;

CREATE OR REPLACE FUNCTION ops.run_dq_checks() RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE rid bigint := nextval('ops.dq_run_seq');
BEGIN
    INSERT INTO ops.dq_result (run_id, check_code, domain, severity, status, metric_value, threshold, detail)
    SELECT rid, check_code, domain, severity,
           CASE WHEN cmp IS NULL THEN 'INFO' WHEN cmp = '<=' AND metric <= threshold THEN 'PASS' WHEN cmp = '>=' AND metric >= threshold THEN 'PASS' ELSE 'FAIL' END,
           metric, threshold, detail
    FROM ops.v_dq_checks;
    RETURN rid;
END $$;

-- Skor kualitas data terakhir
CREATE OR REPLACE VIEW ops.v_dq_latest AS
SELECT * FROM ops.dq_result WHERE run_id = (SELECT max(run_id) FROM ops.dq_result);

CREATE OR REPLACE VIEW ops.v_dq_scorecard AS
SELECT run_id, max(run_at) AS run_at, count(*) FILTER (WHERE status = 'PASS') AS passed, count(*) FILTER (WHERE status = 'FAIL') AS failed,
       count(*) FILTER (WHERE status = 'FAIL' AND severity = 'CRITICAL') AS critical_failed,
       round(100.0 * count(*) FILTER (WHERE status = 'PASS') / NULLIF(count(*) FILTER (WHERE status IN ('PASS', 'FAIL')), 0), 1) AS pass_pct,
       CASE WHEN count(*) FILTER (WHERE status = 'FAIL' AND severity = 'CRITICAL') > 0 THEN 'BLOCK_PUBLISH' ELSE 'OK_TO_PUBLISH' END AS publish_gate
FROM ops.dq_result GROUP BY run_id;

SELECT ops.run_dq_checks() AS run_id;
SELECT check_code, severity, status, metric_value, threshold FROM ops.v_dq_latest WHERE status <> 'INFO' ORDER BY status DESC, severity, check_code;
SELECT * FROM ops.v_dq_scorecard ORDER BY run_id DESC LIMIT 1;
