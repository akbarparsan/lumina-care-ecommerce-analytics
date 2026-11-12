# Kamus KPI — Lumina Care (Personal Care, 4 marketplace)

Seluruh angka dihitung dari data **sintetis & fiktif**. Sumber SQL: `sql/07_marts_kpi.sql` kecuali dinyatakan lain.
Rupiah (IDR); periode 2026-01-01 s.d. 2026-10-31.

## 1. Penjualan
| KPI | Definisi | Catatan |
|---|---|---|
| Gross List GMV | Σ harga list × qty (semua order dibuat) | Dasar kedalaman diskon |
| GMV Placed | Σ harga setelah diskon penjual × qty | Belum dikurangi voucher |
| Net GMV | GMV Placed − batal − retur (status valid: selesai + masih dikirim) | KPI utama "penjualan valid" |
| Completed GMV | GMV order berstatus COMPLETED | Dasar tier rebate JBP |
| Net Sales | Net GMV − voucher penjual | Voucher platform diganti platform, tidak mengurangi brand |
| Price Discount Depth | 1 − GMV Placed / Gross List GMV | Seberapa dalam kita menjual di bawah harga list |
| Cancel / Return Rate | GMV batal (retur) / GMV Placed | |
| AOV | Net GMV / jumlah order valid | |
| WoW / MoM / MA7 | Pertumbuhan & rata-rata bergerak (`v_gmv_trend_daily`, `v_kpi_platform_month`) | |

## 2. Profitabilitas (advanced)
| KPI | Definisi |
|---|---|
| Biaya platform | Net Sales × (komisi + layanan + pembayaran) sesuai kontrak; komisi dikurangi poin diskon saat Double Date/Brand Day |
| CM1 | Net Sales − COGS − biaya platform |
| CM2 | CM1 − belanja iklan |
| CM2 % | CM2 / Net Sales |
| CM1 per SKU × platform × (kampanye / non-kampanye) | `mart.v_sku_margin` — menemukan SKU yang "membakar" margin saat kampanye |

## 3. Iklan
| KPI | Definisi | Catatan |
|---|---|---|
| ROAS | GMV atribusi iklan / belanja iklan | Hanya dari baris `spend_reliable` |
| TACOS | Belanja iklan / Net GMV | Pengukur ketergantungan pada iklan, bukan sekadar efisiensi |
| CTR, CVR, CPC, Cost/Order | Standar | Baris spend=0 dengan klik dikeluarkan dari pembilang rasio |
| Break-even ROAS | 1 / CM1 % | ROAS di bawah ini = iklan merugikan margin (DAX: `Break-even ROAS`) |
| Ad-attributed share | GMV atribusi iklan / GMV Placed | Cek kewajaran atribusi platform |

## 4. Voucher
| KPI | Definisi |
|---|---|
| Quota burn | redemption / kuota; > 100 % = over-quota |
| Budget utilization | biaya penjual / budget voucher |
| GMV per Rp penjual | GMV order bervoucher / biaya penjual |
| AOV uplift | AOV order bervoucher / AOV tanpa voucher − 1 (per platform-bulan) |
| Voucher penetration | % order valid memakai voucher |
| Pelanggaran aturan | V1 di bawah min-spend, V2 di luar masa berlaku, V3 melewati kuota (`ops.v_voucher_rule_violations`) |
| Pecah biaya | Voucher platform co-fund dipecah: bagian penjual vs platform (`v_order_voucher_split`) |

## 5. Kampanye
| KPI | Definisi |
|---|---|
| Uplift GMV | (GMV/hari saat kampanye) / (rata-rata GMV/hari 14 hari non-kampanye sebelumnya) − 1 |
| Incremental GMV / CM2 | (nilai/hari kampanye − baseline/hari) × jumlah hari |
| Verdict | MERUGIKAN MARGIN bila Incremental CM2 < 0 — "GMV naik tetapi uang hilang" |

## 6. JBP (Joint Business Plan)
| KPI | Definisi |
|---|---|
| Attainment tier 1/2 | Completed GMV kuartal / ambang tier |
| Expected rebate | Completed GMV × tarif tier tercapai |
| Pacing | Proyeksi GMV kuartal = run-rate × hari kuartal; GMV harian yang dibutuhkan untuk tier 2 |
| Benefit program | Rebate kuartalan, co-fund Brand Day (% biaya voucher penjual, cap), kredit iklan (% belanja iklan, cap) |

## 7. Kepatuhan harga & promosi
| KPI | Definisi |
|---|---|
| Floor berlaku | MAP (0,78–0,82 × RRP per sub-kategori); floor kampanye 0,70 × RRP hanya pada hari Double Date/Brand Day |
| BELOW_MAP | Harga satuan (paket dibagi isi) di bawah floor yang berlaku |
| STRIKE_PRICE_INFLATION | Harga coret dinaikkan melebihi RRP agar diskon tampak besar |
| Episode pelanggaran | Rentetan snapshot berurutan yang melanggar (gaps-and-islands) + durasi jam terpapar + akar masalah |
| Kebocoran harga | Σ (floor − harga jual) × qty pada order toko resmi di bawah floor |
| Compliance rate | 1 − (snapshot melanggar / snapshot valid) |

## 8. Order mencurigakan
Skor risiko = jumlah bobot aturan (R1 qty besar 40, R2 velocity 35, R3 akun kembar 40, R4 harga anomali 50, R5 voucher 15).
Level: CRITICAL ≥ 80, HIGH ≥ 50, MEDIUM ≥ 30, LOW lainnya. Lihat `ops.suspicious_rule`.

## 9. Rekonsiliasi & banding
| Temuan | Definisi |
|---|---|
| COMMISSION_OVERCHARGE | Komisi settlement > (net sales × tarif kontrak setelah diskon poin kampanye) + toleransi |
| VOUCHER_SUBSIDY_MISSING | Kredit voucher platform di settlement < voucher platform di order |
| DUPLICATE_SETTLEMENT_ROW | Baris settlement ganda untuk order yang sama |
| ORPHAN_SETTLEMENT | Settlement tanpa order padanan |
| UNSETTLED_AGING | Order selesai tanpa settlement > 14 hari |
| ERP_MISSING / ERP_AMOUNT_MISMATCH / ERP_ONLY_CANCELLED | Selisih antara ERP internal dan order platform |
| Program SHORT_PAID / UNPAID / OVER_PAID | Expected vs dibayar dengan toleransi (`ops.recon_tolerance`) |

Konvensi `impact_idr`: positif = uang yang seharusnya kita terima; negatif = kelebihan/tidak berdasar.

## 10. Kualitas data
`ops.v_dq_checks` (±34 pemeriksaan). CRITICAL gagal ⇒ `publish_gate = BLOCK_PUBLISH`.
