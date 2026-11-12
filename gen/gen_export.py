"""Tahap 4: tulis CSV mentah 'kotor' per platform + master + kunci jawaban."""
import pickle, shutil
from common import *

rng = np.random.default_rng(44)
D = pickle.load(open(f"{BUILD}/orders.pkl", "rb")); F = pickle.load(open(f"{BUILD}/fin.pkl", "rb")); M_ = pickle.load(open(f"{BUILD}/monitor.pkl", "rb"))
O, L, V, VIOL, camps = D["O"], D["L"], D["V"], D["VIOL"], D["camps"]
RAW = f"{ROOT}/data/raw"; KEY = f"{ROOT}/answer_key"
for d in (RAW, KEY):
    if os.path.isdir(d):
        shutil.rmtree(d)
for sub in ["orders/shopee", "orders/tiktok_tokopedia", "orders/lazada", "orders/blibli", "ads", "voucher", "promo", "jbp", "contract", "settlement", "program", "erp", "monitoring", "master"]:
    os.makedirs(f"{RAW}/{sub}", exist_ok=True)
os.makedirs(KEY, exist_ok=True)
dirty_log = []  # (platform, dirt_type, n_rows)


def log(p, t, n):
    dirty_log.append((p, t, int(n)))


def fid(n):  # 49900 -> '49.900'
    return f"{int(n):,}".replace(",", ".")


FOLDER = {"SHP": "shopee", "TTK": "tiktok_tokopedia", "LZD": "lazada", "BLI": "blibli"}
PLAT_VAR = {"SHP": ["Shopee", "Shopee", "SHOPEE", "Shopee ID", "shopee "], "TTK": ["TikTok Shop", "Tokopedia", "TikTok Shop & Tokopedia", "TIKTOK SHOP", "Tokopedia "],
            "LZD": ["Lazada", "Lazada", "LAZADA", "Lazada ID"], "BLI": ["Blibli", "Blibli", "BLIBLI", "blibli.com"]}

# ------------------------------------------------------------ gabungkan baris + order (kebenaran bersih)
X = L.drop(columns=["platform_code"]).merge(O.drop(columns=["ord_sub"]), on="order_id").merge(O[["order_id", "ord_sub"]], on="order_id")
X["platform_code"] = X.order_id.map(O.set_index("order_id").platform_code)
X["age"] = (END - X.ts.dt.normalize()).dt.days


def alloc(col):
    a = np.floor(X[col] * X.line_sell / X.ord_sub)
    resid = X[col] - a.groupby(X.order_id).transform("sum")
    a = a.where(X.line_no != 1, a + resid)
    return a.astype(int)


X["sv_alloc"] = alloc("seller_voucher_amt"); X["pv_alloc"] = alloc("platform_voucher_amt")
title = M_["LISTMAP"][M_["LISTMAP"].pack_qty == 1].set_index(["platform_code", "sku"]).listing_title.to_dict()
X["title"] = [title[(p, s)] for p, s in zip(X.platform_code, X.sku)]

# ------------------------------------------------------------ kunci: ringkasan KPI bersih
X["month"] = X.ts.dt.strftime("%Y-%m")
kp = X.groupby(["platform_code", "month"]).agg(order_lines=("line_no", "size"), gmv_placed=("line_sell", "sum"), gross_list_gmv=("line_list", "sum")).reset_index()
Oo = O.assign(month=O.ts.dt.strftime("%Y-%m"))
ordc = Oo.groupby(["platform_code", "month"]).agg(orders_placed=("order_id", "size")).reset_index()
comp = Oo[Oo.status == "COMPLETED"].groupby(["platform_code", "month"]).agg(orders_completed=("order_id", "size"), net_gmv=("ord_sub", "sum"), seller_voucher_completed=("seller_voucher_amt", "sum"), platform_voucher_completed=("platform_voucher_amt", "sum")).reset_index()
GTK = kp.merge(ordc, on=["platform_code", "month"]).merge(comp, on=["platform_code", "month"], how="left")
GTK.to_csv(f"{KEY}/gt_monthly_kpi_clean.csv", index=False)

