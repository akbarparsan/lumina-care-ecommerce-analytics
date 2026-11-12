# Proses pengerjaan — Lumina Care

Dokumen ini merangkum cara proyek dikerjakan dari awal sampai dashboard, termasuk keputusan teknis dan masalah yang ditemui beserta solusinya.
Ringkasan hasil ada di [`README.md`](../README.md); seluruh measure ada di [`DAX_REFERENSI.md`](DAX_REFERENSI.md).

## 0. Alur kerja

| Fase | Pertanyaan yang dijawab | Keluaran |
|---|---|---|
| 1. Brief | Apa yang diminta pekerjaan, dan apa buktinya? | Peta persyaratan → modul (tabel di README) |
| 2. Data sintetis | Bagaimana mendapat data yang realistis **dengan jawaban yang diketahui**? | `data/raw/`, `answer_key/`, `gen/` |
| 3. Staging | Bagaimana memuat tanpa kehilangan apa pun? | `sql/01`, `automation/load_raw.py` |
| 4. Pembersihan | Mana baris yang valid, mana yang dikarantina, dan kenapa? | `sql/02–06`, tabel karantina |
| 5. Mart KPI | Apa definisi satu angka, dan di mana ia dihitung? | `sql/07`, `sql/14`, `KPI_dictionary.md` |
| 6. Pemantauan & rekonsiliasi | Di mana uang bocor atau bisa ditagih? | `sql/08–10` |
| 7. Kualitas data | Apakah data boleh dipublikasikan? | `sql/11`, gerbang publikasi |
| 8. Validasi | Apakah temuan benar? | `sql/13` vs `answer_key/` |
| 9. Power BI | Bagaimana pembaca mendapat jawabannya dalam satu layar? | `powerbi/`, `MODEL_POWERBI.md` |

## 1. Brief dan persyaratan

Persyaratan dari lowongan dibaca sebagai daftar kemampuan yang harus bisa dibuktikan: dashboard performa (GMV, iklan, voucher, promo, JBP, kampanye),
ekstraksi otomatis, pemantauan kepatuhan harga/promosi dan order mencurigakan, rekonsiliasi dan banding ke platform, serta integritas data.
Setiap persyaratan dipetakan ke satu modul SQL dan satu halaman dashboard, sehingga ada jawaban konkret untuk "mana buktinya".

## 2. Data sintetis dengan kunci jawaban

Data dibangkitkan dengan `gen/` (4 platform, 36 SKU, 1 Jan – 31 Okt 2026). Keputusan paling penting: **data kotor disuntikkan secara terukur** dan setiap suntikan dicatat di `answer_key/`.
Jenis kekotoran yang disuntikkan antara lain: baris ganda (dalam satu berkas dan lintas berkas), SKU huruf kecil / tanpa tanda hubung / spasi di ujung / hanya judul,
qty nol atau negatif, order uji, ID order TikTok dalam notasi ilmiah, iklan dengan klik > impresi, belanja iklan nol padahal ada klik, penyesuaian belanja negatif, hari iklan hilang,
dan snapshot harga hilang / kosong / nol.

Manfaatnya: hasil deteksi tidak dinilai "kelihatan masuk akal", tetapi dihitung recall dan precision-nya terhadap kunci.

## 3. Staging dan pemuatan otomatis

- Semua kolom staging bertipe **TEXT** (`sql/01`): tidak ada transformasi saat memuat, sehingga tidak ada data yang hilang karena salah tipe.
- `automation/load_raw.py` mencatat sha256 setiap berkas di registri. Berkas yang sama **dilewati** (`SKIP`), jadi pipeline aman dijalankan berulang dan hasilnya identik.
- `run_pipeline.sh` / `run_pipeline.ps1` menjalankan seluruh rantai (muat → bersihkan → mart → ops → DQ → uji akurasi) dalam ±80 detik.

## 4. Pembersihan dan karantina

