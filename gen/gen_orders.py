"""Tahap 1: bangun 'kebenaran bersih' order (O = level order, L = level baris) + anomali tersuntik + kunci jawaban."""
import pickle
from common import *

rng = np.random.default_rng(11)
camps = build_campaigns()
day_info = build_day_info(camps)
V = build_vouchers(camps)
V["used"] = 0
PB = build_price_book(camps, day_info)
ALIAS = {c[0]: [c[0]] + c[4] for c in CITIES}
CITY_NAMES = [c[0] for c in CITIES]

# ------------------------------------------------------------ pembeli
FIRST = ["dewi", "rizky", "nur", "siti", "budi", "agus", "putri", "andi", "fitri", "wahyu", "ayu", "dian", "eko", "rina", "yoga", "tri", "indah",
         "bayu", "citra", "ilham", "nadia", "fajar", "lestari", "hendra", "maya", "reza", "salsa", "dimas", "anisa", "galih"]
LAST = ["pratama", "sari", "wijaya", "hidayat", "lestari", "putra", "utami", "santoso", "kurniawan", "rahma", "saputra", "nugroho", "amalia",
        "permata", "setiawan", "ramadhan", "fauzi", "anggraini", "firmansyah", "maharani"]
PREFIX = ["62812", "62813", "62821", "62852", "62857", "62878", "62895", "62896"]
POOL_N = {"SHP": 14000, "TTK": 11000, "LZD": 4500, "BLI": 2800}


def mask_name(f, l, style):
    if style == "lazada":
        return f"{f[0].upper()}*** {l[0].upper()}."
    return f"{f[:2].title()}*** {l[:2].title()}***"


def make_pool(p, n):
    f = rng.choice(FIRST, n); l = rng.choice(LAST, n)
    dg = rng.integers(1, 9999, n)
    users = []
    subch = np.array([""] * n, dtype=object)
    if p == "SHP":
        for i in range(n):
            sep = ["_", "", "."][i % 3]
            users.append(f"{f[i]}{sep}{l[i][:rng.integers(1, 4)]}{dg[i]}")
    elif p == "TTK":
        subch = np.where(rng.random(n) < 0.55, "Tokopedia", "TikTok Shop").astype(object)
        for i in range(n):
            users.append(mask_name(f[i], l[i], "m") if subch[i] == "Tokopedia" else f"user{rng.integers(10**9, 10**10)}")
    elif p == "LZD":
        users = [mask_name(f[i], l[i], "lazada") for i in range(n)]
    else:
        users = [mask_name(f[i], l[i], "m") for i in range(n)]
    ph = [f"{rng.choice(PREFIX)}***{rng.integers(0, 10**6):06d}" for _ in range(n)]
    city = rng.choice(len(CITIES), n, p=CITY_W)
    return {"user": np.array(users, dtype=object), "phone": np.array(ph, dtype=object), "city": city, "subch": subch}


POOLS = {p: make_pool(p, POOL_N[p]) for p in PLATS}
NB = dict(POOL_N)  # ukuran pool normal

# ------------------------------------------------------------ id
B36 = np.array(list("ABCDEFGHJKLMNPQRSTUVWXYZ23456789"))
BLI_CTR = [0]


def new_ids(p, ts, n):
    ts = pd.DatetimeIndex(ts)
    if p == "SHP":
        arr = rng.integers(0, len(B36), size=(n, 8))
        return [f"{t:%y%m%d}" + "".join(B36[a]) for t, a in zip(ts, arr)]
    if p == "TTK":
        return [str(x) for x in rng.integers(570_000_000_000_000_000, 580_000_000_000_000_000, n)]
    if p == "LZD":
        return [str(x) for x in rng.integers(700_000_000_000_000, 790_000_000_000_000, n)]
    out = []
    for t in ts:
        BLI_CTR[0] += int(rng.integers(1, 6))
        out.append(f"BLI{t:%y%m}{BLI_CTR[0]:07d}")
    return out