# ------------------------------------------------------------ baris uji (test order) + id TikTok ber-notasi ilmiah
tests = []
for p in PLATS:
    t = X[X.platform_code == p].sample(12, random_state=5).copy()
    t["order_id"] = [f"TEST-{p}-{i:04d}" for i in range(len(t))]; t["user"] = rng.choice(["test_qa_buyer", "TEST BUYER", "tester_seller"], len(t))
    t["unit_sell"] = 100; t["unit_list"] = 100; t["line_sell"] = t.qty * 100; t["sv_alloc"] = 0; t["pv_alloc"] = 0
    t["seller_voucher_amt"] = 0; t["platform_voucher_amt"] = 0; t["status"] = "COMPLETED"
    tests.append(t); log(p, "TEST_ORDER_ROWS", len(t))
XR = pd.concat([X, pd.concat(tests)], ignore_index=True)
XR["raw_order_id"] = XR.order_id
ttk_ord = O[O.platform_code == "TTK"].sample(frac=.0008, random_state=9).order_id
sci = {o: f"{int(o):.2E}" for o in ttk_ord}
XR.loc[XR.order_id.isin(sci), "raw_order_id"] = XR.loc[XR.order_id.isin(sci), "order_id"].map(sci)
log("TTK", "ORDER_ID_SCIENTIFIC_NOTATION_ORDERS", len(sci))
pd.DataFrame({"order_id_true": list(sci), "order_id_in_raw": list(sci.values())}).to_csv(f"{KEY}/gt_ttk_order_id_corrupted.csv", index=False)


def sku_dirty(s):
    r = rng.random(len(s))
    out = s.copy()
    m1 = r < .01; out[m1] = out[m1].str.lower()
    m2 = (r >= .01) & (r < .02); out[m2] = out[m2].str.replace("-", "", regex=False)
    m3 = (r >= .02) & (r < .03); out[m3] = out[m3] + " "
    m4 = (r >= .03) & (r < .0315); out[m4] = ""
    return out, int(m1.sum()), int(m2.sum()), int(m3.sum()), int(m4.sum())


def title_dirty(t):
    r = rng.random(len(t)); out = t.copy()
    m = r < .02; out[m] = "  " + out[m] + " "
    m2 = (r >= .02) & (r < .03); out[m2] = out[m2].str.replace(" ", "  ", n=1, regex=False)
    return out


def status_dirty(s):
    r = rng.random(len(s)); out = s.copy()
    m = r < .015; out[m] = out[m].str.upper()
    m2 = (r >= .015) & (r < .03); out[m2] = " " + out[m2] + " "
    return out


