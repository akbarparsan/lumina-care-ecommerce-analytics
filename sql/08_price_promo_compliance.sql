-- =====================================================================================
-- 08_price_promo_compliance.sql : monitoring kepatuhan harga & promosi (schema ops)
--   A. Alert harga terkini (snapshot terakhir per listing x penjual)
--   B. Episode pelanggaran (gaps-and-islands) + durasi + akar masalah
--   C. Kebocoran harga toko resmi dari ORDER aktual (rupiah yang hilang di bawah floor)
--   D. Validasi aturan voucher (V1 min-spend, V2 masa berlaku, V3 kuota)
-- =====================================================================================
SET search_path = ops, public;

-- ---------------------------------------------------------------- A. Alert terkini
CREATE OR REPLACE VIEW ops.v_price_alerts_latest AS
WITH last_snap AS (
    SELECT DISTINCT ON (platform_code, listing_id, seller_key) *
    FROM dwh.fact_price_snapshot WHERE unit_price IS NOT NULL AND unit_price > 0
    ORDER BY platform_code, listing_id, seller_key, snapshot_ts DESC)
SELECT s.snapshot_ts, s.platform_code, s.seller_name, s.authorization_status, s.listing_id, s.sku, s.pack_qty, s.price_displayed, s.unit_price,
       s.floor_applicable, s.in_deep_campaign_window,
       CASE WHEN s.flag_below_floor THEN 'BELOW_MAP' ELSE 'STRIKE_PRICE_INFLATION' END AS violation_type,
       CASE WHEN s.flag_below_floor THEN round(1 - s.unit_price / NULLIF(s.floor_applicable, 0), 4) END AS pct_below_floor,
       CASE WHEN s.flag_below_floor THEN round((s.floor_applicable - s.unit_price) * s.pack_qty) END AS gap_idr_per_pack,
       CASE WHEN s.flag_below_floor AND s.unit_price < 0.5 * s.floor_applicable THEN 'CRITICAL'
            WHEN s.flag_below_floor AND s.authorization_status = 'OFFICIAL' THEN 'HIGH'
            WHEN s.flag_below_floor THEN 'MEDIUM' ELSE 'LOW' END AS severity,
       (SELECT now()) AS evaluated_at
FROM last_snap s WHERE s.flag_below_floor OR s.flag_strike_inflation;

-- ---------------------------------------------------------------- B. Episode pelanggaran
-- Urutan snapshot per (listing, penjual); snapshot yang hilang tidak memutus episode (kita hanya melihat snapshot yang ada).
CREATE OR REPLACE VIEW ops.v_price_violation_episodes AS
WITH base AS (
    SELECT platform_code, listing_id, seller_key, seller_name, authorization_status, sku, pack_qty, snapshot_ts, unit_price, floor_applicable, in_deep_campaign_window, deep_campaign_id,
           flag_below_floor AS below, flag_strike_inflation AS strike
    FROM dwh.fact_price_snapshot WHERE unit_price IS NOT NULL AND unit_price > 0),
typed AS (
    SELECT *, 'BELOW_MAP'::text AS vtype, below AS bad FROM base
    UNION ALL
    SELECT *, 'STRIKE_PRICE_INFLATION', strike FROM base),
numbered AS (
    SELECT *, row_number() OVER (PARTITION BY platform_code, listing_id, seller_key, vtype ORDER BY snapshot_ts) AS rn_all,
           row_number() OVER (PARTITION BY platform_code, listing_id, seller_key, vtype, bad ORDER BY snapshot_ts) AS rn_bad
    FROM typed),
islands AS (
    SELECT platform_code, listing_id, seller_key, seller_name, authorization_status, sku, pack_qty, vtype, (rn_all - rn_bad) AS grp,
           min(snapshot_ts) AS episode_start, max(snapshot_ts) AS episode_end, count(*) AS snapshots,
           min(unit_price) AS min_unit_price, max(floor_applicable) AS floor_unit, bool_or(in_deep_campaign_window) AS touched_campaign_window
    FROM numbered WHERE bad GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9)
SELECT i.*, round(extract(epoch FROM (episode_end - episode_start)) / 3600 + 3, 1) AS approx_hours_exposed,   -- +3 jam: resolusi snapshot
       CASE WHEN vtype = 'BELOW_MAP' THEN round(1 - min_unit_price / NULLIF(floor_unit, 0), 4) END AS max_pct_below_floor,
       CASE WHEN vtype = 'STRIKE_PRICE_INFLATION' THEN 'STRIKE_INFLATION'
            WHEN authorization_status <> 'OFFICIAL' AND snapshots >= 20 THEN 'RESELLER_PERSISTENT_UNDERCUT'
            WHEN authorization_status <> 'OFFICIAL' THEN 'RESELLER_UNDERCUT_EPISODE'
            WHEN min_unit_price < 0.5 * floor_unit THEN 'PRICE_ERROR_INCIDENT'
            WHEN touched_campaign_window THEN 'CAMPAIGN_OVERRUN'
            ELSE 'OFFICIAL_BELOW_MAP_OTHER' END AS likely_root_cause
FROM islands i;

-- ---------------------------------------------------------------- Ringkasan kepatuhan per platform-hari (untuk tren)
CREATE OR REPLACE VIEW ops.v_price_compliance_daily AS
SELECT platform_code, snapshot_date, authorization_status,
       count(*) AS observations, count(*) FILTER (WHERE flag_below_floor) AS below_floor_obs, count(*) FILTER (WHERE flag_strike_inflation) AS strike_obs,
       round(1 - (count(*) FILTER (WHERE flag_below_floor OR flag_strike_inflation))::numeric / count(*), 4) AS compliance_rate
