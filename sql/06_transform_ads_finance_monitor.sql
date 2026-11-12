-- =====================================================================================
-- 06_transform_ads_finance_monitor.sql
-- Cleaning + transformasi: iklan, settlement platform, ERP internal, statement program, snapshot harga.
-- Keputusan cleaning didokumentasikan di komentar tiap blok (ini yang ditanyakan reviewer/recruiter!).
-- =====================================================================================
SET search_path = etl, public;

-- =============================================================== 1) IKLAN
DROP TABLE IF EXISTS etl.ads_parsed CASCADE;
CREATE TABLE etl.ads_parsed AS
WITH p AS (
    SELECT a._src_file AS src_file, a._row_id AS src_row_id,
           md5((to_jsonb(a) - '_src_file' - '_loaded_at' - '_row_id')::text) AS row_hash,
           etl.platform_code(a.platform_txt) AS platform_code, a.ad_date_txt, a.ad_type, a.campaign_name,
           a.impressions, a.clicks, a.spend, a.ad_orders, a.ad_gmv
    FROM stg.ads a)
SELECT p.src_file, p.src_row_id, p.row_hash, p.platform_code,
       -- format tanggal & angka berbeda per platform
       CASE p.platform_code WHEN 'SHP' THEN to_date(btrim(p.ad_date_txt), 'DD-MM-YYYY')
                            WHEN 'TTK' THEN to_date(btrim(p.ad_date_txt), 'YYYY-MM-DD')
                            WHEN 'LZD' THEN to_date(btrim(p.ad_date_txt), 'DD Mon YYYY')
                            WHEN 'BLI' THEN to_date(btrim(p.ad_date_txt), 'MM/DD/YYYY') END AS ad_date,
       etl.clean_txt(p.ad_type) AS ad_type, etl.clean_txt(p.campaign_name) AS campaign_name,
       etl.num_plain(p.impressions)::bigint AS impressions, etl.num_plain(p.clicks)::bigint AS clicks, etl.num_plain(p.ad_orders)::int AS ad_orders,
       CASE p.platform_code WHEN 'SHP' THEN etl.num_id(p.spend) WHEN 'BLI' THEN etl.num_id(p.spend) ELSE etl.num_plain(p.spend) END AS spend_raw,
       CASE p.platform_code WHEN 'SHP' THEN abs(etl.num_id(p.ad_gmv)) WHEN 'BLI' THEN abs(etl.num_id(p.ad_gmv)) ELSE abs(etl.num_plain(p.ad_gmv)) END AS ad_gmv,
       row_number() OVER (PARTITION BY md5((to_jsonb(p.*) - 'src_file' - 'src_row_id')::text) ORDER BY p.src_file, p.src_row_id) AS dup_rank
FROM p;

DELETE FROM ops.quarantine_row WHERE domain = 'ADS';
INSERT INTO ops.quarantine_row (domain, platform_code, src_file, src_row_id, reason, business_key, payload)
SELECT 'ADS', platform_code, src_file, src_row_id, 'EXACT_DUPLICATE', platform_code || '|' || ad_date || '|' || ad_type || '|' || campaign_name,
       jsonb_build_object('ad_date', ad_date, 'ad_type', ad_type, 'campaign', campaign_name, 'spend_raw', spend_raw)
FROM etl.ads_parsed WHERE dup_rank > 1;

DROP TABLE IF EXISTS dwh.fact_ads_daily CASCADE;
CREATE TABLE dwh.fact_ads_daily AS
SELECT a.ad_date, a.platform_code, a.ad_type, a.campaign_name,
       split_part(a.campaign_name, ' - ', 1) AS sub_category,
       c.campaign_id,
       a.impressions, a.clicks, least(a.clicks, a.impressions) AS clicks_clean,
       -- spend negatif: tanda salah ekspor (baris yang sama membawa ad_orders & ad_gmv positif) -> ABS(). Dicatat di dq_flag.
       abs(a.spend_raw)::bigint AS spend, a.ad_orders, a.ad_gmv::bigint AS ad_gmv,
       CASE WHEN a.spend_raw < 0 THEN 'NEGATIVE_SPEND_SIGN_FIXED'
            WHEN a.spend_raw = 0 AND a.clicks > 0 THEN 'ZERO_SPEND_WITH_CLICKS'
            WHEN a.clicks > a.impressions THEN 'CLICKS_GT_IMPRESSIONS' END AS dq_flag,
       -- baris dengan spend=0 tapi ada klik: nilainya hilang, jangan dipakai untuk rasio (ROAS/CPC) agar tidak bias
       NOT (a.spend_raw = 0 AND a.clicks > 0) AS spend_reliable
