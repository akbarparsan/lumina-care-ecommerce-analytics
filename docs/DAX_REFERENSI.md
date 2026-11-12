# Referensi DAX

Dokumen ini dibangkitkan otomatis dari `powerbi/measures.dax` dan `powerbi/measures_dashboard.dax` oleh `gen/make_dax_reference.py`. Kode lengkap ada di kedua berkas itu; di sini ringkasannya per kelompok. Rumus satu baris ditampilkan utuh, rumus panjang diberi tanda *(lihat berkas)*.
**Total: 250 measure.**


## Model inti (82 measure) — `measures.dax` (82 measure)

### GMV (20)

| Measure | Rumus |
|---|---|
| Gross List GMV | `SUM ( Sales[gross_list_gmv] )` |
| GMV Placed | `SUM ( Sales[gmv_placed] )` |
| Net GMV | `SUM ( Sales[net_gmv] )` |
| Completed GMV | `SUM ( Sales[completed_gmv] )` |
| Cancelled GMV | `SUM ( Sales[gmv_cancelled] )` |
| Returned GMV | `SUM ( Sales[gmv_returned] )` |
| Net Units | `SUM ( Sales[net_units] )` |
| Cancel Rate | `DIVIDE ( [Cancelled GMV], [GMV Placed] )` |
| Return Rate | `DIVIDE ( [Returned GMV], [GMV Placed] )` |
| Price Discount Depth | `DIVIDE ( [Gross List GMV] - [GMV Placed], [Gross List GMV] )` |
| Seller Voucher Cost | `SUM ( Sales[seller_voucher_cost] )` |
| Seller Voucher Rate | `DIVIDE ( [Seller Voucher Cost], [Net GMV] )` |
| Net Sales | `[Net GMV] - [Seller Voucher Cost]` |
| Net GMV LY | `CALCULATE ( [Net GMV], SAMEPERIODLASTYEAR ( DimDate[date] ) )` |
| Net GMV MTD | `CALCULATE ( [Net GMV], DATESMTD ( DimDate[date] ) )` |
| Net GMV MoM % | *(lihat berkas)* |
| Net GMV 7D Avg | `AVERAGEX ( DATESINPERIOD ( DimDate[date], MAX ( DimDate[date] ), -7, DAY ), [Net GMV] )` |
| Platform Share % | `DIVIDE ( [Net GMV], CALCULATE ( [Net GMV], ALL ( DimPlatform ) ) )` |
| Orders (Net) | `SUM ( KPI_M[orders_net] )` |
| AOV | `DIVIDE ( SUM ( KPI_M[net_gmv] ), [Orders (Net)] )` |

### PROFITABILITAS (6)

| Measure | Rumus |
|---|---|
| Platform Fees | `SUM ( KPI_M[platform_fees] )` |
| COGS | `SUM ( KPI_M[cogs] )` |
| CM1 | `SUM ( KPI_M[cm1] )` |
| CM2 | `SUM ( KPI_M[cm2] )` |
| CM1 % | `DIVIDE ( [CM1], SUM ( KPI_M[net_sales] ) )` |
| CM2 % | `DIVIDE ( [CM2], SUM ( KPI_M[net_sales] ) )` |

### IKLAN (11)

| Measure | Rumus |
|---|---|
| Ad Spend | `SUM ( Ads[spend] )` |
| Ad GMV | `SUM ( Ads[ad_gmv] )` |
| ROAS | `DIVIDE ( SUM ( Ads[ad_gmv_reliable] ), SUM ( Ads[spend_reliable] ) )` |
| CPC | `DIVIDE ( SUM ( Ads[spend_reliable] ), SUM ( Ads[clicks_reliable] ) )` |
| CTR | `DIVIDE ( SUM ( Ads[clicks] ), SUM ( Ads[impressions] ) )` |
| CVR | `DIVIDE ( SUM ( Ads[ad_orders] ), SUM ( Ads[clicks] ) )` |
| Cost per Order | `DIVIDE ( SUM ( Ads[spend_reliable] ), SUM ( Ads[ad_orders_reliable] ) )` |
| TACOS | `DIVIDE ( [Ad Spend], [Net GMV] )` |
| Ad-Attributed Share | `DIVIDE ( [Ad GMV], [GMV Placed] )` |
| Break-even ROAS | `DIVIDE ( 1, [CM1 %] )            // ROAS minimum agar iklan tidak merugikan margin` |
| ROAS Gap | `[ROAS] - [Break-even ROAS]       // negatif = iklan membakar margin` |