FROM dwh.fact_price_snapshot WHERE unit_price IS NOT NULL AND unit_price > 0
GROUP BY 1, 2, 3;

-- Cakupan monitoring: snapshot yang diharapkan vs. diterima (3 jam sekali = 8 per hari per listing-penjual) -> deteksi celah crawler
CREATE OR REPLACE VIEW ops.v_monitor_coverage AS
SELECT platform_code, snapshot_date, count(DISTINCT (listing_id, seller_key, snapshot_ts)) AS snapshots_received,
       count(DISTINCT (listing_id, seller_key)) * 8 AS snapshots_expected,
       round(count(DISTINCT (listing_id, seller_key, snapshot_ts))::numeric / NULLIF(count(DISTINCT (listing_id, seller_key)) * 8, 0), 3) AS coverage
FROM dwh.fact_price_snapshot GROUP BY 1, 2;

-- ---------------------------------------------------------------- C. Kebocoran harga toko resmi dari order aktual
-- Baris order dengan harga jual satuan di bawah floor yang berlaku saat itu (MAP; campaign floor hanya di hari kampanye deep-discount).
CREATE OR REPLACE VIEW ops.v_official_price_leakage_lines AS
SELECT l.platform_code, l.order_id, l.line_no, l.order_date, l.sku, l.qty, l.unit_list_price, l.unit_sell_price,
       CASE WHEN coalesce(pd.allows_deep_discount, false) THEN k.campaign_floor_idr ELSE k.map_floor_idr END AS floor_unit,
       pd.campaign_type,
       round((CASE WHEN coalesce(pd.allows_deep_discount, false) THEN k.campaign_floor_idr ELSE k.map_floor_idr END - l.unit_sell_price) * l.qty) AS leakage_idr,
       round(1 - l.unit_sell_price / NULLIF(CASE WHEN coalesce(pd.allows_deep_discount, false) THEN k.campaign_floor_idr ELSE k.map_floor_idr END, 0), 4) AS pct_below_floor
FROM dwh.fact_order_line l
JOIN dwh.fact_order o USING (platform_code, order_id)
JOIN dwh.dim_sku k USING (sku)
LEFT JOIN mart.v_platform_day pd ON pd.platform_code = l.platform_code AND pd.date = l.order_date
WHERE o.is_valid_sale
  AND l.unit_sell_price < (CASE WHEN coalesce(pd.allows_deep_discount, false) THEN k.campaign_floor_idr ELSE k.map_floor_idr END) - 1;

CREATE OR REPLACE VIEW ops.v_official_price_leakage_summary AS
SELECT platform_code, date_trunc('month', order_date)::date AS month_start,
       CASE WHEN pct_below_floor >= 0.5 THEN 'SALAH_HARGA (>=50% di bawah floor)' ELSE 'DI BAWAH FLOOR (<50%)' END AS bucket,
       count(DISTINCT order_id) AS orders, sum(qty) AS units, sum(leakage_idr) AS leakage_idr
FROM ops.v_official_price_leakage_lines GROUP BY 1, 2, 3;

-- ---------------------------------------------------------------- D. Validasi aturan voucher
-- Redemption per (order, kode); subtotal item dipakai untuk uji min-spend. Urutan pemakaian (kuota) memakai order_ts lalu order_id.
CREATE OR REPLACE VIEW ops.v_voucher_rule_violations AS
WITH u AS (
    SELECT x.platform_code, x.order_id, x.voucher_code, o.order_ts, o.order_date, o.gmv_placed, v.min_spend, v.quota, v.start_date, v.end_date,
           row_number() OVER (PARTITION BY x.voucher_code ORDER BY o.order_ts, x.order_id) AS use_seq,
           x.discount_total
    FROM mart.v_voucher_usage x JOIN dwh.fact_order o USING (platform_code, order_id) JOIN dwh.dim_voucher v USING (voucher_code)
    )   -- semua status ikut: pelanggaran aturan terjadi saat order dibuat, sebelum dibatalkan
SELECT platform_code, order_id, voucher_code, 'VOUCHER_BELOW_MIN_SPEND' AS violation_type, discount_total AS exposure_idr, (min_spend - gmv_placed) AS detail_value
FROM u WHERE min_spend > 0 AND gmv_placed < min_spend
UNION ALL
SELECT platform_code, order_id, voucher_code, 'VOUCHER_USED_AFTER_EXPIRY', discount_total, (order_date - end_date) FROM u WHERE order_date > end_date OR order_date < start_date
UNION ALL
SELECT platform_code, order_id, voucher_code, 'VOUCHER_OVER_QUOTA', discount_total, (use_seq - quota) FROM u WHERE quota IS NOT NULL AND use_seq > quota;

CREATE OR REPLACE VIEW ops.v_voucher_violation_summary AS
SELECT platform_code, voucher_code, violation_type, count(*) AS orders, sum(exposure_idr) AS exposure_idr
FROM ops.v_voucher_rule_violations GROUP BY 1, 2, 3;

SELECT violation_type, count(*) AS n FROM ops.v_voucher_rule_violations GROUP BY 1 ORDER BY 1;
SELECT likely_root_cause, vtype, count(*) AS episodes, round(avg(snapshots), 1) AS avg_snapshots FROM ops.v_price_violation_episodes GROUP BY 1, 2 ORDER BY 1;
SELECT bucket, sum(orders) AS orders, sum(leakage_idr) AS leakage_idr FROM ops.v_official_price_leakage_summary GROUP BY 1;
SELECT severity, count(*) FROM ops.v_price_alerts_latest GROUP BY 1 ORDER BY 1;
