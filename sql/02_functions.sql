-- =====================================================================================
-- 02_functions.sql : fungsi bantu parsing/normalisasi + tabel pemetaan status.
-- Semua fungsi bertipe SQL murni (IMMUTABLE) supaya bisa di-inline oleh planner = cepat.
-- =====================================================================================
SET search_path = etl, public;

-- Waktu dinding (WIB, tanpa zona) dari teks. to_timestamp() menganggap zona sesi; AT TIME ZONE zona sesi
-- mengembalikan jam dinding yang sama -> hasil tidak tergantung setelan TimeZone server/klien.
CREATE OR REPLACE FUNCTION etl.parse_ts(txt text, fmt text) RETURNS timestamp
LANGUAGE sql STABLE PARALLEL SAFE AS $$
    SELECT CASE WHEN btrim(coalesce(txt, '')) = '' THEN NULL
                ELSE to_timestamp(btrim(txt), fmt) AT TIME ZONE current_setting('TimeZone') END
$$;

-- Angka format Indonesia: 'Rp 49.900', '49.900', '-15.000', '-Rp 3.000', 'Rp1.234.500' -> numeric (titik = ribuan)
CREATE OR REPLACE FUNCTION etl.num_id(txt text) RETURNS numeric
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE WHEN btrim(coalesce(txt, '')) = '' THEN NULL
                ELSE (CASE WHEN txt ~ '^\s*-' THEN -1 ELSE 1 END)
                     * NULLIF(regexp_replace(txt, '[^0-9]', '', 'g'), '')::numeric END
$$;

-- Angka polos / desimal titik: '88100', '24200.00', '-1', 'Rp 0' (tanda minus dipertahankan)
CREATE OR REPLACE FUNCTION etl.num_plain(txt text) RETURNS numeric
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT NULLIF(regexp_replace(coalesce(txt, ''), '[^0-9.\-]', '', 'g'), '')::numeric
$$;

-- Angka dengan koma ribuan ('39,900') atau polos
CREATE OR REPLACE FUNCTION etl.num_comma(txt text) RETURNS numeric
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT NULLIF(regexp_replace(coalesce(txt, ''), '[^0-9\-]', '', 'g'), '')::numeric
$$;

