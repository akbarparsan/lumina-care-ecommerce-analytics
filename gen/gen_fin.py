"""Tahap 2: settlement, ERP, iklan, kontrak, JBP, program statement + kunci jawaban rekonsiliasi."""
import pickle
from common import *

rng = np.random.default_rng(22)
D = pickle.load(open(f"{BUILD}/orders.pkl", "rb"))
O, L, V, camps, day_info = D["O"], D["L"], D["V"], D["camps"], D["day_info"]
O["date"] = O.ts.dt.normalize()

# ------------------------------------------------------------ kontrak biaya platform (FIKTIF)
FEE = {"SHP": (8.0, 4.0, 2.0), "TTK": (6.0, 3.5, 1.8), "LZD": (8.5, 3.5, 2.0), "BLI": (7.5, 2.5, 1.5)}
COMM_DISC = {"SHP": 1.5, "TTK": 2.0, "LZD": 1.0, "BLI": 1.0}
fee_contract = pd.DataFrame([dict(platform_code=p, commission_pct=FEE[p][0], service_fee_pct=FEE[p][1], payment_fee_pct=FEE[p][2],
                                  valid_from="2026-01-01", valid_to="2026-12-31") for p in PLATS])

# ------------------------------------------------------------ settlement
C = O[O.status == "COMPLETED"].copy()
C["fee_base"] = C.ord_sub - C.seller_voucher_amt
C["is_comm_disc"] = C.campaign_type.isin(["DOUBLE_DATE", "BRAND_DAY"])
C["lag"] = rng.integers(5, 13, len(C))
C["settle_date"] = C.date + pd.to_timedelta(C.lag, unit="D")
C["age"] = (END - C.date).dt.days
C["comm_rate"] = C.platform_code.map(lambda p: FEE[p][0]) - np.where(C.is_comm_disc, C.platform_code.map(COMM_DISC), 0)
C["svc_rate"] = C.platform_code.map(lambda p: FEE[p][1]); C["pay_rate"] = C.platform_code.map(lambda p: FEE[p][2])
C["commission_fee"] = np.round(C.fee_base * C.comm_rate / 100).astype(int)
C["service_fee"] = np.round(C.fee_base * C.svc_rate / 100).astype(int)
C["payment_fee"] = np.round(C.fee_base * C.pay_rate / 100).astype(int)
C["pv_credit"] = C.platform_voucher_amt
C["ship_adj"] = np.where(rng.random(len(C)) < .03, -np.round(rng.uniform(1000, 12000, len(C)), -2), 0).astype(int)
C["expected_net"] = C.fee_base + C.pv_credit - C.commission_fee - C.service_fee - C.payment_fee + C.ship_adj

gt_set = []  # (platform, order_id, type, impact_idr)
settled = C[C.settle_date <= END].copy()
# D4: order selesai > 20 hari tidak punya baris settlement
d4 = settled[(settled.age > 20)].sample(frac=.012, random_state=1)
for r in d4.itertuples():
    gt_set.append((r.platform_code, r.order_id, "UNSETTLED_AGING", int(r.expected_net)))
settled = settled.drop(d4.index)
# D1: komisi tanpa diskon kampanye
pool1 = settled[settled.is_comm_disc]
d1 = pool1.sample(frac=.04, random_state=2)
settled.loc[d1.index, "commission_fee"] = np.round(settled.loc[d1.index, "fee_base"] * (settled.loc[d1.index, "platform_code"].map(lambda p: FEE[p][0])) / 100).astype(int)
for i in d1.index:
    r = settled.loc[i]
    gt_set.append((r.platform_code, r.order_id, "COMMISSION_OVERCHARGE", int(round(r.fee_base * COMM_DISC[r.platform_code] / 100))))
# D2: subsidi voucher platform tidak dikreditkan
pool2 = settled[(settled.platform_voucher_amt > 0) & (~settled.index.isin(d1.index))]
d2 = pool2.sample(frac=.008, random_state=3)
settled.loc[d2.index, "pv_credit"] = 0
for r in d2.itertuples():
    gt_set.append((r.platform_code, r.order_id, "VOUCHER_SUBSIDY_MISSING", int(r.platform_voucher_amt)))