- Fungsi parsing (`sql/02`): tanggal dan angka multi-format, normalisasi SKU, teks, dan nama kota (pencocokan *fuzzy* dengan `pg_trgm`). 13 uji mandiri lewat `etl.selftest()`.
- Transformasi order (`sql/05`): parse → klasifikasi → **karantina** → `fact_order_line` → `fact_order`.
  Baris yang tidak bisa dipercaya (duplikat, order uji, ID rusak, qty tak terpulihkan) masuk tabel karantina beserta alasannya, **tidak dibuang diam-diam**.
- Hasil: 69.250 baris di `dwh.fact_order`, 63.248 di antaranya order valid (`is_valid_sale`).

## 5. Definisi KPI dan mart

- **Net GMV** = GMV setelah diskon penjual, dikurangi batal dan retur (status valid: selesai + masih dikirim). **Net Sales** = Net GMV − voucher penjual.
- **CM1** = Net Sales − COGS − biaya platform (komisi, layanan, pembayaran sesuai kontrak). **CM2** = CM1 − belanja iklan.
- **Iklan**: ROAS dan CPC hanya dari baris dengan *spend* andal (`*_reliable`); **TACOS** = belanja iklan / Net GMV.
- **Kampanye** dibandingkan dengan baseline (uplift GMV, CM2 inkremental); kampanye yang CM2 inkrementalnya negatif ditandai "merugikan margin".
- **JBP**: pencapaian terhadap Tier 1/2, proyeksi kuartal (*pacing*), dan GMV harian yang dibutuhkan untuk Tier 2.
- Definisi lengkap: [`KPI_dictionary.md`](KPI_dictionary.md).

## 6. Kepatuhan, risiko, dan rekonsiliasi

**Harga & promosi (`sql/08`)**
- Snapshot harga dievaluasi terhadap harga lantai (MAP) per penjual resmi/tidak resmi → *alert* dengan tingkat keparahan.
- **Episode pelanggaran** dibentuk dari rentetan snapshot berurutan (*gaps-and-islands*), lalu diberi dugaan akar masalah:
  `RESELLER_UNDERCUT_EPISODE`, `RESELLER_PERSISTENT_UNDERCUT`, `OFFICIAL_BELOW_MAP_OTHER`, `STRIKE_INFLATION`, `PRICE_ERROR_INCIDENT`, `CAMPAIGN_OVERRUN`.
- **Kebocoran harga toko resmi**: order yang terjual ≥ 50 % di bawah harga lantai (salah harga) dihitung selisih Rupiahnya.
- Pelanggaran aturan voucher: di bawah minimum belanja, melebihi kuota, dipakai setelah kedaluwarsa.

**Order mencurigakan (`sql/09`)** — lima aturan berbobot, skor = jumlah bobot:

| Aturan | Arti | Bobot |
|---|---|---|
| R1 | Qty besar (qty baris atau unit order ≥ 12) | 40 |
| R2 | Burst pembelian (≥ 5 order, jeda berurutan ≤ 60 menit) | 35 |
| R3 | Banyak akun (≥ 3 username per telepon tersamar + kota) | 40 |
| R4 | Harga satuan < 50 % MAP | 50 |
| R5 | Melanggar aturan voucher | 15 |

Tingkat: **Kritis** ≥ 80, **Tinggi** ≥ 50, **Sedang** ≥ 30, **Rendah** di bawah itu. Tingkat adalah prioritas pemeriksaan, bukan vonis.

**Rekonsiliasi & banding (`sql/10`)** — lima kategori klaim: settlement belum cair > 14 hari, benefit program kurang bayar, benefit program tidak dibayar,
komisi dipotong berlebih, subsidi voucher platform hilang. Setiap klaim punya toleransi (absolut dan persen) agar selisih kecil tidak menjadi kasus.

## 7. Kualitas data dan gerbang publikasi

