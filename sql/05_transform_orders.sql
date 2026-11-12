-- =====================================================================================
-- 05_transform_orders.sql : CLEANING + TRANSFORMASI order 4 platform -> dwh.fact_order_line / dwh.fact_order
--
-- Tahapan
--   1) etl.orders_parsed      : parse tiap format platform ke satu skema seragam (tanggal, angka, zona waktu, level voucher)
--   2) etl.orders_classified  : normalisasi SKU, pulihkan SKU kosong dari judul listing, tandai duplikat
--   3) ops.quarantine_row     : baris yang disingkirkan + alasan (duplikat, test, ID rusak, SKU/Qty tak terpulihkan)
--   4) dwh.fact_order_line    : baris bersih + alokasi voucher yang konsisten
--   5) dwh.fact_order         : agregat level order (sumber KPI GMV)
--
-- Perangkap data per platform (lihat docs/data_dictionary):
--   Shopee : titik=ribuan, voucher level-order DIULANG di setiap baris SKU (jangan dijumlahkan!)
--   TikTok : waktu UTC (+7 jam), "Subtotal After Discount" sudah dikurangi voucher, ID bisa jadi '5.77E+17'
--   Lazada : angka desimal, tidak ada total baris (qty rusak tidak bisa dihitung ulang), bulan Inggris
--   Blibli : tanggal MM/DD/YYYY 12 jam, delimiter ';', voucher level-order hanya di baris pertama
-- =====================================================================================
SET search_path = etl, public;

DROP TABLE IF EXISTS etl.orders_parsed CASCADE;
CREATE TABLE etl.orders_parsed AS
WITH shp AS (
    SELECT 'SHP'::text AS platform_code, s._src_file AS src_file, s._row_id AS src_row_id,
           md5((to_jsonb(s) - '_src_file' - '_loaded_at' - '_row_id')::text) AS row_hash,
           etl.clean_txt(s.order_no) AS order_id,
           etl.parse_ts(s.created_at_txt, 'DD/MM/YYYY HH24:MI') AS order_ts,
           s.order_status AS status_raw, s.sku_raw, etl.clean_txt(s.product_name) AS title_raw,
           etl.num_plain(s.qty) AS qty_raw,
           CASE WHEN etl.num_plain(s.qty) > 0 THEN etl.num_plain(s.qty)
                ELSE round(etl.num_id(s.product_total) / NULLIF(etl.num_id(s.price_after_discount), 0)) END AS qty,   -- repair: total / harga satuan
           etl.num_id(s.original_price) AS unit_list, etl.num_id(s.price_after_discount) AS unit_sell, etl.num_id(s.product_total) AS line_gmv,
           NULL::numeric AS sv_line, NULL::numeric AS pv_line,
           coalesce(etl.num_id(s.seller_voucher), 0) AS sv_ord, coalesce(etl.num_id(s.shopee_voucher), 0) AS pv_ord, 'ORDER_REPEATED'::text AS voucher_grain,
           coalesce(etl.num_id(s.buyer_shipping_fee), 0) AS ship_fee,
           etl.clean_txt(s.buyer_username) AS buyer_user, etl.clean_txt(s.phone) AS phone, etl.clean_txt(s.city) AS city_raw, etl.clean_txt(s.payment_method) AS payment_method,
           etl.clean_txt(s.seller_voucher_code) AS sv_code, etl.clean_txt(s.platform_voucher_code) AS pv_code, NULL::text AS subchannel, NULL::boolean AS is_live
    FROM stg.orders_shopee s),
ttk AS (
    SELECT 'TTK', s._src_file, s._row_id,
           md5((to_jsonb(s) - '_src_file' - '_loaded_at' - '_row_id')::text),
           etl.clean_txt(s.order_id),
           etl.parse_ts(s.created_time_utc, 'YYYY-MM-DD HH24:MI:SS') + interval '7 hours',                                  -- UTC -> WIB
           s.order_status, s.sku_raw, etl.clean_txt(s.product_name), etl.num_plain(s.qty),
           CASE WHEN etl.num_plain(s.qty) > 0 THEN etl.num_plain(s.qty)
                ELSE round(etl.num_plain(s.subtotal_before_discount) / NULLIF(etl.num_plain(s.unit_original_price), 0)) END,
           etl.num_plain(s.unit_original_price), NULL::numeric,
           etl.num_plain(s.subtotal_after_discount) + coalesce(etl.num_plain(s.seller_voucher_discount), 0) + coalesce(etl.num_plain(s.platform_voucher_discount), 0), -- subtotal after sudah net voucher
           coalesce(etl.num_plain(s.seller_voucher_discount), 0), coalesce(etl.num_plain(s.platform_voucher_discount), 0), NULL::numeric, NULL::numeric, 'LINE',
           coalesce(etl.num_plain(s.shipping_fee), 0),
           etl.clean_txt(s.buyer_username), etl.clean_txt(s.phone), etl.clean_txt(s.city), etl.clean_txt(s.payment_method),
           etl.clean_txt(s.seller_voucher_code), etl.clean_txt(s.platform_voucher_code), etl.clean_txt(s.source), (upper(btrim(s.is_livestream)) = 'Y')
    FROM stg.orders_tiktok s),
