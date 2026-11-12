-- =====================================================================================
-- 07_marts_kpi.sql : KPI siap-dashboard (schema mart)
--
-- DEFINISI KPI (konsisten di SQL & DAX)
--   Gross List GMV     = SUM(harga list x qty)                              semua order yang dibuat
--   GMV Placed         = SUM(harga setelah diskon penjual x qty)            semua order yang dibuat (belum dikurangi voucher)
--   Net GMV            = GMV Placed - GMV Cancelled - GMV Returned          "penjualan valid" (termasuk yang masih dikirim)
--   Completed GMV      = GMV status COMPLETED                               dasar tier rebate JBP
--   Net Sales (brand)  = Net GMV - Voucher penjual                          voucher platform diganti platform -> tidak mengurangi brand
--   CM1                = Net Sales - COGS - Biaya platform (komisi+layanan+pembayaran)
--   CM2                = CM1 - Belanja iklan                                (Contribution Margin setelah iklan)
--   TACOS              = Belanja iklan / Net GMV                            ROAS = GMV atribusi iklan / belanja iklan
-- =====================================================================================
SET search_path = mart, public;

-- ---------------------------------------------------------------- kalender kampanye per platform-hari (kampanye primer)
CREATE OR REPLACE VIEW mart.v_platform_day AS
SELECT d.date, p.platform_code, b.campaign_id, b.campaign_type, (b.campaign_id IS NOT NULL) AS is_campaign_day, coalesce(b.allows_deep_discount, false) AS allows_deep_discount
FROM dwh.dim_date d CROSS JOIN dwh.dim_platform p
LEFT JOIN LATERAL (
    SELECT campaign_id, campaign_type, allows_deep_discount FROM dwh.bridge_campaign_day c
    WHERE c.platform_code = p.platform_code AND c.date = d.date
    ORDER BY CASE campaign_type WHEN 'DOUBLE_DATE' THEN 1 WHEN 'BRAND_DAY' THEN 2 WHEN 'PAYDAY' THEN 3 ELSE 4 END LIMIT 1) b ON true;

-- ---------------------------------------------------------------- ekonomi per order (margin & biaya platform berbasis kontrak)
CREATE OR REPLACE VIEW mart.v_order_econ AS
WITH cg AS (
    SELECT l.platform_code, l.order_id, sum(l.qty * k.cogs_idr) AS cogs
    FROM dwh.fact_order_line l JOIN dwh.dim_sku k USING (sku) GROUP BY 1, 2),
cd AS (SELECT platform_code, tier1_rate_pct AS comm_disc_pts, campaign_scope FROM dwh.dim_jbp WHERE program_code = 'COMMISSION_DISCOUNT')
SELECT o.platform_code, o.order_id, o.order_date, o.status, o.is_valid_sale, o.is_completed, o.units, o.gmv_list, o.gmv_placed,
       o.seller_voucher_amt, o.platform_voucher_amt, o.net_sales_after_seller_voucher AS net_sales, cg.cogs,
       pd.campaign_type, (pd.campaign_type IS NOT NULL AND cd.campaign_scope LIKE '%' || pd.campaign_type || '%') AS commission_discount_applies,
       (f.commission_pct - CASE WHEN pd.campaign_type IS NOT NULL AND cd.campaign_scope LIKE '%' || pd.campaign_type || '%' THEN cd.comm_disc_pts ELSE 0 END) AS commission_rate_pct,
       f.service_fee_pct, f.payment_fee_pct,
       round(o.net_sales_after_seller_voucher * (f.commission_pct - CASE WHEN pd.campaign_type IS NOT NULL AND cd.campaign_scope LIKE '%' || pd.campaign_type || '%' THEN cd.comm_disc_pts ELSE 0 END) / 100) AS commission_fee_exp,
       round(o.net_sales_after_seller_voucher * f.service_fee_pct / 100) AS service_fee_exp,
       round(o.net_sales_after_seller_voucher * f.payment_fee_pct / 100) AS payment_fee_exp
FROM dwh.fact_order o
JOIN cg USING (platform_code, order_id)
JOIN dwh.dim_fee_contract f USING (platform_code)
LEFT JOIN cd USING (platform_code)
LEFT JOIN mart.v_platform_day pd ON pd.platform_code = o.platform_code AND pd.date = o.order_date;

