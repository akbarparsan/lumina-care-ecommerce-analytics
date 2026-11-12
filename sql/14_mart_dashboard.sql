-- =====================================================================================
-- 14_mart_dashboard.sql : tabel/view khusus halaman dashboard hasil adaptasi referensi
--   dim_month            : dimensi bulan (label singkat, bulan terakhir)
--   v_kpi_month_all      : KPI bulanan seluruh platform + variasi vs bulan lalu + penanda bulan terbaik
--   v_sku_movers         : pergerakan Net GMV SKU vs bulan lalu (platform x SKU x bulan), untuk tabel "Siapa naik, siapa turun"
--   v_sku_movers_all     : versi semua platform + peringkat naik/turun (untuk uji di SQL)
--   v_subcat_month       : Net GMV sub-kategori per platform-bulan
--   v_command_center     : 1 baris per platform + 'ALL' untuk kartu detail halaman Command Center
--   v_money_on_table     : kartu "uang di meja" (klaim, kebocoran harga, paparan voucher, gerbang data)
-- Prinsip yang diambil dari referensi: variasi ditampilkan absolut (Rp) DAN persen, peringkat memakai selisih Rp
-- dengan ambang basis minimum (menghindari persen besar dari basis yang sangat kecil).
-- =====================================================================================
SET search_path = mart, public;

CREATE OR REPLACE VIEW mart.dim_month AS
SELECT d.month_start,
       to_char(d.month_start, 'YYYY-MM') AS year_month,
       (ARRAY['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des'])[extract(month FROM d.month_start)::int] AS month_label,
       extract(year FROM d.month_start)::int AS year,
       extract(month FROM d.month_start)::int AS month_no,
       (d.month_start = date_trunc('month', (SELECT max(order_date) FROM dwh.fact_order))::date) AS is_latest_month
FROM (SELECT DISTINCT date_trunc('month', date)::date AS month_start FROM dwh.dim_date
      WHERE date BETWEEN (SELECT min(order_date) FROM dwh.fact_order) AND (SELECT max(order_date) FROM dwh.fact_order)) d;

-- ---------------------------------------------------------------- KPI bulanan seluruh platform
CREATE OR REPLACE VIEW mart.v_kpi_month_all AS
WITH m AS (
    SELECT month_start, sum(orders_net) AS orders_net, sum(net_gmv) AS net_gmv, sum(net_sales) AS net_sales, sum(cm1) AS cm1, sum(cm2) AS cm2,
           sum(ad_spend) AS ad_spend, sum(platform_fees) AS platform_fees
    FROM mart.v_kpi_platform_month GROUP BY 1),
a AS (
    SELECT date_trunc('month', ad_date)::date AS month_start, sum(ad_gmv_reliable)::numeric / NULLIF(sum(spend_reliable), 0) AS roas
    FROM mart.v_ads_daily GROUP BY 1),
x AS (
    SELECT m.*, round(a.roas, 2) AS roas, round(m.ad_spend::numeric / NULLIF(m.net_gmv, 0), 4) AS tacos,
           round(m.cm2::numeric / NULLIF(m.net_sales, 0), 4) AS cm2_pct, round(m.net_gmv::numeric / NULLIF(m.orders_net, 0)) AS aov,
           lag(m.net_gmv) OVER w AS prev_net_gmv, lag(m.cm2) OVER w AS prev_cm2, lag(m.ad_spend) OVER w AS prev_ad_spend
    FROM m LEFT JOIN a USING (month_start) WINDOW w AS (ORDER BY m.month_start))
SELECT x.*,
       (net_gmv - prev_net_gmv) AS delta_net_gmv, round((net_gmv - prev_net_gmv)::numeric / NULLIF(prev_net_gmv, 0), 4) AS delta_net_gmv_pct,
       (cm2 - prev_cm2) AS delta_cm2, round((cm2 - prev_cm2)::numeric / NULLIF(prev_cm2, 0), 4) AS delta_cm2_pct,
       (ad_spend - prev_ad_spend) AS delta_ad_spend, round((ad_spend - prev_ad_spend)::numeric / NULLIF(prev_ad_spend, 0), 4) AS delta_ad_spend_pct,
       (net_gmv = max(net_gmv) OVER ()) AS is_best_net_gmv, (cm2 = max(cm2) OVER ()) AS is_best_cm2, (ad_spend = max(ad_spend) OVER ()) AS is_peak_ad_spend
FROM x;

-- ---------------------------------------------------------------- Pergerakan SKU vs bulan lalu
CREATE OR REPLACE VIEW mart.v_sku_movers AS
WITH s AS (
    SELECT date_trunc('month', order_date)::date AS month_start, platform_code, sku, sum(net_gmv) AS net_gmv FROM mart.mv_sales_daily GROUP BY 1, 2, 3)
