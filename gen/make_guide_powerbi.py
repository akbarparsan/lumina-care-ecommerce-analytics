"""Membuat docs/Panduan_PowerBI_Langkah_Demi_Langkah.docx  (Arial 12, spasi 1,5)."""
import os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.5)
sec.top_margin = sec.bottom_margin = Cm(2.5)
FONT = "Arial"


def style_font(st, size=12, bold=None):
    st.font.name = FONT
    st.font.size = Pt(size)
    st.font.color.rgb = RGBColor(0, 0, 0)
    if bold is not None:
        st.font.bold = bold
    rpr = st.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(a), FONT)
    pf = st.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    pf.space_after = Pt(6)


for n in ("Normal", "Title", "List Bullet"):
    style_font(doc.styles[n])
style_font(doc.styles["Title"], 12, True)
for l in (1, 2, 3):
    style_font(doc.styles[f"Heading {l}"], 12, True)
    doc.styles[f"Heading {l}"].paragraph_format.space_before = Pt(14)
    doc.styles[f"Heading {l}"].paragraph_format.keep_with_next = True


def shade(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def P(text, bold=False, italic=False):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold, r.italic = bold, italic
    return p


def H(text, lvl=1):
    doc.add_heading(text, level=lvl)


def B(items):
    for t in items:
        doc.add_paragraph(t, style="List Bullet")


def S(items):
    """Langkah bernomor manual (nomor mulai dari 1 pada setiap daftar)."""
    for i, t in enumerate(items, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.9)
        p.paragraph_format.first_line_indent = Cm(-0.9)
        p.add_run(f"{i}.  {t}")


def C(text):
    """Blok perintah / kode: latar abu-abu."""
    for line in text.strip("\n").split("\n"):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.5)
        p.paragraph_format.space_after = Pt(0)
        pPr = p._p.get_or_add_pPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), "EDEDED")
        pPr.append(shd)
        p.add_run(line)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def T(header, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold = True
        shade(c, "D9D9D9")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = str(v)
    for row in t.rows:
        for i, c in enumerate(row.cells):
            if widths:
                c.width = Cm(widths[i])
            for p in c.paragraphs:
                p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
                for r in p.runs:
                    r.font.name = FONT
                    r.font.size = Pt(12)
    doc.add_paragraph()


# =============================================================== SAMPUL
doc.add_paragraph("Panduan Lanjutan: dari Database sampai Dashboard Power BI dan Portofolio", style="Title")
P("Proyek Lumina Care (Personal Care, 4 marketplace). Seluruh data bersifat sintetis dan fiktif.", True)
P("Dokumen ini melanjutkan panduan awal. Anda sudah menjalankan seluruh skrip SQL, jadi database ecom_lumina sudah berisi data bersih dan KPI. "
  "Panduan ini membawa Anda dari sana sampai dashboard selesai, diuji, dan siap dipamerkan di portofolio. Desain dashboard mengikuti mock-up hasil adaptasi dashboard referensi "
  "(Command Center, Analisis, Recovery & Kepatuhan).")
P("Catatan kejujuran: skrip SQL sudah saya jalankan dan uji. Measure DAX, tema, dan langkah klik di Power BI Desktop belum bisa saya jalankan karena Power BI hanya berjalan di Windows. "
  "Karena itu nama menu bisa sedikit berbeda antar versi, dan bila sebuah measure menghasilkan error, kerjakan satu per satu lalu kirimkan pesan error-nya kepada saya.", italic=True)

# =============================================================== 0 PETA JALAN
H("0. Peta jalan")
T(["Tahap", "Yang dikerjakan", "Hasil yang harus terlihat", "Perkiraan waktu"],
  [["1", "Perbarui berkas dan jalankan SQL 14 (view dashboard)", "Tabel mart.v_command_center berisi 5 baris", "15 menit"],
   ["2", "Latihan SQL dasar", "Anda bisa menjelaskan 8 kueri sendiri", "45 menit"],
   ["3", "Pasang Power BI Desktop dan sambungkan ke PostgreSQL", "Daftar tabel muncul di Navigator", "20 menit"],
   ["4", "Muat tabel dan bangun model (relasi)", "Model view rapi, tanpa relasi dua arah", "45 menit"],
   ["5", "Tabel kontrol, field parameter, dan measure DAX", "Semua measure tanpa error", "60 menit"],
   ["6", "Tema dan kanvas", "Latar krem, kartu putih bersudut bulat", "15 menit"],
   ["7", "Halaman 1: Command Center", "Mirip artboard 1 pada mock-up", "90 menit"],
   ["8", "Halaman 2: Analisis", "Tab metrik, kartu KPI, grafik, tabel naik/turun", "90 menit"],
   ["9", "Halaman 3: Recovery & Kepatuhan", "Klaim, benefit program, risiko", "75 menit"],
   ["10", "Halaman 4–8 (Iklan, Voucher, Kampanye & JBP, Rekonsiliasi, Kesehatan Data)", "Halaman detail dengan template yang sama", "3–4 jam"],
   ["11", "Interaksi, bookmark, aksesibilitas", "Tombol navigasi, tombol ?, mode buta warna", "60 menit"],
   ["12", "Uji akurasi angka", "Semua angka cocok dengan tabel uji", "30 menit"],
   ["13", "Otomasi refresh", "Skrip terjadwal berjalan", "30 menit"],
   ["14", "Kemas portofolio", "PDF, tangkapan layar, repositori, narasi wawancara", "60 menit"]],
  [1.4, 6.2, 5.6, 2.8])
P("Kerjakan berurutan. Setiap tahap punya pemeriksaan di akhirnya; jangan lanjut sebelum pemeriksaan itu cocok.")

# =============================================================== 1
H("1. Perbarui berkas dan jalankan SQL 14")
P("Paket zip terbaru memuat tiga tambahan: sql/14_mart_dashboard.sql, powerbi/measures_dashboard.dax, dan dua berkas tema. Skrip run_all.sql juga sudah memanggil 14.")
S(["Unduh zip terbaru, lalu ekstrak ke folder proyek Anda dan pilih Replace untuk berkas yang sama. Data di database Anda tidak terhapus karena ia ada di PostgreSQL, bukan di folder.",
   "Buka PowerShell, lalu masuk ke folder proyek dan atur kata sandi sementara:"])
C('cd C:\\lumina\\ecom_portfolio\n$env:PGPASSWORD="ecom"')
S(["Jalankan hanya berkas baru (cukup untuk Anda, tidak perlu mengulang semuanya):"])
C('psql -h 127.0.0.1 -U ecom -d ecom_lumina -v ON_ERROR_STOP=1 -f sql/14_mart_dashboard.sql')
S(["Di akhir, layar menampilkan tabel ringkasan. Periksa angka ini:"])
T(["Platform", "Net GMV (Rp)", "Klaim (Rp)", "Order ditandai"],
  [["ALL", "7.280.003.300", "85.270.011", "1.560"], ["SHP", "3.090.712.000", "36.942.769", "494"], ["TTK", "2.437.029.200", "23.351.783", "375"],
   ["LZD", "1.068.488.000", "14.044.408", "455"], ["BLI", "683.774.100", "10.931.051", "236"]], [3, 4.5, 4, 4.5])
P("Jika angkanya sama, tahap 1 selesai. Jika berbeda, kemungkinan ada skrip sebelumnya yang belum dijalankan: ulangi run_all.sql dari awal (perintahnya ada di panduan pertama).")

# =============================================================== 2
H("2. Latihan SQL dasar (agar Anda paham yang Anda pakai)")
P("Di wawancara, Anda hampir pasti diminta menjelaskan SQL. Delapan latihan ini disusun dari mudah ke sulit memakai tabel proyek Anda sendiri. "
  "Jalankan di pgAdmin: klik kanan database ecom_lumina, Query Tool, tempel kueri, tekan F5.")
H("Latihan 1: melihat isi tabel", 2)
C("SELECT * FROM dwh.dim_platform;")
P("SELECT berarti pilih kolom, tanda bintang berarti semua kolom, FROM menunjukkan tabel. Format nama tabel: schema.tabel. Hasil: 4 platform.")
H("Latihan 2: menghitung baris", 2)
C("SELECT count(*) FROM dwh.fact_order;")
P("Hasil harus 69250. Angka ini adalah jumlah order bersih setelah duplikat dan order uji dibuang.")
H("Latihan 3: mengelompokkan (GROUP BY)", 2)
C("SELECT platform_code, count(*) AS jumlah_order, sum(gmv_placed) AS gmv\nFROM dwh.fact_order\nGROUP BY platform_code\nORDER BY gmv DESC;")
P("GROUP BY membuat satu baris untuk tiap platform, lalu count dan sum menghitung di dalam kelompok itu. Hasil: SHP 29.787 order dengan GMV Rp3.364.869.200 di baris pertama, lalu TTK, LZD, BLI.")
H("Latihan 4: menyaring (WHERE) dan membatasi (LIMIT)", 2)
C("SELECT order_id, order_date, gmv_placed\nFROM dwh.fact_order\nWHERE platform_code = 'SHP' AND order_date = '2026-10-31'\nORDER BY gmv_placed DESC\nLIMIT 5;")
P("WHERE menyaring baris sebelum dikelompokkan. Ganti platform atau tanggalnya sendiri dan lihat hasilnya berubah.")
H("Latihan 5: menggabungkan tabel (JOIN)", 2)
C("SELECT k.product_name, sum(s.net_gmv) AS net_gmv\nFROM mart.v_sales_daily s\nJOIN dwh.dim_sku k USING (sku)\nGROUP BY k.product_name\nORDER BY net_gmv DESC\nLIMIT 3;")
P("JOIN menyambungkan dua tabel lewat kolom yang sama (sku). Hasil: Daily Sunscreen SPF50 40ml (Rp634.822.300), Brightening Serum 30ml, lalu Niacinamide 10% Serum 20ml. Inilah alasan model data memisahkan fakta (transaksi) dari dimensi (daftar produk).")
H("Latihan 6: melihat data yang dibuang", 2)
C("SELECT reason, count(*)\nFROM ops.quarantine_row\nWHERE domain = 'ORDERS'\nGROUP BY reason\nORDER BY 2 DESC;")
P("Hasil: EXACT_DUPLICATE 685, TEST_ORDER 48, ORDER_ID_CORRUPTED_SCIENTIFIC 24, QTY_INVALID_UNRECOVERABLE 4. Ini bukti pembersihan data Anda bisa diaudit: tidak ada baris yang hilang tanpa catatan.")
H("Latihan 7: membandingkan dengan bulan lalu (window function)", 2)
C("SELECT to_char(month_start,'YYYY-MM') AS bulan, net_gmv,\n       lag(net_gmv) OVER (ORDER BY month_start) AS bulan_lalu\nFROM mart.v_kpi_month_all\nORDER BY month_start DESC LIMIT 3;")
P("lag() mengambil nilai dari baris sebelumnya tanpa menggabungkan tabel. Hasil: Oktober Rp838.866.700 dengan bulan lalu Rp848.879.500. Inilah dasar kartu variasi di dashboard.")
H("Latihan 8: memakai view KPI", 2)
C("SELECT platform_code, net_gmv, cm2_pct, tacos, roas, pacing_status\nFROM mart.v_command_center ORDER BY 1;")
P("View adalah kueri yang disimpan dengan nama. Power BI cukup membaca view ini, tanpa perlu tahu logika di baliknya. Cobalah menjawab: platform mana yang TACOS-nya tertinggi, dan platform mana yang proyeksi JBP-nya di bawah Tier 1? (Jawaban: TikTok Shop 8,0 persen; Blibli).")

# =============================================================== 3
H("3. Pasang Power BI Desktop dan sambungkan ke PostgreSQL")
S(["Power BI Desktop hanya tersedia untuk Windows. Pasang gratis dari Microsoft Store (cari Power BI Desktop) atau dari situs Microsoft.",
   "Buka Power BI Desktop, pilih Blank report.",
   "Klik Home, Get data, More..., ketik PostgreSQL, pilih PostgreSQL database, Connect.",
   "Server: isi 127.0.0.1:5432 (atau localhost). Database: ecom_lumina. Data Connectivity mode: Import. Klik OK.",
   "Di jendela kredensial pilih tab Database, isi User name ecom dan kata sandi pengguna ecom, lalu Connect.",
   "Jika muncul peringatan koneksi tidak terenkripsi, pilih OK atau Connect. Ini aman karena database ada di komputer Anda sendiri.",
   "Jika versi Power BI lama meminta pemasangan Npgsql, pasang dari github.com/npgsql/npgsql/releases (pilih GAC installation), lalu ulangi. Versi baru biasanya tidak memerlukannya."])
P("Mode Import menyalin data ke berkas .pbix sehingga dashboard cepat dan bisa dibuka tanpa database menyala. Untuk portofolio ini Import adalah pilihan yang tepat.")

# =============================================================== 4
H("4. Muat tabel dan bangun model")
H("4.1 Pilih tabel di Navigator", 2)
P("Di Navigator, buka ecom_lumina, lalu centang tabel berikut. Gunakan kotak pencarian untuk mempermudah. Setelah semua dicentang klik Transform Data (bukan Load), karena kita akan mengganti nama dulu.")
T(["Schema", "Tabel / view yang dicentang", "Nama baru di Power BI"],
  [["dwh", "dim_date, dim_platform, dim_sku, dim_campaign", "DimDate, DimPlatform, DimSKU, DimCampaign"],
   ["mart", "dim_month, v_sales_daily, v_kpi_platform_month, v_kpi_month_all", "DimMonth, Sales, KPI_M, KPIMonth"],
   ["mart", "v_gmv_trend_daily, v_ads_daily, v_voucher_performance, v_voucher_aov_uplift", "GMVTrend, Ads, Voucher, VoucherAOV"],
   ["mart", "v_campaign_performance, v_sku_margin, v_jbp_attainment, v_jbp_pacing", "Campaign, SKUMargin, JBP, JBPPacing"],
   ["mart", "v_sku_movers, v_subcat_month, v_region_month, v_command_center, v_money_on_table", "Movers, SubCat, Region, CC, Money"],
   ["mart", "v_price_parity_daily, v_customer_repeat, v_hourly_heatmap", "PriceParity, CustomerRepeat, Heatmap"],
   ["ops", "v_price_alerts_latest, v_price_violation_episodes, v_price_compliance_daily", "PriceAlerts, PriceEpisodes, PriceComplianceDaily"],
   ["ops", "v_official_price_leakage_summary, v_voucher_violation_summary", "PriceLeakage, VoucherViolations"],
   ["ops", "v_suspicious_orders_scored, v_suspicious_buyer_clusters", "Suspicious, SuspiciousClusters"],
   ["ops", "v_settlement_audit, v_erp_audit, v_program_reconciliation, v_appeal_pack, v_appeal_board", "SettlementAudit, ERPAudit, ProgramRecon, AppealPack, AppealBoard"],
   ["ops", "v_dq_latest, v_dq_scorecard, v_source_freshness, v_pipeline_health", "DQLatest, DQScore, Freshness, PipelineHealth"]],
  [2.0, 8.0, 6.0])
S(["Di jendela Power Query, klik kanan nama tabel di panel kiri, Rename, ketik nama baru sesuai tabel di atas (nama harus sama persis karena measure DAX memakainya).",
   "Klik Close & Apply (kiri atas). Tunggu sampai semua tabel dimuat; ini bisa beberapa menit."])
H("4.2 Relasi (Model view)", 2)
P("Buka Model view (ikon ketiga di sisi kiri). Seret kolom dari tabel dimensi ke tabel fakta. Setiap relasi harus One to many (1 ke *) dengan Cross filter direction: Single. Hapus relasi otomatis yang salah arah.")
T(["Dari (sisi 1)", "Ke (sisi banyak)"],
  [["DimMonth[month_start]", "KPI_M[month_start], KPIMonth[month_start], Movers[month_start], SubCat[month_start], Region[month_start], CustomerRepeat[month_start]"],
   ["DimDate[date]", "Sales[order_date], Ads[ad_date], PriceParity[snapshot_date], PriceComplianceDaily[snapshot_date]"],
   ["DimPlatform[platform_code]", "Sales, KPI_M, Ads, Voucher, Campaign, JBP, JBPPacing, Movers, SubCat, Region, PriceAlerts, PriceEpisodes, Suspicious, SettlementAudit, ProgramRecon, AppealPack"],
   ["DimSKU[sku]", "Sales[sku], SKUMargin[sku], Movers[sku]"]],
  [5.0, 11.0])
S(["Tandai DimDate sebagai tabel tanggal: pilih tabel DimDate, Table tools, Mark as date table, kolom date.",
   "Pada DimMonth, pilih kolom month_label, lalu Column tools, Sort by column, pilih month_no. Tanpa ini, bulan akan berurutan abjad (Agu, Apr, Des...).",
   "Tabel CC dan Money sengaja tidak punya relasi. Ia difilter lewat measure [Platform Terpilih].",
   "Sembunyikan kolom teknis yang tidak dipakai di visual (klik kanan, Hide in report view), misalnya kolom id dan kolom yang hanya dipakai untuk relasi."])
P("Pemeriksaan: tidak ada garis relasi dengan panah ganda dan tidak ada tabel dimensi yang menggantung tanpa relasi (kecuali CC, Money, dan tabel kontrol).")

# =============================================================== 5
H("5. Tabel kontrol, field parameter, dan measure")
H("5.1 Tabel kontrol (pengganti tombol wilayah pada referensi)", 2)
P("Referensi memakai tombol untuk memilih wilayah. Padanan kita adalah tombol untuk memilih platform. Tombol itu perlu tabel kecil yang berdiri sendiri.")
T(["Tabel", "Kolom dan isi", "Cara membuat"],
  [["PlatSel", "code: ALL, SHP, TTK, LZD, BLI. label: Semua, Shopee, TikTok Shop, Lazada, Blibli", "Home, Enter data, tempel dua kolom, beri nama PlatSel"],
   ["Palette", "code: STD, CB. label: Warna standar, Ramah buta warna", "Enter data"],
   ["ChartMode", "code: LINE, COL. label: Garis, Kolom", "Enter data"],
   ["TopN", "Angka 1 sampai 10, naik 1, default 5", "Modeling, New parameter, Numeric range"],
   ["Metrik", "Field parameter: Net GMV, Margin (CM2), Iklan", "Modeling, New parameter, Fields (lihat 5.2)"]],
  [2.6, 7.4, 6.0])
H("5.2 Field parameter Metrik (tab Net GMV | Margin | Iklan)", 2)
S(["Buat dulu tabel _Measures: Home, Enter data, buat tabel kosong dengan nama _Measures, Load.",
   "Buat tiga measure dasar (lihat 5.3): Metrik Net GMV, Metrik CM2, Metrik Iklan.",
   "Modeling, New parameter, Fields. Beri nama Metrik, lalu tambahkan tiga measure tadi dan ubah label tampilannya menjadi Net GMV, Margin (CM2), Iklan. Pastikan Add slicer to this page dicentang. Klik Create.",
   "Power BI membuat tabel Metrik dengan kolom Metrik, Metrik Fields, dan Metrik Order. Tabel ini yang nanti dipasang pada sumbu Y grafik dan sebagai slicer tab."])
H("5.3 Menempel measure DAX", 2)
P("Buka powerbi/measures.dax dan powerbi/measures_dashboard.dax dengan Notepad. Di Power BI: klik kanan tabel _Measures, New measure, tempel SATU measure (satu blok dari nama sampai measure berikutnya), tekan Enter. Ulangi untuk semua. Urutannya:")
B(["measures.dax, kelompok GMV, Profitabilitas, Iklan, Voucher, Kampanye, JBP, Kepatuhan, Risiko, Rekonsiliasi, Kualitas.",
   "measures_dashboard.dax dari atas ke bawah. Measure yang memakai tabel kontrol (Platform Terpilih, dan seterusnya) harus dibuat setelah tabel kontrolnya ada."])
P("Jika Power BI menandai error merah pada sebuah measure, penyebab tersering ada tiga: nama tabel/kolom tidak sama persis dengan yang Anda beri di langkah 4.1, relasi belum dibuat, atau measure yang dirujuk belum dibuat. Perbaiki lalu lanjut. Setelah semua selesai, uji dengan membuat satu Card berisi [Net GMV]: total harus Rp7.280.003.300.")
P("Tips: measure yang memuat teks (Insight, Catatan Data) paling mudah diuji dengan meletakkannya di visual Card dan melihat apakah kalimatnya terbentuk.")

# =============================================================== 6
H("6. Tema dan kanvas")
S(["View, Themes, Browse for themes, pilih powerbi/lumina_theme.json. Tema ini memberi warna aksen, latar krem pada halaman, dan kartu putih bersudut bulat.",
   "Format pane, tab Page, Canvas settings: Type Custom, Width 1440, Height 960 (cukup untuk seluruh isi, dan nyaman dilihat pada layar 1920).",
   "Page background: krem F5F1EA (sudah diatur tema; bila belum, pilih manual).",
   "Font: Segoe UI sudah ada di Windows. Judul besar memakai Georgia miring (italic), yang menggantikan huruf Fraunces pada mock-up karena Fraunces tidak tersedia bawaan.",
   "Simpan sebagai Lumina_Care.pbix di folder powerbi."])
P("Tema kedua, lumina_theme_buta_warna.json, memakai palet Okabe-Ito yang dirancang aman bagi penderita buta warna. Gunakan untuk versi alternatif; cara pemakaiannya ada di bab 11.")

# =============================================================== 7
H("7. Halaman 1: Command Center")
P("Tujuan: dalam lima detik, pembaca tahu bagaimana kondisi tiap platform dan berapa uang yang bisa diselamatkan. Ini adalah padanan landing page referensi, tetapi isinya ringkasan keputusan, bukan hiasan.")
P("Buat halaman baru, beri nama Command Center. Susun elemen dari atas ke bawah:")
T(["No", "Visual", "Isi", "Pengaturan penting"],
  [["1", "Text box (judul)", "Lumina Care; baris kecil: Command Center, Personal Care, 4 marketplace, Jan-Okt 2026", "Judul Georgia italic 40 pt; baris kecil abu 12 pt"],
   ["2", "Page navigator", "Insert, Buttons, Navigator, Page navigator", "Style: tab. Selected: latar putih. Letakkan kanan atas"],
   ["3", "Slicer platform", "PlatSel[label]", "Slicer settings: Style Tile (horizontal), Single select ON, Select all OFF. Pilih Semua sebagai bawaan"],
   ["4", "Slicer palet", "Palette[label]", "Sama seperti no. 3; dua tombol saja"],
   ["5", "Tombol ?", "Insert, Buttons, Blank. Teks: ?", "Action: Bookmark Catatan Data (bab 11). Alt text: Catatan cakupan data"],
   ["6", "Bar chart wilayah", "Sumbu Y Region[region], nilai SUM Region[net_gmv]", "Urut menurun. Analytics pane, Average line ON, gaya putus-putus. Label data ON. Judul: Dari mana penjualan datang"],
   ["7", "Line chart tren", "X DimMonth[month_label]; Y [Net GMV Tampil]; Legend KPI_M[platform_code]", "Marker ON. Garis akhir diberi label. Judul: Net GMV bulanan per platform"],
   ["8", "Card insight", "[Insight Platform]", "Letakkan di bawah no. 7. Teks 12 pt, tanpa label kategori. Jika kalimat terpotong, aktifkan Text wrap atau pakai text box dengan Dynamic value"],
   ["9", "Kartu detail (6 buah)", "[Rp Ringkas (CC Net GMV)], [CC CM2 %], [CC TACOS], [CC ROAS], [CC Order Valid], [Insight JBP]", "Satu card per measure. Judul kartu: Net GMV, CM2, TACOS, ROAS, Order valid, JBP Q4"],
   ["10", "Baris detail teks", "[CC Klaim Teks], [CC Alert Harga], [CC Order Berisiko]", "Tiga card kecil berlabel"],
   ["11", "Kartu uang di meja (4 buah)", "[Uang Klaim], [Uang Kebocoran], [Uang Voucher], [Gerbang Data]", "Garis kiri tebal oranye untuk tiga pertama, hijau teal untuk gerbang data. Subteks: [Gerbang Data Detail]"],
   ["12", "Tombol Buka analisis", "Insert, Buttons, Blank; teks: Buka analisis", "Action: Page navigation, Analisis"]],
  [1.0, 3.3, 6.3, 5.4])
S(["Platform slicer: setelah memilih Shopee, kartu detail harus berubah. Itu bekerja karena semua measure CC memakai [Platform Terpilih].",
   "Edit interactions: pilih slicer platform, lalu Format, Edit interactions. Atur agar slicer platform HANYA mempengaruhi line chart (no. 7) jika Anda ingin; bar wilayah tidak punya data per platform selain lewat tabel Region yang memang memiliki platform_code. Bila Anda ingin wilayah ikut platform, biarkan bawaan.",
   "Warna garis tiap platform: pilih line chart, Format, Lines, atur Series per platform. Standar: Shopee D9622B, TikTok 2B6CB0, Lazada 2F9E6E, Blibli 8E5BB5. Pada mode buta warna (bab 11) pola garis berbeda dibuat lewat Line style per series.",
   "Kartu JBP: gunakan conditional formatting pada warna font atau latar dengan rule berdasarkan [CC Pacing Warning]: bila 1 maka oranye tua, bila 0 maka teal. Tambahkan juga kata (Di bawah Tier 1) sehingga warna bukan satu-satunya penanda."])
P("Pemeriksaan: Pilih Semua, Net GMV harus Rp7,28 mlr dan klaim Rp85,3 jt (1.307 kasus). Pilih Blibli: Net GMV Rp684 jt, TACOS 4,8 persen, JBP di bawah Tier 1.")

# =============================================================== 8
H("8. Halaman 2: Analisis")
P("Ini template halaman yang meniru halaman kedua referensi: tab di atas, kartu KPI, grafik tren dengan tombol Garis/Kolom, bar dengan garis rata-rata, dan tabel naik/turun. Satu template melayani tiga metrik berkat field parameter.")
T(["No", "Visual", "Isi", "Pengaturan penting"],
  [["1", "Judul + kalimat pengantar", "Text box dengan kata kunci tebal", "Tulis ringkas; satu kalimat tentang lensa yang sedang dilihat"],
   ["2", "Slicer tab", "Metrik[Metrik] (field parameter)", "Style Tile horizontal, Single select ON. Tiga tombol: Net GMV, Margin (CM2), Iklan"],
   ["3", "Filter", "Slicer dropdown PlatSel[label]; slicer dropdown DimSKU[sub_category]; slicer DimMonth[month_start] (rentang)", "Dropdown, ditata dalam satu panel putih"],
   ["4", "Kartu KPI 1", "Net GMV Bulan atau CM2 Bulan atau Belanja Iklan Bulan, menurut tab", "Visual level filter: DimMonth[is_latest_month] = TRUE. Teks bawah: Rata-rata Bulanan dan Bulan Terbaik"],
   ["5", "Kartu KPI 2", "[Delta Net GMV], [Delta Net GMV %] (ikut tab)", "Ikon ▲ teal atau ▼ oranye lewat conditional formatting. Tulis juga kata naik atau turun"],
   ["6", "Grafik tren (Garis)", "X DimMonth[month_label]; Y Metrik (field parameter)", "Marker ON; bulan terbaik diberi label data"],
   ["7", "Grafik tren (Kolom)", "Sama dengan no. 6, jenis Clustered column", "Letakkan persis di atas no. 6; kebergantian lewat bookmark (bab 11)"],
   ["8", "Bar sub-kategori", "Y SubCat[sub_category]; X [Sub Net GMV]", "Garis rata-rata putus-putus (Analytics pane). Filter bulan: DimMonth[is_latest_month]"],
   ["9", "Tabel naik/turun", "Kolom: [Mov Nomor], Movers[product_name], Movers[sub_category], [Mov Teks Delta], [Mov Teks Persen], batang [Mov Delta Rp]", "Filter visual: [Mov Tampil] = 1 dan DimMonth[is_latest_month] = TRUE. Data bar di kolom delta, warna dari [Mov Warna Batang]"],
   ["10", "Parameter Top/Bottom N", "Slicer TopN[TopN]", "Dropdown; bawaan 5"],
   ["11", "Insight di bawah tiap visual", "[Insight Tren], [Insight SKU Turun], [Insight Platform]", "Satu card per kalimat, teks 12 pt"]],
  [1.0, 3.3, 6.3, 5.4])
S(["Untuk grafik tren: tarik Metrik ke Y. Saat tab diganti, grafik berganti dari Net GMV ke CM2 ke Iklan otomatis.",
   "Warna aksen mengikuti tab: pada kartu dan grafik, Format, Colors, fx, Format by Field value, pilih [Warna Aksen Tab].",
   "Tabel naik/turun: peringkat memakai selisih rupiah dan persentase hanya pendamping. SKU dengan basis di bawah Rp5 juta dikeluarkan lewat [Mov Lolos Basis]. Ini sengaja, supaya kita tidak mengulang kelemahan referensi yang menampilkan persen ekstrem dari basis sangat kecil.",
   "Baris pemisah (titik tiga) pada referensi bisa ditiru dengan teks statis ... di antara dua tabel kecil (Top 5 dan Bottom 5): buat dua tabel, satu dengan filter [Mov Rank Naik] <= [TopN Nilai], satu lagi dengan [Mov Rank Naik] > [Mov Total Peringkat] - [TopN Nilai]."])
P("Pemeriksaan: pada tab Net GMV, bulan aktif Oktober, kartu 1 = Rp838,9 jt dan kartu 2 = minus Rp10,0 jt (minus 1,2 persen). Tab Margin: Rp280,8 jt dan plus 7,5 persen. Tab Iklan: Rp53,8 jt dan minus 2,4 persen. Tabel: Daily Sunscreen SPF50 40ml di puncak kenaikan (plus Rp10,07 jt), Anti-Dandruff Shampoo 340ml di puncak penurunan (minus Rp11,90 jt).")

# =============================================================== 9
H("9. Halaman 3: Recovery & Kepatuhan")
T(["Blok", "Visual", "Isi"],
  [["Judul besar", "Card", "[Uang Klaim] (Rp85,3 jt) dengan keterangan 1.307 kasus yang cukup bukti"],
   ["Klaim per platform", "Empat card kecil atau satu tabel", "AppealPack: platform, SUM claim_idr, SUM cases"],
   ["Klaim per kategori", "Bar chart horizontal", "Y AppealPack[category]; X SUM claim_idr; warna oranye tua. Urut menurun"],
   ["Benefit program", "Tabel", "ProgramRecon: platform_code, program_code, period_label, expected_idr, paid_idr, shortfall_idr, recon_status. Filter: recon_status = SHORT_PAID atau UNPAID"],
   ["Kepatuhan harga", "Bar chart", "Y PriceEpisodes[likely_root_cause]; X jumlah baris (Count). Warna ungu"],
   ["Kartu harga", "Dua card", "SUM PriceLeakage[leakage_idr] (Rp64,8 jt), Active Price Alerts (69)"],
   ["Pelanggaran voucher", "Tabel", "VoucherViolations: violation_type, SUM orders, SUM exposure_idr"],
   ["Order berisiko", "Stacked bar tunggal + tabel kecil", "Suspicious[risk_level] dengan Count; bentuk penanda ditambahkan lewat label teks (KRITIS, TINGGI, SEDANG, RENDAH)"],
   ["Aturan yang menyala", "Tabel", "Count order untuk r1_bulk_qty, r2_velocity, r3_farm, r4_price, r5_voucher (gunakan Count dengan filter nilai True)"],
   ["Gerbang publikasi", "Card + teks", "[Gerbang Data] dan [Gerbang Data Detail]"]],
  [3.3, 4.0, 8.7])
P("Drill-through yang berguna: buat halaman tersembunyi bernama Detail Order dengan tabel Suspicious (order_id, platform, risk_score, reasons). Pada halaman Recovery, klik kanan baris, Drill through, Detail Order. Ini yang menunjukkan jejak dari ringkasan ke satu order.")
P("Pemeriksaan: total klaim Rp85.270.011 dengan 1.307 kasus; kebocoran harga Rp64.804.700; pelanggaran voucher 365 order dengan paparan Rp3.699.100; order berisiko 1.560 (kritis 84, tinggi 602, sedang 513, rendah 361).")

# =============================================================== 10
H("10. Halaman 4 sampai 8 (memakai template yang sama)")
P("Setelah tiga halaman utama selesai, halaman berikut mengulang pola yang sama: tab atau slicer di atas, tiga sampai empat kartu KPI, satu grafik besar, satu tabel, dan satu kalimat insight di bawah tiap visual. Salin halaman 2 (klik kanan tab halaman, Duplicate page) lalu ganti isinya.")
T(["Halaman", "Pertanyaan bisnis", "Visual dan measure"],
  [["4 Iklan", "Apakah belanja iklan menguntungkan?", "Kartu: [Ad Spend], [ROAS], [TACOS], [Break-even ROAS]. Grafik: ROAS vs Break-even ROAS per platform (selisih [ROAS Gap]). Tabel: Ads per jenis iklan (CTR, CVR, CPC). Catatan: hari iklan Lazada 5-7 Agustus tidak ada data"],
   ["5 Voucher", "Voucher mana yang boros atau bocor?", "Kartu: [Quota Burn %], [Budget Utilization], [GMV per Seller Rp], [AOV Uplift (Voucher)]. Tabel: Voucher dengan quota_burn lebih dari 1 (misalnya LZDPLT05 terpakai 103 kali dari kuota 8). Grafik: VoucherAOV uplift per platform-bulan"],
   ["6 Kampanye & JBP", "Kampanye mana yang menaikkan GMV tetapi merusak margin? Apakah tier JBP tercapai?", "Scatter: X [Campaign Uplift %], Y [Incremental CM2], titik per kampanye. Kartu: [Margin-Burning Campaigns]. JBP: [Attainment Tier 1], [Attainment Tier 2], [Projected Q GMV], [Required Daily GMV], [Pacing Gap per Day]"],
   ["7 Kepatuhan harga detail", "Siapa yang melanggar harga, seberapa lama, di mana?", "Tabel episode: PriceEpisodes (platform, penjual, SKU, mulai, selesai, jam terpapar, akar masalah). Garis tren: PriceComplianceDaily[compliance_rate]. Kartu: [Official Price Leakage]"],
   ["8 Kesehatan data", "Apakah angka dashboard dapat dipercaya?", "Kartu: [DQ Pass %], [DQ Critical Failed], [Publish Gate]. Tabel DQLatest (check_code, severity, status, detail). Tabel Freshness (umur data per sumber). Tabel PipelineHealth (langkah, durasi, status)"]],
  [3.0, 4.5, 8.5])

# =============================================================== 11
H("11. Interaksi, bookmark, dan aksesibilitas")
H("11.1 Tombol ? (catatan cakupan data)", 2)
S(["Buat text box atau card berisi [Catatan Data] dan beri latar gelap, teks putih. Letakkan di kanan atas.",
   "Buka View, Selection pane dan Bookmarks pane. Di Selection pane, sembunyikan kotak catatan (ikon mata).",
   "Di Bookmarks pane, Add bookmark, namai Catatan Tutup. Munculkan kotak, Add bookmark lagi, namai Catatan Buka. Klik kanan setiap bookmark, matikan Data agar tidak mengubah slicer.",
   "Tombol ? diberi dua perilaku: bookmark Catatan Buka. Tambahkan tombol kecil Tutup di dalam kotak yang memanggil Catatan Tutup."])
H("11.2 Tombol Garis / Kolom", 2)
S(["Letakkan grafik Kolom tepat di atas grafik Garis dengan ukuran sama.",
   "Buat dua bookmark: Mode Garis (grafik Garis terlihat, Kolom disembunyikan) dan Mode Kolom (kebalikannya).",
   "Buat dua tombol; Action masing-masing memanggil bookmark yang sesuai. Beri gaya tombol aktif dan tidak aktif lewat Button, Style, Selected."])
H("11.3 Mode ramah buta warna", 2)
P("Power BI tidak dapat mengganti warna seri pada grafik garis lewat slicer. Cara yang andal:")
S(["Duplikat grafik tren garis. Pada duplikat, atur warna Okabe-Ito dan beda pola garis per seri (Format, Lines, Line style: solid, putus-putus, titik).",
   "Buat dua bookmark Palet Standar dan Palet Buta Warna yang bergantian menampilkan grafik standar dan grafik duplikat. Tombol Palette memanggil bookmark itu.",
   "Untuk elemen berbasis measure (batang naik/turun pada tabel), measure [Warna Naik] dan [Warna Turun] otomatis berganti sesuai slicer Palette.",
   "Selain warna, setiap indikator naik/turun memakai bentuk (▲ ▼) dan kata. Itu pelajaran dari referensi: warna merah-hijau saja tidak cukup."])
H("11.4 Navigasi dan interaksi lain", 2)
B(["Tombol Buka analisis dan tombol kembali memakai Action: Page navigation.",
   "Edit interactions: arahkan agar slicer filter hanya mempengaruhi visual yang relevan. Contoh: slicer Top/Bottom N hanya untuk tabel naik/turun.",
   "Tooltip halaman: buat halaman kecil (Page size: Tooltip) berisi kartu detail SKU, lalu aktifkan pada tabel naik/turun lewat Format, Tooltips, Type Report page.",
   "Sync slicers (View, Sync slicers) agar pilihan platform ikut ke halaman lain bila diinginkan."])
H("11.5 Aksesibilitas (diperiksa sebelum dipublikasikan)", 2)
B(["Alt text pada setiap visual (Format, General, Alt text).",
   "Urutan Tab: Selection pane, tab Tab order, atur dari judul, filter, kartu, grafik, tabel.",
   "Kontras teks setidaknya 4,5 banding 1; teks abu yang dipakai pada tema (5E676B di atas putih) sudah lulus.",
   "Setiap makna warna punya penanda kedua: kata, bentuk, atau pola."])

# =============================================================== 12
H("12. Uji akurasi angka")
P("Sebelum difoto atau dipublikasikan, cocokkan angka berikut. Satu angka yang meleset adalah sinyal ada relasi atau measure yang salah.")
T(["Pemeriksaan", "Angka yang benar", "Di mana"],
  [["Net GMV total", "Rp7.280.003.300", "Command Center, Semua"],
   ["Net GMV Shopee / TikTok / Lazada / Blibli", "3.090.712.000 / 2.437.029.200 / 1.068.488.000 / 683.774.100", "Command Center, tiap platform"],
   ["Net GMV Oktober dan variasi", "838.866.700 dan minus 1,2 persen", "Analisis, tab Net GMV"],
   ["CM2 Oktober dan variasi", "280.798.242 dan plus 7,5 persen", "Analisis, tab Margin"],
   ["TACOS total", "6,25 persen (Oktober 6,42 persen)", "Command Center / Analisis tab Iklan"],
   ["Klaim yang bisa diajukan", "85.270.011 (1.307 kasus)", "Recovery"],
   ["Kebocoran harga toko resmi", "64.804.700 (275 order)", "Recovery"],
   ["Pelanggaran voucher", "365 order, 3.699.100", "Recovery"],
   ["Order ditandai", "1.560 (SHP 494, TTK 375, LZD 455, BLI 236)", "Recovery"],
   ["Gerbang data", "OK_TO_PUBLISH, 20 lulus, 3 peringatan, 0 kritis", "Command Center"]],
  [5.0, 6.5, 4.5])
P("Cara lain yang kuat: untuk setiap angka kunci, jalankan kueri SQL pembandingnya di pgAdmin dan tunjukkan bahwa dashboard dan SQL kembar. Itu praktik rekonsiliasi yang dicari recruiter.")

# =============================================================== 13
H("13. Otomasi refresh")
H("13.1 Menjalankan pipeline otomatis di Windows", 2)
S(["Gunakan skrip automation/run_pipeline.ps1 yang sudah disiapkan. Uji dulu secara manual di PowerShell:"])
C('powershell -ExecutionPolicy Bypass -File C:\\lumina\\ecom_portfolio\\automation\\run_pipeline.ps1')
S(["Buka Task Scheduler (cari di menu Start), Create Basic Task, beri nama Lumina Pipeline Harian.",
   "Trigger: Daily, pilih jam (misalnya 06:00).",
   "Action: Start a program. Program: powershell. Arguments: -ExecutionPolicy Bypass -File C:\\lumina\\ecom_portfolio\\automation\\run_pipeline.ps1",
   "Finish. Klik kanan tugas, Run, lalu periksa kolom Last Run Result bernilai 0x0."])
P("Skrip ini idempoten: file mentah yang sama dilewati, jadi aman dijalankan berulang. Untuk data baru, cukup letakkan file ekspor baru di folder data/raw dengan struktur yang sama.")
H("13.2 Menyegarkan Power BI", 2)
B(["Di Power BI Desktop: Home, Refresh. Data dibaca ulang dari PostgreSQL.",
   "Jika dipublikasikan ke Power BI Service dengan database di komputer Anda, penyegaran terjadwal membutuhkan on-premises data gateway. Untuk portofolio, ini opsional; menyimpan berkas .pbix, PDF, dan tangkapan layar sudah cukup.",
   "Untuk pemantauan hampir real-time di dunia nyata, halaman Kepatuhan memakai DirectQuery dari view ops.v_price_alerts_latest dan ops.v_suspicious_last_24h. Pada latihan ini data statis, jadi cukup dijelaskan polanya."])

# =============================================================== 14
H("14. Kemas portofolio")
H("14.1 Apa yang diserahkan", 2)
B(["Berkas Lumina_Care.pbix (jika ukurannya terlalu besar untuk GitHub, cukup tautan berkas unduhan).",
   "PDF dashboard: File, Export, Export to PDF, semua halaman.",
   "Tangkapan layar tiap halaman (Windows+Shift+S), disimpan sebagai PNG 1920 piksel.",
   "Repositori GitHub: folder sql, automation, powerbi, docs, ditambah README. Jangan unggah folder data/raw jika ukurannya mengganggu; cukup sertakan generator dan petunjuk.",
   "Satu halaman ringkasan: masalah bisnis, solusi, temuan, hasil uji akurasi, keterbatasan."])
H("14.2 Publikasi", 2)
B(["Karena seluruh data fiktif, publikasi ke web tidak membocorkan data nyata. Tetap berhati-hati: Publish to web membuat laporan dapat dilihat siapa pun yang memegang tautan, dan fitur ini bisa dinonaktifkan oleh administrator tenant.",
   "Jika Anda hanya punya akun gratis, pakai PDF dan tangkapan layar. Untuk pelamar, tiga hal yang paling meyakinkan adalah SQL yang bisa dijalankan, dashboard yang angkanya cocok, dan penjelasan Anda yang jelas."])
H("14.3 Poin yang bisa ditaruh di CV (sesuaikan dengan kenyataan Anda)", 2)
B(["Membangun pipeline PostgreSQL untuk 4 marketplace: pembersihan data multi-format, karantina baris bermasalah, dan pemuatan idempoten.",
   "Merancang KPI lanjutan (CM1/CM2, TACOS, uplift kampanye terhadap baseline, pacing JBP) dan dashboard Power BI dengan 8 halaman.",
   "Membangun deteksi kepatuhan harga dan order mencurigakan berbasis aturan dengan recall 100 persen pada data uji terkontrol.",
   "Merekonsiliasi settlement, ERP, dan benefit program platform, menghasilkan paket klaim sekitar Rp85 juta pada data latihan."])
P("Catatan: sebutkan bahwa datanya sintetis. Recruiter menghargai kejujuran itu, dan kunci jawabannya justru membuktikan Anda menguji hasil analisis.")

# =============================================================== 15
H("15. Narasi wawancara (dua menit)")
P("Saya membangun pipeline analitik untuk merek perawatan pribadi fiktif yang dijual di empat marketplace. Datanya sengaja kotor: tiap platform mengekspor format tanggal, angka, dan voucher yang berbeda. "
  "Saya membersihkannya di PostgreSQL, menyimpan baris yang dibuang di tabel karantina, dan memuat ulang secara idempoten. Di atasnya saya membangun KPI yang mengukur uang, bukan hanya penjualan: margin kontribusi setelah iklan, TACOS, dan uplift kampanye terhadap baseline. "
  "Dashboard Power BI saya punya halaman Command Center untuk keputusan cepat, halaman Analisis untuk menelusuri sebab, dan halaman Recovery yang menghitung klaim yang bisa diajukan ke platform sekitar Rp85 juta pada data latihan. "
  "Karena datanya sintetis, saya menyuntikkan anomali dengan kunci jawaban, sehingga bisa mengukur bahwa aturan deteksi saya menemukan seluruhnya. Satu bug yang saya temukan sendiri: memuat ulang DDL staging membuat data hilang diam-diam karena registri file masih mengingatnya, dan saya memperbaikinya dengan mereset registri.")
T(["Pertanyaan yang sering muncul", "Poin jawaban"],
  [["Mengapa memisahkan stg, dwh, mart?", "Stg menyimpan data apa adanya agar bisa ditelusuri; dwh bersih dan terstruktur; mart siap dipakai dashboard. Perubahan aturan tidak merusak data asli"],
  ["Bagaimana Anda memastikan angka benar?", "Rekonsiliasi dengan kunci jawaban, 34 pemeriksaan kualitas data, dan tie-out Rp7.280.003.300 antara SQL dan dashboard"],
   ["Apa itu TACOS dan mengapa bukan ROAS saja?", "TACOS = belanja iklan dibagi seluruh Net GMV; mengukur ketergantungan pada iklan. ROAS yang bagus bisa menutupi iklan yang tetap merugikan margin"],
   ["Bagaimana mendeteksi order mencurigakan?", "Lima aturan berbobot (qty besar, burst waktu, akun kembar, harga anomali, voucher) menjadi skor risiko. Kelemahan: ambang perlu dikalibrasi pada data nyata"],
   ["Apa keterbatasan proyek ini?", "Data sintetis, real-time disimulasikan, aturan berbasis ambang, dan 18 order TikTok dengan ID rusak dikarantina (latihan lanjutan untuk memulihkannya)"]],
  [6.0, 10.0])

# =============================================================== 16
H("16. Pemecahan masalah umum")
T(["Gejala", "Kemungkinan sebab", "Solusi"],
  [["psql tidak dikenali", "PATH belum berisi folder bin PostgreSQL", "Tambahkan C:\\Program Files\\PostgreSQL\\18\\bin ke Path, buka ulang PowerShell"],
   ["password authentication failed", "Kata sandi salah, atau pengguna ecom belum dibuat", "Ulangi pembuatan pengguna ecom; cek $env:PGPASSWORD"],
   ["Power BI gagal terhubung", "Server atau port salah; PostgreSQL tidak berjalan", "Buka Services, pastikan postgresql-x64-18 berstatus Running; coba 127.0.0.1:5432"],
   ["Muncul pesan tentang enkripsi", "Koneksi lokal tanpa SSL", "Pilih Connect; aman untuk komputer sendiri"],
   ["Bulan urut abjad", "Belum Sort by column", "DimMonth, month_label, Sort by column, month_no"],
   ["Kartu menampilkan total yang sama untuk semua platform", "Tabel tanpa relasi atau relasi tidak aktif", "Periksa Model view; untuk CC pastikan measure memakai [Platform Terpilih]"],
   ["Measure Insight kosong", "Tabel Movers atau KPI_M tidak punya data bulan terbaru, atau nama tabel berbeda", "Cek nama tabel sesuai bab 4.1 dan relasi ke DimMonth"],
   ["Angka tidak cocok dengan SQL", "Ada filter halaman atau slicer yang aktif, atau pakai tabel yang salah", "Hapus semua filter lalu bandingkan lagi; gunakan tabel yang ditunjuk bab 12"],
   ["Refresh sangat lambat", "Memuat tabel terlalu banyak atau besar", "Hapus kolom tak terpakai di Power Query; pakai view mart, bukan tabel dwh mentah"]],
  [4.2, 5.4, 6.4])

# =============================================================== LAMPIRAN
H("Lampiran A. KPI tambahan dari penyesuaian referensi")
T(["KPI atau elemen", "Definisi", "Asal ide"],
  [["Variasi vs bulan lalu (Rp dan persen)", "Nilai bulan aktif dikurangi bulan lalu; persen terhadap bulan lalu", "Kartu Life Satisfaction Variation"],
   ["Bulan terbaik", "Bulan dengan Net GMV atau CM2 tertinggi", "Kartu Best Year"],
   ["Siapa naik, siapa turun", "SKU dengan kenaikan/penurunan terbesar dalam rupiah; hanya yang basis bulan lalu minimal Rp5 juta", "Tabel Shifting Pulse, diperbaiki"],
   ["Garis rata-rata", "Rata-rata antar wilayah atau sub-kategori pada bar chart", "Dashed line pada bar chart wilayah"],
   ["Insight dinamis", "Kalimat yang dihitung dari data terkini oleh measure DAX", "Kalimat di bawah tiap visual"],
   ["Uang di meja", "Klaim + kebocoran harga + paparan voucher + gerbang data", "Ide baru; tidak ada di referensi"],
   ["Mode buta warna", "Palet Okabe-Ito, pola garis, bentuk dan kata sebagai penanda kedua", "Slicer Color blindness palette"]],
  [4.4, 7.6, 4.0])

H("Lampiran B. Daftar berkas proyek")
T(["Berkas", "Kegunaan"],
  [["sql/00 sampai 13", "Database, pembersihan, KPI, kepatuhan, deteksi, rekonsiliasi, kualitas data, uji akurasi"],
   ["sql/14_mart_dashboard.sql", "View untuk dashboard hasil adaptasi referensi"],
   ["automation/load_raw.py, run_pipeline.sh, run_pipeline.ps1", "Pemuatan data dan pipeline (Linux/macOS dan Windows)"],
   ["powerbi/measures.dax, measures_dashboard.dax", "Seluruh measure DAX"],
   ["powerbi/power_query.pq", "Daftar tabel, relasi, dan tabel kontrol"],
   ["powerbi/lumina_theme.json, lumina_theme_buta_warna.json", "Tema Power BI"],
   ["docs/KPI_dictionary.md, data_dictionary.md", "Kamus KPI dan data"],
   ["answer_key/", "Kunci jawaban data sintetis"]],
  [7.0, 9.0])

out = os.path.join(ROOT, "docs", "Panduan_PowerBI_Langkah_Demi_Langkah.docx")
doc.save(out)
print("saved", out)