-- Normalisasi SKU: ' skn001 ', 'SKN-001 ', 'skn-001' -> 'SKN-001' ; selain pola 3 huruf + 3 angka -> NULL
CREATE OR REPLACE FUNCTION etl.norm_sku(txt text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE WHEN upper(regexp_replace(coalesce(txt, ''), '[^A-Za-z0-9]', '', 'g')) ~ '^[A-Z]{3}[0-9]{3}$'
                THEN regexp_replace(upper(regexp_replace(txt, '[^A-Za-z0-9]', '', 'g')), '^([A-Z]{3})([0-9]{3})$', '\1-\2') END
$$;

-- Rapikan teks: trim + kompres spasi ganda (termasuk NBSP)
CREATE OR REPLACE FUNCTION etl.clean_txt(txt text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT NULLIF(btrim(regexp_replace(coalesce(txt, ''), '[\s ]+', ' ', 'g')), '')
$$;

-- Kunci alias kota: huruf kecil, titik dibuang, spasi dirapikan ('Kota Adm. Jakarta Selatan' -> 'kota adm jakarta selatan')
CREATE OR REPLACE FUNCTION etl.norm_key(txt text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT btrim(regexp_replace(lower(replace(coalesce(txt, ''), '.', ' ')), '\s+', ' ', 'g'))
$$;

-- Teks platform bebas ('Shopee ID', 'TIKTOK SHOP', 'Tokopedia ', 'blibli.com') -> kode platform
CREATE OR REPLACE FUNCTION etl.platform_code(txt text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE WHEN lower(txt) LIKE '%shopee%' THEN 'SHP'
                WHEN lower(txt) LIKE '%tiktok%' OR lower(txt) LIKE '%tokopedia%' OR lower(txt) LIKE '%tokped%' THEN 'TTK'
                WHEN lower(txt) LIKE '%lazada%' THEN 'LZD'
                WHEN lower(txt) LIKE '%blibli%' THEN 'BLI' END
$$;

-- Pemetaan status lintas platform (tabel -> mudah dirawat tanpa mengubah kode)
DROP TABLE IF EXISTS etl.status_map;
CREATE TABLE etl.status_map (
    platform_code text NOT NULL,
    status_key    text NOT NULL,          -- lower(btrim(status mentah))
    status_clean  text NOT NULL CHECK (status_clean IN ('COMPLETED','SHIPPED','TO_SHIP','CANCELLED','RETURNED')),
    note          text,
    PRIMARY KEY (platform_code, status_key)
);
INSERT INTO etl.status_map VALUES
 ('SHP','selesai','COMPLETED',NULL), ('SHP','sedang dikirim','SHIPPED',NULL), ('SHP','perlu dikirim','TO_SHIP',NULL),
 ('SHP','batal','CANCELLED',NULL), ('SHP','pengembalian','RETURNED',NULL),
 ('TTK','completed','COMPLETED',NULL), ('TTK','delivered','COMPLETED','Delivered dianggap selesai untuk pelaporan GMV; settlement tetap menunggu rilis dana'),
 ('TTK','in transit','SHIPPED',NULL), ('TTK','awaiting shipment','TO_SHIP',NULL), ('TTK','cancelled','CANCELLED',NULL), ('TTK','returned','RETURNED',NULL),
 ('LZD','delivered','COMPLETED',NULL), ('LZD','shipped','SHIPPED',NULL), ('LZD','pending','TO_SHIP',NULL),
 ('LZD','canceled','CANCELLED','Ejaan satu-L'), ('LZD','returned','RETURNED',NULL),
 ('BLI','selesai','COMPLETED',NULL), ('BLI','dikirim','SHIPPED',NULL), ('BLI','diproses','TO_SHIP',NULL),
 ('BLI','dibatalkan','CANCELLED',NULL), ('BLI','retur','RETURNED',NULL);

-- Penilaian cepat: fungsi pengujian internal (dipanggil oleh 11_data_quality.sql)
CREATE OR REPLACE FUNCTION etl.selftest() RETURNS TABLE(test text, ok boolean) LANGUAGE sql AS $$
    VALUES ('num_id Rp',        etl.num_id('Rp 49.900') = 49900),
           ('num_id negatif',   etl.num_id('-15.000') = -15000),
           ('num_id -Rp',       etl.num_id('-Rp 3.000') = -3000),
           ('num_plain desimal',etl.num_plain('24200.00') = 24200),
           ('num_comma',        etl.num_comma('39,900') = 39900),
           ('norm_sku 1',       etl.norm_sku(' skn001 ') = 'SKN-001'),
           ('norm_sku 2',       etl.norm_sku('HCR-008 ') = 'HCR-008'),
           ('norm_sku kosong',  etl.norm_sku('') IS NULL),
           ('norm_key',         etl.norm_key('Kota Adm. Jakarta  Selatan') = 'kota adm jakarta selatan'),
           ('platform_code',    etl.platform_code('TIKTOK SHOP') = 'TTK' AND etl.platform_code('Shopee ID') = 'SHP'),
           ('parse_ts',         etl.parse_ts('06/03/2026 23:00','DD/MM/YYYY HH24:MI') = timestamp '2026-03-06 23:00'),
           ('parse_ts BLI',     etl.parse_ts('03/27/2026 08:57:26 AM','MM/DD/YYYY HH12:MI:SS AM') = timestamp '2026-03-27 08:57:26'),
           ('parse_ts LZD',     etl.parse_ts('21 Mar 2026 23:45','DD Mon YYYY HH24:MI') = timestamp '2026-03-21 23:45')
$$;
