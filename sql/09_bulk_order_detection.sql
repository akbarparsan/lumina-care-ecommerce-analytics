-- =====================================================================================
-- 09_bulk_order_detection.sql : deteksi order mencurigakan / bulk (rule-based + skor risiko)
--   R1 BULK_QTY        : qty satu baris >= 12 atau total unit order >= 12
--   R2 VELOCITY_BURST  : pembeli yang sama >= 5 order dalam rantai jeda <= 60 menit (gaps-and-islands)
--   R3 ACCOUNT_FARM    : nomor telepon (masked) + kota yang sama dipakai >= 3 username berbeda
--   R4 PRICE_ANOMALY   : harga satuan < 50% MAP (kemungkinan salah harga yang dieksploitasi)
--   R5 VOUCHER_ABUSE   : order melanggar aturan voucher (min-spend / kedaluwarsa / kuota)
-- Skor = jumlah bobot rule yang menyala; level: CRITICAL >= 80, HIGH >= 50, MEDIUM >= 30, LOW lainnya
-- =====================================================================================
SET search_path = ops, public;

CREATE TABLE IF NOT EXISTS ops.suspicious_rule (rule_code text PRIMARY KEY, weight int NOT NULL, description text NOT NULL, threshold text);
INSERT INTO ops.suspicious_rule VALUES
 ('R1_BULK_QTY', 40, 'Qty besar dalam satu order (indikasi reseller/penimbun)', 'qty baris >= 12 atau unit order >= 12'),
 ('R2_VELOCITY_BURST', 35, 'Pembeli sama memesan berulang dalam waktu singkat', '>= 5 order, jeda berurutan <= 60 menit'),
 ('R3_ACCOUNT_FARM', 40, 'Banyak akun berbagi telepon + kota yang sama', '>= 3 username per (telepon masked, kota)'),
 ('R4_PRICE_ANOMALY', 50, 'Harga satuan jauh di bawah MAP', 'unit_sell_price < 50% MAP'),
 ('R5_VOUCHER_ABUSE', 15, 'Order melanggar aturan voucher', 'min-spend / kedaluwarsa / over-kuota')
ON CONFLICT (rule_code) DO UPDATE SET weight = EXCLUDED.weight, description = EXCLUDED.description, threshold = EXCLUDED.threshold;

-- R1
CREATE OR REPLACE VIEW ops.v_rule_r1_bulk AS
SELECT platform_code, order_id, max(qty) AS max_line_qty, sum(qty) AS total_units
FROM dwh.fact_order_line GROUP BY 1, 2 HAVING max(qty) >= 12 OR sum(qty) >= 12;

-- R2 : island per pembeli; jeda > 60 menit memutus rantai
CREATE OR REPLACE VIEW ops.v_rule_r2_velocity AS
WITH o AS (
    SELECT platform_code, order_id, buyer_key, order_ts,
           CASE WHEN lag(order_ts) OVER w IS NULL OR order_ts - lag(order_ts) OVER w > interval '60 minutes' THEN 1 ELSE 0 END AS new_island
    FROM dwh.fact_order WINDOW w AS (PARTITION BY platform_code, buyer_key ORDER BY order_ts, order_id)),
isl AS (SELECT *, sum(new_island) OVER (PARTITION BY platform_code, buyer_key ORDER BY order_ts, order_id ROWS UNBOUNDED PRECEDING) AS island_no FROM o),
agg AS (SELECT *, count(*) OVER (PARTITION BY platform_code, buyer_key, island_no) AS orders_in_burst,
               max(order_ts) OVER (PARTITION BY platform_code, buyer_key, island_no) - min(order_ts) OVER (PARTITION BY platform_code, buyer_key, island_no) AS burst_span
        FROM isl)
SELECT platform_code, order_id, buyer_key, island_no, orders_in_burst, burst_span FROM agg WHERE orders_in_burst >= 5;

-- R3
CREATE OR REPLACE VIEW ops.v_rule_r3_farm AS
WITH grp AS (
    SELECT platform_code, phone_masked, city, count(DISTINCT buyer_user) AS distinct_usernames, count(*) AS orders
    FROM dwh.fact_order GROUP BY 1, 2, 3 HAVING count(DISTINCT buyer_user) >= 3)
SELECT o.platform_code, o.order_id, g.phone_masked, g.city, g.distinct_usernames, g.orders AS orders_in_group
FROM dwh.fact_order o JOIN grp g ON g.platform_code = o.platform_code AND g.phone_masked = o.phone_masked AND g.city = o.city;

-- R4
CREATE OR REPLACE VIEW ops.v_rule_r4_price AS
SELECT l.platform_code, l.order_id, min(round(l.unit_sell_price / k.map_floor_idr, 3)) AS min_ratio_to_map, sum((k.map_floor_idr - l.unit_sell_price) * l.qty) AS leakage_idr
FROM dwh.fact_order_line l JOIN dwh.dim_sku k USING (sku)
WHERE l.unit_sell_price < 0.5 * k.map_floor_idr GROUP BY 1, 2;