### VOUCHER (10)

| Measure | Rumus |
|---|---|
| Voucher Redemptions | `SUM ( Voucher[redemptions_valid] )` |
| Voucher Discount | `SUM ( Voucher[discount_given] )` |
| Voucher Seller Cost | `SUM ( Voucher[seller_cost] )` |
| Voucher Platform Cost | `SUM ( Voucher[platform_cost] )` |
| Quota Burn % | `DIVIDE ( SUM ( Voucher[redemptions] ), SUM ( Voucher[quota] ) )` |
| Budget Utilization | `DIVIDE ( SUM ( Voucher[seller_cost] ), SUM ( Voucher[budget_idr] ) )` |
| GMV per Seller Rp | `DIVIDE ( SUM ( Voucher[gmv_on_voucher_orders] ), SUM ( Voucher[seller_cost] ) )` |
| Over-Quota Vouchers | `CALCULATE ( DISTINCTCOUNT ( Voucher[voucher_code] ), FILTER ( Voucher, Voucher[quota_burn] > 1 ) )` |
| AOV Uplift (Voucher) | `AVERAGE ( VoucherAOV[aov_uplift] )` |
| Voucher Penetration % | `AVERAGE ( VoucherAOV[voucher_penetration_pct] ) / 100` |

### KAMPANYE (5)

| Measure | Rumus |
|---|---|
| Campaign Uplift % | `AVERAGE ( Campaign[gmv_uplift_vs_baseline] )` |
| Incremental GMV | `SUM ( Campaign[incremental_gmv] )` |
| Incremental CM2 | `SUM ( Campaign[incremental_cm2] )` |
| Margin-Burning Campaigns | `CALCULATE ( COUNTROWS ( Campaign ), Campaign[verdict] = "MERUGIKAN MARGIN" )` |
| Campaign Verdict Color | `IF ( [Incremental CM2] < 0, "#C0392B", "#1E8449" )` |

### JBP (9)

| Measure | Rumus |
|---|---|
| JBP Completed GMV | `SUM ( JBP[completed_gmv] )` |
| Attainment Tier 1 | `DIVIDE ( [JBP Completed GMV], SUM ( JBP[tier1_threshold] ) )` |
| Attainment Tier 2 | `DIVIDE ( [JBP Completed GMV], SUM ( JBP[tier2_threshold] ) )` |
| Expected Rebate | `SUM ( JBP[expected_rebate_idr] )` |
| Gap to Tier 2 | `SUM ( JBP[gap_to_tier2_idr] )` |
| Projected Q GMV | `SUM ( JBPPacing[projected_quarter_gmv] )` |
| Required Daily GMV | `SUM ( JBPPacing[required_daily_gmv_for_tier2] )` |
| Run Rate Daily GMV | `SUM ( JBPPacing[current_daily_run_rate] )` |
| Pacing Gap per Day | `[Run Rate Daily GMV] - [Required Daily GMV]` |

### KEPATUHAN HARGA & PROMO (8)

