-- =====================================================================================
-- 13_validate_answer_key.sql : uji akurasi pipeline & aturan deteksi terhadap kunci jawaban (data sintetis).
-- Jalankan dari ROOT proyek (path \copy relatif):  psql -d ecom_lumina -f sql/13_validate_answer_key.sql
-- Hasil: qa.validation_summary (recall/precision per skenario) + qa.kpi_tieout (selisih KPI bulanan vs kunci)
-- =====================================================================================
CREATE SCHEMA IF NOT EXISTS qa;

DROP TABLE IF EXISTS qa.gt_order_anomalies, qa.gt_voucher_violations, qa.gt_price_violations, qa.gt_settlement_discrepancies, qa.gt_program_discrepancies, qa.gt_monthly_kpi_clean CASCADE;
CREATE TABLE qa.gt_order_anomalies (platform_code text, order_id text, scenario text, cluster_id text, ts text, usr text, phone text, city_canon text, ord_sub text, status text);
CREATE TABLE qa.gt_voucher_violations (platform_code text, order_id text, voucher_code text, violation_type text);
CREATE TABLE qa.gt_price_violations (snapshot_ts text, platform_code text, seller_name text, listing_id text, price_displayed text, floor_unit text, pack text, violation_type text, injected_cause text);
CREATE TABLE qa.gt_settlement_discrepancies (platform_code text, order_id text, discrepancy_type text, impact_idr numeric);
CREATE TABLE qa.gt_program_discrepancies (platform_code text, program_code text, period_label text, expected_idr numeric, paid_idr numeric, shortfall_idr numeric);
CREATE TABLE qa.gt_monthly_kpi_clean (platform_code text, month text, order_lines bigint, gmv_placed numeric, gross_list_gmv numeric, orders_placed bigint, orders_completed bigint, net_gmv numeric, seller_voucher_completed numeric, platform_voucher_completed numeric);

\copy qa.gt_order_anomalies FROM 'answer_key/gt_order_anomalies.csv' CSV HEADER
\copy qa.gt_voucher_violations FROM 'answer_key/gt_voucher_violations.csv' CSV HEADER
\copy qa.gt_price_violations FROM 'answer_key/gt_price_violations.csv' CSV HEADER
\copy qa.gt_settlement_discrepancies FROM 'answer_key/gt_settlement_discrepancies.csv' CSV HEADER
\copy qa.gt_program_discrepancies FROM 'answer_key/gt_program_discrepancies.csv' CSV HEADER
\copy qa.gt_monthly_kpi_clean FROM 'answer_key/gt_monthly_kpi_clean.csv' CSV HEADER

DROP TABLE IF EXISTS qa.validation_summary;
CREATE TABLE qa.validation_summary AS
WITH
-- 1. order mencurigakan: apakah order GT terdeteksi oleh minimal satu aturan yang relevan?
ord AS (
    SELECT g.scenario AS test, count(*) AS truth, count(*) FILTER (WHERE s.order_id IS NOT NULL AND
              ((g.scenario = 'BULK_QTY' AND s.r1_bulk_qty) OR (g.scenario = 'PRICE_ERROR' AND s.r4_price) OR (g.scenario = 'VELOCITY_BURST' AND s.r2_velocity)
               OR (g.scenario = 'ACCOUNT_FARM' AND (s.r3_farm OR s.r2_velocity)))) AS detected
    FROM qa.gt_order_anomalies g LEFT JOIN ops.v_suspicious_orders s USING (platform_code, order_id) GROUP BY 1),
ord_pred AS (
    SELECT 'ORDER_ANY_RULE_PRECISION' AS test, count(*) AS flagged,
           count(*) FILTER (WHERE EXISTS (SELECT 1 FROM qa.gt_order_anomalies g WHERE g.platform_code = s.platform_code AND g.order_id = s.order_id)) AS correct
    FROM ops.v_suspicious_orders s WHERE r1_bulk_qty OR r2_velocity OR r3_farm OR r4_price),
-- 2. voucher: level jumlah (tie order pada timestamp identik dapat berbeda -> bandingkan per tipe pelanggaran dan order-kode)
vou AS (
    SELECT g.violation_type AS test, count(*) AS truth,
           count(*) FILTER (WHERE EXISTS (SELECT 1 FROM ops.v_voucher_rule_violations v WHERE v.platform_code = g.platform_code AND v.order_id = g.order_id
                                           AND v.voucher_code = g.voucher_code AND v.violation_type = g.violation_type)) AS detected
    FROM qa.gt_voucher_violations g GROUP BY 1),
-- 3. settlement & ERP
sett AS (
    SELECT g.discrepancy_type AS test, count(*) AS truth,
           count(*) FILTER (WHERE EXISTS (SELECT 1 FROM (SELECT platform_code, order_id, discrepancy_type FROM ops.v_settlement_audit UNION ALL SELECT platform_code, order_id, discrepancy_type FROM ops.v_erp_audit) a
                                           WHERE a.platform_code = g.platform_code AND a.order_id = g.order_id AND a.discrepancy_type = g.discrepancy_type)) AS detected
    FROM qa.gt_settlement_discrepancies g GROUP BY 1),