-- ---------------------------------------------------------------- fakta penjualan harian (SKU x platform)
DROP MATERIALIZED VIEW IF EXISTS mart.mv_sales_daily CASCADE;
CREATE MATERIALIZED VIEW mart.mv_sales_daily AS
SELECT l.order_date, l.platform_code, l.sku, k.sub_category,
       count(DISTINCT l.order_id) AS orders_with_sku, sum(l.qty) AS units_placed,
       sum(l.line_list_gmv) AS gross_list_gmv, sum(l.line_gmv) AS gmv_placed,
       coalesce(sum(l.line_gmv) FILTER (WHERE o.status = 'CANCELLED'), 0) AS gmv_cancelled,
       coalesce(sum(l.line_gmv) FILTER (WHERE o.status = 'RETURNED'), 0) AS gmv_returned,
       coalesce(sum(l.line_gmv) FILTER (WHERE o.is_valid_sale), 0) AS net_gmv,
       coalesce(sum(l.line_gmv) FILTER (WHERE o.is_completed), 0) AS completed_gmv,
       coalesce(sum(l.qty) FILTER (WHERE o.is_valid_sale), 0) AS net_units,
       coalesce(sum(l.line_list_gmv - l.line_gmv) FILTER (WHERE o.is_valid_sale), 0) AS seller_price_discount,
       coalesce(sum(l.seller_voucher_alloc) FILTER (WHERE o.is_valid_sale), 0) AS seller_voucher_cost,
       coalesce(sum(l.platform_voucher_alloc) FILTER (WHERE o.is_valid_sale), 0) AS platform_voucher_subsidy,
       coalesce(sum(l.qty * k.cogs_idr) FILTER (WHERE o.is_valid_sale), 0) AS cogs
FROM dwh.fact_order_line l JOIN dwh.fact_order o USING (platform_code, order_id) JOIN dwh.dim_sku k USING (sku)
GROUP BY 1, 2, 3, 4;
CREATE UNIQUE INDEX ON mart.mv_sales_daily (order_date, platform_code, sku);

-- ---------------------------------------------------------------- tren GMV harian + MA7 + WoW
CREATE OR REPLACE VIEW mart.v_gmv_trend_daily AS
SELECT platform_code, order_date, orders, net_gmv,
       round(avg(net_gmv) OVER (PARTITION BY platform_code ORDER BY order_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)) AS net_gmv_ma7,
       round(net_gmv / NULLIF(lag(net_gmv, 7) OVER (PARTITION BY platform_code ORDER BY order_date), 0) - 1, 4) AS wow_growth
FROM (SELECT platform_code, order_date, count(*) FILTER (WHERE is_valid_sale) AS orders, coalesce(sum(gmv_placed) FILTER (WHERE is_valid_sale), 0) AS net_gmv
      FROM dwh.fact_order GROUP BY 1, 2) x;

-- ---------------------------------------------------------------- IKLAN
DROP VIEW IF EXISTS mart.v_ads_daily CASCADE;
CREATE VIEW mart.v_ads_daily AS
SELECT a.ad_date, a.platform_code, a.ad_type, a.sub_category,
       sum(a.spend) AS spend, sum(a.impressions) AS impressions, sum(a.clicks_clean) AS clicks, sum(a.ad_orders) AS ad_orders, sum(a.ad_gmv) AS ad_gmv,
       coalesce(sum(a.spend) FILTER (WHERE a.spend_reliable), 0) AS spend_reliable, coalesce(sum(a.ad_gmv) FILTER (WHERE a.spend_reliable), 0) AS ad_gmv_reliable,
       coalesce(sum(a.clicks_clean) FILTER (WHERE a.spend_reliable), 0) AS clicks_reliable, coalesce(sum(a.ad_orders) FILTER (WHERE a.spend_reliable), 0) AS ad_orders_reliable,
       -- rasio hanya dari baris dengan spend andal
       round(sum(a.ad_gmv) FILTER (WHERE a.spend_reliable)::numeric / NULLIF(sum(a.spend) FILTER (WHERE a.spend_reliable), 0), 2) AS roas,
       round(sum(a.clicks_clean)::numeric / NULLIF(sum(a.impressions), 0), 4) AS ctr,
       round(sum(a.spend) FILTER (WHERE a.spend_reliable)::numeric / NULLIF(sum(a.clicks_clean) FILTER (WHERE a.spend_reliable), 0), 0) AS cpc,
       round(sum(a.ad_orders)::numeric / NULLIF(sum(a.clicks_clean), 0), 4) AS cvr,
       round(sum(a.spend) FILTER (WHERE a.spend_reliable)::numeric / NULLIF(sum(a.ad_orders) FILTER (WHERE a.spend_reliable), 0), 0) AS cost_per_order
