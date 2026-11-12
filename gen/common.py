"""Modul bersama generator data sintetis e-commerce Personal Care (brand fiktif: Lumina Care).
Semua angka, tarif platform, dan kontrak JBP di sini FIKTIF dan hanya untuk latihan portofolio.
"""
import os
import numpy as np
import pandas as pd

ROOT = "/home/claude/ecom_portfolio"
BUILD = "/home/claude/ecom_build"  # file perantara (tidak ikut dikirim)
os.makedirs(BUILD, exist_ok=True)

START = pd.Timestamp("2026-01-01")
END = pd.Timestamp("2026-10-31")
DAYS = pd.date_range(START, END, freq="D")
ND = len(DAYS)

PLATS = ["SHP", "TTK", "LZD", "BLI"]
PNAME = {"SHP": "Shopee", "TTK": "TikTok Shop/Tokopedia", "LZD": "Lazada", "BLI": "Blibli"}
PIDX = {"SHP": 1.00, "TTK": 0.99, "LZD": 1.01, "BLI": 1.02}  # indeks harga list vs RRP
BASE_ORD = {"SHP": 80, "TTK": 55, "LZD": 28, "BLI": 17}
GROWTH = {"SHP": (0.85, 1.15), "TTK": (0.70, 1.45), "LZD": (0.95, 1.00), "BLI": (0.95, 1.05)}
CAMP_SCALE = {"SHP": 1.0, "TTK": 1.15, "LZD": 0.9, "BLI": 0.8}
VSCALE = {"SHP": 1.0, "TTK": 0.75, "LZD": 0.35, "BLI": 0.2}

# ---------------------------------------------------------------- SKU master
SKU_ROWS = [
    ("SKN-001", "Lumina Gentle Face Wash 100ml", "Skincare", 39900, .42, 10),
    ("SKN-002", "Lumina Gentle Face Wash 200ml", "Skincare", 69900, .41, 6),
    ("SKN-003", "Lumina Brightening Serum 30ml", "Skincare", 129000, .35, 7),
    ("SKN-004", "Lumina Niacinamide 10% Serum 20ml", "Skincare", 99000, .33, 9),
    ("SKN-005", "Lumina Hydra Gel Moisturizer 50g", "Skincare", 79000, .38, 8),
    ("SKN-006", "Lumina Barrier Repair Cream 30g", "Skincare", 109000, .36, 5),
    ("SKN-007", "Lumina Daily Sunscreen SPF50 40ml", "Skincare", 89000, .37, 12),
    ("SKN-008", "Lumina Sunscreen Stick SPF50 15g", "Skincare", 99000, .39, 4),
    ("SKN-009", "Lumina Micellar Water 300ml", "Skincare", 59000, .44, 6),
    ("SKN-010", "Lumina Calming Toner 150ml", "Skincare", 69000, .40, 5),
    ("SKN-011", "Lumina Acne Spot Gel 15g", "Skincare", 45000, .38, 6),
    ("SKN-012", "Lumina Lip Balm SPF15 4g", "Skincare", 29000, .45, 7),
    ("HCR-001", "Lumina Anti-Dandruff Shampoo 340ml", "Haircare", 52000, .50, 9),
    ("HCR-002", "Lumina Smooth Shine Shampoo 340ml", "Haircare", 49000, .50, 8),
    ("HCR-003", "Lumina Smooth Conditioner 340ml", "Haircare", 52000, .50, 5),
    ("HCR-004", "Lumina Repair Hair Serum 50ml", "Haircare", 59000, .40, 5),
    ("HCR-005", "Lumina Keratin Hair Mask 200g", "Haircare", 89000, .42, 4),
    ("HCR-006", "Lumina Anti Hair-Fall Tonic 100ml", "Haircare", 65000, .41, 4),
    ("HCR-007", "Lumina Dry Shampoo Spray 150ml", "Haircare", 69000, .45, 2),
    ("HCR-008", "Lumina Shampoo Refill 700ml", "Haircare", 79000, .52, 4),
    ("BDY-001", "Lumina Brightening Body Lotion 400ml", "Body Care", 59000, .46, 10),
    ("BDY-002", "Lumina Shea Butter Body Lotion 400ml", "Body Care", 59000, .46, 6),
    ("BDY-003", "Lumina Fresh Body Wash 450ml", "Body Care", 55000, .47, 8),
    ("BDY-004", "Lumina Milk Body Wash 450ml", "Body Care", 55000, .47, 6),
    ("BDY-005", "Lumina Deodorant Roll-On 50ml", "Body Care", 35000, .43, 9),
    ("BDY-006", "Lumina Deodorant Spray 150ml", "Body Care", 45000, .43, 5),
    ("BDY-007", "Lumina Hand Cream 50g", "Body Care", 32000, .42, 4),
    ("BDY-008", "Lumina Coffee Body Scrub 200g", "Body Care", 49000, .44, 3),
    ("ORL-001", "Lumina Whitening Toothpaste 150g", "Oral Care", 24000, .55, 8),
    ("ORL-002", "Lumina Sensitive Toothpaste 150g", "Oral Care", 28000, .55, 5),
    ("ORL-003", "Lumina Mint Mouthwash 500ml", "Oral Care", 42000, .52, 4),
    ("ORL-004", "Lumina Soft Toothbrush 3-Pack", "Oral Care", 35000, .48, 3),
    ("MEN-001", "Lumina Men Oil Control Face Wash 100ml", "Men Grooming", 42000, .42, 7),
    ("MEN-002", "Lumina Men Hair Pomade 75g", "Men Grooming", 59000, .40, 4),
    ("MEN-003", "Lumina Men Body Spray 120ml", "Men Grooming", 49000, .43, 5),
    ("MEN-004", "Lumina Men Shave Gel 150ml", "Men Grooming", 38000, .45, 2),
]
sku = pd.DataFrame(SKU_ROWS, columns=["sku", "product_name", "sub_category", "rrp", "cogs_pct", "pop"])
MAP_PCT = {"Skincare": .82, "Haircare": .80, "Body Care": .78, "Oral Care": .80, "Men Grooming": .80}
sku["cogs"] = (sku.rrp * sku.cogs_pct).round(-2).astype(int)
sku["map_floor"] = (sku.rrp * sku.sub_category.map(MAP_PCT)).round(-2).astype(int)
sku["campaign_floor"] = (sku.rrp * 0.70).round(-2).astype(int)
NS = len(sku)

