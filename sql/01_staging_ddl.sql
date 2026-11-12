-- 01_staging_ddl.sql : tabel pendaratan (landing) mentah. SEMUA kolom bertipe TEXT agar tidak ada data hilang saat load.
-- Kolom meta: _src_file (nama file), _loaded_at, _row_id. Dibuat otomatis oleh gen/make_staging_ddl.py

SET search_path = stg, public;

DROP TABLE IF EXISTS stg.orders_shopee CASCADE;
CREATE TABLE stg.orders_shopee (
    order_no                     text,  -- No. Pesanan
    order_status                 text,  -- Status Pesanan
    created_at_txt               text,  -- Waktu Pesanan Dibuat
    sku_raw                      text,  -- SKU Induk
    product_name                 text,  -- Nama Produk
    original_price               text,  -- Harga Awal
    price_after_discount         text,  -- Harga Setelah Diskon
    qty                          text,  -- Jumlah
    product_total                text,  -- Total Harga Produk
    seller_discount              text,  -- Diskon dari Penjual
    seller_voucher               text,  -- Voucher Penjual
    shopee_voucher               text,  -- Voucher Shopee
    buyer_shipping_fee           text,  -- Ongkos Kirim Dibayar Pembeli
    city                         text,  -- Kota/Kabupaten
    buyer_username               text,  -- Username (Pembeli)
    phone                        text,  -- No. Telepon
    payment_method               text,  -- Metode Pembayaran
    seller_voucher_code          text,  -- Kode Voucher Penjual
    platform_voucher_code        text,  -- Kode Voucher Shopee
    _src_file                    text,
    _loaded_at                   timestamptz DEFAULT now(),
    _row_id                      bigserial
);

DROP TABLE IF EXISTS stg.orders_tiktok CASCADE;
CREATE TABLE stg.orders_tiktok (
    order_id                     text,  -- Order ID
    order_status                 text,  -- Order Status
    created_time_utc             text,  -- Created Time
    sku_raw                      text,  -- Seller SKU
    product_name                 text,  -- Product Name
    unit_original_price          text,  -- SKU Unit Original Price
    subtotal_before_discount     text,  -- SKU Subtotal Before Discount
    seller_discount              text,  -- SKU Seller Discount
    seller_voucher_discount      text,  -- Seller Voucher Discount
    platform_voucher_discount    text,  -- Platform Voucher Discount
    subtotal_after_discount      text,  -- SKU Subtotal After Discount
    qty                          text,  -- Quantity
    shipping_fee                 text,  -- Shipping Fee
    buyer_username               text,  -- Buyer Username
    phone                        text,  -- Recipient Phone
    city                         text,  -- Regency and City
    source                       text,  -- Source
    is_livestream                text,  -- Is Livestream
    payment_method               text,  -- Payment Method
    seller_voucher_code          text,  -- Seller Voucher Code
    platform_voucher_code        text,  -- Platform Voucher Code
    _src_file                    text,
    _loaded_at                   timestamptz DEFAULT now(),
    _row_id                      bigserial
);

DROP TABLE IF EXISTS stg.orders_lazada CASCADE;
CREATE TABLE stg.orders_lazada (
    order_item_id                text,  -- orderItemId
    order_id                     text,  -- orderId
    create_time_txt              text,  -- createTime
    status                       text,  -- status
    sku_raw                      text,  -- sellerSku
    item_name                    text,  -- itemName
    unit_price                   text,  -- unitPrice
    promo_price                  text,  -- promoPrice
    qty                          text,  -- quantity
    seller_voucher               text,  -- sellerVoucher
    platform_voucher             text,  -- platformVoucher
    paid_price                   text,  -- paidPrice
    shipping_fee                 text,  -- shippingFee
    customer_name                text,  -- customerName
    phone                        text,  -- shippingPhone
    city                         text,  -- shippingCity
    payment_method               text,  -- paymentMethod
    seller_voucher_code          text,  -- voucherCodeSeller
    platform_voucher_code        text,  -- voucherCodePlatform
    _src_file                    text,
    _loaded_at                   timestamptz DEFAULT now(),
    _row_id                      bigserial
);