lzd AS (
    SELECT 'LZD', s._src_file, s._row_id,
           md5((to_jsonb(s) - '_src_file' - '_loaded_at' - '_row_id')::text),
           etl.clean_txt(s.order_id),
           etl.parse_ts(s.create_time_txt, 'DD Mon YYYY HH24:MI'),
           s.status, s.sku_raw, etl.clean_txt(s.item_name), etl.num_plain(s.qty),
           CASE WHEN etl.num_plain(s.qty) > 0 THEN etl.num_plain(s.qty) END,                                                -- tidak ada total baris -> tidak bisa direpair
           etl.num_plain(s.unit_price), etl.num_plain(s.promo_price),
           etl.num_plain(s.promo_price) * etl.num_plain(s.qty),
           coalesce(etl.num_plain(s.seller_voucher), 0), coalesce(etl.num_plain(s.platform_voucher), 0), NULL::numeric, NULL::numeric, 'LINE',
           coalesce(etl.num_plain(s.shipping_fee), 0),
           etl.clean_txt(s.customer_name), etl.clean_txt(s.phone), etl.clean_txt(s.city), etl.clean_txt(s.payment_method),
           etl.clean_txt(s.seller_voucher_code), etl.clean_txt(s.platform_voucher_code), NULL::text, NULL::boolean
    FROM stg.orders_lazada s),
bli AS (
    SELECT 'BLI', s._src_file, s._row_id,
           md5((to_jsonb(s) - '_src_file' - '_loaded_at' - '_row_id')::text),
           etl.clean_txt(s.order_no),
           etl.parse_ts(s.order_date_txt, 'MM/DD/YYYY HH12:MI:SS AM'),
           s.status, s.sku_raw, etl.clean_txt(s.product_name), etl.num_plain(s.qty),
           CASE WHEN etl.num_plain(s.qty) > 0 THEN etl.num_plain(s.qty)
                ELSE round((etl.num_id(s.total) + etl.num_id(s.item_discount)) / NULLIF(etl.num_id(s.price), 0)) END,       -- (total + diskon) / harga list
           etl.num_id(s.price), NULL::numeric, etl.num_id(s.total), NULL::numeric, NULL::numeric,
           coalesce(etl.num_id(s.order_voucher_merchant), 0), coalesce(etl.num_id(s.order_voucher_blibli), 0), 'ORDER_FIRST_ROW',
           coalesce(etl.num_id(s.shipping), 0),
           etl.clean_txt(s.customer), etl.clean_txt(s.phone), etl.clean_txt(s.city), etl.clean_txt(s.payment),
           etl.clean_txt(s.merchant_voucher_code), etl.clean_txt(s.blibli_voucher_code), NULL::text, NULL::boolean
    FROM stg.orders_blibli s)
SELECT u.platform_code, u.src_file, u.src_row_id, u.row_hash, u.order_id, u.order_ts, u.status_raw, u.sku_raw, u.title_raw, u.qty_raw, u.qty, u.unit_list,
       coalesce(u.unit_sell, round(u.line_gmv / NULLIF(u.qty, 0))) AS unit_sell, u.line_gmv, u.sv_line, u.pv_line, u.sv_ord, u.pv_ord, u.voucher_grain, u.ship_fee,
       u.buyer_user, u.phone, u.city_raw, u.payment_method, u.sv_code, u.pv_code, u.subchannel, u.is_live
FROM (SELECT * FROM shp UNION ALL SELECT * FROM ttk UNION ALL SELECT * FROM lzd UNION ALL SELECT * FROM bli) u;