# afinitas sub-kategori per platform (mengubah bobot popularitas SKU)
AFF = {
    "SHP": {"Skincare": 1.0, "Haircare": 1.0, "Body Care": 1.0, "Oral Care": 1.0, "Men Grooming": 1.0},
    "TTK": {"Skincare": 1.35, "Haircare": 0.9, "Body Care": 1.1, "Oral Care": 0.6, "Men Grooming": 0.9},
    "LZD": {"Skincare": 0.9, "Haircare": 1.1, "Body Care": 1.1, "Oral Care": 1.2, "Men Grooming": 1.0},
    "BLI": {"Skincare": 1.1, "Haircare": 0.9, "Body Care": 0.9, "Oral Care": 1.3, "Men Grooming": 1.2},
}


def sku_weights(p):
    w = sku["pop"].values * sku.sub_category.map(AFF[p]).values
    return w / w.sum()


# ---------------------------------------------------------------- kota
CITIES = [
    ("Jakarta Selatan", "DKI Jakarta", "Jabodetabek", 5.5, ["Jaksel", "Kota Jakarta Selatan", "JAKARTA SELATAN", "Kota Adm. Jakarta Selatan", "jakarta selatan"]),
    ("Jakarta Barat", "DKI Jakarta", "Jabodetabek", 4.0, ["Jakbar", "Kota Jakarta Barat", "JAKARTA BARAT", "Kota Adm. Jakarta Barat", "jakarta barat"]),
    ("Jakarta Timur", "DKI Jakarta", "Jabodetabek", 4.0, ["Jaktim", "Kota Jakarta Timur", "JAKARTA TIMUR", "Kota Adm. Jakarta Timur", "jakarta timur"]),
    ("Jakarta Utara", "DKI Jakarta", "Jabodetabek", 2.5, ["Jakut", "Kota Jakarta Utara", "JAKARTA UTARA", "Kota Adm. Jakarta Utara", "jakarta utara"]),
    ("Jakarta Pusat", "DKI Jakarta", "Jabodetabek", 1.5, ["Jakpus", "Kota Jakarta Pusat", "JAKARTA PUSAT", "Kota Adm. Jakarta Pusat", "jakarta pusat"]),
    ("Tangerang", "Banten", "Jabodetabek", 4.0, ["Kota Tangerang", "Kab. Tangerang", "TANGERANG", "KAB. TANGERANG", "tangerang"]),
    ("Tangerang Selatan", "Banten", "Jabodetabek", 3.5, ["Tangsel", "Kota Tangerang Selatan", "TANGERANG SELATAN", "tangerang selatan"]),
    ("Bekasi", "Jawa Barat", "Jabodetabek", 5.0, ["Kota Bekasi", "Kab. Bekasi", "BEKASI", "KAB. BEKASI", "bekasi"]),
    ("Depok", "Jawa Barat", "Jabodetabek", 3.5, ["Kota Depok", "DEPOK", "KOTA DEPOK", "depok"]),
    ("Bogor", "Jawa Barat", "Jabodetabek", 3.0, ["Kota Bogor", "Kab. Bogor", "BOGOR", "KAB. BOGOR", "bogor"]),
    ("Bandung", "Jawa Barat", "Jawa", 5.5, ["Kota Bandung", "Kab. Bandung", "BANDUNG", "KOTA BANDUNG", "bandung"]),
    ("Semarang", "Jawa Tengah", "Jawa", 3.5, ["Kota Semarang", "Kab. Semarang", "SEMARANG", "KOTA SEMARANG", "semarang"]),
    ("Yogyakarta", "DI Yogyakarta", "Jawa", 3.0, ["Kota Yogyakarta", "Jogja", "YOGYAKARTA", "KOTA YOGYAKARTA", "yogyakarta"]),
    ("Surabaya", "Jawa Timur", "Jawa", 6.0, ["Kota Surabaya", "SURABAYA", "KOTA SURABAYA", "surabaya", "Sby"]),
    ("Malang", "Jawa Timur", "Jawa", 3.0, ["Kota Malang", "Kab. Malang", "MALANG", "KOTA MALANG", "malang"]),
    ("Denpasar", "Bali", "Bali-Nusa Tenggara", 2.5, ["Kota Denpasar", "DENPASAR", "KOTA DENPASAR", "denpasar"]),
    ("Medan", "Sumatera Utara", "Sumatera", 4.5, ["Kota Medan", "MEDAN", "KOTA MEDAN", "medan"]),
    ("Palembang", "Sumatera Selatan", "Sumatera", 3.0, ["Kota Palembang", "PALEMBANG", "KOTA PALEMBANG", "palembang"]),
    ("Pekanbaru", "Riau", "Sumatera", 2.5, ["Kota Pekanbaru", "PEKANBARU", "KOTA PEKANBARU", "pekanbaru"]),
    ("Batam", "Kepulauan Riau", "Sumatera", 2.0, ["Kota Batam", "BATAM", "KOTA BATAM", "batam"]),
    ("Makassar", "Sulawesi Selatan", "Sulawesi", 3.5, ["Kota Makassar", "MAKASSAR", "KOTA MAKASSAR", "makassar"]),
    ("Manado", "Sulawesi Utara", "Sulawesi", 1.5, ["Kota Manado", "MANADO", "KOTA MANADO", "manado"]),
    ("Balikpapan", "Kalimantan Timur", "Kalimantan", 2.0, ["Kota Balikpapan", "BALIKPAPAN", "KOTA BALIKPAPAN", "balikpapan"]),
    ("Banjarmasin", "Kalimantan Selatan", "Kalimantan", 2.0, ["Kota Banjarmasin", "BANJARMASIN", "KOTA BANJARMASIN", "banjarmasin"]),
]
CITY_W = np.array([c[3] for c in CITIES]); CITY_W = CITY_W / CITY_W.sum()
CITY_TYPOS = {"Surabaya": "Surabya", "Bandung": "Bandun", "Yogyakarta": "Yogjakarta", "Pekanbaru": "Pekanbru",
              "Makassar": "Makasar", "Semarang": "Semaarang", "Bekasi": "Bekassi", "Palembang": "Palembag"}