DROP TABLE IF EXISTS stg.orders_blibli CASCADE;
CREATE TABLE stg.orders_blibli (
    order_no                     text,  -- Order No
    order_date_txt               text,  -- Order Date
    status                       text,  -- Status
    sku_raw                      text,  -- Merchant SKU
    product_name                 text,  -- Product Name
    price                        text,  -- Price
    qty                          text,  -- Qty
    item_discount                text,  -- Item Discount
    total                        text,  -- Total
    order_voucher_merchant       text,  -- Order Voucher Merchant
    order_voucher_blibli         text,  -- Order Voucher Blibli
    shipping                     text,  -- Shipping
    customer                     text,  -- Customer
    phone                        text,  -- Phone
    city                         text,  -- City
    payment                      text,  -- Payment
    merchant_voucher_code        text,  -- Merchant Voucher Code
    blibli_voucher_code          text,  -- Blibli Voucher Code
    _src_file                    text,
    _loaded_at                   timestamptz DEFAULT now(),
    _row_id                      bigserial
);

DROP TABLE IF EXISTS stg.ads CASCADE;
CREATE TABLE stg.ads (
    ad_date_txt                  text,  -- Date
    platform_txt                 text,  -- Platform
    ad_type                      text,  -- Ad Type
    campaign_name                text,  -- Campaign Name
    impressions                  text,  -- Impressions
    clicks                       text,  -- Clicks
    spend                        text,  -- Spend
    ad_orders                    text,  -- Ad Orders
    ad_gmv                       text,  -- Ad GMV
    _src_file                    text,
    _loaded_at                   timestamptz DEFAULT now(),
    _row_id                      bigserial
);

DROP TABLE IF EXISTS stg.voucher_master CASCADE;
CREATE TABLE stg.voucher_master (
    voucher_code                 text,  -- voucher_code
    platform_txt                 text,  -- platform
    voucher_type                 text,  -- voucher_type
    funding_model                text,  -- funding_model
    seller_share_pct             text,  -- seller_share_pct
    discount_kind                text,  -- discount_kind
    discount_value               text,  -- discount_value
    max_discount                 text,  -- max_discount
    min_spend                    text,  -- min_spend
    quota                        text,  -- quota
    budget_idr                   text,  -- budget_idr
    start_date                   text,  -- start_date
    end_date                     text,  -- end_date
    campaign_id                  text,  -- campaign_id
    _src_file                    text,
    _loaded_at                   timestamptz DEFAULT now(),
    _row_id                      bigserial
);

DROP TABLE IF EXISTS stg.campaign_calendar CASCADE;
CREATE TABLE stg.campaign_calendar (
    platform_txt                 text,  -- platform
    campaign_id                  text,  -- campaign_id
    campaign_name                text,  -- campaign_name
    campaign_type                text,  -- campaign_type
    start_date                   text,  -- start_date
    end_date                     text,  -- end_date
    allows_deep_discount         text,  -- allows_deep_discount
    _src_file                    text,
    _loaded_at                   timestamptz DEFAULT now(),
    _row_id                      bigserial
);

DROP TABLE IF EXISTS stg.jbp_agreement CASCADE;
CREATE TABLE stg.jbp_agreement (
    agreement_id                 text,  -- agreement_id
    platform_txt                 text,  -- platform
    program_code                 text,  -- program_code
    period_type                  text,  -- period_type
    valid_from                   text,  -- valid_from
    valid_to                     text,  -- valid_to
    metric                       text,  -- metric
    tier1_threshold              text,  -- tier1_threshold
    tier1_rate_pct               text,  -- tier1_rate_pct
    tier2_threshold              text,  -- tier2_threshold
    tier2_rate_pct               text,  -- tier2_rate_pct
    cap_amount                   text,  -- cap_amount
    campaign_scope               text,  -- campaign_scope
    notes                        text,  -- notes
    _src_file                    text,
    _loaded_at                   timestamptz DEFAULT now(),
    _row_id                      bigserial
);