-- ---------------------------------------------------------------- klasifikasi
DROP TABLE IF EXISTS etl.orders_classified CASCADE;
CREATE TABLE etl.orders_classified AS
SELECT p.*,
       coalesce(etl.norm_sku(p.sku_raw), lm.sku) AS sku,
       CASE WHEN etl.norm_sku(p.sku_raw) IS NOT NULL THEN 'SKU_FIELD' WHEN lm.sku IS NOT NULL THEN 'LISTING_TITLE' END AS sku_source,
       sm.status_clean,
       row_number() OVER (PARTITION BY p.platform_code, p.row_hash ORDER BY p.src_file, p.src_row_id) AS dup_rank,
       CASE
           WHEN row_number() OVER (PARTITION BY p.platform_code, p.row_hash ORDER BY p.src_file, p.src_row_id) > 1 THEN 'EXACT_DUPLICATE'
           WHEN p.order_id ~* '^TEST-' OR lower(coalesce(p.buyer_user, '')) LIKE '%test%' THEN 'TEST_ORDER'
           WHEN p.order_id ~ '^[0-9]\.[0-9]+E\+[0-9]+$' THEN 'ORDER_ID_CORRUPTED_SCIENTIFIC'
           WHEN p.order_ts IS NULL THEN 'TIMESTAMP_UNPARSEABLE'
           WHEN coalesce(etl.norm_sku(p.sku_raw), lm.sku) IS NULL THEN 'SKU_UNRESOLVED'
           WHEN p.qty IS NULL OR p.qty <= 0 THEN 'QTY_INVALID_UNRECOVERABLE'
           WHEN sm.status_clean IS NULL THEN 'STATUS_UNMAPPED'
       END AS reject_reason
FROM etl.orders_parsed p
LEFT JOIN dwh.dim_listing lm ON lm.platform_code = p.platform_code AND lm.pack_qty = 1 AND lm.listing_title = p.title_raw
LEFT JOIN etl.status_map sm ON sm.platform_code = p.platform_code AND sm.status_key = lower(btrim(p.status_raw));
CREATE INDEX ON etl.orders_classified (platform_code, order_id);

-- ---------------------------------------------------------------- quarantine (domain ORDERS)
DELETE FROM ops.quarantine_row WHERE domain = 'ORDERS';
INSERT INTO ops.quarantine_row (domain, platform_code, src_file, src_row_id, reason, business_key, payload)
SELECT 'ORDERS', c.platform_code, c.src_file, c.src_row_id, c.reject_reason, c.order_id,
       jsonb_build_object('order_id', c.order_id, 'sku_raw', c.sku_raw, 'title', c.title_raw, 'qty_raw', c.qty_raw, 'line_gmv', c.line_gmv, 'buyer', c.buyer_user, 'status_raw', c.status_raw)
FROM etl.orders_classified c WHERE c.reject_reason IS NOT NULL;

-- ---------------------------------------------------------------- baris bersih + alokasi voucher
DROP TABLE IF EXISTS dwh.fact_order_line CASCADE;
CREATE TABLE dwh.fact_order_line AS
WITH v AS (
    SELECT * FROM etl.orders_classified WHERE reject_reason IS NULL),
agg AS (
    SELECT platform_code, order_id,
           CASE WHEN bool_or(voucher_grain = 'LINE') THEN sum(sv_line) ELSE max(sv_ord) END AS sv_total,
           CASE WHEN bool_or(voucher_grain = 'LINE') THEN sum(pv_line) ELSE max(pv_ord) END AS pv_total,
           max(ship_fee) AS ship_fee,                         -- Shopee diulang per baris; lainnya hanya baris pertama -> MAX benar untuk keduanya
           sum(line_gmv) AS ord_gmv
    FROM v GROUP BY 1, 2),
l AS (
    SELECT v.*, row_number() OVER (PARTITION BY v.platform_code, v.order_id ORDER BY v.sku) AS line_no,
           a.sv_total, a.pv_total, a.ord_gmv
    FROM v JOIN agg a USING (platform_code, order_id))
SELECT l.platform_code, l.order_id, l.line_no, l.order_ts, l.order_ts::date AS order_date, l.sku, l.sku_source,
       l.qty::int AS qty, l.unit_list::int AS unit_list_price, l.unit_sell AS unit_sell_price,
       (l.unit_list * l.qty)::bigint AS line_list_gmv, l.line_gmv::bigint AS line_gmv,
       -- alokasi voucher: level-baris dipakai apa adanya; level-order dialokasikan proporsional (sisa pembulatan ke baris pertama)
       (CASE WHEN l.voucher_grain = 'LINE' THEN l.sv_line
             ELSE floor(l.sv_total * l.line_gmv / l.ord_gmv)
                  + CASE WHEN l.line_no = 1 THEN l.sv_total - sum(floor(l.sv_total * l.line_gmv / l.ord_gmv)) OVER (PARTITION BY l.platform_code, l.order_id) ELSE 0 END END)::bigint AS seller_voucher_alloc,
       (CASE WHEN l.voucher_grain = 'LINE' THEN l.pv_line
             ELSE floor(l.pv_total * l.line_gmv / l.ord_gmv)
                  + CASE WHEN l.line_no = 1 THEN l.pv_total - sum(floor(l.pv_total * l.line_gmv / l.ord_gmv)) OVER (PARTITION BY l.platform_code, l.order_id) ELSE 0 END END)::bigint AS platform_voucher_alloc,
       l.status_clean AS status, l.qty_raw <= 0 AS qty_repaired, l.src_file