FROM etl.ads_parsed a
LEFT JOIN dwh.dim_campaign c ON c.platform_code = a.platform_code AND c.campaign_name = split_part(a.campaign_name, ' - ', 2)
                            AND a.ad_date BETWEEN c.start_date AND c.end_date
WHERE a.dup_rank = 1;
ALTER TABLE dwh.fact_ads_daily ADD PRIMARY KEY (ad_date, platform_code, ad_type, campaign_name);
CREATE INDEX ON dwh.fact_ads_daily (platform_code, ad_date);

-- =============================================================== 2) SETTLEMENT PLATFORM
-- Konvensi tanda berbeda tiap platform (Shopee/Lazada: potongan negatif; TikTok/Blibli: potongan positif).
-- Kita simpan SEMUA potongan sebagai besaran positif, kecuali shipping_adj (bertanda: negatif = dipotong).
DROP TABLE IF EXISTS dwh.fact_settlement CASCADE;
CREATE TABLE dwh.fact_settlement AS
WITH u AS (
    SELECT 'SHP'::text AS platform_code, s._src_file AS src_file, s._row_id AS src_row_id, etl.clean_txt(s.order_ref) AS order_id,
           to_date(btrim(s.settle_date_txt), 'DD/MM/YYYY') AS settle_date,
           etl.num_id(s.gross_item_amt) AS gross_item_amt, abs(etl.num_id(s.seller_voucher)) AS seller_voucher_amt, abs(etl.num_id(s.platform_voucher_credit)) AS platform_voucher_credit,
           abs(etl.num_id(s.commission_fee)) AS commission_fee, abs(etl.num_id(s.service_fee)) AS service_fee, abs(etl.num_id(s.payment_fee)) AS payment_fee,
           etl.num_id(s.shipping_adj) AS shipping_adj, etl.num_id(s.net_payout) AS net_payout
    FROM stg.settlement_shopee s
    UNION ALL
    SELECT 'TTK', s._src_file, s._row_id, etl.clean_txt(s.order_ref),
           (etl.parse_ts(btrim(s.settle_date_txt), 'YYYY-MM-DD"T"HH24:MI:SS"Z"') + interval '7 hours')::date,                -- UTC -> WIB
           etl.num_plain(s.gross_item_amt), abs(etl.num_plain(s.seller_voucher)), abs(etl.num_plain(s.platform_voucher_credit)),
           abs(etl.num_plain(s.commission_fee)), abs(etl.num_plain(s.service_fee)), abs(etl.num_plain(s.payment_fee)), etl.num_plain(s.shipping_adj), etl.num_plain(s.net_payout)
    FROM stg.settlement_tiktok s
    UNION ALL
    SELECT 'LZD', s._src_file, s._row_id, etl.clean_txt(s.order_ref), to_date(btrim(s.settle_date_txt), 'DD Mon YYYY'),
           etl.num_plain(s.gross_item_amt), abs(etl.num_plain(s.seller_voucher)), abs(etl.num_plain(s.platform_voucher_credit)),
           abs(etl.num_plain(s.commission_fee)), abs(etl.num_plain(s.service_fee)), abs(etl.num_plain(s.payment_fee)), etl.num_plain(s.shipping_adj), etl.num_plain(s.net_payout)
    FROM stg.settlement_lazada s
    UNION ALL
    SELECT 'BLI', s._src_file, s._row_id, etl.clean_txt(s.order_ref), to_date(btrim(s.settle_date_txt), 'MM/DD/YYYY'),
           etl.num_id(s.gross_item_amt), abs(etl.num_id(s.seller_voucher)), abs(etl.num_id(s.platform_voucher_credit)),
           abs(etl.num_id(s.commission_fee)), abs(etl.num_id(s.service_fee)), abs(etl.num_id(s.payment_fee)), etl.num_id(s.shipping_adj), etl.num_id(s.net_payout)
    FROM stg.settlement_blibli s)