DROP TABLE IF EXISTS stg.fee_contract CASCADE;
CREATE TABLE stg.fee_contract (
    platform_txt                 text,  -- platform
    commission_pct               text,  -- commission_pct
    service_fee_pct              text,  -- service_fee_pct
    payment_fee_pct              text,  -- payment_fee_pct
    valid_from                   text,  -- valid_from
    valid_to                     text,  -- valid_to
    _src_file                    text,
    _loaded_at                   timestamptz DEFAULT now(),
    _row_id                      bigserial
);

DROP TABLE IF EXISTS stg.settlement_shopee CASCADE;
CREATE TABLE stg.settlement_shopee (
    order_ref                    text,  -- No. Pesanan
    settle_date_txt              text,  -- Tanggal Dana Dilepaskan
    gross_item_amt               text,  -- Harga Produk
    seller_voucher               text,  -- Voucher Penjual
    platform_voucher_credit      text,  -- Voucher Shopee (Disubsidi)
    commission_fee               text,  -- Biaya Administrasi
    service_fee                  text,  -- Biaya Layanan
    payment_fee                  text,  -- Biaya Proses Pesanan
    shipping_adj                 text,  -- Selisih Ongkir
    net_payout                   text,  -- Total Penghasilan
    _src_file                    text,
    _loaded_at                   timestamptz DEFAULT now(),
    _row_id                      bigserial
);

DROP TABLE IF EXISTS stg.settlement_tiktok CASCADE;
CREATE TABLE stg.settlement_tiktok (
    order_ref                    text,  -- Order/adjustment ID
    settle_date_txt              text,  -- Settlement time
    gross_item_amt               text,  -- Total Revenue
    seller_voucher               text,  -- Seller discount
    platform_voucher_credit      text,  -- Platform voucher subsidy
    commission_fee               text,  -- Commission fee
    service_fee                  text,  -- Service fee
    payment_fee                  text,  -- Payment fee
    shipping_adj                 text,  -- Shipping adjustment
    net_payout                   text,  -- Total settlement amount
    _src_file                    text,
    _loaded_at                   timestamptz DEFAULT now(),
    _row_id                      bigserial
);

DROP TABLE IF EXISTS stg.settlement_lazada CASCADE;
CREATE TABLE stg.settlement_lazada (
    order_ref                    text,  -- orderNumber
    settle_date_txt              text,  -- statementDate
    gross_item_amt               text,  -- itemRevenue
    seller_voucher               text,  -- sellerVoucher
    platform_voucher_credit      text,  -- lazadaVoucherSubsidy
    commission_fee               text,  -- commission
    service_fee                  text,  -- serviceFee
    payment_fee                  text,  -- paymentFee
    shipping_adj                 text,  -- shippingDiff
    net_payout                   text,  -- payout
    _src_file                    text,
    _loaded_at                   timestamptz DEFAULT now(),
    _row_id                      bigserial
);

DROP TABLE IF EXISTS stg.settlement_blibli CASCADE;
CREATE TABLE stg.settlement_blibli (
    order_ref                    text,  -- Nomor Order
    settle_date_txt              text,  -- Tgl Settlement
    gross_item_amt               text,  -- Penjualan
    seller_voucher               text,  -- Voucher Merchant
    platform_voucher_credit      text,  -- Subsidi Blibli
    commission_fee               text,  -- Komisi
    service_fee                  text,  -- Biaya Layanan
    payment_fee                  text,  -- Biaya Pembayaran
    shipping_adj                 text,  -- Selisih Ongkir
    net_payout                   text,  -- Total Dibayarkan
    _src_file                    text,
    _loaded_at                   timestamptz DEFAULT now(),
    _row_id                      bigserial
);

