// =====================================================================================
// power_query.pq : cara memuat model dari PostgreSQL ke Power BI Desktop
// Home > Get Data > Blank Query > Advanced Editor; buat satu query per tabel di bawah.
// Pertama: buat parameter  pServer (mis. "localhost:5432")  dan  pDatabase ("ecom_lumina").
// Mode: Import untuk semua (data harian); DirectQuery hanya untuk halaman real-time (PriceAlerts, Suspicious).
// =====================================================================================

// --- Fungsi umum: ambil satu relasi/view PostgreSQL
// Simpan sebagai query "fnPg"
(schemaName as text, objectName as text) as table =>
let
    Source = PostgreSQL.Database(pServer, pDatabase),
    Obj    = Source{[Schema = schemaName, Item = objectName]}[Data]
in
    Obj

// --- Daftar query (masing-masing: = fnPg("schema", "objek"))
// Dimensi
//   DimDate           = fnPg("dwh",  "dim_date")
//   DimPlatform       = fnPg("dwh",  "dim_platform")
//   DimSKU            = fnPg("dwh",  "dim_sku")
//   DimCampaign       = fnPg("dwh",  "dim_campaign")
// Fakta / mart
//   Sales             = fnPg("mart", "v_sales_daily")   // mv_sales_daily tidak tampil di Navigator; pakai view pembungkus
//   KPI_M             = fnPg("mart", "v_kpi_platform_month")
//   GMVTrend          = fnPg("mart", "v_gmv_trend_daily")
//   Ads               = fnPg("mart", "v_ads_daily")
//   AdsPlatformDaily  = fnPg("mart", "v_ads_platform_daily")
//   Voucher           = fnPg("mart", "v_voucher_performance")
//   VoucherAOV        = fnPg("mart", "v_voucher_aov_uplift")
//   Campaign          = fnPg("mart", "v_campaign_performance")
//   SKUMargin         = fnPg("mart", "v_sku_margin")
//   JBP               = fnPg("mart", "v_jbp_attainment")
//   JBPPacing         = fnPg("mart", "v_jbp_pacing")
//   PriceParity       = fnPg("mart", "v_price_parity_daily")
//   CustomerRepeat    = fnPg("mart", "v_customer_repeat")
//   Region            = fnPg("mart", "v_region_month")
//   Heatmap           = fnPg("mart", "v_hourly_heatmap")
// Kepatuhan & risiko
//   PriceAlerts       = fnPg("ops",  "v_price_alerts_latest")
//   PriceEpisodes     = fnPg("ops",  "v_price_violation_episodes")
//   PriceComplianceDaily = fnPg("ops", "v_price_compliance_daily")
//   PriceLeakage      = fnPg("ops",  "v_official_price_leakage_summary")
//   VoucherViolations = fnPg("ops",  "v_voucher_violation_summary")
//   Suspicious        = fnPg("ops",  "v_suspicious_orders_scored")
//   SuspiciousClusters= fnPg("ops",  "v_suspicious_buyer_clusters")
// Rekonsiliasi & banding
//   SettlementAudit   = fnPg("ops",  "v_settlement_audit")
//   ERPAudit          = fnPg("ops",  "v_erp_audit")
//   ProgramRecon      = fnPg("ops",  "v_program_reconciliation")
//   AppealPack        = fnPg("ops",  "v_appeal_pack")
//   AppealBoard       = fnPg("ops",  "v_appeal_board")
// Kualitas data & pipeline
//   DQLatest          = fnPg("ops",  "v_dq_latest")
//   DQScore           = fnPg("ops",  "v_dq_scorecard")
//   Freshness         = fnPg("ops",  "v_source_freshness")
//   PipelineHealth    = fnPg("ops",  "v_pipeline_health")

// --- Relasi (Model view)
//   DimDate[date]            1 -> * Sales[order_date], Ads[ad_date], Campaign (via start_date; relasi tidak aktif), PriceParity[snapshot_date]
//   DimPlatform[platform_code] 1 -> * Sales, KPI_M, Ads, Voucher, Campaign, JBP, JBPPacing, PriceAlerts, Suspicious, SettlementAudit, ProgramRecon, AppealPack
//   DimSKU[sku]              1 -> * Sales[sku], SKUMargin[sku], PriceAlerts[sku]
//   KPI_M[month_start]       * -> 1 DimDate[date] (hubungkan ke tanggal awal bulan; pakai tabel tanggal terpisah "DimMonth" bila perlu)
// Arah filter: single (dimensi -> fakta). Hindari relasi dua arah.

// =====================================================================================
// TAMBAHAN (butuh sql/14_mart_dashboard.sql sudah dijalankan)
//   DimMonth          = fnPg("mart", "dim_month")
//   KPIMonth          = fnPg("mart", "v_kpi_month_all")
//   Movers            = fnPg("mart", "v_sku_movers")
//   SubCat            = fnPg("mart", "v_subcat_month")
//   CC                = fnPg("mart", "v_command_center")
//   Money             = fnPg("mart", "v_money_on_table")
// Relasi tambahan:
//   DimMonth[month_start]   1 -> * KPIMonth[month_start], Movers[month_start], SubCat[month_start], KPI_M[month_start]
//   DimPlatform[platform_code] 1 -> * Movers[platform_code], SubCat[platform_code]
//   CC dan Money berdiri sendiri (tanpa relasi): CC difilter oleh measure [Platform Terpilih].
// Tabel kontrol (Home > Enter Data):
//   PlatSel  : code = ALL, SHP, TTK, LZD, BLI ; label = Semua, Shopee, TikTok Shop, Lazada, Blibli
//   Palette  : code = STD, CB ; label = Warna standar, Ramah buta warna
//   ChartMode: code = LINE, COL ; label = Garis, Kolom
//   TopN     : Modeling > New parameter > Numeric range, 1 sampai 10, naik 1, default 5
// =====================================================================================