| Measure | Rumus |
|---|---|
| Active Price Alerts | `COUNTROWS ( PriceAlerts )` |
| Critical Alerts | `CALCULATE ( COUNTROWS ( PriceAlerts ), PriceAlerts[severity] = "CRITICAL" )` |
| Violation Episodes | `COUNTROWS ( PriceEpisodes )` |
| Avg Hours Exposed | `AVERAGE ( PriceEpisodes[approx_hours_exposed] )` |
| Price Compliance % | `AVERAGE ( PriceComplianceDaily[compliance_rate] )` |
| Official Price Leakage | `SUM ( PriceLeakage[leakage_idr] )` |
| Voucher Rule Violations | `SUM ( VoucherViolations[orders] )` |
| Voucher Exposure Rp | `SUM ( VoucherViolations[exposure_idr] )` |

### ORDER MENCURIGAKAN (4)

| Measure | Rumus |
|---|---|
| Flagged Orders | `COUNTROWS ( Suspicious )` |
| Flagged GMV | `SUM ( Suspicious[gmv_placed] )` |
| Critical+High Orders | `CALCULATE ( COUNTROWS ( Suspicious ), Suspicious[risk_level] IN { "CRITICAL", "HIGH" } )` |
| Flagged Order Share | `DIVIDE ( [Flagged Orders], SUM ( KPI_M[orders_placed] ) )` |

### REKONSILIASI & BANDING (5)

| Measure | Rumus |
|---|---|
| Claimable Amount | `SUM ( AppealPack[claim_idr] )` |
| Claim Cases | `SUM ( AppealPack[cases] )` |
| Program Shortfall | `CALCULATE ( SUM ( ProgramRecon[shortfall_idr] ), ProgramRecon[recon_status] IN { "SHORT_PAID", "UNPAID" } )` |
| Recovery Rate | `DIVIDE ( SUM ( AppealBoard[recovered_idr] ), SUM ( AppealBoard[claim_idr] ) )` |
| Unsettled Orders | `CALCULATE ( COUNTROWS ( SettlementAudit ), SettlementAudit[discrepancy_type] = "UNSETTLED_AGING" )` |

### KUALITAS DATA (4)

| Measure | Rumus |
|---|---|
| DQ Pass % | *(lihat berkas)* |
| DQ Critical Failed | `CALCULATE ( COUNTROWS ( DQLatest ), DQLatest[status] = "FAIL", DQLatest[severity] = "CRITICAL" )` |
| Data Freshness (days) | `MAX ( Freshness[lag_days] )` |
| Publish Gate | `IF ( [DQ Critical Failed] > 0, "TAHAN PUBLIKASI", "AMAN" )` |

## Dashboard (Command Center, Analisis, Recovery & Kepatuhan) — `measures_dashboard.dax` (168 measure)

### Pemilihan (4)

| Measure | Rumus |
|---|---|
| Platform Terpilih | `SELECTEDVALUE ( PlatSel[code], "ALL" )` |
| Palet Terpilih | `SELECTEDVALUE ( Palette[code], "STD" )` |
| Mode Grafik | `SELECTEDVALUE ( ChartMode[code], "LINE" )` |
| TopN Nilai | `SELECTEDVALUE ( TopN[TopN], 5 )` |

### Kartu detail Command Center (20)