def norm_alias(s):
    return " ".join(s.lower().replace(".", " ").split())


def city_alias_table():
    rows = []
    for name, prov, reg, _, al in CITIES:
        for a in [name] + al:
            rows.append((norm_alias(a), name, prov, reg))
    df = pd.DataFrame(rows, columns=["alias_key", "city", "province", "region"]).drop_duplicates("alias_key")
    return df


# ---------------------------------------------------------------- kampanye
BRAND = {"SHP": [(3, 15), (6, 15), (9, 15)], "TTK": [(2, 18), (5, 18), (9, 18)],
         "LZD": [(2, 12), (5, 12), (8, 12)], "BLI": [(3, 5), (6, 5), (9, 5)]}
BRAND_NAME = {"SHP": "Shopee Brand Festival", "TTK": "TikTok Brand Mega Live", "LZD": "LazBrand Day", "BLI": "Blibli Brand Fest"}


def build_campaigns():
    rows = []
    for p in PLATS:
        for m in range(1, 11):
            d0 = pd.Timestamp(2026, m, m)
            rows.append((p, f"{p}-DD-{m:02d}", f"{m}.{m} Mega Sale", "DOUBLE_DATE", max(d0 - pd.Timedelta(days=1), START), d0 + pd.Timedelta(days=1), True))
            rows.append((p, f"{p}-PD-{m:02d}", "Payday Sale", "PAYDAY", pd.Timestamp(2026, m, 25), pd.Timestamp(2026, m, 27), False))
        for m, d in BRAND[p]:
            s = pd.Timestamp(2026, m, d)
            rows.append((p, f"{p}-BD-{m:02d}", BRAND_NAME[p], "BRAND_DAY", s, s + pd.Timedelta(days=2), True))
        rows.append((p, f"{p}-RM-02", "Ramadan Sale", "SEASONAL", pd.Timestamp(2026, 2, 18), pd.Timestamp(2026, 3, 19), False))
    camps = pd.DataFrame(rows, columns=["platform_code", "campaign_id", "campaign_name", "campaign_type", "start_date", "end_date", "allows_deep_discount"])
    return camps


