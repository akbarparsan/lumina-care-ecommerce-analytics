# Model Power BI — tabel, relasi, kontrol, dan halaman

Berkas pendukung: [`powerbi/power_query.pq`](../powerbi/power_query.pq) (query), [`powerbi/measures.dax`](../powerbi/measures.dax) dan
[`powerbi/measures_dashboard.dax`](../powerbi/measures_dashboard.dax) (measure), [`DAX_REFERENSI.md`](DAX_REFERENSI.md), [`powerbi/deneb/`](../powerbi/deneb/).

## 1. Koneksi

- Get data → PostgreSQL. **Server** `127.0.0.1:5432` (bukan `localhost`, agar tidak diterjemahkan ke IPv6), **Database** `ecom_lumina`, mode **Import**.
- Buat parameter `pServer` dan `pDatabase`, lalu satu fungsi `fnPg(schema, objek)`; setiap tabel berupa `= fnPg("mart", "v_kpi_platform_month")` dan seterusnya.
- Navigator tidak menampilkan *materialized view*, maka `Sales` memakai `mart.v_sales_daily` (pembungkus `mart.mv_sales_daily`).
- Kredensial memakai tab **Database** (user `ecom`).

## 2. Tabel

| Kelompok | Tabel Power BI → sumber |
|---|---|
| Dimensi | `DimDate` → `dwh.dim_date` · `DimPlatform` → `dwh.dim_platform` · `DimSKU` → `dwh.dim_sku` · `DimCampaign` → `dwh.dim_campaign` · `DimMonth` → `mart.dim_month` |
| Penjualan | `Sales` → `mart.v_sales_daily` · `KPI_M` → `mart.v_kpi_platform_month` · `KPIMonth` → `mart.v_kpi_month_all` · `GMVTrend` → `mart.v_gmv_trend_daily` · `Region` → `mart.v_region_month` |
| Iklan, voucher, kampanye, JBP | `Ads`, `Voucher`, `VoucherAOV`, `Campaign`, `JBP`, `JBPPacing`, `SKUMargin` → `mart.v_*` |
| Analisis dashboard | `Movers` → `mart.v_sku_movers` · `SubCat` → `mart.v_subcat_month` · `CC` → `mart.v_command_center` · `Money` → `mart.v_money_on_table` |
| Kepatuhan & risiko | `PriceAlerts`, `PriceEpisodes`, `PriceLeakage`, `VoucherViolations`, `Suspicious` → `ops.v_*` |
| Rekonsiliasi & banding | `ProgramRecon`, `AppealPack`, `SettlementAudit`, `ERPAudit` → `ops.v_*` (`AppealBoard` tidak dimuat: kosong) |
| Kualitas data | `DQLatest` → `ops.v_dq_latest` · `DQScore` → `ops.v_dq_scorecard` |
| Tabel measure | `_Measures` (Enter data, kosong) tempat semua measure disimpan |

## 3. Relasi

Arah filter **single**, dari dimensi ke fakta. Hindari relasi dua arah.

| Dari (1) | Ke (*) |
|---|---|
| `DimDate[date]` | `Sales[order_date]`, `Ads[ad_date]`, `PriceParity[snapshot_date]` (`Campaign` lewat `start_date`, relasi tidak aktif) |
| `DimPlatform[platform_code]` | `Sales`, `KPI_M`, `Ads`, `Voucher`, `Campaign`, `JBP`, `JBPPacing`, `PriceAlerts`, `PriceEpisodes`, `PriceLeakage`, `VoucherViolations`, `Suspicious`, `ProgramRecon`, `AppealPack`, `Movers`, `SubCat`, `Region` |
| `DimSKU[sku]` | `Sales[sku]`, `SKUMargin[sku]`, `PriceAlerts[sku]` |
| `DimMonth[month_start]` | `KPIMonth`, `Movers`, `SubCat`, `KPI_M` |

Tanpa relasi (disengaja): `CC` dan `Money` (disaring oleh measure `[Platform Terpilih]`), `DQScore`, dan seluruh **tabel kontrol** di bawah.