| Measure | Rumus |
|---|---|
| CC Net GMV | *(lihat berkas)* |
| CC CM2 | *(lihat berkas)* |
| CC CM2 % | *(lihat berkas)* |
| CC TACOS | *(lihat berkas)* |
| CC ROAS | *(lihat berkas)* |
| CC Order Valid | *(lihat berkas)* |
| CC Klaim Rp | *(lihat berkas)* |
| CC Klaim Kasus | *(lihat berkas)* |
| CC Alert Harga | *(lihat berkas)* |
| CC Order Berisiko | *(lihat berkas)* |
| CC Risiko Tinggi | *(lihat berkas)* |
| CC Pacing Status | *(lihat berkas)* |
| CC Pacing Warning | `IF ( CONTAINSSTRING ( [CC Pacing Status], "BAWAH" ), 1, 0 )` |
| Rp Ringkas (CC Net GMV) | *(lihat berkas)* |
| CC Klaim Teks | `"Rp" & FORMAT ( [CC Klaim Rp] / 1000000, "0.0" ) & " jt · " & FORMAT ( [CC Klaim Kasus], "#,0" ) & " kasus"` |
| Uang Klaim | `"Rp" & FORMAT ( SUM ( Money[claimable_idr] ) / 1000000, "0.0" ) & " jt"` |
| Uang Kebocoran | `"Rp" & FORMAT ( SUM ( Money[price_leakage_idr] ) / 1000000, "0.0" ) & " jt"` |
| Uang Voucher | `"Rp" & FORMAT ( SUM ( Money[voucher_exposure_idr] ) / 1000000, "0.0" ) & " jt"` |
| Gerbang Data | `IF ( MAX ( Money[publish_gate] ) = "OK_TO_PUBLISH", "Aman", "Tahan publikasi" )` |
| Gerbang Data Detail | `SUM ( Money[dq_passed] ) & " lulus · " & SUM ( Money[dq_failed] ) & " peringatan · " & SUM ( Money[dq_critical_failed] ) & " kritis"` |

### Kartu KPI gaya referensi (17)

| Measure | Rumus |
|---|---|
| Bulan Aktif | `MAX ( DimMonth[month_start] )` |
| Net GMV Bulan | `SUM ( KPIMonth[net_gmv] )` |
| CM2 Bulan | `SUM ( KPIMonth[cm2] )` |
| Belanja Iklan Bulan | `SUM ( KPIMonth[ad_spend] )` |
| TACOS Bulan | `DIVIDE ( [Belanja Iklan Bulan], [Net GMV Bulan] )` |
| Delta Net GMV | `SUM ( KPIMonth[delta_net_gmv] )` |
| Delta Net GMV % | `AVERAGE ( KPIMonth[delta_net_gmv_pct] )` |
| Delta CM2 | `SUM ( KPIMonth[delta_cm2] )` |
| Delta CM2 % | `AVERAGE ( KPIMonth[delta_cm2_pct] )` |
| Delta Iklan | `SUM ( KPIMonth[delta_ad_spend] )` |
| Delta Iklan % | `AVERAGE ( KPIMonth[delta_ad_spend_pct] )` |
| Rata-rata Bulanan Net GMV | `AVERAGEX ( ALL ( KPIMonth[month_start] ), CALCULATE ( SUM ( KPIMonth[net_gmv] ) ) )` |
| Rata-rata Bulanan CM2 | `AVERAGEX ( ALL ( KPIMonth[month_start] ), CALCULATE ( SUM ( KPIMonth[cm2] ) ) )` |
| Rata-rata Bulanan Iklan | `AVERAGEX ( ALL ( KPIMonth[month_start] ), CALCULATE ( SUM ( KPIMonth[ad_spend] ) ) )` |
| Bulan Terbaik Net GMV | *(lihat berkas)* |
| Bulan Terbaik CM2 | *(lihat berkas)* |
| Bulan Puncak Iklan | *(lihat berkas)* |

### Metrik berganti lewat tab (4)

| Measure | Rumus |
|---|---|
| Metrik Net GMV | `[Net GMV Bulan]` |
| Metrik CM2 | `[CM2 Bulan]` |
| Metrik Iklan | `[Belanja Iklan Bulan]` |
| Warna Aksen Tab | *(lihat berkas)* |

### "Siapa naik, siapa turun" (15)

