"""Tahap 3: data pemantauan harga (price monitoring) + peta listing + kunci jawaban pelanggaran."""
import pickle
from common import *

rng = np.random.default_rng(33)
D = pickle.load(open(f"{BUILD}/orders.pkl", "rb"))
camps, day_info, PB, INC = D["camps"], D["day_info"], D["PB"], D["INCIDENTS"]

# ---------------------------------------------------------------- peta listing
sku_idx = {s: i for i, s in enumerate(sku.sku)}
bundle_base = ["SKN-007", "BDY-001"]
LIST_SKU = list(range(NS)) + [sku_idx[b] for b in bundle_base]
PACK = np.array([1] * NS + [2, 2])
NLIST = len(LIST_SKU)
TITLE = {"SHP": lambda n: f"[BPOM] {n} - Lumina Official Store", "TTK": lambda n: f"{n} | BPOM | Original",
         "LZD": lambda n: f"Lumina Official - {n}", "BLI": lambda n: f"{n} Original"}
rows = []
for p in PLATS:
    for j in range(NLIST):
        s = sku.iloc[LIST_SKU[j]]
        lid = {"SHP": str(rng.integers(10**9, 10**10)), "TTK": str(rng.integers(1_700_000_000_000_000_000, 1_800_000_000_000_000_000)),
               "LZD": str(rng.integers(10**9, 10**10)), "BLI": f"BLI-{rng.integers(10000, 99999)}-{rng.integers(10000, 99999)}"}[p]
        name = s.product_name if PACK[j] == 1 else f"Paket Hemat 2pcs {s.product_name}"
        rows.append((p, lid, s.sku, int(PACK[j]), TITLE[p](name)))
LISTMAP = pd.DataFrame(rows, columns=["platform_code", "listing_id", "sku", "pack_qty", "listing_title"])

# ---------------------------------------------------------------- grid snapshot
SNAP = pd.date_range("2026-09-01 00:00", "2026-10-31 21:00", freq="3h")
NSN = len(SNAP)
sd = ((SNAP.normalize() - START).days).values
SELLERS = [("OFFICIAL", "Lumina Official Store"), ("AUTH_RESELLER", "Toko Beauty Sejahtera"), ("UNAUTH_RESELLER", "Grosir Kosmetik Murah")]
AUTH = pd.DataFrame([("Lumina Official Store", "OFFICIAL"), ("Toko Beauty Sejahtera", "AUTHORIZED")], columns=["seller_name", "authorization_status"])

