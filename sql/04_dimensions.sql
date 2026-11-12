-- =====================================================================================
-- 04_dimensions.sql : dimensi & data referensi bersih (dwh.*). Full refresh, idempoten.
-- =====================================================================================
SET search_path = dwh, public;

DROP TABLE IF EXISTS dwh.dim_platform CASCADE;
CREATE TABLE dwh.dim_platform AS
SELECT * FROM (VALUES
    ('SHP', 'Shopee',                'WIB', 'Waktu ekspor WIB; angka format Indonesia (titik ribuan); voucher level-order diulang di tiap baris'),
    ('TTK', 'TikTok Shop/Tokopedia', 'UTC', 'Waktu ekspor UTC (+7 jam ke WIB); voucher dialokasikan per baris SKU; ID bisa rusak jadi notasi ilmiah di Excel'),
    ('LZD', 'Lazada',                'WIB', 'Angka desimal titik; voucher per item; bulan berbahasa Inggris'),
    ('BLI', 'Blibli',                'WIB', 'Tanggal format US (MM/DD/YYYY 12 jam); delimiter titik-koma; voucher level-order hanya di baris pertama')
) v(platform_code, platform_name, export_timezone, export_notes);
ALTER TABLE dwh.dim_platform ADD PRIMARY KEY (platform_code);

DROP TABLE IF EXISTS dwh.dim_sku CASCADE;
CREATE TABLE dwh.dim_sku AS
SELECT sku, product_name, sub_category,
       rrp_idr::int AS rrp_idr, cogs_idr::int AS cogs_idr, map_floor_idr::int AS map_floor_idr, campaign_floor_idr::int AS campaign_floor_idr,
       round(cogs_idr::numeric / rrp_idr::numeric, 4) AS cogs_pct_of_rrp,
       round(map_floor_idr::numeric / rrp_idr::numeric, 4) AS map_pct_of_rrp
FROM stg.sku_master;
ALTER TABLE dwh.dim_sku ADD PRIMARY KEY (sku);

DROP TABLE IF EXISTS dwh.dim_listing CASCADE;
CREATE TABLE dwh.dim_listing AS
SELECT etl.platform_code(platform_txt) AS platform_code, listing_id, sku, pack_qty::int AS pack_qty, etl.clean_txt(listing_title) AS listing_title
FROM stg.listing_map;
ALTER TABLE dwh.dim_listing ADD PRIMARY KEY (platform_code, listing_id);
CREATE INDEX ON dwh.dim_listing (platform_code, sku, pack_qty);

DROP TABLE IF EXISTS dwh.ref_city_alias CASCADE;
CREATE TABLE dwh.ref_city_alias AS
SELECT etl.norm_key(alias_key) AS alias_key, city, province, region FROM stg.ref_city_alias;
ALTER TABLE dwh.ref_city_alias ADD PRIMARY KEY (alias_key);

DROP TABLE IF EXISTS dwh.dim_city CASCADE;
CREATE TABLE dwh.dim_city AS SELECT DISTINCT city, province, region FROM dwh.ref_city_alias;
ALTER TABLE dwh.dim_city ADD PRIMARY KEY (city);

DROP TABLE IF EXISTS dwh.dim_campaign CASCADE;
CREATE TABLE dwh.dim_campaign AS
SELECT etl.platform_code(platform_txt) AS platform_code, campaign_id, campaign_name, campaign_type,
       start_date::date AS start_date, end_date::date AS end_date,
       (lower(allows_deep_discount) IN ('true','t','1','yes')) AS allows_deep_discount,
       (end_date::date - start_date::date + 1) AS duration_days
FROM stg.campaign_calendar;
ALTER TABLE dwh.dim_campaign ADD PRIMARY KEY (campaign_id);
CREATE INDEX ON dwh.dim_campaign (platform_code, start_date, end_date);

DROP TABLE IF EXISTS dwh.dim_voucher CASCADE;
CREATE TABLE dwh.dim_voucher AS
SELECT voucher_code, etl.platform_code(platform_txt) AS platform_code, voucher_type, funding_model,
       seller_share_pct::numeric AS seller_share_pct, discount_kind, discount_value::numeric AS discount_value, max_discount::numeric AS max_discount,
       min_spend::numeric AS min_spend, quota::int AS quota, budget_idr::numeric AS budget_idr, start_date::date AS start_date, end_date::date AS end_date,
       nullif(campaign_id, '') AS campaign_id
FROM stg.voucher_master;
ALTER TABLE dwh.dim_voucher ADD PRIMARY KEY (voucher_code);

DROP TABLE IF EXISTS dwh.dim_fee_contract CASCADE;
CREATE TABLE dwh.dim_fee_contract AS
SELECT etl.platform_code(platform_txt) AS platform_code, commission_pct::numeric AS commission_pct, service_fee_pct::numeric AS service_fee_pct,
       payment_fee_pct::numeric AS payment_fee_pct, valid_from::date AS valid_from, valid_to::date AS valid_to
FROM stg.fee_contract;
ALTER TABLE dwh.dim_fee_contract ADD PRIMARY KEY (platform_code);