FROM dwh.fact_ads_daily a GROUP BY 1, 2, 3, 4;

CREATE OR REPLACE VIEW mart.v_ads_platform_daily AS
SELECT a.ad_date, a.platform_code, sum(a.spend) AS spend, sum(a.ad_gmv) AS ad_gmv,
       round(sum(a.ad_gmv) FILTER (WHERE a.spend_reliable)::numeric / NULLIF(sum(a.spend) FILTER (WHERE a.spend_reliable), 0), 2) AS roas,
       g.net_gmv, round(sum(a.spend)::numeric / NULLIF(g.net_gmv, 0), 4) AS tacos, round(sum(a.ad_gmv)::numeric / NULLIF(g.gmv_placed, 0), 4) AS ad_attributed_share
FROM dwh.fact_ads_daily a
LEFT JOIN (SELECT order_date, platform_code, sum(gmv_placed) FILTER (WHERE is_valid_sale) AS net_gmv, sum(gmv_placed) AS gmv_placed FROM dwh.fact_order GROUP BY 1, 2) g
       ON g.order_date = a.ad_date AND g.platform_code = a.platform_code
GROUP BY a.ad_date, a.platform_code, g.net_gmv, g.gmv_placed;

-- ---------------------------------------------------------------- VOUCHER: pecah biaya per kode voucher
-- Total order: seller_voucher_amt = (voucher penjual) + (bagian penjual dari voucher co-fund); platform_voucher_amt = bagian platform.
-- Jika voucher platform punya bagian penjual s (0<=s<1): total_P = platform_amt / (1 - s); bagian penjual = total_P - platform_amt.
CREATE OR REPLACE VIEW mart.v_order_voucher_split AS
SELECT o.platform_code, o.order_id, o.order_date, o.status, o.is_valid_sale, o.gmv_placed,
       o.seller_voucher_code AS s_code, o.platform_voucher_code AS p_code, vp.funding_model AS p_funding,
       o.seller_voucher_amt, o.platform_voucher_amt,
       CASE WHEN o.platform_voucher_code IS NULL THEN 0 WHEN vp.seller_share_pct >= 100 THEN o.seller_voucher_amt
            ELSE round(o.platform_voucher_amt / (1 - vp.seller_share_pct / 100)) END AS p_total_discount,
       CASE WHEN o.platform_voucher_code IS NULL THEN 0 WHEN vp.seller_share_pct >= 100 THEN o.seller_voucher_amt
            ELSE round(o.platform_voucher_amt / (1 - vp.seller_share_pct / 100)) - o.platform_voucher_amt END AS p_seller_cost,
       o.platform_voucher_amt AS p_platform_cost
FROM dwh.fact_order o LEFT JOIN dwh.dim_voucher vp ON vp.voucher_code = o.platform_voucher_code
WHERE o.seller_voucher_code IS NOT NULL OR o.platform_voucher_code IS NOT NULL;

CREATE OR REPLACE VIEW mart.v_voucher_usage AS     -- 1 baris per (order, kode voucher)
SELECT platform_code, order_id, order_date, status, is_valid_sale, gmv_placed, s_code AS voucher_code, 'SELLER'::text AS role,
       (seller_voucher_amt - CASE WHEN p_code IS NULL THEN 0 ELSE p_seller_cost END) AS discount_total, (seller_voucher_amt - CASE WHEN p_code IS NULL THEN 0 ELSE p_seller_cost END) AS seller_cost, 0::numeric AS platform_cost
FROM mart.v_order_voucher_split WHERE s_code IS NOT NULL
UNION ALL
SELECT platform_code, order_id, order_date, status, is_valid_sale, gmv_placed, p_code, 'PLATFORM', p_total_discount, p_seller_cost, p_platform_cost
FROM mart.v_order_voucher_split WHERE p_code IS NOT NULL;