> **Peringatan:** Power BI membuat relasi otomatis antar kolom yang namanya sama. `TabSel[urut]` dan `Aturan[urut]` pernah tersambung sendiri dan mempersempit daftar slicer.
> Setelah menambah tabel kontrol, buka Model view dan hapus garis yang tidak direncanakan; matikan **File → Options → Current File → Data Load → Autodetect new relationships**.

## 4. Tabel kontrol (Enter data) — tanpa relasi

| Tabel | Isi | Dipakai oleh |
|---|---|---|
| `PlatSel` | code ALL/SHP/TTK/LZD/BLI · label Semua/Shopee/TikTok Shop/Lazada/Blibli · warna | `[Platform Terpilih]`, tombol platform |
| `TabSel` | urut 0/1/2 · label Net GMV/Margin (CM2)/Iklan | `[Tab Aktif]` |
| `Palette` | code STD/CB · label Warna standar/Ramah buta warna | `[Palet Terpilih]` |
| `ChartMode` | code LINE/COL · label Garis/Kolom | `[Mode Grafik]` |
| `TopN` | parameter numerik 1–10, default 5 (Modeling → New parameter) | `[TopN Nilai]` |
| `Aturan` | kode R1–R5 · nama aturan · urut | tabel "Aturan yang menyala" |
| `RingkasRows` | urut 1–3 | `[Ringkas Nilai]` |

## 5. Kolom hitung (New column, bukan measure)

| Tabel | Kolom | Isi |
|---|---|---|
| `AppealPack` | `Kategori Label` | Nama kategori klaim dalam bahasa Indonesia |
| `ProgramRecon` | `Program Periode` | `program_code & " · " & period_label` |
| `PriceEpisodes` | `Akar Masalah` | Nama akar masalah dalam bahasa Indonesia |
| `VoucherViolations` | `Aturan Label` | Nama pelanggaran voucher |
| `Suspicious` | `Level Label`, `Level Nama`, `Level Urut` | Tingkat risiko dengan simbol, nama, urutan (Sort by column → `Level Urut`) |

Kode lengkap ada di blok "KOLOM HITUNG" pada `measures_dashboard.dax` (ditulis sebagai komentar; salin tanpa tanda `//`).

## 6. Halaman dan visual

### Command Center
- Slicer platform (`PlatSel[label]` berbentuk tombol; warna tombol mengikuti warna platform).
- Kartu per platform dari `CC` lewat measure `CC ...`, kartu "uang di meja" dari `Money`, kartu JBP (`JBP Ringkas`, `JBP Detail`).
- Grafik tren Net GMV bulanan: **tiga grafik garis bertumpuk** (dasar semua platform, tebal platform terpilih, titik bulan terakhir) dengan ukuran dan sumbu identik.
- Batang wilayah (`powerbi/deneb/region_bar.vl.json`) dan kalimat insight dinamis.

### Analisis
- Slicer tersembunyi `TabSel[label]` (pilihan tunggal) + tiga tombol tab berbasis bookmark (*Data On, Display Off, Current page On*).
- Dua kartu KPI: `KPI Judul`, `KPI Nilai Teks`, `KPI Rata Teks`, `KPI Terbaik Teks`, `KPI Delta Teks`, `KPI Delta Pct Teks`, `KPI Extra`.
- Grafik tren per tab (`Seri Net GMV`, `Seri CM2`, `Seri Iklan`) dengan pengalih Garis/Kolom (bookmark) dan sorotan bulan tertinggi (`Warna Bar Tertinggi`).
- Dua tabel *Top N naik / turun* (filter visual `Mov Tampil Atas = 1` dan `Mov Tampil Bawah = 1`; warna teks `Mov Warna Teks`).
- Panel sub-kategori (`powerbi/deneb/subkategori.vl.json`) dan insight `Insight Analisis`, `Insight Naik Turun`, `Insight Sub`, `Insight Sub Gerak`, `Insight Konsentrasi`.
- Slicer bulan dropdown (`DimMonth[month_label]`, urut menurut `month_no`) memakai `Bulan Pilih`; gunakan **Edit interactions → None** pada visual yang tidak boleh ikut.