DROP TABLE IF EXISTS stg.program_statement CASCADE;
CREATE TABLE stg.program_statement (
    statement_id                 text,  -- statement_id
    platform_txt                 text,  -- platform
    program_code                 text,  -- program_code
    period_label                 text,  -- period_label
    period_start                 text,  -- period_start
    period_end                   text,  -- period_end
    paid_amount                  text,  -- paid_amount
    paid_date                    text,  -- paid_date
    remarks                      text,  -- remarks
    _src_file                    text,
    _loaded_at                   timestamptz DEFAULT now(),
    _row_id                      bigserial
);

DROP TABLE IF EXISTS stg.erp_sales CASCADE;
CREATE TABLE stg.erp_sales (
    erp_doc_no                   text,  -- erp_doc_no
    channel                      text,  -- channel
    order_ref                    text,  -- order_ref
    ship_date                    text,  -- ship_date
    gross_amount                 text,  -- gross_amount
    disc_amount                  text,  -- disc_amount
    net_amount                   text,  -- net_amount
    _src_file                    text,
    _loaded_at                   timestamptz DEFAULT now(),
    _row_id                      bigserial
);

DROP TABLE IF EXISTS stg.price_monitor CASCADE;
CREATE TABLE stg.price_monitor (
    snapshot_ts_txt              text,  -- snapshot_ts
    platform_txt                 text,  -- platform
    seller_name                  text,  -- seller_name
    listing_id                   text,  -- listing_id
    price_displayed              text,  -- price_displayed
    price_strike                 text,  -- price_strike
    promo_label                  text,  -- promo_label
    stock_qty                    text,  -- stock_qty
    _src_file                    text,
    _loaded_at                   timestamptz DEFAULT now(),
    _row_id                      bigserial
);

DROP TABLE IF EXISTS stg.sku_master CASCADE;
CREATE TABLE stg.sku_master (
    sku                          text,  -- sku
    product_name                 text,  -- product_name
    sub_category                 text,  -- sub_category
    rrp_idr                      text,  -- rrp_idr
    cogs_idr                     text,  -- cogs_idr
    map_floor_idr                text,  -- map_floor_idr
    campaign_floor_idr           text,  -- campaign_floor_idr
    _src_file                    text,
    _loaded_at                   timestamptz DEFAULT now(),
    _row_id                      bigserial
);

DROP TABLE IF EXISTS stg.listing_map CASCADE;
CREATE TABLE stg.listing_map (
    platform_txt                 text,  -- platform
    listing_id                   text,  -- listing_id
    sku                          text,  -- sku
    pack_qty                     text,  -- pack_qty
    listing_title                text,  -- listing_title
    _src_file                    text,
    _loaded_at                   timestamptz DEFAULT now(),
    _row_id                      bigserial
);

DROP TABLE IF EXISTS stg.authorized_sellers CASCADE;
CREATE TABLE stg.authorized_sellers (
    seller_name                  text,  -- seller_name
    authorization_status         text,  -- authorization_status
    _src_file                    text,
    _loaded_at                   timestamptz DEFAULT now(),
    _row_id                      bigserial
);

DROP TABLE IF EXISTS stg.ref_city_alias CASCADE;
CREATE TABLE stg.ref_city_alias (
    alias_key                    text,  -- alias_key
    city                         text,  -- city
    province                     text,  -- province
    region                       text,  -- region
    _src_file                    text,
    _loaded_at                   timestamptz DEFAULT now(),
    _row_id                      bigserial
);

-- registri file untuk loader idempoten (skip file yang sama, reload jika checksum berubah)
CREATE SCHEMA IF NOT EXISTS etl;
CREATE TABLE IF NOT EXISTS etl.file_registry (
    file_path    text PRIMARY KEY,
    stream       text NOT NULL,
    sha256       text NOT NULL,
    rows_loaded  bigint NOT NULL,
    loaded_at    timestamptz NOT NULL DEFAULT now()
);
-- Tabel stg baru saja dibuat ulang (kosong) -> registri harus direset agar loader memuat ulang semua file.
TRUNCATE etl.file_registry;