CREATE OR REPLACE VIEW mart.v_voucher_performance AS
SELECT v.voucher_code, v.platform_code, v.voucher_type, v.funding_model, v.seller_share_pct, v.discount_kind, v.discount_value, v.max_discount, v.min_spend,
       v.quota, v.budget_idr, v.start_date, v.end_date,
       count(u.order_id) AS redemptions, count(u.order_id) FILTER (WHERE u.is_valid_sale) AS redemptions_valid,
       round(count(u.order_id)::numeric / NULLIF(v.quota, 0), 3) AS quota_burn,
       coalesce(sum(u.discount_total) FILTER (WHERE u.is_valid_sale), 0) AS discount_given,
       coalesce(sum(u.seller_cost) FILTER (WHERE u.is_valid_sale), 0) AS seller_cost,
       coalesce(sum(u.platform_cost) FILTER (WHERE u.is_valid_sale), 0) AS platform_cost,
       round(coalesce(sum(u.seller_cost) FILTER (WHERE u.is_valid_sale), 0) / NULLIF(v.budget_idr, 0), 3) AS seller_budget_utilization,
       coalesce(sum(u.gmv_placed) FILTER (WHERE u.is_valid_sale), 0) AS gmv_on_voucher_orders,
       round(sum(u.gmv_placed) FILTER (WHERE u.is_valid_sale) / NULLIF(sum(u.seller_cost) FILTER (WHERE u.is_valid_sale), 0), 1) AS gmv_per_seller_rupiah,
       round(sum(u.gmv_placed) FILTER (WHERE u.is_valid_sale) / NULLIF(count(u.order_id) FILTER (WHERE u.is_valid_sale), 0)) AS aov_voucher_orders
FROM dwh.dim_voucher v LEFT JOIN mart.v_voucher_usage u ON u.voucher_code = v.voucher_code
GROUP BY v.voucher_code, v.platform_code, v.voucher_type, v.funding_model, v.seller_share_pct, v.discount_kind, v.discount_value, v.max_discount, v.min_spend, v.quota, v.budget_idr, v.start_date, v.end_date;

-- AOV dengan vs tanpa voucher per platform-bulan (apakah voucher benar-benar mendorong keranjang lebih besar?)
CREATE OR REPLACE VIEW mart.v_voucher_aov_uplift AS
SELECT platform_code, date_trunc('month', order_date)::date AS month_start,
       count(*) FILTER (WHERE is_valid_sale) AS orders,
       round(100.0 * count(*) FILTER (WHERE is_valid_sale AND (seller_voucher_code IS NOT NULL OR platform_voucher_code IS NOT NULL)) / NULLIF(count(*) FILTER (WHERE is_valid_sale), 0), 1) AS voucher_penetration_pct,
       round(avg(gmv_placed) FILTER (WHERE is_valid_sale AND (seller_voucher_code IS NOT NULL OR platform_voucher_code IS NOT NULL))) AS aov_with_voucher,
       round(avg(gmv_placed) FILTER (WHERE is_valid_sale AND seller_voucher_code IS NULL AND platform_voucher_code IS NULL)) AS aov_without_voucher,
       round(avg(gmv_placed) FILTER (WHERE is_valid_sale AND (seller_voucher_code IS NOT NULL OR platform_voucher_code IS NOT NULL))
             / NULLIF(avg(gmv_placed) FILTER (WHERE is_valid_sale AND seller_voucher_code IS NULL AND platform_voucher_code IS NULL), 0) - 1, 3) AS aov_uplift
FROM dwh.fact_order GROUP BY 1, 2;

-- ---------------------------------------------------------------- KPI platform-bulan (halaman ringkasan eksekutif)
CREATE OR REPLACE VIEW mart.v_kpi_platform_month AS
WITH s AS (
    SELECT platform_code, date_trunc('month', order_date)::date AS month_start,
           count(*) AS orders_placed, count(*) FILTER (WHERE is_valid_sale) AS orders_net, count(*) FILTER (WHERE status = 'CANCELLED') AS orders_cancelled,
           count(*) FILTER (WHERE status = 'RETURNED') AS orders_returned, coalesce(sum(units) FILTER (WHERE is_valid_sale), 0) AS net_units,
           sum(gmv_list) AS gross_list_gmv, sum(gmv_placed) AS gmv_placed, coalesce(sum(gmv_placed) FILTER (WHERE is_valid_sale), 0) AS net_gmv,
           coalesce(sum(gmv_placed) FILTER (WHERE status = 'CANCELLED'), 0) AS cancelled_gmv, coalesce(sum(gmv_placed) FILTER (WHERE status = 'RETURNED'), 0) AS returned_gmv,
           coalesce(sum(gmv_placed) FILTER (WHERE is_completed), 0) AS completed_gmv,
           coalesce(sum(seller_voucher_amt) FILTER (WHERE is_valid_sale), 0) AS seller_voucher_cost, coalesce(sum(platform_voucher_amt) FILTER (WHERE is_valid_sale), 0) AS platform_voucher_subsidy
    FROM dwh.fact_order GROUP BY 1, 2),