PAYM = {"SHP": (["ShopeePay", "COD", "Transfer Bank", "SPayLater", "Kartu Kredit"], [.38, .22, .2, .12, .08]),
        "TTK": (["COD", "TikTok Pay", "Transfer Bank", "GoPay", "Kartu Kredit"], [.3, .3, .2, .13, .07]),
        "LZD": (["COD", "Transfer Bank", "Kartu Kredit", "Akulaku", "OVO"], [.28, .3, .2, .1, .12]),
        "BLI": (["Transfer Bank", "Kartu Kredit", "GoPay", "OVO", "COD"], [.35, .25, .2, .12, .08])}
SHIP_FEES = [0, 9000, 12000, 15000, 18000, 22000]

# ------------------------------------------------------------ voucher
viol_rows = []  # (platform, order_id, voucher_code, violation_type)


def apply_group(p, d, grp, sub, oids, pu):
    n = len(sub)
    code = np.full(n, "", dtype=object); samt = np.zeros(n); pamt = np.zeros(n)
    cand = V[(V.platform_code == p) & (V.group == grp) & (V.start_date <= d) & (V.end_eff >= d)]
    if cand.empty or n == 0:
        return code, samt, pamt
    use = rng.random(n) < pu
    choice = rng.integers(0, len(cand), n)
    for j, (vi, row) in enumerate(cand.iterrows()):
        m = use & (choice == j) & (code == "")
        if row.late_days > 0 and d > row.end_date:
            m = (code == "") & (rng.random(n) < 0.35)
        ok_min = sub >= row.min_spend
        leak = (~ok_min) & (rng.random(n) < 0.01)
        idx = np.where(m & (ok_min | leak))[0]
        if len(idx) == 0:
            continue
        rem = int(row.quota - V.at[vi, "used"])
        if not row.ignore_quota:
            idx = idx[:max(rem, 0)]
        if len(idx) == 0:
            continue
        if row.discount_kind == "PCT":
            amt = np.minimum(np.floor(sub[idx] * row.discount_value / 100 / 100) * 100, row.max_discount)
        else:
            amt = np.full(len(idx), float(row.discount_value))
        amt = np.minimum(amt, np.floor(sub[idx] * 0.6 / 100) * 100)
        sa = np.round(amt * row.seller_share_pct / 100); pa = amt - sa
        code[idx] = row.voucher_code; samt[idx] = sa; pamt[idx] = pa
        used_before = int(V.at[vi, "used"])
        cum = used_before + np.arange(1, len(idx) + 1)
        for k, i in enumerate(idx):
            if not ok_min[i]:
                viol_rows.append((p, oids[i], row.voucher_code, "VOUCHER_BELOW_MIN_SPEND"))
            if d > row.end_date:
                viol_rows.append((p, oids[i], row.voucher_code, "VOUCHER_USED_AFTER_EXPIRY"))
            if cum[k] > row.quota:
                viol_rows.append((p, oids[i], row.voucher_code, "VOUCHER_OVER_QUOTA"))
        V.at[vi, "used"] = used_before + len(idx)
    return code, samt, pamt


def status_probs(age, camp_mult):
    if age <= 2:
        return ["CANCELLED", "TO_SHIP", "SHIPPED", "COMPLETED"], [.05, .30, .60, .05]
    if age <= 7:
        return ["CANCELLED", "RETURNED", "SHIPPED", "COMPLETED"], [.05, .01, .25, .69]
    cp = .05 + (.03 if camp_mult > 1.5 else 0)
    return ["CANCELLED", "RETURNED", "COMPLETED"], [cp, .025, 1 - cp - .025]