settled["net_payout"] = settled.fee_base + settled.pv_credit - settled.commission_fee - settled.service_fee - settled.payment_fee + settled.ship_adj
# D3: baris settlement ganda
d3 = settled.sample(frac=.0015, random_state=4)
for r in d3.itertuples():
    gt_set.append((r.platform_code, r.order_id, "DUPLICATE_SETTLEMENT_ROW", -int(r.net_payout)))
# D6: baris yatim (order id tidak ada di ekspor order)
orph = settled.sample(frac=.001, random_state=5).copy()
orph["order_id"] = ["ZZ" + x[2:] if not x.startswith("BLI") else "BLI9" + x[4:] for x in orph.order_id]
for r in orph.itertuples():
    gt_set.append((r.platform_code, r.order_id, "ORPHAN_SETTLEMENT", -int(r.net_payout)))
SETTLE = pd.concat([settled, settled.loc[d3.index], orph], ignore_index=True)
SETTLE = SETTLE[["platform_code", "order_id", "settle_date", "ord_sub", "seller_voucher_amt", "pv_credit", "commission_fee", "service_fee", "payment_fee", "ship_adj", "net_payout", "fee_base"]]

# ------------------------------------------------------------ ERP
E = O[O.status.isin(["COMPLETED", "SHIPPED"])].copy()
e_missing = E[E.status == "COMPLETED"].sample(frac=.003, random_state=6)
for r in e_missing.itertuples():
    gt_set.append((r.platform_code, r.order_id, "ERP_MISSING", int(r.ord_sub - r.seller_voucher_amt)))
E = E.drop(e_missing.index)
E["net_amount"] = E.ord_sub - E.seller_voucher_amt
e_mis = E.sample(frac=.004, random_state=7)
chg = np.round(E.loc[e_mis.index, "net_amount"] * rng.uniform(.01, .08, len(e_mis)) * rng.choice([-1, 1], len(e_mis)), -2).astype(int)
for (i, r), c in zip(E.loc[e_mis.index].iterrows(), chg):
    gt_set.append((r.platform_code, r.order_id, "ERP_AMOUNT_MISMATCH", int(c)))
E.loc[e_mis.index, "net_amount"] = E.loc[e_mis.index, "net_amount"] + chg
e_only = O[O.status == "CANCELLED"].sample(n=25, random_state=8).copy()
e_only["net_amount"] = e_only.ord_sub - e_only.seller_voucher_amt
for r in e_only.itertuples():
    gt_set.append((r.platform_code, r.order_id, "ERP_ONLY_CANCELLED", int(r.net_amount)))
E = pd.concat([E, e_only], ignore_index=True).sort_values("ts").reset_index(drop=True)
E["ship_date"] = E.date + pd.to_timedelta(rng.integers(1, 3, len(E)), unit="D")
E["erp_doc_no"] = [f"SO/2026/{i+1:06d}" for i in range(len(E))]
ERP = E[["erp_doc_no", "platform_code", "order_id", "ship_date", "ord_sub", "seller_voucher_amt", "net_amount"]]

# ------------------------------------------------------------ iklan
Lm = L.merge(O[["order_id", "date"]], on="order_id")
gmv_day = Lm.groupby(["platform_code", "date", "sub_category"]).line_sell.sum().reset_index()
aov = (O.groupby("platform_code").ord_sub.sum() / O.groupby("platform_code").size()).to_dict()
ADT = {"SHP": [("Product Search Ads", .45, 9.0), ("Shop Ads", .20, 6.0), ("GMV Max", .35, 7.5)],
       "TTK": [("Product GMV Max", .40, 8.0), ("LIVE GMV Max", .35, 5.0), ("Video Shopping Ads", .25, 6.0)],
       "LZD": [("Sponsored Solutions", .60, 7.0), ("Sponsored Discovery", .40, 4.5)],
       "BLI": [("Iklan Produk", .65, 6.5), ("Banner & Display", .35, 3.5)]}