out = []
for p in PLATS:
    plist = PB[p]["list"]
    sell_day = PB[p]["sell"][sd][:, LIST_SKU]  # (NSN, NLIST) harga satuan toko resmi
    deep = PB[p]["deep"][sd]  # (NSN,)
    rrp = sku.rrp.values[LIST_SKU]; lst_unit = plist[LIST_SKU]
    map_f = sku.map_floor.values[LIST_SKU]; camp_f = sku.campaign_floor.values[LIST_SKU]
    floor_unit = np.where(deep[:, None], camp_f[None, :], map_f[None, :])
    bundle_f = np.where(PACK == 2, 2 * 0.95, 1.0)

    cause_off = np.full((NSN, NLIST), "", dtype=object)
    off_unit = sell_day.astype(float).copy()
    # (a) harga kampanye tertinggal setelah kampanye berakhir (00:00-06:00 hari berikutnya)
    for _, c in camps[(camps.platform_code == p) & camps.allows_deep_discount].iterrows():
        e = c.end_date
        if e < pd.Timestamp("2026-09-01") or e + pd.Timedelta(days=1) > pd.Timestamp("2026-10-31"):
            continue
        rows_i = np.where((SNAP >= e + pd.Timedelta(days=1)) & (SNAP < e + pd.Timedelta(hours=30)))[0]
        last_i = np.where(SNAP.normalize() == e)[0][-1]
        cand = np.where((off_unit[last_i] < map_f) & (PACK == 1))[0]
        pick = rng.choice(cand, size=max(1, int(len(cand) * .45)), replace=False) if len(cand) else []
        for j in pick:
            off_unit[rows_i, j] = off_unit[last_i, j]; cause_off[rows_i, j] = "CAMPAIGN_OVERRUN"
    # (b) insiden salah input harga
    for k, (pp, sk, t0, t1) in enumerate(INC):
        if pp != p:
            continue
        j = sku_idx[sk]
        ii = np.where((SNAP >= pd.Timestamp(t0)) & (SNAP <= pd.Timestamp(t1)))[0]
        off_unit[ii, j] = np.ceil(off_unit[ii, j] * 0.10 / 100) * 100; cause_off[ii, j] = "PRICE_ERROR_INCIDENT"
    price_off = np.ceil(off_unit * bundle_f / 100) * 100
    strike_off = np.round(lst_unit * np.where(PACK == 2, 2, 1) / 100) * 100

    # reseller resmi: ikut harga toko resmi (tanpa insiden), sesekali undercut 1 hari
    base_unit = sell_day.astype(float)
    fA = rng.uniform(.97, 1.03, NLIST)
    pA = np.maximum(base_unit * fA, floor_unit)
    day_id = SNAP.normalize()
    ud = rng.random((len(np.unique(day_id)), NLIST)) < .02
    udm = ud[(sd - sd.min())]
    pA = np.where(udm, floor_unit * rng.uniform(.85, .95, (NSN, NLIST)), pA)
    cause_A = np.where(udm, "RESELLER_UNDERCUT_EPISODE", "").astype(object)
    price_A = np.ceil(pA * bundle_f / 100) * 100

    # reseller tidak resmi: 35% listing dijual jauh di bawah RRP secara persisten; 20% listing strike-price digelembungkan
    persist = rng.random(NLIST) < .35
    disc_b = rng.uniform(.15, .38, NLIST)
    fB = rng.uniform(.98, 1.02, NLIST)
    pB = np.where(persist[None, :], lst_unit[None, :] * (1 - disc_b[None, :]), np.maximum(base_unit * fB, floor_unit))
    cause_B = np.where(np.broadcast_to(persist[None, :], (NSN, NLIST)), "RESELLER_PERSISTENT_UNDERCUT", "").astype(object)
    price_B = np.ceil(pB * bundle_f / 100) * 100
    infl = rng.random(NLIST) < .20
    strike_B = np.where(infl, np.round(lst_unit * rng.uniform(1.15, 1.40, NLIST) * np.where(PACK == 2, 2, 1) / 100) * 100, strike_off)

    for role, name in SELLERS:
        price, strike, cause = {"OFFICIAL": (price_off, np.broadcast_to(strike_off, (NSN, NLIST)), cause_off),
                                "AUTH_RESELLER": (price_A, np.broadcast_to(strike_off, (NSN, NLIST)), cause_A),
                                "UNAUTH_RESELLER": (price_B, np.broadcast_to(strike_B, (NSN, NLIST)), cause_B)}[role]
        lid = LISTMAP[LISTMAP.platform_code == p].listing_id.values
        promo = np.where(price < strike * 0.97, np.where(deep[:, None], "Flash Sale", "Diskon"), "")
        stock = rng.integers(0, 400, (NSN, NLIST))
        df = pd.DataFrame({
            "snapshot_ts": np.repeat(SNAP.values, NLIST), "platform_code": p, "seller_role": role, "seller_name": name,
            "listing_id": np.tile(lid, NSN), "j": np.tile(np.arange(NLIST), NSN),
            "price_displayed": price.reshape(-1).astype(int), "price_strike": np.asarray(strike).reshape(-1).astype(int),
            "promo_label": promo.reshape(-1), "stock_qty": stock.reshape(-1), "cause": cause.reshape(-1)})
        df["floor_unit"] = floor_unit.reshape(-1).astype(int)
        df["rrp"] = rrp[df.j.values]; df["pack"] = PACK[df.j.values]
        out.append(df)

M = pd.concat(out, ignore_index=True)
M["unit_price"] = M.price_displayed / M.pack
M["v_below"] = M.unit_price < M.floor_unit
M["v_strike"] = M.price_strike / M.pack > 1.10 * M.rrp
GT = M[M.v_below | M.v_strike].copy()
GT["violation_type"] = np.where(GT.v_below & GT.v_strike, "BELOW_MAP|STRIKE_PRICE_INFLATION", np.where(GT.v_below, "BELOW_MAP", "STRIKE_PRICE_INFLATION"))
GT["injected_cause"] = np.where(GT.cause != "", GT.cause, np.where(GT.v_strike & ~GT.v_below, "STRIKE_INFLATION", "RULE_DERIVED"))
GT = GT[["snapshot_ts", "platform_code", "seller_name", "listing_id", "price_displayed", "floor_unit", "pack", "violation_type", "injected_cause"]]
M = M[["snapshot_ts", "platform_code", "seller_role", "seller_name", "listing_id", "price_displayed", "price_strike", "promo_label", "stock_qty"]]
print("monitor rows", len(M), "violations", len(GT))
print(GT.groupby(["seller_name", "violation_type"]).size())
print(GT.injected_cause.value_counts().to_dict())
pickle.dump(dict(M=M, GT=GT, LISTMAP=LISTMAP, AUTH=AUTH), open(f"{BUILD}/monitor.pkl", "wb"))