O_parts, L_parts = [], []
for di, d in enumerate(DAYS):
    for p in PLATS:
        info = day_info[p].iloc[di]
        dow = [.95, .95, 1.0, 1.0, 1.05, 1.1, 1.05][d.dayofweek]
        g0, g1 = GROWTH[p]
        lam = BASE_ORD[p] * dow * (g0 + (g1 - g0) * di / (ND - 1)) * info.mult * rng.lognormal(0, .07)
        n = int(rng.poisson(lam))
        if n == 0:
            continue
        w = hour_weights(info.campaign_type, info.off)
        sec = np.sort(rng.choice(24, n, p=w) * 3600 + rng.integers(0, 3600, n))
        ts = d + pd.to_timedelta(sec, unit="s")
        nl = rng.choice([1, 2, 3, 4], n, p=[.62, .25, .10, .03])
        o = np.repeat(np.arange(n), nl)
        s = rng.choice(NS, len(o), p=sku_weights(p))
        q = rng.choice([1, 2, 3, 4, 6], len(o), p=[.78, .14, .05, .02, .01])
        dl = pd.DataFrame({"o": o, "s": s, "q": q}).groupby(["o", "s"], as_index=False).q.sum()
        dl["line_no"] = dl.groupby("o").cumcount() + 1
        ulist = PB[p]["list"][dl.s.values]; usell = PB[p]["sell"][di][dl.s.values]
        sub = np.bincount(dl.o.values, weights=usell * dl.q.values, minlength=n)
        oids = new_ids(p, ts, n)
        pool = POOLS[p]
        bi = (NB[p] * rng.random(n) ** 1.6).astype(int)
        city = pool["city"][bi].copy()
        swap = rng.random(n) < .03
        city[swap] = rng.choice(len(CITIES), swap.sum(), p=CITY_W)
        ct = info.campaign_type
        pS = {"DOUBLE_DATE": .28, "BRAND_DAY": .30, "PAYDAY": .25, "SEASONAL": .22}.get(ct, .18)
        pP = {"DOUBLE_DATE": .60, "BRAND_DAY": .50, "PAYDAY": .40, "SEASONAL": .25}.get(ct, .20)
        cS, sS, pS_ = apply_group(p, d, "S", sub, oids, pS)
        cP, sP, pP_ = apply_group(p, d, "P", sub, oids, pP)
        age = (END - d).days
        names, pr = status_probs(age, info.mult)
        st = rng.choice(names, n, p=pr)
        subch = pool["subch"][bi] if p == "TTK" else np.array([""] * n, dtype=object)
        evening = (sec // 3600 >= 19) & (sec // 3600 <= 23)
        live = (subch == "TikTok Shop") & (rng.random(n) < np.where(evening, .30, .05)) if p == "TTK" else np.zeros(n, dtype=bool)
        raw_city = []
        for c in city:
            nm = CITY_NAMES[c]
            raw_city.append(CITY_TYPOS[nm] if (nm in CITY_TYPOS and rng.random() < .004) else rng.choice(ALIAS[nm]))
        pm = rng.choice(PAYM[p][0], n, p=PAYM[p][1])
        O_parts.append(pd.DataFrame({
            "platform_code": p, "order_id": oids, "ts": ts, "user": pool["user"][bi], "phone": pool["phone"][bi],
            "city_canon": [CITY_NAMES[c] for c in city], "city_raw": raw_city, "status": st, "campaign_id": info.campaign_id,
            "campaign_type": ct, "subchannel": subch, "is_live": live, "payment_method": pm,
            "seller_voucher_code": cS, "platform_voucher_code": cP, "seller_voucher_amt": (sS + sP).astype(int),
            "platform_voucher_amt": (pS_ + pP_).astype(int), "shipping_fee": rng.choice(SHIP_FEES, n, p=[.3, .1, .2, .2, .12, .08]),
            "scenario": "", "cluster_id": "", "ord_sub": sub.astype(int)}))
        oid_arr = np.array(oids, dtype=object)
        L_parts.append(pd.DataFrame({
            "platform_code": p, "order_id": oid_arr[dl.o.values], "line_no": dl.line_no.values, "sku": sku.sku.values[dl.s.values],
            "qty": dl.q.values, "unit_list": ulist.astype(int), "unit_sell": usell.astype(int)}))

O = pd.concat(O_parts, ignore_index=True); L = pd.concat(L_parts, ignore_index=True)
print("normal orders", len(O), "lines", len(L))

# ------------------------------------------------------------ anomali tersuntik (order manual)
man_O, man_L = [], []
CL = {"n": 0}


def status_manual(scen, ts):
    age = (END - ts.normalize()).days
    if scen == "PRICE_ERROR":
        return rng.choice(["CANCELLED", "COMPLETED", "RETURNED"], p=[.55, .40, .05])
    if scen == "ACCOUNT_FARM":
        return rng.choice(["CANCELLED", "COMPLETED", "RETURNED"], p=[.25, .70, .05])
    return rng.choice(["COMPLETED", "CANCELLED", "RETURNED"], p=[.86, .10, .04]) if age > 7 else "SHIPPED"


def add_manual(p, ts, user, phone, city_idx, subch, lines, scen, cluster, price_override=None, status=None):
    di = (ts.normalize() - START).days
    info = day_info[p].iloc[di]
    ul = []; us = []
    for si, qty in lines:
        ul.append(PB[p]["list"][si]); us.append(PB[p]["sell"][di][si] if price_override is None else np.ceil(PB[p]["sell"][di][si] * price_override / 100) * 100)
    oid = new_ids(p, [ts], 1)[0]
    nm = CITY_NAMES[city_idx]
    man_O.append(dict(platform_code=p, order_id=oid, ts=ts, user=user, phone=phone, city_canon=nm, city_raw=rng.choice(ALIAS[nm]),
                      status=status or status_manual(scen, ts), campaign_id=info.campaign_id, campaign_type=info.campaign_type,
                      subchannel=subch, is_live=False, payment_method=rng.choice(PAYM[p][0], p=PAYM[p][1]), seller_voucher_code="",
                      platform_voucher_code="", seller_voucher_amt=0, platform_voucher_amt=0, shipping_fee=int(rng.choice(SHIP_FEES)),
                      scenario=scen, cluster_id=cluster, ord_sub=int(sum(u * q for u, (_, q) in zip(us, lines)))))
    for k, ((si, qty), a, b) in enumerate(zip(lines, ul, us), start=1):
        man_L.append(dict(platform_code=p, order_id=oid, line_no=k, sku=sku.sku.values[si], qty=int(qty), unit_list=int(a), unit_sell=int(b)))
    return oid


def pool_new_account(p, user, phone=None, city=None):
    pool = POOLS[p]
    ph = phone or f"{rng.choice(PREFIX)}***{rng.integers(0, 10**6):06d}"
    c = city if city is not None else int(rng.choice(len(CITIES), p=CITY_W))
    sub = ("Tokopedia" if rng.random() < .5 else "TikTok Shop") if p == "TTK" else ""
    return user, ph, c, sub


def rand_ts(day, hour_lo=0, hour_hi=24):
    return day + pd.Timedelta(seconds=int(rng.integers(hour_lo * 3600, hour_hi * 3600)))


camp_days = {p: [DAYS[i] for i in range(ND) if day_info[p].campaign_type.iloc[i] in ("DOUBLE_DATE", "BRAND_DAY")] for p in PLATS}
top_sku = np.argsort(-sku["pop"].values)[:12]

# S1 BULK_QTY: 24 akun grosir (6 per platform), 30 order per platform
for p in PLATS:
    accts = [pool_new_account(p, f"grosir_{p.lower()}_{k}" if p == "SHP" else mask_name("grosir", "toko", "m")) for k in range(6)]
    for k in range(30):
        a = accts[rng.integers(0, 6)]
        day = camp_days[p][rng.integers(0, len(camp_days[p]))] if rng.random() < .7 else DAYS[rng.integers(0, ND - 8)]
        si = int(rng.choice(top_sku))
        lines = [(si, int(np.clip(rng.lognormal(3.1, .4), 12, 60)))]
        if rng.random() < .3:
            lines.append((int(rng.choice([x for x in top_sku if x != si])), int(rng.integers(10, 30))))
        add_manual(p, rand_ts(day, 8, 23), *a, lines, "BULK_QTY", f"BULK-{p}")

# S2 VELOCITY_BURST: 18 burst
for b in range(18):
    p = PLATS[b % 4]
    a = pool_new_account(p, f"flash_{p.lower()}_{b}" if p == "SHP" else mask_name("flash", "buyer", "m"))
    day = DAYS[rng.integers(5, ND - 8)]
    t0 = rand_ts(day, 9, 21); si = int(rng.choice(top_sku))
    for k in range(int(rng.integers(6, 16))):
        add_manual(p, t0 + pd.Timedelta(seconds=int(rng.integers(0, 45 * 60))), *a, [(si, int(rng.integers(1, 4)))], "VELOCITY_BURST", f"VEL-{b:02d}")

# S3 ACCOUNT_FARM: 8 farm (2 per platform), akun berbagi telepon + kota
for f in range(8):
    p = PLATS[f % 4]
    shared_phone = f"{rng.choice(PREFIX)}***{rng.integers(0, 10**6):06d}"; shared_city = int(rng.choice(len(CITIES), p=CITY_W))
    accts = [pool_new_account(p, f"promo_hunter_{f}_{k}" if p == "SHP" else mask_name("promo", f"h{f}{k}", "m"), shared_phone, shared_city) for k in range(int(rng.integers(3, 7)))]
    day = camp_days[p][rng.integers(0, len(camp_days[p]))]
    flash = rng.choice(NS, 2, replace=False)
    start_h = 0 if rng.random() < .5 else 12
    for k in range(int(rng.integers(15, 41))):
        a = accts[rng.integers(0, len(accts))]
        t = day + pd.Timedelta(hours=start_h, seconds=int(rng.integers(0, 20 * 60)))
        add_manual(p, t, *a, [(int(rng.choice(flash)), int(rng.integers(1, 3)))], "ACCOUNT_FARM", f"FARM-{f}")

# S4 PRICE_ERROR: 6 insiden harga (toko resmi salah input ~10% dari harga normal)
INCIDENTS = [("SHP", "SKN-004", "2026-09-04 11:40", "2026-09-04 15:05"), ("TTK", "HCR-001", "2026-09-18 20:10", "2026-09-18 23:50"),
             ("LZD", "SKN-007", "2026-09-27 05:15", "2026-09-27 09:30"), ("BLI", "BDY-001", "2026-10-02 13:00", "2026-10-02 16:20"),
             ("SHP", "BDY-005", "2026-10-14 08:00", "2026-10-14 12:45"), ("TTK", "SKN-003", "2026-10-21 22:30", "2026-10-22 02:10")]
for k, (p, sk, t0, t1) in enumerate(INCIDENTS):
    si = int(sku.index[sku.sku == sk][0]); t0 = pd.Timestamp(t0); t1 = pd.Timestamp(t1)
    nO = int(rng.integers(60, 260)); dur = (t1 - t0).total_seconds()
    resell = [pool_new_account(p, f"reseller_inc{k}_{j}" if p == "SHP" else mask_name("resel", f"i{k}{j}", "m")) for j in range(8)]
    rcount = {j: 0 for j in range(8)}
    for _ in range(nO):
        t = t0 + pd.Timedelta(seconds=float(rng.random() * dur))
        if rng.random() < .35:
            j = int(rng.integers(0, 8))
            if rcount[j] >= 4:
                continue
            rcount[j] += 1; a = resell[j]
        else:
            bi = int(rng.integers(0, NB[p]))
            a = (POOLS[p]["user"][bi], POOLS[p]["phone"][bi], int(POOLS[p]["city"][bi]), POOLS[p]["subch"][bi])
        qty = int(rng.choice([1, 2, 3, 5, 10, 12, 20], p=[.35, .2, .12, .1, .1, .08, .05]))
        # tanggal berganti dihitung dari ts, harga hari itu dikali 0.1
        add_manual(p, t, *a, [(si, qty)], "PRICE_ERROR", f"PERR-{k+1}", price_override=0.10)

MO = pd.DataFrame(man_O); ML = pd.DataFrame(man_L)
print("manual orders", len(MO), MO.scenario.value_counts().to_dict())
O = pd.concat([O, MO], ignore_index=True)
L = pd.concat([L, ML], ignore_index=True)
assert O.order_id.is_unique, "order_id tidak unik"
O = O.sort_values("ts").reset_index(drop=True)
O["ord_sub"] = O.ord_sub.astype(int)

# kolom turunan baris
L = L.merge(sku[["sku", "sub_category", "cogs"]], on="sku", how="left")
L["line_list"] = L.unit_list * L.qty
L["line_sell"] = L.unit_sell * L.qty

VIOL = pd.DataFrame(viol_rows, columns=["platform_code", "order_id", "voucher_code", "violation_type"])
print("voucher violations", VIOL.violation_type.value_counts().to_dict())
print("status", O.status.value_counts(normalize=True).round(3).to_dict())
print(O.groupby("platform_code").size().to_dict(), "lines", len(L))
pickle.dump(dict(O=O, L=L, V=V, VIOL=VIOL, camps=camps, day_info=day_info, PB=PB, INCIDENTS=INCIDENTS), open(f"{BUILD}/orders.pkl", "wb"))