e AS (
    SELECT platform_code, date_trunc('month', order_date)::date AS month_start, sum(net_sales) AS net_sales, sum(cogs) AS cogs,
           sum(commission_fee_exp + service_fee_exp + payment_fee_exp) AS platform_fees
    FROM mart.v_order_econ WHERE is_valid_sale GROUP BY 1, 2),
a AS (
    SELECT platform_code, date_trunc('month', ad_date)::date AS month_start, sum(spend) AS ad_spend, sum(ad_gmv) AS ad_gmv,
           sum(ad_gmv) FILTER (WHERE spend_reliable) AS ad_gmv_rel, sum(spend) FILTER (WHERE spend_reliable) AS ad_spend_rel
    FROM dwh.fact_ads_daily GROUP BY 1, 2)
SELECT s.platform_code, s.month_start, s.orders_placed, s.orders_net, s.net_units, s.gross_list_gmv, s.gmv_placed, s.net_gmv, s.completed_gmv, s.cancelled_gmv, s.returned_gmv,
       round(s.orders_cancelled::numeric / s.orders_placed, 4) AS cancel_rate, round(s.orders_returned::numeric / s.orders_placed, 4) AS return_rate,
       round(s.net_gmv::numeric / NULLIF(s.orders_net, 0)) AS aov, round(s.net_units::numeric / NULLIF(s.orders_net, 0), 2) AS units_per_order,
       round(1 - s.gmv_placed::numeric / s.gross_list_gmv, 4) AS price_discount_depth,
       s.seller_voucher_cost, s.platform_voucher_subsidy, round(s.seller_voucher_cost::numeric / NULLIF(s.net_gmv, 0), 4) AS seller_voucher_rate,
       e.net_sales, e.cogs, e.platform_fees, (e.net_sales - e.cogs - e.platform_fees) AS cm1,
       a.ad_spend, a.ad_gmv, round(a.ad_gmv_rel::numeric / NULLIF(a.ad_spend_rel, 0), 2) AS roas, round(a.ad_spend::numeric / NULLIF(s.net_gmv, 0), 4) AS tacos,
       (e.net_sales - e.cogs - e.platform_fees - coalesce(a.ad_spend, 0)) AS cm2,
       round((e.net_sales - e.cogs - e.platform_fees - coalesce(a.ad_spend, 0))::numeric / NULLIF(e.net_sales, 0), 4) AS cm2_pct,
       round(s.net_gmv::numeric / NULLIF(lag(s.net_gmv) OVER (PARTITION BY s.platform_code ORDER BY s.month_start), 0) - 1, 4) AS net_gmv_mom
FROM s JOIN e USING (platform_code, month_start) LEFT JOIN a USING (platform_code, month_start);

-- ---------------------------------------------------------------- Margin per SKU (SKU yang "membakar" margin saat kampanye)
CREATE OR REPLACE VIEW mart.v_sku_margin AS
WITH l AS (
    SELECT l.platform_code, l.sku, o.campaign_type IS NOT NULL AS in_campaign, l.qty, l.line_gmv, l.line_list_gmv, l.seller_voucher_alloc,
           (l.line_gmv - l.seller_voucher_alloc) AS net_sales,
           round((l.line_gmv - l.seller_voucher_alloc) * (e.commission_rate_pct + e.service_fee_pct + e.payment_fee_pct) / 100) AS fees
    FROM dwh.fact_order_line l JOIN mart.v_order_econ e USING (platform_code, order_id)
    JOIN dwh.fact_order fo USING (platform_code, order_id)
    LEFT JOIN mart.v_platform_day o ON o.platform_code = l.platform_code AND o.date = l.order_date
    WHERE fo.is_valid_sale)