def build_day_info(camps):
    """Per platform per hari: pengali volume, campaign primer, offset dari hari-H."""
    info = {}
    for p in PLATS:
        mult = np.ones(ND); cid = np.array([""] * ND, dtype=object); ctype = np.array([""] * ND, dtype=object); off = np.zeros(ND, dtype=int)
        for _, c in camps[camps.platform_code == p].iterrows():
            span = pd.date_range(c.start_date, c.end_date)
            for k, d in enumerate(span):
                if d < START or d > END:
                    continue
                i = (d - START).days
                if c.campaign_type == "DOUBLE_DATE":
                    center = pd.Timestamp(2026, int(c.campaign_id[-2:]), int(c.campaign_id[-2:]))
                    o = (d - center).days
                    mv = {-1: 1.7, 0: 3.2, 1: 1.5}[o]
                elif c.campaign_type == "BRAND_DAY":
                    o = k; mv = [2.3, 2.0, 1.7][k]
                elif c.campaign_type == "PAYDAY":
                    o = k; mv = 1.5
                else:
                    o = k; mv = 1.15
                eff = 1 + (mv - 1) * CAMP_SCALE[p]
                if eff > mult[i]:
                    mult[i] = eff; cid[i] = c.campaign_id; ctype[i] = c.campaign_type; off[i] = o
        info[p] = pd.DataFrame({"mult": mult, "campaign_id": cid, "campaign_type": ctype, "off": off}, index=DAYS)
    return info