def build_orders(p):
    d = XR[XR.platform_code == p].copy().reset_index(drop=True)
    n = len(d)
    sk, a, b, c, e = sku_dirty(d.sku)
    log(p, "SKU_LOWERCASE", a); log(p, "SKU_NO_HYPHEN", b); log(p, "SKU_TRAILING_SPACE", c); log(p, "SKU_BLANK_TITLE_ONLY", e)
    qty = d.qty.astype(str)
    jm = rng.random(n) < .0005
    qty[jm] = rng.choice(["0", "-1"], jm.sum()); log(p, "QTY_ZERO_OR_NEGATIVE", jm.sum())
    ttl = title_dirty(d.title)
    if p == "SHP":
        st = d.status.map({"COMPLETED": "Selesai", "SHIPPED": "Sedang Dikirim", "TO_SHIP": "Perlu Dikirim", "CANCELLED": "Batal", "RETURNED": "Pengembalian"})
        df = pd.DataFrame({
            "No. Pesanan": d.raw_order_id, "Status Pesanan": status_dirty(st), "Waktu Pesanan Dibuat": d.ts.dt.strftime("%d/%m/%Y %H:%M"),
            "SKU Induk": sk, "Nama Produk": ttl, "Harga Awal": d.unit_list.map(fid), "Harga Setelah Diskon": d.unit_sell.map(fid), "Jumlah": qty,
            "Total Harga Produk": d.line_sell.map(fid), "Diskon dari Penjual": ((d.unit_list - d.unit_sell) * d.qty).map(fid),
            "Voucher Penjual": d.seller_voucher_amt.map(fid), "Voucher Shopee": d.platform_voucher_amt.map(fid),  # level order: berulang di tiap baris
            "Ongkos Kirim Dibayar Pembeli": d.shipping_fee.map(fid), "Kota/Kabupaten": d.city_raw, "Username (Pembeli)": d.user, "No. Telepon": d.phone,
            "Metode Pembayaran": d.payment_method, "Kode Voucher Penjual": d.seller_voucher_code, "Kode Voucher Shopee": d.platform_voucher_code})
        for col in ["Voucher Penjual", "Voucher Shopee"]:
            z = rng.random(n) < .5
            df.loc[(d.seller_voucher_amt == 0) & z if col == "Voucher Penjual" else (d.platform_voucher_amt == 0) & z, col] = ""
    elif p == "TTK":
        st = d.status.map({"COMPLETED": "Completed", "SHIPPED": "In transit", "TO_SHIP": "Awaiting shipment", "CANCELLED": "Cancelled", "RETURNED": "Returned"})
        dl = (d.status == "COMPLETED") & (d.age <= 7) & (rng.random(n) < .4); st[dl] = "Delivered"
        utc = d.ts - pd.Timedelta(hours=7)  # TikTok mengekspor waktu dalam UTC
        df = pd.DataFrame({
            "Order ID": d.raw_order_id, "Order Status": status_dirty(st), "Created Time": utc.dt.strftime("%Y-%m-%d %H:%M:%S"), "Seller SKU": sk, "Product Name": ttl,
            "SKU Unit Original Price": d.unit_list, "SKU Subtotal Before Discount": d.unit_list * d.qty, "SKU Seller Discount": (d.unit_list - d.unit_sell) * d.qty,
            "Seller Voucher Discount": d.sv_alloc, "Platform Voucher Discount": d.pv_alloc, "SKU Subtotal After Discount": d.line_sell - d.sv_alloc - d.pv_alloc,
            "Quantity": qty, "Shipping Fee": np.where(d.line_no == 1, d.shipping_fee, 0), "Buyer Username": d.user, "Recipient Phone": d.phone, "Regency and City": d.city_raw,
            "Source": d.subchannel, "Is Livestream": np.where(d.is_live, "Y", "N"), "Payment Method": d.payment_method,
            "Seller Voucher Code": d.seller_voucher_code, "Platform Voucher Code": d.platform_voucher_code})
    elif p == "LZD":
        st = d.status.map({"COMPLETED": "delivered", "SHIPPED": "shipped", "TO_SHIP": "pending", "CANCELLED": "canceled", "RETURNED": "returned"})
        item_id = [str(x) for x in rng.integers(10**15, 10**16, n)]
        df = pd.DataFrame({
            "orderItemId": item_id, "orderId": d.raw_order_id, "createTime": d.ts.dt.strftime("%d %b %Y %H:%M"), "status": status_dirty(st), "sellerSku": sk, "itemName": ttl,
            "unitPrice": d.unit_list.map(lambda v: f"{v:.2f}"), "promoPrice": d.unit_sell.map(lambda v: f"{v:.2f}"), "quantity": qty,
            "sellerVoucher": d.sv_alloc.map(lambda v: f"{v:.2f}"), "platformVoucher": d.pv_alloc.map(lambda v: f"{v:.2f}"),
            "paidPrice": ((d.line_sell - d.sv_alloc - d.pv_alloc) / d.qty.replace(0, 1)).map(lambda v: f"{v:.2f}"),
            "shippingFee": np.where(d.line_no == 1, d.shipping_fee, 0), "customerName": d.user, "shippingPhone": d.phone, "shippingCity": d.city_raw,
            "paymentMethod": d.payment_method, "voucherCodeSeller": d.seller_voucher_code, "voucherCodePlatform": d.platform_voucher_code})
    else:
        st = d.status.map({"COMPLETED": "Selesai", "SHIPPED": "Dikirim", "TO_SHIP": "Diproses", "CANCELLED": "Dibatalkan", "RETURNED": "Retur"})
        first = d.line_no == 1
        df = pd.DataFrame({
            "Order No": d.raw_order_id, "Order Date": d.ts.dt.strftime("%m/%d/%Y %I:%M:%S %p"), "Status": status_dirty(st), "Merchant SKU": sk, "Product Name": ttl,
            "Price": d.unit_list.map(lambda v: "Rp " + fid(v)), "Qty": qty, "Item Discount": ((d.unit_list - d.unit_sell) * d.qty).map(lambda v: "Rp " + fid(v)),
            "Total": d.line_sell.map(lambda v: "Rp " + fid(v)),
            "Order Voucher Merchant": np.where(first, d.seller_voucher_amt.map(lambda v: "Rp " + fid(v)), ""),  # level order: hanya baris pertama
            "Order Voucher Blibli": np.where(first, d.platform_voucher_amt.map(lambda v: "Rp " + fid(v)), ""),
            "Shipping": np.where(first, d.shipping_fee.map(lambda v: "Rp " + fid(v)), ""), "Customer": d.user, "Phone": d.phone, "City": d.city_raw, "Payment": d.payment_method,
            "Merchant Voucher Code": d.seller_voucher_code, "Blibli Voucher Code": d.platform_voucher_code})
    return df, d.ts