DROP TABLE IF EXISTS dwh.dim_jbp CASCADE;
CREATE TABLE dwh.dim_jbp AS
SELECT agreement_id, etl.platform_code(platform_txt) AS platform_code, program_code, period_type, valid_from::date AS valid_from, valid_to::date AS valid_to, metric,
       nullif(tier1_threshold, '')::numeric AS tier1_threshold, nullif(tier1_rate_pct, '')::numeric AS tier1_rate_pct,
       nullif(tier2_threshold, '')::numeric AS tier2_threshold, nullif(tier2_rate_pct, '')::numeric AS tier2_rate_pct,
       nullif(cap_amount, '')::numeric AS cap_amount, campaign_scope, notes
FROM stg.jbp_agreement;
ALTER TABLE dwh.dim_jbp ADD PRIMARY KEY (agreement_id);

-- Registri penjual resmi/otorisasi; penjual lain yang terlihat di marketplace dianggap TIDAK RESMI
DROP TABLE IF EXISTS dwh.dim_seller CASCADE;
CREATE TABLE dwh.dim_seller AS
WITH seen AS (SELECT DISTINCT lower(etl.clean_txt(seller_name)) AS seller_key FROM stg.price_monitor WHERE etl.clean_txt(seller_name) IS NOT NULL),
     reg  AS (SELECT lower(etl.clean_txt(seller_name)) AS seller_key, etl.clean_txt(seller_name) AS seller_name, authorization_status FROM stg.authorized_sellers)
SELECT s.seller_key,
       coalesce(r.seller_name, initcap(s.seller_key)) AS seller_name,
       coalesce(r.authorization_status, 'UNAUTHORIZED') AS authorization_status
FROM seen s LEFT JOIN reg r USING (seller_key);
ALTER TABLE dwh.dim_seller ADD PRIMARY KEY (seller_key);

DROP TABLE IF EXISTS dwh.dim_date CASCADE;
CREATE TABLE dwh.dim_date AS
SELECT d::date AS date,
       to_char(d, 'YYYYMMDD')::int AS date_key,
       extract(year FROM d)::int AS year, extract(quarter FROM d)::int AS quarter, extract(month FROM d)::int AS month,
       to_char(d, 'YYYY-MM') AS year_month, to_char(d, 'TMMon') AS month_name,
       date_trunc('week', d)::date AS week_start, extract(isodow FROM d)::int AS iso_dow, to_char(d, 'TMDy') AS day_name,
       (extract(isodow FROM d) >= 6) AS is_weekend,
       (extract(day FROM d) BETWEEN 25 AND 27) AS is_payday_window,
       (extract(day FROM d) = extract(month FROM d)) AS is_double_date,
       (date_trunc('month', d) + interval '1 month - 1 day')::date AS month_end
FROM generate_series('2025-12-01'::date, '2026-12-31'::date, '1 day') g(d);
ALTER TABLE dwh.dim_date ADD PRIMARY KEY (date);

-- Hari kampanye per platform (1 baris per platform-hari-kampanye); kampanye tumpang-tindih tetap muncul
DROP TABLE IF EXISTS dwh.bridge_campaign_day CASCADE;
CREATE TABLE dwh.bridge_campaign_day AS
SELECT c.platform_code, d.date, c.campaign_id, c.campaign_type, c.allows_deep_discount
FROM dwh.dim_campaign c JOIN dwh.dim_date d ON d.date BETWEEN c.start_date AND c.end_date;
ALTER TABLE dwh.bridge_campaign_day ADD PRIMARY KEY (platform_code, date, campaign_id);

-- Resolusi kota: alias persis -> canonical; salah ketik -> kemiripan trigram (pg_trgm) >= 0.45
DROP TABLE IF EXISTS etl.city_resolved CASCADE;
CREATE TABLE etl.city_resolved AS
WITH raw_keys AS (
    SELECT DISTINCT etl.norm_key(city) AS city_key FROM (
        SELECT city FROM stg.orders_shopee UNION SELECT city FROM stg.orders_tiktok UNION SELECT city FROM stg.orders_lazada UNION SELECT city FROM stg.orders_blibli) x
    WHERE etl.clean_txt(city) IS NOT NULL)
SELECT k.city_key,
       coalesce(a.city, f.city) AS city,
       CASE WHEN a.city IS NOT NULL THEN 'ALIAS' WHEN f.city IS NOT NULL THEN 'FUZZY' ELSE 'UNRESOLVED' END AS method,
       f.sim
FROM raw_keys k
LEFT JOIN dwh.ref_city_alias a ON a.alias_key = k.city_key
LEFT JOIN LATERAL (SELECT c.city, similarity(lower(c.city), k.city_key) AS sim FROM dwh.dim_city c
                   ORDER BY similarity(lower(c.city), k.city_key) DESC LIMIT 1) f ON a.city IS NULL AND f.sim >= 0.45;
ALTER TABLE etl.city_resolved ADD PRIMARY KEY (city_key);

SELECT 'dim_sku' AS tabel, count(*) FROM dwh.dim_sku UNION ALL SELECT 'dim_listing', count(*) FROM dwh.dim_listing UNION ALL SELECT 'dim_voucher', count(*) FROM dwh.dim_voucher
UNION ALL SELECT 'dim_campaign', count(*) FROM dwh.dim_campaign UNION ALL SELECT 'dim_date', count(*) FROM dwh.dim_date UNION ALL SELECT 'dim_seller', count(*) FROM dwh.dim_seller
UNION ALL SELECT 'city_resolved:'||method, count(*) FROM etl.city_resolved GROUP BY method;
