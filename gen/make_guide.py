"""Membuat docs/Panduan_Portofolio_Ecommerce_Analyst.docx  (Arial 12, spasi 1,5)."""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
doc = Document()
sec = doc.sections[0]
sec.page_width = Cm(21.0)
sec.page_height = Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.5)
sec.top_margin = sec.bottom_margin = Cm(2.5)

FONT = "Arial"


def set_font(style, size=12, bold=None, color=None):
    style.font.name = FONT
    style.font.size = Pt(size)
    if bold is not None:
        style.font.bold = bold
    if color:
        style.font.color.rgb = RGBColor(*color)
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(a), FONT)
    pf = style.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    pf.space_after = Pt(6)


for name in ("Normal", "List Bullet", "List Number", "Title"):
    set_font(doc.styles[name])
set_font(doc.styles["Title"], 12, True)
for lvl in (1, 2, 3):
    set_font(doc.styles[f"Heading {lvl}"], 12, True, (0, 0, 0))
    doc.styles[f"Heading {lvl}"].paragraph_format.space_before = Pt(12)
    doc.styles[f"Heading {lvl}"].paragraph_format.keep_with_next = True


def P(text, bold=False):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = bold
    return p


def B(items, style="List Bullet"):
    for t in items:
        doc.add_paragraph(t, style=style)


def H(text, lvl=1):
    doc.add_heading(text, level=lvl)


def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)


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


# ------------------------------------------------------------------ Sampul
doc.add_paragraph("Panduan Portofolio E-Commerce Data Analyst", style="Title")
P("Proyek: Lumina Care — analitik Personal Care di Shopee, TikTok Shop/Tokopedia, Lazada, dan Blibli", True)
P("Seluruh data bersifat sintetis dan fiktif (merek, tarif, kontrak, angka). Periode data: 1 Januari – 31 Oktober 2026. "
  "Stack: PostgreSQL 16, SQL murni (tanpa ORM), Power BI Desktop, Python hanya untuk memuat file.")

# ------------------------------------------------------------------ 1
H("1. Tujuan dan pemetaan ke kebutuhan recruiter")
P("Proyek ini disusun supaya setiap poin lowongan dapat ditunjukkan dengan bukti yang bisa dijalankan ulang, bukan sekadar klaim di CV.")
T(["Kebutuhan recruiter", "Bukti di proyek", "Berkas utama"],
  [["Dashboard GMV, Ads, Voucher, Promotion, JBP & Campaign",
    "Mart KPI + 8 halaman Power BI + ±80 measure DAX",
    "sql/07_marts_kpi.sql, powerbi/measures.dax"],
   ["Otomasi ekstraksi multi-platform (harian/real-time)",
    "Loader idempoten berbasis checksum, pipeline satu perintah, prosedur refresh terjadwal",
    "automation/load_raw.py, automation/run_pipeline.sh, sql/12_etl_procedures.sql"],
   ["Monitoring kepatuhan harga & promosi, order mencurigakan/bulk",
    "Alert harga terkini, episode pelanggaran, kebocoran harga, validasi voucher, 5 aturan risiko dengan skor",
    "sql/08_price_promo_compliance.sql, sql/09_bulk_order_detection.sql"],
   ["Validasi & rekonsiliasi benefit program, dukung banding/dispute",
    "Audit settlement, ERP, benefit JBP expected vs dibayar, paket banding per platform",
    "sql/10_reconciliation_appeal.sql"],
   ["Akurasi & integritas data, insight yang bisa ditindak",
    "34 pemeriksaan DQ dengan gerbang publikasi, karantina baris kotor, uji akurasi vs kunci jawaban",
    "sql/11_data_quality.sql, sql/13_validate_answer_key.sql"]],
  [4.5, 6.5, 5.0])

# ------------------------------------------------------------------ 2
H("2. Arsitektur")
P("Alur data: file ekspor mentah → schema stg (semua TEXT) → fungsi pembersih di schema etl → model bintang di schema dwh → mart KPI dan modul operasional di schema ops → Power BI.")
B(["Landing (stg): data apa adanya agar setiap angka bisa ditelusuri ke file dan nomor barisnya.",
   "Karantina (ops.quarantine_row): baris yang dibuang disimpan beserta alasan dan muatan JSON, sehingga pembersihan bisa diaudit.",
   "Full-refresh CREATE TABLE AS: skrip dapat dijalankan ulang kapan saja dan hasilnya sama.",
   "Registri file sha256 (etl.file_registry): file yang sama dilewati, file yang berubah dimuat ulang.",
   "Gerbang kualitas: pemeriksaan CRITICAL yang gagal mengubah publish_gate menjadi BLOCK_PUBLISH."])