HW = np.array([0.4, 0.2, 0.1, 0.1, 0.1, 0.2, 0.8, 1.2, 1.8, 2.2, 2.8, 3.2, 3.5, 3.0, 2.6, 2.5, 2.8, 3.2, 3.8, 4.6, 5.2, 4.8, 3.0, 1.6])


def hour_weights(ctype, off):
    w = HW.copy()
    if ctype == "DOUBLE_DATE":
        if off == 0:
            w[0] *= 14; w[12] *= 1.6; w[20] *= 1.6
        elif off == -1:
            w[22] *= 2.0; w[23] *= 3.0
        else:
            w[0] *= 2.0
    elif ctype == "BRAND_DAY":
        w[12] *= 2.0; w[20] *= 2.0
    elif ctype == "PAYDAY":
        w[0] *= 2.0; w[12] *= 1.3
    return w / w.sum()


# ---------------------------------------------------------------- voucher
SELLER_GROUP = ("Seller Voucher", "Follower Voucher", "Live Voucher")
PLATFORM_GROUP = ("Platform Voucher", "Brand Voucher")
# voucher dengan perilaku anomali (jawaban ada di answer_key)
QUOTA_LEAK = {"SHPDD06PLT": 8, "SHPDD09PLT": 8, "LZDPLT05": 8, "TTKBD09": 10}  # kuota sengaja kecil -> pasti terlampaui
LATE_USE = {"SHPSAVE05": 2, "TTKSAVE06": 2, "LZDSAVE07": 2}


def build_vouchers(camps):
    r = np.random.default_rng(101)
    V = []

    def add(**k):
        V.append(k)

    for p in PLATS:
        sc = VSCALE[p]
        for m in range(1, 11):
            ms = pd.Timestamp(2026, m, 1); me = ms + pd.offsets.MonthEnd(0)
            add(voucher_code=f"{p}SAVE{m:02d}", platform_code=p, voucher_type="Seller Voucher", funding_model="SELLER", seller_share_pct=100,
                discount_kind="PCT", discount_value=10, max_discount=15000, min_spend=99000, quota=int(520 * sc * r.uniform(.8, 1.3)), start_date=ms, end_date=me, campaign_id="")
            add(voucher_code=f"{p}NEWB{m:02d}", platform_code=p, voucher_type="Follower Voucher", funding_model="SELLER", seller_share_pct=100,
                discount_kind="FIXED", discount_value=7500, max_discount=7500, min_spend=60000, quota=int(350 * sc * r.uniform(.8, 1.3)), start_date=ms, end_date=me, campaign_id="")
            add(voucher_code=f"{p}PLT{m:02d}", platform_code=p, voucher_type="Platform Voucher", funding_model="PLATFORM", seller_share_pct=0,
                discount_kind="PCT", discount_value=5, max_discount=10000, min_spend=80000, quota=int(600 * sc * r.uniform(.8, 1.3)), start_date=ms, end_date=me, campaign_id="")
            if p == "TTK":
                add(voucher_code=f"TTKLIVE{m:02d}", platform_code=p, voucher_type="Live Voucher", funding_model="SELLER", seller_share_pct=100,
                    discount_kind="PCT", discount_value=8, max_discount=12000, min_spend=50000, quota=int(300 * sc * r.uniform(.8, 1.3)), start_date=ms, end_date=me, campaign_id="")
        for _, c in camps[camps.platform_code == p].iterrows():
            m = c.start_date.month if c.campaign_type != "DOUBLE_DATE" else int(c.campaign_id[-2:])
            if c.campaign_type == "DOUBLE_DATE":
                add(voucher_code=f"{p}DD{m:02d}PLT", platform_code=p, voucher_type="Platform Voucher", funding_model="PLATFORM", seller_share_pct=0,
                    discount_kind="PCT", discount_value=12, max_discount=30000, min_spend=150000, quota=int(450 * sc * r.uniform(.8, 1.2)), start_date=c.start_date, end_date=c.end_date, campaign_id=c.campaign_id)
                add(voucher_code=f"{p}DD{m:02d}CF", platform_code=p, voucher_type="Platform Voucher", funding_model="COFUND", seller_share_pct=50,
                    discount_kind="FIXED", discount_value=20000, max_discount=20000, min_spend=200000, quota=int(220 * sc * r.uniform(.8, 1.2)), start_date=c.start_date, end_date=c.end_date, campaign_id=c.campaign_id)
            elif c.campaign_type == "PAYDAY":
                add(voucher_code=f"{p}PD{m:02d}", platform_code=p, voucher_type="Platform Voucher", funding_model="PLATFORM", seller_share_pct=0,
                    discount_kind="PCT", discount_value=8, max_discount=25000, min_spend=100000, quota=int(300 * sc * r.uniform(.8, 1.2)), start_date=c.start_date, end_date=c.end_date, campaign_id=c.campaign_id)
            elif c.campaign_type == "BRAND_DAY":
                add(voucher_code=f"{p}BD{m:02d}", platform_code=p, voucher_type="Brand Voucher", funding_model="COFUND", seller_share_pct=40,
                    discount_kind="PCT", discount_value=15, max_discount=40000, min_spend=120000, quota=int(400 * sc * r.uniform(.8, 1.2)), start_date=c.start_date, end_date=c.end_date, campaign_id=c.campaign_id)
    V = pd.DataFrame(V)
    V["ignore_quota"] = V.voucher_code.isin(QUOTA_LEAK)
    for _c, _q in QUOTA_LEAK.items():
        V.loc[V.voucher_code == _c, "quota"] = _q
    V["late_days"] = V.voucher_code.map(LATE_USE).fillna(0).astype(int)
    V["end_eff"] = V.end_date + pd.to_timedelta(V.late_days, unit="D")
    V["group"] = np.where(V.voucher_type.isin(SELLER_GROUP), "S", "P")
    V["budget_idr"] = (V.quota * np.where(V.discount_kind == "FIXED", V.discount_value, V.max_discount * 0.6) * V.seller_share_pct / 100).round(-3).astype(int)
    return V.reset_index(drop=True)