FROM l;
ALTER TABLE dwh.fact_order_line ADD PRIMARY KEY (platform_code, order_id, line_no);
CREATE UNIQUE INDEX ON dwh.fact_order_line (platform_code, order_id, sku);
CREATE INDEX ON dwh.fact_order_line (order_date, platform_code);
CREATE INDEX ON dwh.fact_order_line (sku);

-- ---------------------------------------------------------------- level order
DROP TABLE IF EXISTS dwh.fact_order CASCADE;
CREATE TABLE dwh.fact_order AS
WITH ol AS (
    SELECT platform_code, order_id, min(order_ts) AS order_ts, min(status) AS status, count(*) AS n_lines, sum(qty) AS units,
           sum(line_list_gmv) AS gmv_list, sum(line_gmv) AS gmv_placed, sum(seller_voucher_alloc) AS seller_voucher_amt, sum(platform_voucher_alloc) AS platform_voucher_amt
    FROM dwh.fact_order_line GROUP BY 1, 2),
at AS (   -- atribut level order dari baris bersih (nilai sama di semua baris order)
    SELECT DISTINCT ON (c.platform_code, c.order_id) c.platform_code, c.order_id, c.buyer_user, c.phone, c.city_raw, c.payment_method, c.sv_code, c.pv_code, c.subchannel, c.is_live,
           max(c.ship_fee) OVER (PARTITION BY c.platform_code, c.order_id) AS ship_fee
    FROM etl.orders_classified c WHERE c.reject_reason IS NULL ORDER BY c.platform_code, c.order_id, c.src_row_id)
SELECT o.platform_code, o.order_id, o.order_ts, o.order_ts::date AS order_date, extract(hour FROM o.order_ts)::int AS order_hour, o.status,
       a.subchannel, coalesce(a.is_live, false) AS is_livestream,
       a.buyer_user, a.phone AS phone_masked, o.platform_code || '|' || coalesce(a.buyer_user, '') || '|' || coalesce(a.phone, '') AS buyer_key,
       coalesce(cr.city, 'Tidak Diketahui') AS city, coalesce(dc.province, 'Tidak Diketahui') AS province, coalesce(dc.region, 'Tidak Diketahui') AS region, a.payment_method,
       a.sv_code AS seller_voucher_code, a.pv_code AS platform_voucher_code,
       o.n_lines, o.units, o.gmv_list, o.gmv_placed, o.seller_voucher_amt, o.platform_voucher_amt, a.ship_fee AS shipping_fee,
       (o.gmv_placed - o.seller_voucher_amt) AS net_sales_after_seller_voucher,
       (o.gmv_placed - o.seller_voucher_amt - o.platform_voucher_amt) AS customer_paid_items,
       (o.status NOT IN ('CANCELLED', 'RETURNED')) AS is_valid_sale,
       (o.status = 'COMPLETED') AS is_completed
FROM ol o
JOIN at a USING (platform_code, order_id)
LEFT JOIN etl.city_resolved cr ON cr.city_key = etl.norm_key(a.city_raw)
LEFT JOIN dwh.dim_city dc ON dc.city = cr.city;
ALTER TABLE dwh.fact_order ADD PRIMARY KEY (platform_code, order_id);
CREATE INDEX ON dwh.fact_order (order_date, platform_code);
CREATE INDEX ON dwh.fact_order (buyer_key, order_ts);
CREATE INDEX ON dwh.fact_order (phone_masked, city);
CREATE INDEX ON dwh.fact_order (seller_voucher_code) WHERE seller_voucher_code IS NOT NULL;
CREATE INDEX ON dwh.fact_order (platform_voucher_code) WHERE platform_voucher_code IS NOT NULL;

-- ---------------------------------------------------------------- ringkasan
SELECT 'raw_rows' AS metrik, count(*)::text AS nilai FROM etl.orders_parsed
UNION ALL SELECT 'clean_lines', count(*)::text FROM dwh.fact_order_line
UNION ALL SELECT 'clean_orders', count(*)::text FROM dwh.fact_order
UNION ALL SELECT 'quarantine:' || reason, count(*)::text FROM ops.quarantine_row WHERE domain = 'ORDERS' GROUP BY reason
UNION ALL SELECT 'sku_dari_judul', count(*)::text FROM dwh.fact_order_line WHERE sku_source = 'LISTING_TITLE'
UNION ALL SELECT 'qty_direpair', count(*)::text FROM dwh.fact_order_line WHERE qty_repaired;