| Measure | Rumus |
|---|---|
| Mov Net GMV | *(lihat berkas)* |
| Mov Net GMV Lalu | *(lihat berkas)* |
| Mov Delta Rp | *(lihat berkas)* |
| Mov Delta % | `DIVIDE ( [Mov Delta Rp], [Mov Net GMV Lalu] )` |
| Mov Lolos Basis | `IF ( [Mov Net GMV Lalu] >= 5000000, 1, 0 )          // basis minimum Rp5 jt (cegah % ekstrem dari basis kecil)` |
| Mov Rank Naik | *(lihat berkas)* |
| Mov Total Peringkat | `COUNTROWS ( FILTER ( ALLSELECTED ( Movers[product_name], Movers[sub_category] ), [Mov Lolos Basis] = 1 ) )` |
| Mov Tampil | `IF ( [Mov Lolos Basis] = 1 && ( [Mov Rank Naik] <= [TopN Nilai] \|\| [Mov Rank Naik] > [Mov Total Peringkat] - [TopN Nilai] ), 1, 0 )` |
| Mov Nomor | `[Mov Rank Naik]` |
| Mov Panah | `IF ( [Mov Delta Rp] >= 0, "▲", "▼" )` |
| Mov Teks Delta | `[Mov Panah] & " " & IF ( [Mov Delta Rp] >= 0, "+", "−" ) & "Rp" & FORMAT ( ABS ( [Mov Delta Rp] ) / 1000000, "0.00" ) & " jt"` |
| Mov Teks Persen | `IF ( [Mov Delta %] >= 0, "+", "−" ) & FORMAT ( ABS ( [Mov Delta %] ), "0.0%" )` |
| Warna Naik | `IF ( [Palet Terpilih] = "CB", "#0072B2", "#1F6F78" )` |
| Warna Turun | `IF ( [Palet Terpilih] = "CB", "#D55E00", "#B8541F" )` |
| Mov Warna Batang | `IF ( [Mov Delta Rp] >= 0, [Warna Naik], [Warna Turun] )` |

### Sub-kategori + garis rata-rata (3)

| Measure | Rumus |
|---|---|
| Sub Net GMV | `SUM ( SubCat[net_gmv] )` |
| Sub Rata-rata | `AVERAGEX ( ALLSELECTED ( SubCat[sub_category] ), [Sub Net GMV] )     // pakai juga Analytics pane > Average line` |
| Sub Porsi % | `DIVIDE ( [Sub Net GMV], CALCULATE ( [Sub Net GMV], ALLSELECTED ( SubCat[sub_category] ) ) )` |

### KALIMAT INSIGHT DINAMIS (3)

| Measure | Rumus |
|---|---|
| Insight Platform | *(lihat berkas)* |
| Insight JBP | *(lihat berkas)* |
| Insight Tren | *(lihat berkas)* |

### Catatan cakupan data (1)

| Measure | Rumus |
|---|---|
| Catatan Data | *(lihat berkas)* |

### Grafik tren per platform: sorot platform terpilih (1)

| Measure | Rumus |
|---|---|
| Net GMV Tampil | `IF ( [Platform Terpilih] = "ALL" \|\| [Platform Terpilih] = SELECTEDVALUE ( KPI_M[platform_code] ), SUM ( KPI_M[net_gmv] ), BLANK () )` |

### HALAMAN ANALISIS: kartu, grafik, dan insight yang mengikuti TAB (30)