ADS_SHARE = {"SHP": .38, "TTK": .45, "LZD": .30, "BLI": .22}
camp_name = {(p, d): day_info[p].campaign_id.iloc[i] for p in PLATS for i, d in enumerate(DAYS)}
cname_by_id = camps.set_index("campaign_id").campaign_name.to_dict()
rows = []
for r in gmv_day.itertuples():
    p = r.platform_code; cid = camp_name[(p, r.date)]
    for (at, sh, roas) in ADT[p]:
        camp_f = 1.1 if cid else 1.0
        ad_gmv = r.line_sell * ADS_SHARE[p] * sh * camp_f * rng.lognormal(0, .15)
        ro = roas * (1.15 if cid else 1.0) * rng.lognormal(0, .12)
        spend = ad_gmv / ro
        ao = max(1, int(round(ad_gmv / (aov[p] * rng.uniform(.9, 1.1)))))
        clicks = max(ao, int(round(ao / rng.uniform(.025, .06))))
        imp = int(round(clicks / rng.uniform(.008, .025)))
        rows.append((r.date, p, at, f"{r.sub_category} - {cname_by_id[cid] if cid else 'Always-On'}", r.sub_category, imp, clicks, int(round(spend, -2)), ao, int(round(ad_gmv, -2))))
ADS = pd.DataFrame(rows, columns=["date", "platform_code", "ad_type", "campaign_name", "sub_category", "impressions", "clicks", "spend", "ad_orders", "ad_gmv"])
# kesenjangan ekstraksi: Lazada 5-7 Agustus tidak ada
gap_mask = (ADS.platform_code == "LZD") & (ADS.date.between("2026-08-05", "2026-08-07"))
ADS_GAP = ADS[gap_mask].groupby(["platform_code", "date"]).size().reset_index()[["platform_code", "date"]]
ADS = ADS[~gap_mask].reset_index(drop=True)
print("ads rows", len(ADS), "TACOS approx", (ADS.spend.sum() / O.ord_sub.sum()).round(4))

# ------------------------------------------------------------ JBP + program statement
def qtr(d):
    return (d.month - 1) // 3 + 1


C2 = O[O.status == "COMPLETED"].copy(); C2["q"] = C2.date.map(qtr)
qgmv = C2.groupby(["platform_code", "q"]).ord_sub.sum().unstack()
jbp = []
RATES = {"SHP": (1.0, 1.8), "TTK": (1.2, 2.0), "LZD": (0.8, 1.5), "BLI": (1.0, 1.6)}
COFUND = {"SHP": (35, 25_000_000), "TTK": (30, 20_000_000), "LZD": (40, 10_000_000), "BLI": (25, 5_000_000)}
ADSCR = {"SHP": 5, "TTK": 4, "LZD": 6, "BLI": 3}
thr = {}
for p in PLATS:
    t1 = int(np.floor(0.90 * qgmv.loc[p, 1] / 1e7) * 1e7); t2 = int(np.floor(1.00 * qgmv.loc[p, 2] / 1e7) * 1e7)
    thr[p] = (t1, t2)
    jbp.append(dict(agreement_id=f"JBP26-{p}-REB", platform_code=p, program_code="QUARTERLY_REBATE", period_type="QUARTER", valid_from="2026-01-01", valid_to="2026-12-31",
                    metric="NET_GMV_COMPLETED", tier1_threshold=t1, tier1_rate_pct=RATES[p][0], tier2_threshold=t2, tier2_rate_pct=RATES[p][1], cap_amount=None, campaign_scope="", notes="Rebate = tarif tier x Net GMV kuartal (order selesai, harga setelah diskon penjual, sebelum voucher)"))
    jbp.append(dict(agreement_id=f"JBP26-{p}-BDC", platform_code=p, program_code="BRAND_DAY_COFUND", period_type="CAMPAIGN", valid_from="2026-01-01", valid_to="2026-12-31",
                    metric="SELLER_VOUCHER_COST", tier1_threshold=None, tier1_rate_pct=COFUND[p][0], tier2_threshold=None, tier2_rate_pct=None, cap_amount=COFUND[p][1], campaign_scope="BRAND_DAY", notes="Platform mengganti % biaya voucher yang didanai penjual pada order selesai selama Brand Day"))
    jbp.append(dict(agreement_id=f"JBP26-{p}-CMD", platform_code=p, program_code="COMMISSION_DISCOUNT", period_type="CAMPAIGN", valid_from="2026-01-01", valid_to="2026-12-31",
                    metric="COMMISSION_PCT_POINTS", tier1_threshold=None, tier1_rate_pct=COMM_DISC[p], tier2_threshold=None, tier2_rate_pct=None, cap_amount=None, campaign_scope="DOUBLE_DATE,BRAND_DAY", notes="Tarif komisi dikurangi sekian poin persen selama kampanye"))
    jbp.append(dict(agreement_id=f"JBP26-{p}-ADC", platform_code=p, program_code="ADS_CREDIT", period_type="QUARTER", valid_from="2026-01-01", valid_to="2026-12-31",
                    metric="AD_SPEND", tier1_threshold=None, tier1_rate_pct=ADSCR[p], tier2_threshold=None, tier2_rate_pct=None, cap_amount=60_000_000, campaign_scope="", notes="Bonus kredit iklan = % belanja iklan kuartal berjalan"))