### Recovery & Kepatuhan
- Uang yang bisa diselamatkan: kartu `Klaim Rp Ringkas` + `Klaim Kasus Teks`, empat kartu per platform (filter visual per platform), batang per kategori (`powerbi/deneb/klaim_kategori.vl.json`).
- Benefit program: tabel `ProgramRecon` (filter `recon_status ≠ MATCHED`) dengan `Prog Status Teks` dan `Prog Status Warna`; `Insight Program`.
- Kepatuhan harga & promosi: batang akar masalah (`powerbi/deneb/akar_masalah.vl.json`), kartu kebocoran dan alert aktif, tabel voucher, `Insight Kepatuhan`.
- Order berisiko: batang proporsi 100 % menurut `Level Nama`, daftar tingkat (ikon SVG dari measure `Level Ikon`), tabel "Aturan yang menyala" (`Order Menyala`), `Insight Risiko`.
- Banner gerbang publikasi: `Gerbang Teks` dengan warna `Gerbang Warna`.

## 7. Spesifikasi Deneb

Seluruh spesifikasi memakai Vega-Lite 5 dan nama field yang harus persis sama dengan yang diseret ke *Values*:

| Berkas | Field di Values |
|---|---|
| `deneb/region_bar.vl.json` | `Region[region]`, `[Region Net GMV]` |
| `deneb/subkategori.vl.json` | `SubCat[sub_category]`, `[Sub Net GMV Akhir]`, `[Warna Aksen Tab]` |
| `deneb/klaim_kategori.vl.json` | `AppealPack[Kategori Label]`, `[Klaim Rp]`, `[Klaim Kasus]` |
| `deneb/akar_masalah.vl.json` | `PriceEpisodes[Akar Masalah]`, `[Episode]` |

Cara memasang: tambahkan visual **Deneb** → isi *Values* → **… → Edit** → pilih **Vega-Lite** → tempel spesifikasi → **Apply**.
Warna di Deneb bersifat tetap (tidak membaca palet Power BI).

## 8. Tema dan aksesibilitas

- `lumina_theme.json` (warna data #1F6F78, #B8541F, #5B4B9A, #2B6CB0, #2F9E6E, #E0A15C, #8E5BB5, #5E676B; latar halaman #F5F1EA) dan `lumina_theme_buta_warna.json` (palet Okabe–Ito). Pasang lewat **View → Themes → Browse for themes**.
- Tombol palet (`Palette`) mengganti warna yang dikendalikan measure (naik/turun, aksen tab, warna teks movers); tema mengganti warna bawaan visual. Keduanya saling melengkapi, dan Deneb tidak ikut.
- Informasi tidak hanya bergantung pada warna: panah ▲▼, simbol ◆▲●○, dan kata tingkat risiko selalu ditampilkan. Isi *Alt text* pada setiap visual.

## 9. Daftar periksa sebelum publikasi

- [ ] `Net GMV` total di model = `SUM(net_gmv)` di `mart.v_kpi_platform_month` (Rp7.280.003.300).
- [ ] Pilih tiap platform: kartu Command Center berubah (CM2 %, ROAS, order valid, pacing).
- [ ] Ganti tab Net GMV / CM2 / Iklan: kartu, grafik, dan warna berubah; bookmark diperbarui setelah slicer berada pada tab yang benar.
- [ ] Tabel movers: lima teratas dan lima terbawah dari SKU yang lolos basis Rp5 jt, peringkat tidak berulang per kategori; Daily Sunscreen +Rp10,1 jt paling atas, Anti-Dandruff Shampoo −Rp11,9 jt paling bawah.
- [ ] Recovery: total klaim Rp85.270.011 dan 1.307 kasus; kategori program kurang bayar + tidak dibayar = Rp12.481.037.
- [ ] Order berisiko 1.560 (84 / 602 / 513 / 361); R1 225, R2 378, R3 33, R4 666, R5 362.
- [ ] Model view: tidak ada relasi pada tabel kontrol.
- [ ] Gerbang publikasi "aman" dan catatan cakupan data memuat kalimat "Semua angka fiktif".