SELECT s.month_start, s.platform_code, s.sku, k.product_name, k.sub_category, s.net_gmv,
       lag(s.net_gmv) OVER w AS prev_net_gmv,
       (s.net_gmv - lag(s.net_gmv) OVER w) AS delta_idr,
       round((s.net_gmv - lag(s.net_gmv) OVER w)::numeric / NULLIF(lag(s.net_gmv) OVER w, 0), 4) AS delta_pct
FROM s JOIN dwh.dim_sku k USING (sku)
WINDOW w AS (PARTITION BY s.platform_code, s.sku ORDER BY s.month_start);

CREATE OR REPLACE VIEW mart.v_sku_movers_all AS
WITH s AS (
    SELECT month_start, sku, product_name, sub_category, sum(net_gmv) AS net_gmv, sum(prev_net_gmv) AS prev_net_gmv, sum(delta_idr) AS delta_idr
    FROM mart.v_sku_movers WHERE prev_net_gmv IS NOT NULL GROUP BY 1, 2, 3, 4)
SELECT s.*, round(delta_idr::numeric / NULLIF(prev_net_gmv, 0), 4) AS delta_pct,
       (prev_net_gmv >= 5000000) AS passes_min_base,           -- basis minimum Rp5 jt: menghindari % ekstrem dari basis kecil
       rank() OVER (PARTITION BY month_start ORDER BY delta_idr DESC) AS rank_up,
       rank() OVER (PARTITION BY month_start ORDER BY delta_idr ASC) AS rank_down
FROM s;

-- ---------------------------------------------------------------- Sub-kategori
CREATE OR REPLACE VIEW mart.v_subcat_month AS
SELECT date_trunc('month', order_date)::date AS month_start, platform_code, sub_category, sum(net_gmv) AS net_gmv, sum(net_units) AS net_units, sum(cogs) AS cogs
FROM mart.mv_sales_daily GROUP BY 1, 2, 3;

-- ---------------------------------------------------------------- Command Center (kartu detail per platform + ALL)
CREATE OR REPLACE VIEW mart.v_command_center AS
WITH k AS (
    SELECT platform_code, sum(net_gmv) AS net_gmv, sum(net_sales) AS net_sales, sum(cm2) AS cm2, sum(ad_spend) AS ad_spend, sum(orders_net) AS orders_net
    FROM mart.v_kpi_platform_month GROUP BY 1),
r AS (
    SELECT platform_code, round(sum(ad_gmv_reliable)::numeric / NULLIF(sum(spend_reliable), 0), 2) AS roas FROM mart.v_ads_daily GROUP BY 1),
j AS (SELECT platform_code, pacing_status, projected_quarter_gmv, tier1_threshold, tier2_threshold FROM mart.v_jbp_pacing),
c AS (SELECT platform_code, sum(claim_idr) AS claim_idr, sum(cases) AS claim_cases FROM ops.v_appeal_pack GROUP BY 1),
al AS (SELECT platform_code, count(*) AS price_alerts, count(*) FILTER (WHERE severity IN ('CRITICAL', 'HIGH')) AS price_alerts_high FROM ops.v_price_alerts_latest GROUP BY 1),
sp AS (SELECT platform_code, count(*) AS flagged_orders, count(*) FILTER (WHERE risk_level IN ('CRITICAL', 'HIGH')) AS high_risk_orders FROM ops.v_suspicious_orders_scored GROUP BY 1),
lk AS (SELECT platform_code, sum(leakage_idr) AS price_leakage_idr, sum(orders) AS leakage_orders FROM ops.v_official_price_leakage_summary GROUP BY 1),
vv AS (SELECT platform_code, sum(orders) AS voucher_violation_orders, sum(exposure_idr) AS voucher_exposure_idr FROM ops.v_voucher_violation_summary GROUP BY 1),
p AS (
    SELECT k.platform_code, k.net_gmv, k.net_sales, k.cm2, k.ad_spend, k.orders_net, r.roas, j.pacing_status, j.projected_quarter_gmv, j.tier1_threshold, j.tier2_threshold,
           coalesce(c.claim_idr, 0) AS claim_idr, coalesce(c.claim_cases, 0) AS claim_cases, coalesce(al.price_alerts, 0) AS price_alerts, coalesce(al.price_alerts_high, 0) AS price_alerts_high,
           coalesce(sp.flagged_orders, 0) AS flagged_orders, coalesce(sp.high_risk_orders, 0) AS high_risk_orders,
           coalesce(lk.price_leakage_idr, 0) AS price_leakage_idr, coalesce(lk.leakage_orders, 0) AS leakage_orders,
           coalesce(vv.voucher_violation_orders, 0) AS voucher_violation_orders, coalesce(vv.voucher_exposure_idr, 0) AS voucher_exposure_idr
    FROM k LEFT JOIN r USING (platform_code) LEFT JOIN j USING (platform_code) LEFT JOIN c USING (platform_code) LEFT JOIN al USING (platform_code)
    LEFT JOIN sp USING (platform_code) LEFT JOIN lk USING (platform_code) LEFT JOIN vv USING (platform_code))