SELECT row_number() OVER (ORDER BY platform_code, order_id, src_row_id) AS settlement_row_id,
       u.platform_code, u.order_id, u.settle_date, u.gross_item_amt::bigint, u.seller_voucher_amt::bigint, u.platform_voucher_credit::bigint,
       u.commission_fee::bigint, u.service_fee::bigint, u.payment_fee::bigint, u.shipping_adj::bigint, u.net_payout::bigint,
       -- identitas: net = gross - voucher penjual + subsidi - komisi - layanan - pembayaran + selisih ongkir
       (u.gross_item_amt - u.seller_voucher_amt + u.platform_voucher_credit - u.commission_fee - u.service_fee - u.payment_fee + u.shipping_adj = u.net_payout) AS net_identity_ok,
       row_number() OVER (PARTITION BY u.platform_code, u.order_id ORDER BY u.src_file, u.src_row_id) AS dup_rank,
       u.src_file
FROM u;
ALTER TABLE dwh.fact_settlement ADD PRIMARY KEY (settlement_row_id);
CREATE INDEX ON dwh.fact_settlement (platform_code, order_id);
CREATE INDEX ON dwh.fact_settlement (settle_date);

-- =============================================================== 3) ERP INTERNAL
DROP TABLE IF EXISTS dwh.fact_erp_sales CASCADE;
CREATE TABLE dwh.fact_erp_sales AS
SELECT e.erp_doc_no, etl.platform_code(e.channel) AS platform_code, etl.clean_txt(e.order_ref) AS order_id, to_date(e.ship_date, 'YYYY-MM-DD') AS ship_date,
       etl.num_plain(e.gross_amount)::bigint AS gross_amount, etl.num_plain(e.disc_amount)::bigint AS disc_amount, etl.num_plain(e.net_amount)::bigint AS net_amount
FROM stg.erp_sales e;
ALTER TABLE dwh.fact_erp_sales ADD PRIMARY KEY (erp_doc_no);
CREATE INDEX ON dwh.fact_erp_sales (platform_code, order_id);

-- =============================================================== 4) STATEMENT PROGRAM PLATFORM
DROP TABLE IF EXISTS dwh.fact_program_statement CASCADE;
CREATE TABLE dwh.fact_program_statement AS
SELECT statement_id, etl.platform_code(platform_txt) AS platform_code, program_code, period_label,
       period_start::date AS period_start, period_end::date AS period_end, etl.num_id(paid_amount)::bigint AS paid_amount, paid_date::date AS paid_date, nullif(remarks, '') AS remarks
FROM stg.program_statement;
ALTER TABLE dwh.fact_program_statement ADD PRIMARY KEY (statement_id);

-- =============================================================== 5) SNAPSHOT HARGA (price monitoring)
DROP TABLE IF EXISTS etl.monitor_parsed CASCADE;
CREATE TABLE etl.monitor_parsed AS
SELECT m._src_file AS src_file, m._row_id AS src_row_id, md5((to_jsonb(m) - '_src_file' - '_loaded_at' - '_row_id')::text) AS row_hash,
       etl.platform_code(m.platform_txt) AS platform_code,
       CASE etl.platform_code(m.platform_txt)
            WHEN 'SHP' THEN etl.parse_ts(m.snapshot_ts_txt, 'YYYY-MM-DD HH24:MI:SS')
            WHEN 'TTK' THEN etl.parse_ts(left(m.snapshot_ts_txt, 19), 'YYYY-MM-DD"T"HH24:MI:SS')      -- sudah +07:00 (WIB), sufiks dibuang
            WHEN 'LZD' THEN etl.parse_ts(m.snapshot_ts_txt, 'DD/MM/YYYY HH24:MI')
            WHEN 'BLI' THEN etl.parse_ts(m.snapshot_ts_txt, 'YYYY-MM-DD HH24:MI:SS') END AS snapshot_ts,
       lower(etl.clean_txt(m.seller_name)) AS seller_key, etl.clean_txt(m.listing_id) AS listing_id,
       etl.num_id(m.price_displayed) AS price_displayed,           -- 'Rp 39.900' / '39,900' / '39900' -> 39900 ; '' -> NULL
       etl.num_id(m.price_strike) AS price_strike, nullif(etl.clean_txt(m.promo_label), '') AS promo_label, etl.num_plain(m.stock_qty)::int AS stock_qty,
       row_number() OVER (PARTITION BY md5((to_jsonb(m) - '_src_file' - '_loaded_at' - '_row_id')::text) ORDER BY m._src_file, m._row_id) AS dup_rank