| Measure | Rumus |
|---|---|
| Tab Aktif | `SELECTEDVALUE ( TabSel[urut], 0 )          // 0 = Net GMV, 1 = CM2, 2 = Iklan` |
| Bulan Akhir | `CALCULATE ( MAX ( KPIMonth[month_start] ), ALL ( KPIMonth ), ALL ( DimMonth ) )` |
| Bulan Awal | `CALCULATE ( MIN ( KPIMonth[month_start] ), ALL ( KPIMonth ), ALL ( DimMonth ) )` |
| Bulan Akhir Label | `LOOKUPVALUE ( DimMonth[month_label], DimMonth[month_start], [Bulan Akhir] )` |
| Bulan Awal Label | `LOOKUPVALUE ( DimMonth[month_label], DimMonth[month_start], [Bulan Awal] )` |
| Seri Net GMV | `IF ( [Tab Aktif] = 0, SUM ( KPIMonth[net_gmv] )   / 1000000, BLANK () )` |
| Seri CM2 | `IF ( [Tab Aktif] = 1, SUM ( KPIMonth[cm2] )       / 1000000, BLANK () )` |
| Seri Iklan | `IF ( [Tab Aktif] = 2, SUM ( KPIMonth[ad_spend] )  / 1000000, BLANK () )` |
| KPI Nilai | *(lihat berkas)* |
| KPI Delta | *(lihat berkas)* |
| KPI Delta Pct | *(lihat berkas)* |
| KPI Rata-rata | `SWITCH ( [Tab Aktif], 0, [Rata-rata Bulanan Net GMV], 1, [Rata-rata Bulanan CM2], [Rata-rata Bulanan Iklan] )` |
| KPI Judul | `SWITCH ( [Tab Aktif], 0, "Net GMV", 1, "CM2", "Belanja iklan" ) & " · " & [Bulan Akhir Label] & " " & YEAR ( [Bulan Akhir] )` |
| KPI Nilai Teks | `"Rp" & FORMAT ( [KPI Nilai] / 1000000, "#,0.0" ) & " jt"` |
| KPI Rata Teks | *(lihat berkas)* |
| KPI Terbaik Teks | *(lihat berkas)* |
| KPI Panah | `IF ( [KPI Delta] >= 0, "▲", "▼" )` |
| KPI Delta Teks | `[KPI Panah] & " " & IF ( [KPI Delta] >= 0, "+", "−" ) & "Rp" & FORMAT ( ABS ( [KPI Delta] ) / 1000000, "#,0.0" ) & " jt"` |
| KPI Delta Pct Teks | `IF ( [KPI Delta Pct] >= 0, "+", "−" ) & FORMAT ( ABS ( [KPI Delta Pct] ) * 100, "0.0" ) & " % dari bulan sebelumnya"` |
| Warna Delta | `IF ( [KPI Delta] >= 0, [Warna Naik], [Warna Turun] )` |
| TACOS Akhir | *(lihat berkas)* |
| TACOS Awal | *(lihat berkas)* |
| KPI Extra | *(lihat berkas)* |
| Insight Analisis | *(lihat berkas)* |
| Insight Sub | *(lihat berkas)* |
| Mov Tampil Atas | `IF ( [Mov Lolos Basis] = 1 && [Mov Rank Naik] <= [TopN Nilai], 1, 0 )` |
| Mov Tampil Bawah | `IF ( [Mov Lolos Basis] = 1 && [Mov Rank Naik] > [Mov Total Peringkat] - [TopN Nilai], 1, 0 )` |
| Mov Delta Teks | `IF ( [Mov Delta Rp] >= 0, "+", "−" ) & "Rp" & FORMAT ( ABS ( [Mov Delta Rp] ) / 1000000, "0.00" ) & " jt"` |
| Mov Warna Teks | `IF ( [Mov Delta Rp] >= 0, IF ( [Palet Terpilih] = "CB", "#0072B2", "#2E8B57" ), IF ( [Palet Terpilih] = "CB", "#D55E00", "#C0392B" ) )` |
| Sub Net GMV Akhir | *(lihat berkas)* |

### INSIGHT NAIK/TURUN & SUB-KATEGORI (3)

| Measure | Rumus |
|---|---|
| Insight Naik Turun | *(lihat berkas)* |
| Insight Sub Gerak | *(lihat berkas)* |
| Insight Konsentrasi | *(lihat berkas)* |

### Uang yang bisa diselamatkan (6)