`sql/11` menjalankan 34 pemeriksaan (lulus / gagal / info) dengan tingkat keparahan. **Gerbang publikasi**: bila ada pemeriksaan KRITIS yang gagal, publikasi ditahan.
Kondisi terakhir: 20 lulus, 3 peringatan (hari iklan hilang, selisih identitas settlement, umur snapshot), 0 kritis → aman.

## 8. Validasi

| Uji | Hasil |
|---|---|
| Order mencurigakan, pelanggaran voucher, selisih settlement/ERP, kekurangan benefit program vs kunci | recall 100 % |
| Snapshot pelanggaran harga vs kunci | 98,1 % (selisih = snapshot rusak tak terpulihkan) |
| GMV bersih per platform-bulan vs kunci | cocok; selisih ≤ 0,07 % dari order yang dikarantina |
| Tie-out Power BI | `Net GMV` = Rp7.280.003.300 = `SUM(net_gmv)` di `mart.v_kpi_platform_month` |

Kueri kontrol untuk mereproduksi angka utama README:

```sql
SELECT count(*), count(*) FILTER (WHERE is_valid_sale) FROM dwh.fact_order;                -- 69.250 | 63.248
SELECT platform_code, round(sum(net_gmv)) FROM mart.v_kpi_platform_month GROUP BY 1;        -- SHP 3.090.712.000 · TTK 2.437.029.200 · LZD 1.068.488.000 · BLI 683.774.100
SELECT sum(claim_idr), sum(cases) FROM ops.v_appeal_pack;                                   -- 85.270.011 | 1.307
SELECT sum(leakage_idr), sum(orders) FROM ops.v_official_price_leakage_summary;             -- 64.804.700 | 275
SELECT sum(exposure_idr), sum(orders) FROM ops.v_voucher_violation_summary;                 -- 3.699.100 | 365
SELECT risk_level, count(*), sum(gmv_placed) FROM ops.v_suspicious_orders_scored GROUP BY 1; -- 84 / 602 / 513 / 361 (total 1.560)
SELECT * FROM ops.v_dq_scorecard ORDER BY run_id DESC LIMIT 1;                              -- 20 lulus · 3 gagal · 0 kritis · OK_TO_PUBLISH
```

## 9. Power BI

Ringkasan; rincian lengkap di [`MODEL_POWERBI.md`](MODEL_POWERBI.md).

- **Koneksi**: PostgreSQL, mode **Import**, server `127.0.0.1:5432`, database `ecom_lumina`. Satu fungsi `fnPg(schema, objek)` dipakai oleh semua query.
- **Model**: dimensi (`DimDate`, `DimPlatform`, `DimSKU`, `DimMonth`) → fakta/mart; tabel kontrol (`PlatSel`, `TabSel`, `Palette`, `TopN`, `ChartMode`, `Aturan`) **tanpa relasi**.
- **Pola DAX yang dipakai berulang**
  1. *Variabel sebelum filter*: `VAR p = [Platform Terpilih] RETURN CALCULATE(..., CC[platform_code] = p)` (menghindari galat "PLACEHOLDER").
  2. *Terkunci bulan*: `CALCULATE(SUM(x), ALL(DimMonth), tabel[month_start] = [Bulan Akhir])`; `Bulan Pilih` untuk bagian yang mengikuti dropdown.
  3. *Peringkat dua kolom*: `RANKX(FILTER(ALLSELECTED(produk, sub_kategori), ...), [Selisih Rp], , DESC, DENSE)`.
  4. *Seri berganti tab*: tiga measure "Seri ..." yang mengembalikan `BLANK()` kecuali tab aktif → warna dan skala berganti otomatis.
  5. *Warna lewat measure*: kode warna dikembalikan measure lalu dipakai di *Conditional formatting → Field value*; dua palet (standar, buta warna).
  6. *Teks dinamis*: kalimat insight dirakit dengan `FORMAT`/`TOPN`/`MAXX`, ditampilkan di kartu atau kotak teks.