for p in PLATS:
    df, ts = build_orders(p)
    key = ts.dt.strftime("%Y-%m")
    months = sorted(key.unique())
    dup_next = df.sample(frac=.003, random_state=12)
    for m in months:
        part = df[key == m]
        dups = part.sample(frac=.004, random_state=3)
        nxt = dup_next[key.loc[dup_next.index] == m]
        extra = pd.concat([dups, nxt]) if m != months[-1] else dups
        # tambahan: duplikat silang-bulan masuk ke file bulan berikutnya
        prev_m = months[months.index(m) - 1] if months.index(m) > 0 else None
        cross = dup_next[key.loc[dup_next.index] == prev_m] if prev_m else df.iloc[0:0]
        out = pd.concat([part, dups, cross]).sample(frac=1, random_state=7).reset_index(drop=True)
        sep = ";" if p == "BLI" else ","
        out.to_csv(f"{RAW}/orders/{FOLDER[p]}/orders_{FOLDER[p]}_{m}.csv", index=False, sep=sep, encoding="utf-8")
        log(p, "EXACT_DUPLICATE_ROWS_SAME_FILE", len(dups)); log(p, "EXACT_DUPLICATE_ROWS_CROSS_FILE", len(cross))
    print(p, "raw rows", len(df))

# ------------------------------------------------------------ iklan
A = F["ADS"].copy()
n = len(A)
pl = A.platform_code.map(lambda p: PLAT_VAR[p][int(rng.integers(0, len(PLAT_VAR[p])))] if rng.random() < .25 else PLAT_VAR[p][0])


def datef(row_p, d):
    return {"SHP": d.strftime("%d-%m-%Y"), "TTK": d.strftime("%Y-%m-%d"), "LZD": d.strftime("%d %b %Y"), "BLI": d.strftime("%m/%d/%Y")}[row_p]


def numf(p, v):
    return {"SHP": "Rp" + fid(v), "TTK": str(int(v)), "LZD": f"{v:.2f}", "BLI": fid(v)}[p]


ad = pd.DataFrame({"Date": [datef(p, d) for p, d in zip(A.platform_code, A.date)], "Platform": pl, "Ad Type": A.ad_type, "Campaign Name": A.campaign_name,
                   "Impressions": A.impressions, "Clicks": A.clicks, "Spend": [numf(p, v) for p, v in zip(A.platform_code, A.spend)], "Ad Orders": A.ad_orders,
                   "Ad GMV": [numf(p, v) for p, v in zip(A.platform_code, A.ad_gmv)]})
