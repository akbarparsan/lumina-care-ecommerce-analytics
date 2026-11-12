"""Membuat sql/01_staging_ddl.sql dari definisi kolom (diverifikasi terhadap header CSV)."""
import csv, glob, os
ROOT = "/home/claude/ecom_portfolio"
RAW = f"{ROOT}/data/raw"
SETTLE = ["order_ref", "settle_date_txt", "gross_item_amt", "seller_voucher", "platform_voucher_credit", "commission_fee", "service_fee", "payment_fee", "shipping_adj", "net_payout"]
STG = {
    "orders_shopee": (["order_no", "order_status", "created_at_txt", "sku_raw", "product_name", "original_price", "price_after_discount", "qty", "product_total", "seller_discount",
                       "seller_voucher", "shopee_voucher", "buyer_shipping_fee", "city", "buyer_username", "phone", "payment_method", "seller_voucher_code", "platform_voucher_code"],
                      "orders/shopee/*.csv", ","),
    "orders_tiktok": (["order_id", "order_status", "created_time_utc", "sku_raw", "product_name", "unit_original_price", "subtotal_before_discount", "seller_discount",
                       "seller_voucher_discount", "platform_voucher_discount", "subtotal_after_discount", "qty", "shipping_fee", "buyer_username", "phone", "city", "source",
                       "is_livestream", "payment_method", "seller_voucher_code", "platform_voucher_code"], "orders/tiktok_tokopedia/*.csv", ","),
    "orders_lazada": (["order_item_id", "order_id", "create_time_txt", "status", "sku_raw", "item_name", "unit_price", "promo_price", "qty", "seller_voucher", "platform_voucher",
                       "paid_price", "shipping_fee", "customer_name", "phone", "city", "payment_method", "seller_voucher_code", "platform_voucher_code"], "orders/lazada/*.csv", ","),
    "orders_blibli": (["order_no", "order_date_txt", "status", "sku_raw", "product_name", "price", "qty", "item_discount", "total", "order_voucher_merchant", "order_voucher_blibli",
                       "shipping", "customer", "phone", "city", "payment", "merchant_voucher_code", "blibli_voucher_code"], "orders/blibli/*.csv", ";"),
    "ads": (["ad_date_txt", "platform_txt", "ad_type", "campaign_name", "impressions", "clicks", "spend", "ad_orders", "ad_gmv"], "ads/*.csv", ","),
    "voucher_master": (["voucher_code", "platform_txt", "voucher_type", "funding_model", "seller_share_pct", "discount_kind", "discount_value", "max_discount", "min_spend", "quota",
                        "budget_idr", "start_date", "end_date", "campaign_id"], "voucher/*.csv", ","),
    "campaign_calendar": (["platform_txt", "campaign_id", "campaign_name", "campaign_type", "start_date", "end_date", "allows_deep_discount"], "promo/*.csv", ","),
    "jbp_agreement": (["agreement_id", "platform_txt", "program_code", "period_type", "valid_from", "valid_to", "metric", "tier1_threshold", "tier1_rate_pct", "tier2_threshold",
                       "tier2_rate_pct", "cap_amount", "campaign_scope", "notes"], "jbp/*.csv", ","),
    "fee_contract": (["platform_txt", "commission_pct", "service_fee_pct", "payment_fee_pct", "valid_from", "valid_to"], "contract/*.csv", ","),
    "settlement_shopee": (SETTLE, "settlement/raw_settlement_shopee.csv", ","),
    "settlement_tiktok": (SETTLE, "settlement/raw_settlement_tiktok_tokopedia.csv", ","),
    "settlement_lazada": (SETTLE, "settlement/raw_settlement_lazada.csv", ","),
    "settlement_blibli": (SETTLE, "settlement/raw_settlement_blibli.csv", ","),
    "program_statement": (["statement_id", "platform_txt", "program_code", "period_label", "period_start", "period_end", "paid_amount", "paid_date", "remarks"], "program/*.csv", ","),
    "erp_sales": (["erp_doc_no", "channel", "order_ref", "ship_date", "gross_amount", "disc_amount", "net_amount"], "erp/*.csv", ","),
    "price_monitor": (["snapshot_ts_txt", "platform_txt", "seller_name", "listing_id", "price_displayed", "price_strike", "promo_label", "stock_qty"], "monitoring/*.csv", ","),
    "sku_master": (["sku", "product_name", "sub_category", "rrp_idr", "cogs_idr", "map_floor_idr", "campaign_floor_idr"], "master/sku_master.csv", ","),
    "listing_map": (["platform_txt", "listing_id", "sku", "pack_qty", "listing_title"], "master/listing_map.csv", ","),
    "authorized_sellers": (["seller_name", "authorization_status"], "master/authorized_sellers.csv", ","),
    "ref_city_alias": (["alias_key", "city", "province", "region"], "master/ref_city_alias.csv", ","),
}
out = ["-- 01_staging_ddl.sql : tabel pendaratan (landing) mentah. SEMUA kolom bertipe TEXT agar tidak ada data hilang saat load.",
       "-- Kolom meta: _src_file (nama file), _loaded_at, _row_id. Dibuat otomatis oleh gen/make_staging_ddl.py\n", "SET search_path = stg, public;\n"]
for t, (cols, pat, sep) in STG.items():
    files = sorted(glob.glob(f"{RAW}/{pat}"))
    assert files, (t, pat)
    with open(files[0], encoding="utf-8", newline="") as f:
        hdr = next(csv.reader(f, delimiter=sep))
    assert len(hdr) == len(cols), (t, len(hdr), len(cols), hdr)
    out.append(f"DROP TABLE IF EXISTS stg.{t} CASCADE;")
    out.append(f"CREATE TABLE stg.{t} (")
    for c, h in zip(cols, hdr):
        out.append(f"    {c:<28} text,  -- {h}")
    out.append("    _src_file                    text,")
    out.append("    _loaded_at                   timestamptz DEFAULT now(),")
    out.append("    _row_id                      bigserial")
    out.append(");\n")
out.append("""-- registri file untuk loader idempoten (skip file yang sama, reload jika checksum berubah)
CREATE SCHEMA IF NOT EXISTS etl;
CREATE TABLE IF NOT EXISTS etl.file_registry (
    file_path    text PRIMARY KEY,
    stream       text NOT NULL,
    sha256       text NOT NULL,
    rows_loaded  bigint NOT NULL,
    loaded_at    timestamptz NOT NULL DEFAULT now()
);
-- Tabel stg baru saja dibuat ulang (kosong) -> registri harus direset agar loader memuat ulang semua file.
TRUNCATE etl.file_registry;""")
open(f"{ROOT}/sql/01_staging_ddl.sql", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("ok", len(STG), "tabel staging")