| Measure | Rumus |
|---|---|
| Klaim Rp | `SUM ( AppealPack[claim_idr] )` |
| Klaim Kasus | `SUM ( AppealPack[cases] )` |
| Klaim Rp Ringkas | `"Rp" & FORMAT ( [Klaim Rp] / 1000000, "#,0.0" ) & " jt"` |
| Klaim Kasus Teks | `FORMAT ( [Klaim Kasus], "#,0" ) & " kasus yang cukup bukti untuk diajukan"` |
| Klaim Label | `[Klaim Rp Ringkas] & " · " & FORMAT ( [Klaim Kasus], "#,0" ) & " kasus"` |
| Klaim Settlement Porsi | `DIVIDE ( CALCULATE ( [Klaim Rp], AppealPack[category] = "UNSETTLED_AGING" ), CALCULATE ( [Klaim Rp], ALL ( AppealPack[category] ) ) )` |

### Benefit program: dibayar vs seharusnya (6)

| Measure | Rumus |
|---|---|
| Prog Seharusnya | `SUM ( ProgramRecon[expected_idr] )` |
| Prog Dibayar | `SUM ( ProgramRecon[paid_idr] )` |
| Prog Kurang Klaim | `CALCULATE ( SUM ( ProgramRecon[shortfall_idr] ), ProgramRecon[recon_status] IN { "SHORT_PAID", "UNPAID" } )` |
| Prog Status Teks | *(lihat berkas)* |
| Prog Status Warna | *(lihat berkas)* |
| Insight Program | *(lihat berkas)* |

### Kepatuhan harga & promosi (11)

| Measure | Rumus |
|---|---|
| Episode | `COUNTROWS ( PriceEpisodes )` |
| Episode Reseller | `CALCULATE ( [Episode], PriceEpisodes[likely_root_cause] IN { "RESELLER_UNDERCUT_EPISODE", "RESELLER_PERSISTENT_UNDERCUT" } )` |
| Episode Salah Harga | `CALCULATE ( [Episode], PriceEpisodes[likely_root_cause] = "PRICE_ERROR_INCIDENT" )` |
| Episode Teks | `FORMAT ( [Episode], "#,0" ) & " episode"` |
| Bocor Rp | `SUM ( PriceLeakage[leakage_idr] )` |
| Bocor Order | `SUM ( PriceLeakage[orders] )` |
| Bocor Rp Ringkas | `"Rp" & FORMAT ( [Bocor Rp] / 1000000, "#,0.0" ) & " jt"` |
| Bocor Order Teks | `FORMAT ( [Bocor Order], "#,0" ) & " order di bawah floor"` |
| Alert Aktif | `COUNTROWS ( PriceAlerts )` |
| Alert Rincian | *(lihat berkas)* |
| Insight Kepatuhan | *(lihat berkas)* |

### Pelanggaran voucher (3)

| Measure | Rumus |
|---|---|
| Voucher Order | `SUM ( VoucherViolations[orders] )` |
| Voucher Paparan | `SUM ( VoucherViolations[exposure_idr] )` |
| Voucher Paparan Teks | `"Rp" & FORMAT ( [Voucher Paparan] / 1000000, "#,0.0" ) & " jt"` |

### Order berisiko (6)

| Measure | Rumus |
|---|---|
| Order Berisiko | `COUNTROWS ( Suspicious )` |
| GMV Berisiko | `SUM ( Suspicious[gmv_placed] )` |
| GMV Berisiko Teks | `"Rp" & FORMAT ( [GMV Berisiko] / 1000000, "#,0.0" ) & " jt"` |
| Order Kritis | `CALCULATE ( COUNTROWS ( Suspicious ), Suspicious[risk_level] = "CRITICAL" )` |
| Order Menyala | *(lihat berkas)* |
| Insight Risiko | *(lihat berkas)* |

### Gerbang publikasi (2)

| Measure | Rumus |
|---|---|
| Gerbang Teks | *(lihat berkas)* |
| Gerbang Warna | *(lihat berkas)* |

### GRAFIK TREN PER PLATFORM (10)