bad = rng.random(n)
m1 = bad < .001; ad.loc[m1, "Clicks"] = ad.loc[m1, "Impressions"] + rng.integers(1, 500, m1.sum()); log("ALL", "ADS_CLICKS_GT_IMPRESSIONS", m1.sum())
m2 = (bad >= .001) & (bad < .003); ad.loc[m2, "Spend"] = "0"; log("ALL", "ADS_SPEND_ZERO_WITH_CLICKS", m2.sum())
m3 = (bad >= .003) & (bad < .0035); ad.loc[m3, "Spend"] = "-" + ad.loc[m3, "Spend"].astype(str); log("ALL", "ADS_NEGATIVE_SPEND_ADJUSTMENT", m3.sum())
ad_d = ad.sample(frac=.003, random_state=4); log("ALL", "ADS_EXACT_DUPLICATES", len(ad_d))
pd.concat([ad, ad_d]).sample(frac=1, random_state=2).to_csv(f"{RAW}/ads/raw_ads_all_platforms.csv", index=False)
F["ADS_GAP"].to_csv(f"{KEY}/gt_ads_missing_days.csv", index=False)

# ------------------------------------------------------------ master / kontrak / kampanye / voucher
Vo = V.drop(columns=["ignore_quota", "late_days", "end_eff", "group", "used"]).copy()
Vo["platform"] = Vo.platform_code.map(PNAME); Vo = Vo.drop(columns=["platform_code"])
Vo["start_date"] = Vo.start_date.dt.strftime("%Y-%m-%d"); Vo["end_date"] = Vo.end_date.dt.strftime("%Y-%m-%d")
Vo = Vo[["voucher_code", "platform", "voucher_type", "funding_model", "seller_share_pct", "discount_kind", "discount_value", "max_discount", "min_spend", "quota", "budget_idr", "start_date", "end_date", "campaign_id"]]
Vo.to_csv(f"{RAW}/voucher/raw_voucher_master.csv", index=False)
cc = camps.copy(); cc["platform"] = cc.platform_code.map(PNAME)
cc["start_date"] = cc.start_date.dt.strftime("%Y-%m-%d"); cc["end_date"] = cc.end_date.dt.strftime("%Y-%m-%d")
cc[["platform", "campaign_id", "campaign_name", "campaign_type", "start_date", "end_date", "allows_deep_discount"]].to_csv(f"{RAW}/promo/raw_campaign_calendar.csv", index=False)
J = F["JBP"].copy(); J["platform"] = J.platform_code.map(PNAME)
J.drop(columns=["platform_code"])[["agreement_id", "platform", "program_code", "period_type", "valid_from", "valid_to", "metric", "tier1_threshold", "tier1_rate_pct", "tier2_threshold", "tier2_rate_pct", "cap_amount", "campaign_scope", "notes"]].to_csv(f"{RAW}/jbp/raw_jbp_agreement.csv", index=False)
fc = F["fee_contract"].copy(); fc["platform"] = fc.platform_code.map(PNAME)
fc.drop(columns=["platform_code"])[["platform", "commission_pct", "service_fee_pct", "payment_fee_pct", "valid_from", "valid_to"]].to_csv(f"{RAW}/contract/raw_platform_fee_contract.csv", index=False)
S = F["STMT"].copy(); S["platform"] = S.platform_code.map(PNAME)
S["paid_amount"] = [("Rp " + fid(v)) if i % 3 == 0 else str(v) for i, v in enumerate(S.paid_amount)]
for c in ("period_start", "period_end", "paid_date"):
    S[c] = S[c].dt.strftime("%Y-%m-%d")
S[["statement_id", "platform", "program_code", "period_label", "period_start", "period_end", "paid_amount", "paid_date", "remarks"]].to_csv(f"{RAW}/program/raw_program_statement.csv", index=False)
E = F["ERP"].copy()
E["channel"] = E.platform_code.map({"SHP": "SHOPEE", "TTK": "TOKPED/TIKTOK", "LZD": "LAZADA", "BLI": "BLIBLI"})
E["ship_date"] = E.ship_date.dt.strftime("%Y-%m-%d")
E.rename(columns={"order_id": "order_ref", "ord_sub": "gross_amount", "seller_voucher_amt": "disc_amount"})[["erp_doc_no", "channel", "order_ref", "ship_date", "gross_amount", "disc_amount", "net_amount"]].to_csv(f"{RAW}/erp/raw_internal_erp_sales.csv", index=False)