FROM stg.price_monitor m;

DELETE FROM ops.quarantine_row WHERE domain = 'MONITOR';
INSERT INTO ops.quarantine_row (domain, platform_code, src_file, src_row_id, reason, business_key, payload)
SELECT 'MONITOR', platform_code, src_file, src_row_id,
       CASE WHEN dup_rank > 1 THEN 'EXACT_DUPLICATE' WHEN price_displayed IS NULL THEN 'PRICE_MISSING' WHEN price_displayed <= 0 THEN 'PRICE_ZERO' END,
       platform_code || '|' || listing_id || '|' || seller_key || '|' || snapshot_ts,
       jsonb_build_object('snapshot_ts', snapshot_ts, 'seller', seller_key, 'listing', listing_id, 'price', price_displayed)
FROM etl.monitor_parsed WHERE dup_rank > 1 OR price_displayed IS NULL OR price_displayed <= 0;

DROP TABLE IF EXISTS dwh.fact_price_snapshot CASCADE;
CREATE TABLE dwh.fact_price_snapshot AS
SELECT m.platform_code, m.snapshot_ts, m.snapshot_ts::date AS snapshot_date, m.seller_key, s.seller_name, s.authorization_status, m.listing_id,
       l.sku, l.pack_qty, m.price_displayed::int AS price_displayed, m.price_strike::int AS price_strike, m.promo_label, m.stock_qty,
       round(m.price_displayed / l.pack_qty, 2) AS unit_price, round(m.price_strike / l.pack_qty, 2) AS unit_strike,
       k.rrp_idr, k.map_floor_idr, k.campaign_floor_idr,
       (cb.date IS NOT NULL) AS in_deep_campaign_window, cb.campaign_id AS deep_campaign_id,
       CASE WHEN cb.date IS NOT NULL THEN k.campaign_floor_idr ELSE k.map_floor_idr END AS floor_applicable,
       (m.price_displayed / l.pack_qty) < (CASE WHEN cb.date IS NOT NULL THEN k.campaign_floor_idr ELSE k.map_floor_idr END) AS flag_below_floor,
       (m.price_strike / l.pack_qty) > 1.10 * k.rrp_idr AS flag_strike_inflation
FROM etl.monitor_parsed m
JOIN dwh.dim_listing l ON l.platform_code = m.platform_code AND l.listing_id = m.listing_id
JOIN dwh.dim_sku k ON k.sku = l.sku
JOIN dwh.dim_seller s ON s.seller_key = m.seller_key
LEFT JOIN (SELECT DISTINCT ON (platform_code, date) platform_code, date, campaign_id FROM dwh.bridge_campaign_day WHERE allows_deep_discount ORDER BY platform_code, date, campaign_id) cb
       ON cb.platform_code = m.platform_code AND cb.date = m.snapshot_ts::date
WHERE m.dup_rank = 1 AND m.price_displayed > 0;
ALTER TABLE dwh.fact_price_snapshot ADD PRIMARY KEY (platform_code, listing_id, seller_key, snapshot_ts);
CREATE INDEX ON dwh.fact_price_snapshot (snapshot_ts DESC);
CREATE INDEX ON dwh.fact_price_snapshot (platform_code, sku, snapshot_ts);
CREATE INDEX ON dwh.fact_price_snapshot (snapshot_ts) WHERE flag_below_floor OR flag_strike_inflation;

-- =============================================================== ringkasan
SELECT 'fact_ads_daily' AS tabel, count(*) AS baris FROM dwh.fact_ads_daily
UNION ALL SELECT 'fact_settlement', count(*) FROM dwh.fact_settlement
UNION ALL SELECT 'fact_erp_sales', count(*) FROM dwh.fact_erp_sales
UNION ALL SELECT 'fact_program_statement', count(*) FROM dwh.fact_program_statement
UNION ALL SELECT 'fact_price_snapshot', count(*) FROM dwh.fact_price_snapshot
UNION ALL SELECT 'quarantine ' || domain || ':' || reason, count(*) FROM ops.quarantine_row WHERE domain IN ('ADS','MONITOR') GROUP BY domain, reason
ORDER BY 1;