sett_pred AS (
    SELECT a.discrepancy_type AS test, count(*) AS flagged,
           count(*) FILTER (WHERE EXISTS (SELECT 1 FROM qa.gt_settlement_discrepancies g WHERE g.platform_code = a.platform_code AND g.order_id = a.order_id AND g.discrepancy_type = a.discrepancy_type)) AS correct
    FROM (SELECT platform_code, order_id, discrepancy_type FROM ops.v_settlement_audit UNION ALL SELECT platform_code, order_id, discrepancy_type FROM ops.v_erp_audit) a GROUP BY 1),
-- 4. program
prog AS (
    SELECT 'PROGRAM_SHORTFALL' AS test, count(*) AS truth,
           count(*) FILTER (WHERE EXISTS (SELECT 1 FROM ops.v_program_reconciliation r WHERE r.platform_code = g.platform_code AND r.program_code = g.program_code
                                           AND r.period_label = g.period_label AND r.recon_status IN ('SHORT_PAID', 'UNPAID') AND abs(r.shortfall_idr - g.shortfall_idr) <= 0.01 * g.shortfall_idr)) AS detected
    FROM qa.gt_program_discrepancies g),
prog_pred AS (SELECT 'PROGRAM_SHORTFALL' AS test, count(*) AS flagged, count(*) FILTER (WHERE EXISTS (SELECT 1 FROM qa.gt_program_discrepancies g WHERE g.platform_code = r.platform_code
                                           AND g.program_code = r.program_code AND g.period_label = r.period_label)) AS correct
              FROM ops.v_program_reconciliation r WHERE r.recon_status IN ('SHORT_PAID', 'UNPAID')),
-- 5. harga: tingkat snapshot (tipe gabungan dipecah)
pv AS (
    SELECT g.snapshot_ts::timestamp AS ts, g.platform_code, g.listing_id, t AS vtype
    FROM qa.gt_price_violations g, unnest(string_to_array(g.violation_type, '|')) t),
pf AS (
    SELECT DISTINCT snapshot_ts AS ts, platform_code, listing_id, 'BELOW_MAP' AS vtype FROM dwh.fact_price_snapshot WHERE flag_below_floor
    UNION SELECT DISTINCT snapshot_ts, platform_code, listing_id, 'STRIKE_PRICE_INFLATION' FROM dwh.fact_price_snapshot WHERE flag_strike_inflation),
price AS (
    SELECT 'PRICE_SNAPSHOT_VIOLATION' AS test, (SELECT count(DISTINCT (ts, platform_code, listing_id, vtype)) FROM pv) AS truth,
           (SELECT count(*) FROM (SELECT DISTINCT ts, platform_code, listing_id, vtype FROM pv) a JOIN pf USING (ts, platform_code, listing_id, vtype)) AS detected),
price_pred AS (
    SELECT 'PRICE_SNAPSHOT_VIOLATION' AS test, (SELECT count(*) FROM pf) AS flagged,
           (SELECT count(*) FROM pf JOIN (SELECT DISTINCT ts, platform_code, listing_id, vtype FROM pv) a USING (ts, platform_code, listing_id, vtype)) AS correct)
SELECT test, truth, detected, round(100.0 * detected / NULLIF(truth, 0), 2) AS recall_pct, NULL::bigint AS flagged, NULL::bigint AS correct, NULL::numeric AS precision_pct FROM (
    SELECT * FROM ord UNION ALL SELECT * FROM vou UNION ALL SELECT * FROM sett UNION ALL SELECT * FROM prog UNION ALL SELECT * FROM price) a
UNION ALL SELECT test, NULL, NULL, NULL, flagged, correct, round(100.0 * correct / NULLIF(flagged, 0), 2) FROM (
    SELECT * FROM ord_pred UNION ALL SELECT * FROM sett_pred UNION ALL SELECT * FROM prog_pred UNION ALL SELECT * FROM price_pred) b;

-- Tie-out KPI bulanan: selisih nilai pipeline vs kunci (selisih wajar = order dikarantina: ID TikTok rusak & qty Lazada tak terpulihkan)
DROP TABLE IF EXISTS qa.kpi_tieout;
CREATE TABLE qa.kpi_tieout AS
SELECT k.platform_code, k.month, k.gmv_placed AS gt_gmv_placed, m.gmv_placed AS pipeline_gmv_placed, (m.gmv_placed - k.gmv_placed) AS diff_gmv,
       round(100.0 * (m.gmv_placed - k.gmv_placed) / NULLIF(k.gmv_placed, 0), 3) AS diff_pct, k.orders_placed AS gt_orders, m.orders_placed AS pipeline_orders, (m.orders_placed - k.orders_placed) AS diff_orders,
       k.net_gmv AS gt_net_gmv, m.net_gmv AS pipeline_net_gmv
FROM qa.gt_monthly_kpi_clean k JOIN mart.v_kpi_platform_month m ON m.platform_code = k.platform_code AND to_char(m.month_start, 'YYYY-MM') = k.month;

SELECT * FROM qa.validation_summary ORDER BY test;
SELECT platform_code, sum(gt_gmv_placed) gt_gmv, sum(diff_gmv) diff_gmv, round(100.0 * sum(diff_gmv) / sum(gt_gmv_placed), 4) AS diff_pct, sum(diff_orders) diff_orders FROM qa.kpi_tieout GROUP BY 1 ORDER BY 1;