# settlement
ST = F["SETTLE"].copy()
for p in PLATS:
    s = ST[ST.platform_code == p].sort_values("settle_date")
    sd = s.settle_date
    if p == "SHP":
        out = pd.DataFrame({"No. Pesanan": s.order_id, "Tanggal Dana Dilepaskan": sd.dt.strftime("%d/%m/%Y"), "Harga Produk": s.ord_sub.map(fid),
                            "Voucher Penjual": (-s.seller_voucher_amt).map(lambda v: ("-" + fid(-v)) if v < 0 else "0"), "Voucher Shopee (Disubsidi)": s.pv_credit.map(fid),
                            "Biaya Administrasi": (-s.commission_fee).map(lambda v: "-" + fid(-v)), "Biaya Layanan": (-s.service_fee).map(lambda v: "-" + fid(-v)),
                            "Biaya Proses Pesanan": (-s.payment_fee).map(lambda v: "-" + fid(-v)), "Selisih Ongkir": s.ship_adj.map(lambda v: ("-" + fid(-v)) if v < 0 else "0"),
                            "Total Penghasilan": s.net_payout.map(fid)})
    elif p == "TTK":
        out = pd.DataFrame({"Order/adjustment ID": s.order_id, "Settlement time": (sd + pd.Timedelta(hours=3)).dt.strftime("%Y-%m-%dT%H:%M:%SZ"), "Total Revenue": s.ord_sub,
                            "Seller discount": s.seller_voucher_amt, "Platform voucher subsidy": s.pv_credit, "Commission fee": s.commission_fee, "Service fee": s.service_fee,
                            "Payment fee": s.payment_fee, "Shipping adjustment": s.ship_adj, "Total settlement amount": s.net_payout})
    elif p == "LZD":
        out = pd.DataFrame({"orderNumber": s.order_id, "statementDate": sd.dt.strftime("%d %b %Y"), "itemRevenue": s.ord_sub.map(lambda v: f"{v:.2f}"),
                            "sellerVoucher": (-s.seller_voucher_amt).map(lambda v: f"{v:.2f}"), "lazadaVoucherSubsidy": s.pv_credit.map(lambda v: f"{v:.2f}"),
                            "commission": (-s.commission_fee).map(lambda v: f"{v:.2f}"), "serviceFee": (-s.service_fee).map(lambda v: f"{v:.2f}"),
                            "paymentFee": (-s.payment_fee).map(lambda v: f"{v:.2f}"), "shippingDiff": s.ship_adj.map(lambda v: f"{v:.2f}"), "payout": s.net_payout.map(lambda v: f"{v:.2f}")})
    else:
        rp = lambda v: "Rp " + fid(v)
        out = pd.DataFrame({"Nomor Order": s.order_id, "Tgl Settlement": sd.dt.strftime("%m/%d/%Y"), "Penjualan": s.ord_sub.map(rp), "Voucher Merchant": s.seller_voucher_amt.map(rp),
                            "Subsidi Blibli": s.pv_credit.map(rp), "Komisi": s.commission_fee.map(rp), "Biaya Layanan": s.service_fee.map(rp), "Biaya Pembayaran": s.payment_fee.map(rp),
                            "Selisih Ongkir": s.ship_adj.map(lambda v: ("-Rp " + fid(-v)) if v < 0 else "Rp 0"), "Total Dibayarkan": s.net_payout.map(rp)})
    out.to_csv(f"{RAW}/settlement/raw_settlement_{FOLDER[p]}.csv", index=False)