SELECT l.platform_code, l.sku, k.product_name, k.sub_category, l.in_campaign, sum(l.qty) AS units, sum(l.net_sales) AS net_sales,
       sum(l.qty * k.cogs_idr) AS cogs, sum(l.fees) AS fees, sum(l.net_sales) - sum(l.qty * k.cogs_idr) - sum(l.fees) AS cm1,
       round((sum(l.net_sales) - sum(l.qty * k.cogs_idr) - sum(l.fees))::numeric / NULLIF(sum(l.net_sales), 0), 4) AS cm1_pct,
       round(1 - sum(l.line_gmv)::numeric / sum(l.line_list_gmv), 4) AS price_discount_depth
FROM l JOIN dwh.dim_sku k USING (sku) GROUP BY 1, 2, 3, 4, 5;

-- ---------------------------------------------------------------- PERFORMA KAMPANYE vs baseline 14 hari non-kampanye sebelum kampanye
CREATE OR REPLACE VIEW mart.v_platform_day_econ AS
SELECT pd.platform_code, pd.date, pd.campaign_id, pd.campaign_type, pd.is_campaign_day,
       coalesce(e.orders, 0) AS orders, coalesce(e.net_gmv, 0) AS net_gmv, coalesce(e.gmv_list, 0) AS gmv_list, coalesce(e.gmv_placed_valid, 0) AS gmv_placed_valid,
       coalesce(e.seller_voucher, 0) AS seller_voucher, coalesce(e.platform_voucher, 0) AS platform_voucher, coalesce(e.net_sales, 0) AS net_sales,
       coalesce(e.cogs, 0) AS cogs, coalesce(e.fees, 0) AS fees, coalesce(a.spend, 0) AS ad_spend,
       (coalesce(e.net_sales, 0) - coalesce(e.cogs, 0) - coalesce(e.fees, 0) - coalesce(a.spend, 0)) AS cm2
FROM mart.v_platform_day pd
LEFT JOIN (SELECT platform_code, order_date, count(*) AS orders, sum(gmv_placed) AS net_gmv, sum(gmv_placed) AS gmv_placed_valid, sum(gmv_list) AS gmv_list, sum(seller_voucher_amt) AS seller_voucher,
                  sum(platform_voucher_amt) AS platform_voucher, sum(net_sales) AS net_sales, sum(cogs) AS cogs, sum(commission_fee_exp + service_fee_exp + payment_fee_exp) AS fees
           FROM mart.v_order_econ WHERE is_valid_sale GROUP BY 1, 2) e ON e.platform_code = pd.platform_code AND e.order_date = pd.date
LEFT JOIN (SELECT platform_code, ad_date, sum(spend) AS spend FROM dwh.fact_ads_daily GROUP BY 1, 2) a ON a.platform_code = pd.platform_code AND a.ad_date = pd.date
WHERE pd.date BETWEEN (SELECT min(order_date) FROM dwh.fact_order) AND (SELECT max(order_date) FROM dwh.fact_order);

CREATE OR REPLACE VIEW mart.v_campaign_performance AS
SELECT c.platform_code, c.campaign_id, c.campaign_name, c.campaign_type, c.start_date, c.end_date, c.duration_days, c.allows_deep_discount,
       w.days_with_data, w.net_gmv, w.orders, w.seller_voucher, w.platform_voucher, w.ad_spend, w.net_sales, w.cogs, w.fees, w.cm2,
       round(w.net_gmv::numeric / NULLIF(w.orders, 0)) AS aov,
       round(1 - w.gmv_placed_valid::numeric / NULLIF(w.gmv_list, 0), 4) AS price_discount_depth,
       round(w.ad_spend::numeric / NULLIF(w.net_gmv, 0), 4) AS tacos,
       round(b.base_net_gmv_daily) AS baseline_net_gmv_daily, round(w.net_gmv::numeric / NULLIF(w.days_with_data, 0)) AS campaign_net_gmv_daily,
       round(w.net_gmv::numeric / NULLIF(w.days_with_data, 0) / NULLIF(b.base_net_gmv_daily, 0) - 1, 3) AS gmv_uplift_vs_baseline,
       round((w.net_gmv::numeric / NULLIF(w.days_with_data, 0) - b.base_net_gmv_daily) * w.days_with_data) AS incremental_gmv,
       round(1 - b.base_gmv_placed / NULLIF(b.base_gmv_list, 0), 4) AS baseline_price_discount_depth,
       round(b.base_cm2_daily) AS baseline_cm2_daily, round(w.cm2::numeric / NULLIF(w.days_with_data, 0)) AS campaign_cm2_daily,
       round(w.cm2 - b.base_cm2_daily * w.days_with_data) AS incremental_cm2,
       CASE WHEN b.base_cm2_daily IS NULL THEN NULL WHEN w.cm2 - b.base_cm2_daily * w.days_with_data < 0 THEN 'MERUGIKAN MARGIN' ELSE 'MENAMBAH MARGIN' END AS verdict