# ------------------------------------------------------------------ 3
H("3. Cara menjalankan dari nol")
P("Prasyarat: PostgreSQL 14+ (diuji di 16) dengan ekstensi pg_trgm, Python 3.9+, klien psql.")
B(["Buat database sebagai superuser: psql -U postgres -f sql/00_create_database.sql",
   "Buat peran dan beri hak, misalnya pengguna ecom dengan kata sandi, pada database ecom_lumina.",
   "Buat tabel staging satu kali: psql -d ecom_lumina -f sql/01_staging_ddl.sql (perhatian: ini mengosongkan stg dan mereset registri).",
   "Jalankan pipeline: export PGPASSWORD=... lalu ./automation/run_pipeline.sh (sekitar 80 detik untuk ±460 ribu baris mentah).",
   "Jalankan ulang pipeline untuk membuktikan idempoten: semua 57 file dilewati dan jumlah baris tidak berubah.",
   "Opsional: buka answer_key/ dan hasil qa.validation_summary untuk melihat akurasi deteksi."], "List Number")
P("Penting: sql/01_staging_ddl.sql sengaja tidak dimasukkan ke run_all.sql karena ia membuat ulang tabel stg yang kosong. "
  "Itu pelajaran dari bug nyata yang ditemukan saat pengujian: registri masih menandai file sebagai sudah dimuat sehingga data hilang diam-diam. "
  "Perbaikannya: skrip DDL juga mereset registri. Ceritakan temuan ini saat wawancara — ia menunjukkan Anda menguji idempotensi, bukan hanya jalur bahagia.")

# ------------------------------------------------------------------ 4
H("4. Data kotor dan cara membersihkannya")
P("Setiap platform mengekspor dengan format berbeda. Tabel berikut meringkas jebakan utama; detail lengkap ada di docs/data_dictionary.md.")
T(["Platform", "Jebakan", "Penanganan"],
  [["Shopee", "Titik ribuan, dd/mm/yyyy, voucher order diulang di tiap baris", "Parser angka Indonesia; voucher diambil sekali per order"],
   ["TikTok/Tokopedia", "UTC (+7 jam), nilai sudah net voucher, ID order rusak menjadi notasi ilmiah", "Konversi zona waktu, rekonstruksi nilai, ID rusak dikarantina"],
   ["Lazada", "Desimal titik, bulan Inggris, tidak ada total baris", "Parser khusus, qty dipulihkan dari total"],
   ["Blibli", "Delimiter titik-koma, MM/DD/YYYY 12 jam, string Rp, voucher hanya baris pertama", "Loader dengan delimiter berbeda, parser tanggal, voucher baris pertama"]],
  [3.5, 6.5, 6.0])
P("Hasil pembersihan order: 104.793 baris mentah menjadi 104.032 baris bersih dan 69.250 order. 685 duplikat persis, 48 order uji, 24 baris ID rusak, dan 4 baris qty tak terpulihkan dikarantina. "
  "155 SKU dipulihkan dari judul listing dan 51 qty diperbaiki. GMV per platform-bulan cocok dengan kunci jawaban; selisih hanya berasal dari order yang dikarantina (Lazada 0,02 %, TikTok 0,06 %).")

# ------------------------------------------------------------------ 5
H("5. KPI lanjutan")
P("Kamus lengkap ada di docs/KPI_dictionary.md. KPI yang membedakan portofolio ini dari dashboard GMV biasa:")
B(["Contribution Margin CM1 dan CM2: Net Sales dikurangi COGS dan biaya platform sesuai kontrak (komisi dikurangi poin diskon kampanye), lalu dikurangi belanja iklan.",
   "TACOS dan Break-even ROAS: iklan dinilai terhadap margin, bukan hanya ROAS yang tampak bagus.",
   "Uplift kampanye terhadap baseline 14 hari non-kampanye, dengan vonis MERUGIKAN MARGIN bila Incremental CM2 negatif. Pada data latihan, 9 dari 90 kampanye merugikan margin (total −Rp10,5 juta) sementara 81 lainnya menambah Rp200 juta.",
   "Pacing JBP: proyeksi GMV kuartal berjalan terhadap ambang tier dan GMV harian yang dibutuhkan untuk tier 2. Blibli Q4 terproyeksi di bawah tier 1.",
   "AOV uplift voucher dan pemecahan biaya voucher co-fund antara penjual dan platform.",
   "Kebocoran harga toko resmi dari order aktual (rupiah di bawah floor), terpisah menurut salah-harga dan pelanggaran biasa."])