JBP = pd.DataFrame(jbp)

stmt = []; gt_prog = []
sid = [0]


def add_stmt(p, prog, label, ps, pe, expected, paid, note=""):
    sid[0] += 1
    if paid is not None:
        stmt.append(dict(statement_id=f"ST{sid[0]:04d}", platform_code=p, program_code=prog, period_label=label, period_start=ps, period_end=pe,
                         paid_amount=int(paid), paid_date=pe + pd.Timedelta(days=int(rng.integers(10, 25))), remarks=note))
    shortfall = int(expected - (paid or 0))
    if abs(shortfall) > max(1000, 0.005 * expected):
        gt_prog.append((p, prog, label, int(expected), int(paid or 0), shortfall))


qrange = {1: ("2026-01-01", "2026-03-31"), 2: ("2026-04-01", "2026-06-30"), 3: ("2026-07-01", "2026-09-30")}
for p in PLATS:
    for q in (1, 2, 3):
        g = float(qgmv.loc[p, q]); t1, t2 = thr[p]
        rate = RATES[p][1] if g >= t2 else (RATES[p][0] if g >= t1 else 0.0)
        exp_ = round(g * rate / 100)
        paid = exp_
        if (p, q) == ("SHP", 2): paid = round(g * RATES[p][0] / 100)  # dibayar di tier 1 padahal capai tier 2
        if (p, q) == ("LZD", 3): paid = round(0.92 * g * rate / 100)  # basis dihitung kurang
        if (p, q) == ("BLI", 2): paid = None  # tidak dibayar
        ps, pe = pd.Timestamp(qrange[q][0]), pd.Timestamp(qrange[q][1])
        add_stmt(p, "QUARTERLY_REBATE", f"2026-Q{q}", ps, pe, exp_, paid)
        sp = ADS[(ADS.platform_code == p) & (ADS.date.between(ps, pe))].spend.sum()
        exp_a = min(60_000_000, round(sp * ADSCR[p] / 100)); paid_a = exp_a
        if (p, q) == ("SHP", 3): paid_a = round(.6 * exp_a)
        add_stmt(p, "ADS_CREDIT", f"2026-Q{q}", ps, pe, exp_a, paid_a)
    for _, c in camps[(camps.platform_code == p) & (camps.campaign_type == "BRAND_DAY")].iterrows():
        w = C2[(C2.platform_code == p) & (C2.date.between(c.start_date, c.end_date))]
        exp_c = min(COFUND[p][1], round(w.seller_voucher_amt.sum() * COFUND[p][0] / 100)); paid_c = exp_c
        if c.campaign_id == "TTK-BD-09": paid_c = None
        if c.campaign_id == "LZD-BD-05": paid_c = round(.5 * exp_c)
        add_stmt(p, "BRAND_DAY_COFUND", c.campaign_id, c.start_date, c.end_date, exp_c, paid_c)
STMT = pd.DataFrame(stmt)
GT_PROG = pd.DataFrame(gt_prog, columns=["platform_code", "program_code", "period_label", "expected_idr", "paid_idr", "shortfall_idr"])
GT_SET = pd.DataFrame(gt_set, columns=["platform_code", "order_id", "discrepancy_type", "impact_idr"])
print("thresholds", thr)
print(GT_PROG.to_string())
print(GT_SET.discrepancy_type.value_counts().to_dict())
print("settlement rows", len(SETTLE), "ERP rows", len(ERP), "stmt rows", len(STMT))
pickle.dump(dict(SETTLE=SETTLE, ERP=ERP, ADS=ADS, ADS_GAP=ADS_GAP, JBP=JBP, STMT=STMT, GT_PROG=GT_PROG, GT_SET=GT_SET, fee_contract=fee_contract,
                 COMM_DISC=COMM_DISC, FEE=FEE), open(f"{BUILD}/fin.pkl", "wb"))