FROM dwh.dim_campaign c
CROSS JOIN LATERAL (
    SELECT count(*) AS days_with_data, sum(net_gmv) AS net_gmv, sum(orders) AS orders, sum(seller_voucher) AS seller_voucher, sum(platform_voucher) AS platform_voucher, sum(ad_spend) AS ad_spend,
           sum(net_sales) AS net_sales, sum(cogs) AS cogs, sum(fees) AS fees, sum(cm2) AS cm2, sum(gmv_placed_valid) AS gmv_placed_valid, sum(gmv_list) AS gmv_list
    FROM mart.v_platform_day_econ d WHERE d.platform_code = c.platform_code AND d.date BETWEEN c.start_date AND c.end_date) w
CROSS JOIN LATERAL (
    SELECT avg(net_gmv) AS base_net_gmv_daily, avg(cm2) AS base_cm2_daily, sum(gmv_placed_valid) AS base_gmv_placed, sum(gmv_list) AS base_gmv_list
    FROM mart.v_platform_day_econ d WHERE d.platform_code = c.platform_code AND d.date BETWEEN c.start_date - 14 AND c.start_date - 1 AND NOT d.is_campaign_day) b
WHERE w.days_with_data > 0;

-- ---------------------------------------------------------------- JBP: pencapaian tier, selisih ke tier berikut, dan pacing kuartal berjalan
CREATE OR REPLACE VIEW mart.v_jbp_attainment AS
WITH asof AS (SELECT max(order_date) AS as_of FROM dwh.fact_order),
q AS (
    SELECT o.platform_code, extract(quarter FROM o.order_date)::int AS quarter, sum(o.gmv_placed) FILTER (WHERE o.is_completed) AS completed_gmv,
           min(o.order_date) AS first_day, max(o.order_date) AS last_day
    FROM dwh.fact_order o GROUP BY 1, 2)
SELECT q.platform_code, q.quarter, q.completed_gmv, j.tier1_threshold, j.tier2_threshold, j.tier1_rate_pct, j.tier2_rate_pct,
       round(q.completed_gmv / j.tier1_threshold, 3) AS attainment_tier1, round(q.completed_gmv / j.tier2_threshold, 3) AS attainment_tier2,
       CASE WHEN q.completed_gmv >= j.tier2_threshold THEN 'TIER 2' WHEN q.completed_gmv >= j.tier1_threshold THEN 'TIER 1' ELSE 'BELUM TIER' END AS tier_achieved,
       CASE WHEN q.completed_gmv >= j.tier2_threshold THEN j.tier2_rate_pct WHEN q.completed_gmv >= j.tier1_threshold THEN j.tier1_rate_pct ELSE 0 END AS rebate_rate_pct,
       round(q.completed_gmv * CASE WHEN q.completed_gmv >= j.tier2_threshold THEN j.tier2_rate_pct WHEN q.completed_gmv >= j.tier1_threshold THEN j.tier1_rate_pct ELSE 0 END / 100) AS expected_rebate_idr,
       greatest(j.tier2_threshold - q.completed_gmv, 0) AS gap_to_tier2_idr, greatest(j.tier1_threshold - q.completed_gmv, 0) AS gap_to_tier1_idr,
       (q.last_day < make_date(2026, q.quarter * 3, 1) + interval '1 month - 1 day' AND q.last_day = (SELECT as_of FROM asof)) AS is_in_progress,
       (q.last_day - make_date(2026, (q.quarter - 1) * 3 + 1, 1) + 1) AS days_elapsed,
       (make_date(2026, q.quarter * 3, 1) + interval '1 month - 1 day')::date - make_date(2026, (q.quarter - 1) * 3 + 1, 1) + 1 AS days_in_quarter
FROM q JOIN dwh.dim_jbp j ON j.platform_code = q.platform_code AND j.program_code = 'QUARTERLY_REBATE';