# ------------------------------------------------------------------ 6
H("6. Model dan halaman Power BI")
H("6.1 Memuat data dan model", 2)
B(["Buat parameter pServer dan pDatabase, lalu buat query sesuai powerbi/power_query.pq (satu fungsi fnPg dan ±33 query).",
   "Mode Import untuk semua tabel. DirectQuery hanya untuk halaman real-time (PriceAlerts dan Suspicious) bila server mengizinkan.",
   "Relasi: DimDate, DimPlatform, DimSKU sebagai dimensi dengan filter satu arah ke tabel fakta. Hindari relasi dua arah.",
   "Tempel measure dari powerbi/measures.dax ke tabel _Measures dan kelompokkan dengan display folder (GMV, Profitabilitas, Iklan, Voucher, Kampanye, JBP, Kepatuhan, Risiko, Rekonsiliasi, Kualitas)."])
H("6.2 Delapan halaman yang disarankan", 2)
T(["Halaman", "Isi utama", "Sumber"],
  [["1 Ringkasan Eksekutif", "Net GMV, CM2 %, TACOS, cancel rate, tren harian + MA7, porsi platform, pacing JBP", "KPI_M, GMVTrend, JBPPacing"],
   ["2 GMV & Margin", "Net GMV per platform/sub-kategori, waterfall GMV → Net Sales → CM1 → CM2, SKU membakar margin", "Sales, KPI_M, SKUMargin"],
   ["3 Iklan", "Spend, ROAS vs Break-even ROAS, TACOS, CPC/CTR/CVR per jenis iklan, hari data hilang", "Ads, AdsPlatformDaily"],
   ["4 Voucher", "Quota burn, budget utilization, AOV uplift, pelanggaran aturan, pecahan biaya", "Voucher, VoucherAOV, VoucherViolations"],
   ["5 Promo & Kampanye", "Uplift vs baseline, Incremental GMV/CM2, vonis margin, kedalaman diskon", "Campaign"],
   ["6 JBP & Benefit", "Attainment tier, rebate yang diharapkan, pacing kuartal berjalan, status benefit", "JBP, JBPPacing, ProgramRecon"],
   ["7 Kepatuhan Harga & Order Mencurigakan", "Alert terkini, episode pelanggaran, kebocoran harga, daftar order berisiko, kluster pembeli", "PriceAlerts, PriceEpisodes, PriceLeakage, Suspicious"],
   ["8 Rekonsiliasi & Banding + Kesehatan Data", "Paket banding per platform, selisih settlement/ERP, papan kasus, skor DQ, kesegaran sumber", "AppealPack, SettlementAudit, ERPAudit, DQLatest, Freshness"]],
  [4.0, 8.0, 4.0])
P("Referensi dashboard dari Anda akan menentukan tata letak, palet warna, dan gaya visual. Setelah referensi dikirim, panduan halaman ini dapat disesuaikan satu per satu.")

# ------------------------------------------------------------------ 7
H("7. Otomasi dan mendekati real-time")
B(["Harian: jadwalkan automation/run_pipeline.sh dengan cron (Linux/macOS) atau Task Scheduler (Windows).",
   "Per jam: CALL etl.sp_refresh_marts() menyegarkan materialized view dan menjalankan pemeriksaan kualitas; cocok dengan pg_cron (contoh perintah ada di sql/12_etl_procedures.sql).",
   "Real-time: view ops.v_price_alerts_latest dan ops.v_suspicious_last_24h selalu menghitung dari snapshot/order terbaru; pasang di halaman DirectQuery dengan refresh halaman otomatis.",
   "Kesehatan pipeline: ops.v_pipeline_health (durasi dan status tiap langkah) dan ops.v_source_freshness (umur data per sumber)."])
P("Catatan jujur: data latihan ini statis. Pada proyek nyata, sumber \"real-time\" adalah API atau ekspor terjadwal; yang Anda tunjukkan di sini adalah pola idempoten, berlog, dan bergerbang kualitas yang akan tetap berlaku.")