SELECT platform_code, net_gmv, net_sales, cm2, round(cm2::numeric / NULLIF(net_sales, 0), 4) AS cm2_pct, ad_spend, round(ad_spend::numeric / NULLIF(net_gmv, 0), 4) AS tacos, roas, orders_net,
       pacing_status, projected_quarter_gmv, tier1_threshold, tier2_threshold, claim_idr, claim_cases, price_alerts, price_alerts_high, flagged_orders, high_risk_orders,
       price_leakage_idr, leakage_orders, voucher_violation_orders, voucher_exposure_idr
FROM p
UNION ALL
SELECT 'ALL', sum(net_gmv), sum(net_sales), sum(cm2), round(sum(cm2)::numeric / NULLIF(sum(net_sales), 0), 4), sum(ad_spend), round(sum(ad_spend)::numeric / NULLIF(sum(net_gmv), 0), 4),
       (SELECT round(sum(ad_gmv_reliable)::numeric / NULLIF(sum(spend_reliable), 0), 2) FROM mart.v_ads_daily), sum(orders_net),
       CASE WHEN bool_or(pacing_status = 'DI BAWAH TIER 1') THEN 'ADA PLATFORM DI BAWAH TIER 1' ELSE 'SEMUA DI JALUR TIER' END, NULL, NULL, NULL,
       sum(claim_idr), sum(claim_cases), sum(price_alerts), sum(price_alerts_high), sum(flagged_orders), sum(high_risk_orders), sum(price_leakage_idr), sum(leakage_orders),
       sum(voucher_violation_orders), sum(voucher_exposure_idr)
FROM p;

-- ---------------------------------------------------------------- Uang di meja
CREATE OR REPLACE VIEW mart.v_money_on_table AS
SELECT (SELECT sum(claim_idr) FROM ops.v_appeal_candidates) AS claimable_idr,
       (SELECT count(*) FROM ops.v_appeal_candidates) AS claim_cases,
       (SELECT sum(leakage_idr) FROM ops.v_official_price_leakage_summary) AS price_leakage_idr,
       (SELECT sum(orders) FROM ops.v_official_price_leakage_summary) AS leakage_orders,
       (SELECT sum(exposure_idr) FROM ops.v_voucher_violation_summary) AS voucher_exposure_idr,
       (SELECT sum(orders) FROM ops.v_voucher_violation_summary) AS voucher_violation_orders,
       (SELECT publish_gate FROM ops.v_dq_scorecard ORDER BY run_id DESC LIMIT 1) AS publish_gate,
       (SELECT passed FROM ops.v_dq_scorecard ORDER BY run_id DESC LIMIT 1) AS dq_passed,
       (SELECT failed FROM ops.v_dq_scorecard ORDER BY run_id DESC LIMIT 1) AS dq_failed,
       (SELECT critical_failed FROM ops.v_dq_scorecard ORDER BY run_id DESC LIMIT 1) AS dq_critical_failed;

-- ---------------------------------------------------------------- Pemeriksaan cepat (cocok dengan mock-up)
SELECT platform_code, net_gmv, cm2_pct, tacos, roas, pacing_status, claim_idr, price_alerts, flagged_orders FROM mart.v_command_center ORDER BY 1;
SELECT * FROM mart.v_money_on_table;
SELECT month_start, net_gmv, delta_net_gmv, delta_net_gmv_pct, cm2, delta_cm2_pct, ad_spend, tacos FROM mart.v_kpi_month_all ORDER BY 1 DESC LIMIT 3;
SELECT product_name, delta_idr, delta_pct, rank_up FROM mart.v_sku_movers_all WHERE month_start = '2026-10-01' AND passes_min_base ORDER BY rank_up LIMIT 3;
SELECT product_name, delta_idr, delta_pct, rank_down FROM mart.v_sku_movers_all WHERE month_start = '2026-10-01' AND passes_min_base ORDER BY rank_down LIMIT 3;

-- Power BI Navigator tidak menampilkan MATERIALIZED VIEW; sediakan view biasa sebagai pembungkus.
CREATE OR REPLACE VIEW mart.v_sales_daily AS SELECT * FROM mart.mv_sales_daily;