CREATE OR REPLACE VIEW mart.v_jbp_pacing AS
SELECT platform_code, quarter, completed_gmv, days_elapsed, days_in_quarter,
       round(completed_gmv::numeric / days_elapsed * days_in_quarter) AS projected_quarter_gmv,
       tier1_threshold, tier2_threshold,
       CASE WHEN completed_gmv::numeric / days_elapsed * days_in_quarter >= tier2_threshold THEN 'ON TRACK TIER 2'
            WHEN completed_gmv::numeric / days_elapsed * days_in_quarter >= tier1_threshold THEN 'ON TRACK TIER 1'
            ELSE 'DI BAWAH TIER 1' END AS pacing_status,
       round(greatest(tier2_threshold - completed_gmv, 0)::numeric / NULLIF(days_in_quarter - days_elapsed, 0)) AS required_daily_gmv_for_tier2,
       round(completed_gmv::numeric / days_elapsed) AS current_daily_run_rate
FROM mart.v_jbp_attainment WHERE is_in_progress;

-- ---------------------------------------------------------------- Paritas harga (toko resmi, per hari, harga satuan)
CREATE OR REPLACE VIEW mart.v_price_parity_daily AS
WITH d AS (
    SELECT snapshot_date, sku, platform_code, round(avg(unit_price)) AS official_unit_price
    FROM dwh.fact_price_snapshot WHERE authorization_status = 'OFFICIAL' AND pack_qty = 1 GROUP BY 1, 2, 3)
SELECT snapshot_date, sku, min(official_unit_price) AS min_price, max(official_unit_price) AS max_price,
       round(max(official_unit_price)::numeric / NULLIF(min(official_unit_price), 0) - 1, 4) AS gap_pct,
       (array_agg(platform_code ORDER BY official_unit_price))[1] AS cheapest_platform, (array_agg(platform_code ORDER BY official_unit_price DESC))[1] AS priciest_platform,
       count(*) AS platforms_compared
FROM d GROUP BY 1, 2 HAVING count(*) = 4;

-- ---------------------------------------------------------------- Pembeli baru vs berulang
CREATE OR REPLACE VIEW mart.v_customer_repeat AS
WITH fb AS (SELECT buyer_key, min(order_date) AS first_date FROM dwh.fact_order WHERE is_valid_sale GROUP BY 1),
m AS (SELECT o.platform_code, date_trunc('month', o.order_date)::date AS month_start, o.buyer_key, count(*) AS orders_in_month, min(fb.first_date) AS first_date
      FROM dwh.fact_order o JOIN fb USING (buyer_key) WHERE o.is_valid_sale GROUP BY 1, 2, 3)
SELECT platform_code, month_start, count(*) AS buyers, count(*) FILTER (WHERE date_trunc('month', first_date) = month_start) AS new_buyers,
       count(*) FILTER (WHERE date_trunc('month', first_date) < month_start) AS returning_buyers,
       round(100.0 * count(*) FILTER (WHERE date_trunc('month', first_date) < month_start) / count(*), 1) AS returning_buyer_pct,
       round(sum(orders_in_month)::numeric / count(*), 3) AS orders_per_buyer
FROM m GROUP BY 1, 2;

-- ---------------------------------------------------------------- Penjualan per wilayah & jam (heatmap)
CREATE OR REPLACE VIEW mart.v_region_month AS
SELECT platform_code, date_trunc('month', order_date)::date AS month_start, region, province, city, count(*) FILTER (WHERE is_valid_sale) AS orders, coalesce(sum(gmv_placed) FILTER (WHERE is_valid_sale), 0) AS net_gmv
FROM dwh.fact_order GROUP BY 1, 2, 3, 4, 5;

CREATE OR REPLACE VIEW mart.v_hourly_heatmap AS
SELECT platform_code, extract(isodow FROM order_date)::int AS iso_dow, order_hour, count(*) AS orders, round(avg(gmv_placed)) AS avg_order_value
FROM dwh.fact_order WHERE is_valid_sale GROUP BY 1, 2, 3;

-- ---------------------------------------------------------------- ringkasan cepat
SELECT platform_code, to_char(month_start, 'YYYY-MM') AS bulan, net_gmv, aov, cancel_rate, tacos, roas, cm1, cm2, cm2_pct FROM mart.v_kpi_platform_month WHERE month_start >= '2026-09-01' ORDER BY 1, 2;