# monitoring harga
MM = M_["M"].copy()
keep = rng.random(len(MM)) > .015; log("ALL", "MONITOR_MISSING_SNAPSHOT_ROWS", (~keep).sum()); MM = MM[keep]
p_str = lambda v: "Rp " + fid(v)
pf = rng.random(len(MM))
price_txt = np.where(pf < .5, MM.price_displayed.map(str), np.where(pf < .85, MM.price_displayed.map(p_str), MM.price_displayed.map(lambda v: f"{v:,}")))
strike_txt = np.where(pf < .5, MM.price_strike.map(str), np.where(pf < .85, MM.price_strike.map(p_str), MM.price_strike.map(lambda v: f"{v:,}")))
pr = pd.Series(price_txt, index=MM.index); nz = rng.random(len(MM)); pr[nz < .004] = ""; pr[(nz >= .004) & (nz < .005)] = "0"
log("ALL", "MONITOR_NULL_PRICE", int((nz < .004).sum())); log("ALL", "MONITOR_ZERO_PRICE", int(((nz >= .004) & (nz < .005)).sum()))
tsf = {"SHP": "%Y-%m-%d %H:%M:%S", "TTK": "%Y-%m-%dT%H:%M:%S+07:00", "LZD": "%d/%m/%Y %H:%M", "BLI": "%Y-%m-%d %H:%M:%S"}
ts_txt = [pd.Timestamp(t).strftime(tsf[p]) for t, p in zip(MM.snapshot_ts, MM.platform_code)]
seller = MM.seller_name.copy(); sr = rng.random(len(MM)); seller[sr < .01] = seller[sr < .01].str.upper(); seller[(sr >= .01) & (sr < .02)] = seller[(sr >= .01) & (sr < .02)] + " "
mon = pd.DataFrame({"snapshot_ts": ts_txt, "platform": [PLAT_VAR[p][0] for p in MM.platform_code], "seller_name": seller, "listing_id": MM.listing_id,
                    "price_displayed": pr, "price_strike": strike_txt, "promo_label": MM.promo_label, "stock_qty": MM.stock_qty})
mon["month"] = pd.DatetimeIndex(MM.snapshot_ts).strftime("%Y-%m")
for m, g in mon.groupby("month"):
    dd = g.drop(columns="month")
    dd = pd.concat([dd, dd.sample(frac=.003, random_state=5)]).sample(frac=1, random_state=1)
    dd.to_csv(f"{RAW}/monitoring/raw_price_monitor_{m}.csv", index=False)

# master
sk_out = sku[["sku", "product_name", "sub_category", "rrp", "cogs", "map_floor", "campaign_floor"]].rename(columns={"rrp": "rrp_idr", "cogs": "cogs_idr", "map_floor": "map_floor_idr", "campaign_floor": "campaign_floor_idr"})
sk_out.to_csv(f"{RAW}/master/sku_master.csv", index=False)
lm = M_["LISTMAP"].copy(); lm["platform"] = lm.platform_code.map(PNAME)
lm[["platform", "listing_id", "sku", "pack_qty", "listing_title"]].to_csv(f"{RAW}/master/listing_map.csv", index=False)
M_["AUTH"].to_csv(f"{RAW}/master/authorized_sellers.csv", index=False)
city_alias_table().to_csv(f"{RAW}/master/ref_city_alias.csv", index=False)

# ------------------------------------------------------------ kunci jawaban
GA = O[O.scenario != ""][["platform_code", "order_id", "scenario", "cluster_id", "ts", "user", "phone", "city_canon", "ord_sub", "status"]]
GA.to_csv(f"{KEY}/gt_order_anomalies.csv", index=False)
VIOL.to_csv(f"{KEY}/gt_voucher_violations.csv", index=False)
M_["GT"].to_csv(f"{KEY}/gt_price_violations.csv", index=False)
F["GT_SET"].to_csv(f"{KEY}/gt_settlement_discrepancies.csv", index=False)
F["GT_PROG"].to_csv(f"{KEY}/gt_program_discrepancies.csv", index=False)
pd.DataFrame(dirty_log, columns=["platform_code", "dirt_type", "n"]).groupby(["platform_code", "dirt_type"], as_index=False).n.sum().to_csv(f"{KEY}/gt_dirty_injection_summary.csv", index=False)
print("export selesai")