# ------------------------------------------------------------------ 8
H("8. Bukti akurasi (uji terhadap kunci jawaban)")
P("Karena data sintetis, setiap anomali yang disuntikkan tercatat di folder answer_key. Skrip sql/13_validate_answer_key.sql mengukur seberapa baik aturan Anda menemukannya.")
T(["Pengujian", "Recall", "Precision / catatan"],
  [["Order mencurigakan (bulk, velocity, akun kembar, salah harga)", "100 %", "98,3 % (21 order di luar kunci)"],
   ["Pelanggaran voucher (min-spend, kedaluwarsa, kuota)", "100 %", "—"],
   ["Selisih settlement (komisi, subsidi voucher, duplikat, belum cair)", "100 %", "99,6 % pada komisi"],
   ["Selisih ERP (hilang, nilai beda, hanya batal)", "100 %", "99,2 %–100 %"],
   ["Orphan settlement", "100 %", "80 % (15 tambahan dari ID TikTok rusak)"],
   ["Kekurangan benefit program (6 kasus)", "100 %", "100 %"],
   ["Pelanggaran harga per snapshot", "98,1 %", "100 % (selisih = snapshot rusak tak terpulihkan)"]],
  [8.0, 2.5, 5.5])
P("Tiga pelajaran yang layak diceritakan: (1) perubahan satu aturan (mengikutsertakan order batal pada uji voucher) menaikkan recall dari 94 % menjadi 100 % — "
  "pelanggaran terjadi saat order dibuat, bukan saat selesai; (2) akun kembar di platform tanpa username unik hanya tertangkap oleh aturan velocity, bukan aturan akun kembar; "
  "(3) satu baris settlement Blibli melanggar identitas net payout pada data platform sendiri, temuan nyata dari pemeriksaan DQ.")

# ------------------------------------------------------------------ 9
H("9. Temuan bisnis contoh (untuk narasi portofolio)")
B(["Total klaim yang dapat diajukan ke platform ±Rp85 juta: Rp71,4 juta settlement belum cair lebih dari 14 hari (703 order), Rp8,9 juta benefit program kurang bayar (4 kasus), Rp3,6 juta benefit tidak dibayar (2 kasus), Rp0,85 juta komisi berlebih (534 order), Rp0,59 juta subsidi voucher hilang (64 order).",
   "Rebate kuartalan Shopee Q2 dibayar pada tier 1 padahal pencapaian tier 2: kekurangan Rp7,4 juta. Rebate Blibli Q2 tidak dibayar sama sekali (Rp3,2 juta).",
   "Voucher platform LZDPLT05 terpakai 103 kali padahal kuota 8: contoh kebocoran kontrol kuota.",
   "Enam insiden salah-harga di toko resmi (harga 10 % dari RRP) menghasilkan kebocoran harga ±Rp64,8 juta pada 275 order.",
   "Blibli Q4 terproyeksi Rp169 juta, di bawah tier 1 (Rp170 juta): rekomendasi dorong GMV harian dari Rp1,84 juta ke sekitar Rp2,34 juta untuk tier 2."])
P("Tulis temuan dengan pola: apa yang terjadi, berapa rupiahnya, siapa pemilik tindakan, dan apa langkah berikutnya. Itulah yang dimaksud \"data yang bisa ditindak\" pada lowongan.")

# ------------------------------------------------------------------ 10
H("10. Cara menceritakan proyek ini saat wawancara")
B(["Mulai dari masalah bisnis (uang bocor di harga, voucher, dan benefit platform), baru ke teknik.",
   "Tunjukkan satu alur bukti: halaman banding → daftar order → baris mentah di karantina atau staging.",
   "Sebutkan keterbatasan sendiri: data sintetis, sumber real-time disimulasikan, aturan risiko berbasis ambang yang perlu dikalibrasi dengan data nyata.",
   "Bawa angka akurasi dari bagian 8 dan cerita bug idempotensi dari bagian 3."])

# ------------------------------------------------------------------ 11
H("11. Latihan lanjutan")
B(["Pulihkan 18 order TikTok ber-ID notasi ilmiah lewat sidik jari (tanggal, nilai, kota) terhadap ERP, lalu ukur seberapa banyak orphan settlement hilang.",
   "Tambahkan model skor risiko berbobot hasil regresi logistik pada fitur order dan bandingkan dengan aturan.",
   "Bangun halaman Power BI what-if untuk mencapai tier 2 JBP (slider GMV harian).",
   "Tambahkan pengujian SQL otomatis (pgTAP) untuk setiap pemeriksaan DQ CRITICAL.",
   "Jadwalkan pipeline dengan pg_cron dan buat peringatan email bila publish_gate berubah menjadi BLOCK_PUBLISH."])

out = os.path.join(ROOT, "docs", "Panduan_Portofolio_Ecommerce_Analyst.docx")
doc.save(out)
print("saved", out)