-- R5
CREATE OR REPLACE VIEW ops.v_rule_r5_voucher AS
SELECT platform_code, order_id, string_agg(DISTINCT violation_type, ',') AS violations, sum(exposure_idr) AS exposure_idr
FROM ops.v_voucher_rule_violations GROUP BY 1, 2;

-- Gabungan + skor
CREATE OR REPLACE VIEW ops.v_suspicious_orders AS
SELECT o.platform_code, o.order_id, o.order_ts, o.status, o.buyer_user, o.phone_masked, o.city, o.units, o.gmv_placed,
       (r1.order_id IS NOT NULL) AS r1_bulk_qty, (r2.order_id IS NOT NULL) AS r2_velocity, (r3.order_id IS NOT NULL) AS r3_farm,
       (r4.order_id IS NOT NULL) AS r4_price, (r5.order_id IS NOT NULL) AS r5_voucher,
       (CASE WHEN r1.order_id IS NOT NULL THEN 40 ELSE 0 END + CASE WHEN r2.order_id IS NOT NULL THEN 35 ELSE 0 END + CASE WHEN r3.order_id IS NOT NULL THEN 40 ELSE 0 END
        + CASE WHEN r4.order_id IS NOT NULL THEN 50 ELSE 0 END + CASE WHEN r5.order_id IS NOT NULL THEN 15 ELSE 0 END) AS risk_score,
       r1.max_line_qty, r2.orders_in_burst, r3.distinct_usernames, r4.min_ratio_to_map, r5.violations AS voucher_violations
FROM dwh.fact_order o
LEFT JOIN ops.v_rule_r1_bulk r1 USING (platform_code, order_id)
LEFT JOIN ops.v_rule_r2_velocity r2 USING (platform_code, order_id)
LEFT JOIN ops.v_rule_r3_farm r3 USING (platform_code, order_id)
LEFT JOIN ops.v_rule_r4_price r4 USING (platform_code, order_id)
LEFT JOIN ops.v_rule_r5_voucher r5 USING (platform_code, order_id)
WHERE r1.order_id IS NOT NULL OR r2.order_id IS NOT NULL OR r3.order_id IS NOT NULL OR r4.order_id IS NOT NULL OR r5.order_id IS NOT NULL;

CREATE OR REPLACE VIEW ops.v_suspicious_orders_scored AS
SELECT *, CASE WHEN risk_score >= 80 THEN 'CRITICAL' WHEN risk_score >= 50 THEN 'HIGH' WHEN risk_score >= 30 THEN 'MEDIUM' ELSE 'LOW' END AS risk_level,
       concat_ws(' + ', CASE WHEN r1_bulk_qty THEN 'BULK_QTY' END, CASE WHEN r2_velocity THEN 'VELOCITY' END, CASE WHEN r3_farm THEN 'ACCOUNT_FARM' END,
                 CASE WHEN r4_price THEN 'PRICE_ANOMALY' END, CASE WHEN r5_voucher THEN 'VOUCHER' END) AS reasons
FROM ops.v_suspicious_orders;

-- Ringkasan kluster pembeli (satu baris per pembeli/telepon) untuk daftar investigasi
CREATE OR REPLACE VIEW ops.v_suspicious_buyer_clusters AS
SELECT platform_code, phone_masked, city, count(*) AS flagged_orders, count(DISTINCT buyer_user) AS usernames, sum(units) AS units, sum(gmv_placed) AS gmv,
       max(risk_score) AS max_risk, min(order_ts) AS first_seen, max(order_ts) AS last_seen, string_agg(DISTINCT reasons, ' | ') AS reasons
FROM ops.v_suspicious_orders_scored WHERE risk_level IN ('CRITICAL', 'HIGH', 'MEDIUM')
GROUP BY 1, 2, 3 ORDER BY max_risk DESC, gmv DESC;

-- Pemantauan "near-real-time": order mencurigakan dalam N jam terakhir relatif terhadap data terbaru
CREATE OR REPLACE VIEW ops.v_suspicious_last_24h AS
SELECT * FROM ops.v_suspicious_orders_scored
WHERE order_ts >= (SELECT max(order_ts) FROM dwh.fact_order) - interval '24 hours' ORDER BY risk_score DESC, order_ts DESC;

SELECT risk_level, count(*) AS orders, sum(gmv_placed) AS gmv FROM ops.v_suspicious_orders_scored GROUP BY 1 ORDER BY 1;
SELECT 'R1' r, count(*) FROM ops.v_rule_r1_bulk UNION ALL SELECT 'R2', count(*) FROM ops.v_rule_r2_velocity UNION ALL SELECT 'R3', count(*) FROM ops.v_rule_r3_farm
UNION ALL SELECT 'R4', count(*) FROM ops.v_rule_r4_price UNION ALL SELECT 'R5', count(*) FROM ops.v_rule_r5_voucher;