# ---------------------------------------------------------------- buku harga
def build_price_book(camps, day_info):
    """Harga jual toko resmi per hari per SKU per platform. Kepatuhan: >= MAP, atau >= campaign_floor di kampanye diskon dalam."""
    r = np.random.default_rng(202)
    out = {}
    for p in PLATS:
        plist = np.round(sku.rrp.values * PIDX[p], -2)
        dmax_reg = np.clip(1 - sku.map_floor.values / plist, 0, 0.5)
        dmax_camp = np.clip(1 - sku.campaign_floor.values / plist, 0, 0.5)
        base_by_month = {}
        for m in range(1, 11):
            base_by_month[m] = np.minimum(r.choice([0, .03, .05, .08, .10], size=NS, p=[.2, .15, .25, .25, .15]), dmax_reg)
        camp_disc = {}
        for _, c in camps[camps.platform_code == p].iterrows():
            if c.campaign_type == "DOUBLE_DATE":
                camp_disc[c.campaign_id] = r.uniform(.14, .28, NS)
            elif c.campaign_type == "BRAND_DAY":
                camp_disc[c.campaign_id] = r.uniform(.16, .28, NS)
            elif c.campaign_type == "PAYDAY":
                camp_disc[c.campaign_id] = r.uniform(.08, .18, NS)
            else:
                camp_disc[c.campaign_id] = r.uniform(.03, .10, NS)
        ctab = camps.set_index("campaign_id")
        sell = np.zeros((ND, NS)); deep = np.zeros(ND, dtype=bool)
        di = day_info[p]
        for i, d in enumerate(DAYS):
            b = base_by_month[d.month]
            cid = di.campaign_id.iloc[i]
            if cid:
                allow = bool(ctab.loc[cid, "allows_deep_discount"])
                disc = np.minimum(np.maximum(b, camp_disc[cid]), dmax_camp if allow else dmax_reg)
                deep[i] = allow
            else:
                disc = b
            sell[i] = np.ceil(plist * (1 - disc) / 100) * 100
        out[p] = {"list": plist, "sell": sell, "deep": deep}
    return out


# ---------------------------------------------------------------- helpers
def to_wib_str(ts):
    return ts