| Measure | Rumus |
|---|---|
| Net GMV Juta | `SUM ( KPI_M[net_gmv] ) / 1000000` |
| Net GMV Juta Pilih | *(lihat berkas)* |
| Net GMV Juta Akhir | *(lihat berkas)* |
| Net GMV Juta Tampil | *(lihat berkas)* |
| IF ( p | `"ALL" \|\| p = SELECTEDVALUE ( KPI_M[platform_code] ), SUM ( KPI_M[net_gmv] ) / 1000000, BLANK () )` |
| Label Net GMV | `"Net GMV · " & SELECTEDVALUE ( PlatSel[label], "Semua" )` |
| Warna Platform | `SELECTEDVALUE ( PlatSel[warna], "#1F6F78" )` |
| Insight Tren Platform | *(lihat berkas)* |
| Insight Tren Pilih | *(lihat berkas)* |
| IF ( p | *(lihat berkas)* |

### JBP, RINGKASAN, UANG DI MEJA (11)

| Measure | Rumus |
|---|---|
| JBP Kalimat | *(lihat berkas)* |
| JBP Ringkas | *(lihat berkas)* |
| JBP Detail | *(lihat berkas)* |
| IF ( p | *(lihat berkas)* |
| JBP Ikon | `IF ( COUNTROWS ( FILTER ( CC, CC[platform_code] <> "ALL" && CONTAINSSTRING ( CC[pacing_status], "DI BAWAH" ) ) ) > 0, "▲", "●" )` |
| CC Order Teks | `FORMAT ( [CC Order Valid], "#,0" ) & " order valid"` |
| Ringkas Nilai | *(lihat berkas)* |
| Uang Klaim Sub | *(lihat berkas)* |
| Uang Kebocoran Sub | `FORMAT ( SUM ( Money[leakage_orders] ), "#,0" ) & " order terjual di bawah floor (" & COUNTROWS ( PriceLeakage ) & " insiden salah harga)"` |
| Uang Voucher Sub | `FORMAT ( SUM ( Money[voucher_violation_orders] ), "#,0" ) & " order: di bawah min-spend, kedaluwarsa, over-kuota"` |
| Gerbang Ikon | `IF ( MAX ( Money[publish_gate] ) = "OK_TO_PUBLISH", "✔ ", "⚠ " ) & [Gerbang Data]` |

### REGION (4)

| Measure | Rumus |
|---|---|
| Region Net GMV | `SUM ( Region[net_gmv] )` |
| Region Rata-rata | `AVERAGEX ( ALLSELECTED ( Region[region] ), CALCULATE ( SUM ( Region[net_gmv] ) ) )` |
| Region Label | `"Rp" & FORMAT ( [Region Net GMV] / 1000000000, "0.00" ) & " mlr"` |
| Region Insight | *(lihat berkas)* |

### HALAMAN ANALISIS: judul, bulan terpilih, sorotan bar tertinggi (5)

| Measure | Rumus |
|---|---|
| Judul Tren | `SWITCH ( [Tab Aktif], 0, "Net GMV bulanan", 1, "Contribution Margin 2 (setelah iklan) bulanan", "Belanja iklan bulanan" )` |
| Bulan Pilih | `IF ( ISCROSSFILTERED ( DimMonth ), MAX ( DimMonth[month_start] ), [Bulan Akhir] )` |
| Nilai Seri Aktif | `SWITCH ( [Tab Aktif], 0, SUM ( KPIMonth[net_gmv] ), 1, SUM ( KPIMonth[cm2] ), SUM ( KPIMonth[ad_spend] ) ) / 1000000` |
| Warna Bar Tertinggi | *(lihat berkas)* |
| Label Bar Tertinggi | *(lihat berkas)* |

### Teks pelengkap kartu (2)

| Measure | Rumus |
|---|---|
| GMV Berisiko Label | `"GMV " & [GMV Berisiko Teks]` |
| Klaim Kasus Singkat | `FORMAT ( [Klaim Kasus], "#,0" ) & " kasus"` |

### Ikon SVG untuk tabel tingkat risiko (1)

| Measure | Rumus |
|---|---|
| Level Ikon | *(lihat berkas)* |