- **Interaksi**: tombol tab berbasis *bookmark* (Data On, Display Off) yang mengubah slicer tersembunyi; slicer bulan dan platform; pengalih "?" dengan dua tombol bertumpuk.
- **Visual kustom**: Deneb (Vega-Lite) untuk batang dengan label di atas batang dan garis rata-rata (`powerbi/deneb/`).

## 10. Masalah yang ditemui dan solusinya

| Masalah | Penyebab | Solusi |
|---|---|---|
| `mart.mv_sales_daily` tidak tampil di Navigator | Navigator tidak menampilkan *materialized view* | Buat `mart.v_sales_daily` sebagai pembungkus |
| Galat "PLACEHOLDER … True/False expression" | Ukuran dipakai langsung sebagai filter boolean di `CALCULATE` | Simpan ukuran dalam `VAR` terlebih dulu |
| Kartu Command Center sama untuk semua platform (CM2 37,5 %, order 126.496) | Measure tidak menyaring tabel `CC` | Semua measure CC memakai `VAR p = [Platform Terpilih]` + filter `CC[platform_code] = p` |
| Pacing "ON TRACK" untuk semua platform | Hal yang sama; status tidak disaring | Perbaikan yang sama, plus `CC Pacing Status` |
| Insight wilayah menampilkan "0 %" | Pecahan tidak dikali 100 sebelum `FORMAT` | Kalikan 100 lebih dulu |
| Grafik tren hanya menampilkan platform terpilih | Lapisan dasar memakai measure yang ikut menyaring | Lapisan dasar memakai `[Net GMV Juta]` (tanpa filter platform) |
| Garis antar lapisan tidak sejajar | Judul, sumbu, dan padding tiap lapisan berbeda | Samakan semua; aktifkan *Show items with no data* pada sumbu X |
| Peringkat tabel movers berulang per kategori, nilai menjumlah semua bulan | `RANKX` satu kolom; measure tidak terkunci bulan | Peringkat dua kolom + measure terkunci bulan |
| Dua kartu KPI tidak berubah saat tab diganti | Kartu memakai measure lama / slicer tidak terhubung ke `Tab Aktif` | Uji kartu `Tab Aktif`; pasang measure `KPI ...`; perbarui bookmark |
| Slicer tab hanya menampilkan satu item | Relasi otomatis `TabSel[urut]` ↔ `Aturan[urut]` menyaring daftar | Hapus relasi; matikan *Autodetect relationships* |
| "A single value for column 'risk_level' cannot be determined" | Rumus kolom dibuat sebagai measure | Buat sebagai kolom hitung (*New column*) |
| Kolom hitung tidak terbentuk saat ditempel | Baris komentar `//` ikut tersalin | Tempel kodenya saja, tanpa `//` |
| Error koneksi "unreachable network" | `localhost` diterjemahkan ke IPv6 | Pakai `127.0.0.1:5432` |

## 11. Pelajaran

1. **Kunci jawaban mengubah cara menilai**: temuan dihitung recall-nya, bukan dinilai dengan perasaan.
2. **Definisi dulu, visual kemudian**: banyak galat dashboard berasal dari definisi yang belum terkunci (bulan, platform, basis minimum), bukan dari visualnya.
3. **Tabel kontrol harus bebas relasi** dan dicek di Model view setiap kali ada tabel baru.
4. **Uji tie-out di setiap tahap**: total di model harus sama dengan total di SQL sebelum membangun halaman berikutnya.
5. **Jujur soal batas**: data fiktif, `.pbix` tidak disertakan, dan sebagian spesifikasi visual ditulis tanpa Power BI Desktop.

## 12. Peta jalan

- Halaman Iklan, Voucher, Kampanye & JBP, Kepatuhan harga rinci, Kesehatan data (measure dasarnya sudah ada di `measures.dax`).
- Penjadwalan refresh otomatis (Windows Task Scheduler memanggil `run_pipeline.ps1`).
- Pemulihan ID order TikTok yang rusak (notasi ilmiah) dari berkas settlement.
- Tangkapan layar dashboard di `docs/img/` untuk README.
