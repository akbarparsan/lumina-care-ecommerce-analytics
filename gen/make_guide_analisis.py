"""Panduan halaman Analisis (tab + perubahan warna). Arial 12, spasi 1,5."""
import os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(ROOT, "gen", "make_guide_powerbi.py"), encoding="utf-8").read()
head = src.split("# =============================================================== SAMPUL")[0]
exec(head)   # memakai ulang pembantu: doc, P, H, B, S, C, T

doc.add_paragraph("Panduan Halaman Analisis: Tab, Kartu KPI, Grafik, dan Perubahan Warna", style="Title")
P("Proyek Lumina Care. Dokumen ini menjelaskan, langkah demi langkah, cara membangun halaman 2 (Analisis) seperti mock-up, termasuk bagaimana warna berubah ketika tab Net GMV, Margin (CM2), atau Iklan dipilih.", True)
P("Catatan kejujuran: semua measure DAX dan langkah klik di bawah belum bisa saya jalankan di Power BI (hanya berjalan di Windows). Letak beberapa menu bisa berbeda di versi Anda; gunakan kotak pencarian di panel Format bila menu tidak ditemukan. Bila ada measure yang error, kirimkan nama dan pesannya.", italic=True)

# ------------------------------------------------------------------ 1
H("1. Hasil akhir yang dituju")
P("Satu halaman melayani tiga lensa. Saat tab diganti, enam hal berubah serentak: judul kartu, angka, perbandingan bulan lalu, grafik, kalimat insight, dan warna aksen. Yang tetap hanya tabel naik/turun dan batang sub-kategori (isinya tidak bergantung tab, hanya warnanya).")
H("1.1 Warna per tab", 2)
T(["Tab", "Warna standar", "Warna ramah buta warna", "Makna"],
  [["Net GMV", "teal #1F6F78", "biru #0072B2", "penjualan"],
   ["Margin (CM2)", "oranye tua #B8541F", "oranye-merah #D55E00", "keuntungan setelah iklan"],
   ["Iklan", "ungu #5B4B9A", "merah muda #CC79A7", "belanja iklan"]], [3, 4, 4.5, 4.5])
H("1.2 Elemen mana yang berubah warna, dan caranya", 2)
T(["Elemen", "Cara warnanya mengikuti tab", "Mekanisme Power BI"],
  [["Tombol tab terpilih", "Terisi warna aksen tab itu", "Tombol + bookmark; Style > Apply settings to: Selected (warna tetap per tombol)"],
   ["Garis di sisi kiri kartu KPI", "Berganti teal / oranye / ungu", "Shape Rectangle, Fill > fx > Field value > [Warna Aksen Tab]"],
   ["Angka besar kartu KPI", "Berganti warna", "Card > Callout value > Color > fx > Field value > [Warna Aksen Tab]"],
   ["Grafik garis dan kolom", "Berganti warna", "Tiga measure seri (Seri Net GMV, Seri CM2, Seri Iklan); hanya satu berisi data, warna tiap seri diatur tetap"],
   ["Batang sub-kategori", "Berganti warna", "Bars > Color > fx > Field value > [Warna Aksen Tab]"],
   ["Segitiga dan selisih (▲ ▼)", "Teal bila naik, oranye bila turun, tidak bergantung tab", "Font color > fx > [Warna Delta]"]],
  [4.2, 5.2, 6.6])
P("Catatan penting: warna garis/kolom pada grafik tidak bisa diganti lewat slicer atau field parameter, karena Power BI hanya mengizinkan warna seri tetap. Karena itu grafik memakai tiga measure terpisah. Cara itu andal dan tidak butuh bookmark tambahan.")

# ------------------------------------------------------------------ 2
H("2. Prasyarat (cek dulu)")
B(["Tabel termuat: DimMonth, KPIMonth, KPI_M, SubCat, Movers, DimPlatform, DimSKU. Relasi: DimMonth[month_start] ke KPIMonth, SubCat, Movers (satu arah).",
   "DimMonth[month_label] sudah di-Sort by column > month_no.",
   "Tabel kontrol ada: Palette (STD, CB), TopN (parameter 1 sampai 10, bawaan 5), dan TabSel (bagian 2.1).",
   "Tabel _Measures ada dan measure dasar (Net GMV Bulan, CM2 Bulan, Belanja Iklan Bulan, Rata-rata Bulanan *, Warna Naik, Warna Turun, Mov *, Sub *, TopN Nilai, Palet Terpilih) sudah dibuat.",
   "Tema lumina_theme.json sudah diterapkan dan kanvas 1440 x 960."])
H("2.1 Membuat tabel TabSel (pengganti field parameter)", 2)
P("Tab tidak memerlukan field parameter. Cukup satu tabel kecil bernama TabSel dengan kolom urut (0, 1, 2) dan label. Cara ini lebih sederhana dan tidak bergantung pada fitur New parameter.")
S(["Home > Transform data > New Source > Blank Query. Di panel kanan beri nama query: TabSel.",
   "Klik Advanced Editor, hapus isinya, lalu tempel kode di bawah, klik Done.",
   "Home > Close & Apply.",
   "Di panel Data, klik kolom label pada tabel TabSel. Tab Column tools > Sort by column > urut. Tanpa ini, tab berurutan abjad.",
   "Tabel TabSel berdiri sendiri: jangan buat relasi."])
C("""let
    Source = Table.FromRows(
        { {0, "Net GMV"}, {1, "Margin (CM2)"}, {2, "Iklan"} },
        {"urut", "label"}
    ),
    Typed = Table.TransformColumnTypes(Source, {{"urut", Int64.Type}, {"label", type text}})
in
    Typed""")

# ------------------------------------------------------------------ 3
H("3. Measure untuk halaman Analisis")
P("Seluruh measure baru ada di Lampiran A dan di berkas powerbi/measures_dashboard.dax (bagian HALAMAN ANALISIS). Tempel satu per satu di tabel _Measures: klik kanan tabel > New measure > tempel > Enter.")
P("Sebelumnya, ganti measure lama Warna Aksen Tab dengan versi baru di lampiran (versi baru ikut palet buta warna). Urutan pembuatan yang aman: Tab Aktif, Bulan Akhir, Bulan Awal, Bulan Akhir Label, Bulan Awal Label, TACOS Akhir, TACOS Awal, lalu measure lainnya.")
T(["Measure", "Fungsi", "Nilai uji (Net GMV / CM2 / Iklan)"],
  [["Tab Aktif", "0, 1, atau 2 sesuai tab", "0 / 1 / 2"],
   ["KPI Nilai Teks", "Angka besar kartu 1", "Rp838,9 jt / Rp280,8 jt / Rp53,8 jt"],
   ["KPI Rata Teks", "Rata-rata bulanan (+TACOS pada tab Iklan)", "Rp728,0 jt / Rp244,9 jt / Rp45,5 jt + TACOS 6,42 %"],
   ["KPI Terbaik Teks", "Bulan terbaik", "Sep (Rp848,9 jt) / Okt (Rp280,8 jt) / Sep (Rp55,2 jt)"],
   ["KPI Delta Teks", "Selisih vs bulan lalu", "▼ −Rp10,0 jt / ▲ +Rp19,6 jt / ▼ −Rp1,3 jt"],
   ["KPI Delta Pct Teks", "Persen vs bulan lalu", "−1,2 % / +7,5 % / −2,4 %"],
   ["KPI Extra", "Keterangan definisi", "Net GMV valid... / Net sales − COGS... / TACOS Jan 6,15 %"],
   ["Insight Analisis", "Kalimat insight menurut tab", "lihat bagian 8"],
   ["Insight Sub", "Kalimat sub-kategori", "Skincare = 53 % Net GMV Okt; Oral Care dan Men Grooming paling rendah."]],
  [4.0, 5.2, 6.8])
P("Pemisah desimal pada hasil teks (titik atau koma) mengikuti pengaturan regional komputer Anda. Bila ingin koma Indonesia, tambahkan argumen ketiga \"id-ID\" pada fungsi FORMAT yang memuat angka desimal.")
P("Penting (pelajaran dari galat sebelumnya): jangan menulis measure langsung di dalam filter CALCULATE, misalnya KPIMonth[month_start] = [Bulan Akhir]. Simpan dulu ke VAR, lalu pakai variabelnya. Semua measure di lampiran sudah ditulis demikian.")

# ------------------------------------------------------------------ 4
H("4. Kanvas dan tata letak")
P("Buat halaman baru, beri nama Analisis (klik kanan tab halaman > Rename). Format > Page > Canvas settings: Custom 1440 x 960. Gunakan Format > General > Properties > Size & Position untuk mengisi posisi tepat tiap elemen.")
T(["Area", "X", "Y", "Lebar", "Tinggi", "Isi"],
  [["Judul dan pengantar", "40", "24", "820", "96", "Text box"],
   ["Navigasi halaman", "900", "36", "500", "44", "Page navigator"],
   ["Tombol tab (3)", "40", "136", "3 x 170 + jarak 10", "44", "Tombol + bookmark"],
   ["Panel filter", "900", "130", "500", "56", "Slicer dropdown"],
   ["Panel kiri: Sub-kategori", "40", "204", "300", "716", "Bar chart + insight"],
   ["Kartu KPI 1", "356", "204", "252", "150", "Garis kiri + teks + card"],
   ["Kartu KPI 2", "624", "204", "252", "150", "Garis kiri + teks + card"],
   ["Grafik tren", "356", "370", "520", "550", "Line + Column + insight"],
   ["Panel kanan: naik/turun", "892", "204", "508", "716", "Slicer TopN + tabel"]],
  [4.2, 1.2, 1.2, 3.2, 1.4, 4.8])
P("Setiap panel diberi latar putih, sudut membulat 14, dan garis tepi #E4DED3 (sudah diatur tema). Gunakan Rectangle putih di belakang bila visual tidak berlatar.")

# ------------------------------------------------------------------ 5
H("5. Judul, pengantar, dan navigasi")
S(["Text box 1: ketik Lumina Care, Georgia, miring (italic), 40 pt.",
   "Text box 2 (pengantar): ketik 'Tiga lensa atas satu bisnis: ', lalu tambahkan nilai dinamis. Karena Text box tidak dapat mengubah warna sebagian teks secara dinamis, tulis kata lensa aktif dari measure KPI Judul versi singkat bila mau, atau cukup tulis kalimat statis 'Tiga lensa atas satu bisnis: Net GMV, margin, dan iklan, diperiksa berdampingan.' Warna aksen cukup ditampilkan lewat kartu dan tombol.",
   "Insert > Buttons > Navigator > Page navigator, letakkan di kanan atas. Format > Pages: pilih Command Center, Analisis, Recovery & Kepatuhan. Style: tab; Selected: latar putih."])

# ------------------------------------------------------------------ 6
H("6. Tombol tab yang berganti warna")
P("Slicer field parameter standar tidak bisa memberi tiap tab warna sendiri. Solusinya: simpan pilihan di slicer TabSel yang disembunyikan, lalu tombol berwarna memanggil bookmark yang menyimpan pilihan itu.")
S(["Tarik TabSel[label] ke visual Slicer. Pengaturan: Single select On, Select all Off. Pilih Net GMV.",
   "Buka View > Selection pane. Klik ikon mata di samping slicer TabSel agar tersembunyi. Slicer tersembunyi tetap bekerja dan tersimpan di bookmark.",
   "Buka View > Bookmarks pane. Munculkan slicer sebentar (ikon mata), pilih Net GMV, lalu Add. Namai: Tab Net GMV. Ulangi untuk Margin (CM2) dengan nama Tab CM2, dan Iklan dengan nama Tab Iklan. Setelah selesai sembunyikan slicernya lagi.",
   "Untuk TIAP bookmark: klik titik tiga > matikan Display, nyalakan Data, nyalakan Current page. (Display Off penting supaya bookmark ini tidak mengubah visibilitas grafik Garis/Kolom yang diatur bookmark lain.)",
   "Insert > Buttons > Blank, tiga kali. Beri teks Net GMV, Margin (CM2), Iklan. Ukuran 170 x 44, sudut membulat 10.",
   "Gaya Default tiap tombol: latar putih, teks #1E2528 tebal, garis tepi #D9D2C5.",
   "Di bagian Style, ubah 'Apply settings to' dari Default menjadi Selected. Atur warna isi: tombol Net GMV #1F6F78, tombol CM2 #B8541F, tombol Iklan #5B4B9A; teks putih; garis tepi warna yang sama.",
   "Action: nyalakan, Type: Bookmark, pilih bookmark tombol itu (Tab Net GMV, Tab CM2, Tab Iklan).",
   "Pilih ketiga tombol dan Group agar rapi. Pastikan sebelum menyimpan, slicer TabSel berada pada Net GMV, lalu klik tombol Net GMV sekali agar halaman dibuka dalam kondisi itu."])
P("Hasil: tombol yang aktif terisi warna aksen tab (teal, oranye, atau ungu), dua tombol lainnya putih. Tombol dengan bookmark aktif otomatis memakai gaya Selected.")

# ------------------------------------------------------------------ 7
H("7. Panel filter")
S(["Slicer 1: DimPlatform[platform_name], gaya Dropdown, multi-select. Catatan: platform hanya menyaring batang sub-kategori dan tabel naik/turun. Kartu KPI dan grafik tren bersumber dari KPIMonth (total semua platform per bulan) sehingga tidak ikut platform. Beri keterangan 'semua platform' pada subjudul grafik.",
   "Slicer 2: DimSKU[sub_category], gaya Dropdown. Menyaring tabel naik/turun (dan sub-kategori bila relasinya ada).",
   "Jangan membuat slicer periode bila Anda ingin kartu selalu menampilkan bulan terakhir. Measure KPI memakai [Bulan Akhir] yang mengabaikan filter bulan.",
   "Letakkan ketiga elemen dalam satu panel putih dengan judul Filter."])

# ------------------------------------------------------------------ 8
H("8. Panel kiri: sub-kategori yang menopang")
S(["Visual Bar chart (horizontal). Y-axis: SubCat[sub_category]. X-axis: [Sub Net GMV].",
   "Visual level filter: DimMonth[is_latest_month] = TRUE (hanya bulan terakhir). Urutkan menurun menurut [Sub Net GMV].",
   "Format > Bars > Color > fx > Format style: Field value > Based on field: [Warna Aksen Tab]. Sekarang batang berganti warna mengikuti tab.",
   "Format > Bars > Space between categories sekitar 40 %; Corner radius bila ada. Gridlines Off, X-axis Off, Legend Off.",
   "Data labels On, Display units: Millions, 1 desimal; subjudul 'Rp juta'.",
   "Analytics (kaca pembesar) > X-axis constant line > Add line, Value > fx > Field value > [Sub Rata-rata] (Rp168 jt). Style: Dashed, warna #1E2528, ketebalan 2. Bila fx tidak tersedia, pakai Average line.",
   "Judul (Format > General > Title): Sub-kategori yang menopang. Subjudul: Net GMV bulan terakhir. Garis putus = rata-rata sub-kategori.",
   "Di bawah chart, tambahkan garis pemisah tipis dan Text box dengan nilai dinamis [Insight Sub]."])

# ------------------------------------------------------------------ 9
H("9. Dua kartu KPI di tengah atas")
P("Tiap kartu disusun dari empat lapis yang ditumpuk. Cara ini dipakai karena Card bawaan tidak dapat menampilkan teks berjenjang dan garis warna di tepi kiri sekaligus.")
H("9.1 Kartu 1 (nilai)", 2)
S(["Rectangle putih (252 x 150), sudut membulat 14, garis tepi #E4DED3.",
   "Rectangle tipis di tepi kiri (lebar 6, tinggi 150). Format shape > Style > Fill > Color > fx > Field value > [Warna Aksen Tab]. Garis tepi Off. Hasil: garis kiri berganti teal, oranye, ungu.",
   "Text box kecil di bagian atas: nilai dinamis [KPI Judul] (abu #5E676B, 12 pt). Hasil: 'Net GMV · Okt 2026'.",
   "Visual Card: field [KPI Nilai Teks]. Category label Off. Callout value 34 pt tebal; Color > fx > Field value > [Warna Aksen Tab]. Background Off, Border Off.",
   "Text box bawah (11 pt, abu): nilai dinamis [KPI Rata Teks], baris baru, teks 'Bulan terbaik: ', lalu [KPI Terbaik Teks]. Di Text box, tambah nilai dinamis lewat tombol Add value."])
H("9.2 Kartu 2 (variasi bulan lalu)", 2)
S(["Ulangi empat lapis, dengan Rectangle kiri yang sama (juga mengikuti [Warna Aksen Tab]).",
   "Text box judul: teks 'Variasi vs bulan lalu'.",
   "Visual Card: field [KPI Delta Teks] (sudah memuat ▲ atau ▼). Callout value 28 pt tebal; Color > fx > Field value > [Warna Delta]. Hasil: teal bila naik, oranye bila turun, tidak bergantung tab.",
   "Text box bawah: [KPI Delta Pct Teks], baris baru, [KPI Extra]."])
P("Bila Anda ingin Card tanpa lapisan Rectangle, Anda bisa memakai satu Multi-row card, tetapi garis warna di tepi kiri tidak dapat dibuat dinamis dengan cara itu.")

# ------------------------------------------------------------------ 10
H("10. Grafik tren dengan tombol Garis / Kolom")
H("10.1 Grafik garis", 2)
S(["Line chart baru. X-axis: DimMonth[month_label]. Y-axis: tiga measure sekaligus, berurutan [Seri Net GMV], [Seri CM2], [Seri Iklan]. Legend dikosongkan.",
   "Format > Lines > Colors > Series: Seri Net GMV = #1F6F78, Seri CM2 = #B8541F, Seri Iklan = #5B4B9A. Width 3 px.",
   "Format > Markers On, ukuran 8. Untuk menandai titik terbaik, tambahkan Data labels pada seri dan matikan label lain, atau cukup aktifkan label di semua titik bila tampilan masih rapi.",
   "Y-axis: Start 0, End Auto (sumbu menyesuaikan karena hanya satu seri yang berisi). Titles Off. Gridlines abu muda #E4DED3. Legend Off.",
   "Judul: Net GMV, CM2, atau Belanja iklan bulanan. Subjudul: Rp juta per bulan, semua platform."])
P("Mengapa tiga seri? Dua seri selalu kosong, jadi hanya satu garis yang tergambar dan sumbu Y otomatis menyesuaikan ke tab itu. Warna garis berganti karena tiap seri punya warna tetap sendiri.")
H("10.2 Grafik kolom", 2)
S(["Salin grafik garis (Ctrl+C, Ctrl+V), lalu ubah jenisnya menjadi Stacked column chart (bukan Clustered; kolom bertumpuk menempati lebar penuh karena seri kosong bernilai nol).",
   "Warna seri sama seperti garis. Space between categories sekitar 30 %. Ukuran dan posisi sama persis dengan grafik garis.",
   "Gridlines dan sumbu mengikuti grafik garis."])
H("10.3 Bookmark Mode Garis / Mode Kolom", 2)
S(["Selection pane: beri nama grafik garis 'Grafik Garis' dan kolom 'Grafik Kolom'.",
   "Sembunyikan Grafik Kolom (ikon mata), lalu Bookmarks > Add: Mode Garis. Munculkan Kolom dan sembunyikan Garis, Add: Mode Kolom.",
   "Untuk kedua bookmark: Data Off, Display On, Current page On. (Berlawanan dengan bookmark tab: ini mengatur visibilitas, bukan data. Karena Data Off, pilihan tab tidak ikut berubah.)",
   "Buat dua tombol kecil 'Garis' dan 'Kolom' di pojok kanan atas grafik, masing-masing dengan Action > Bookmark > Mode Garis / Mode Kolom. Style Selected: latar #1E2528, teks putih."])
H("10.4 Kalimat insight di bawah grafik", 2)
P("Text box dengan nilai dinamis [Insight Analisis], 12 pt, di bawah garis pemisah tipis. Teks berubah menurut tab.")

# ------------------------------------------------------------------ 11
H("11. Panel kanan: siapa naik, siapa turun")
S(["Slicer TopN: tarik TopN[TopN], gaya Dropdown (bawaan 5). Letakkan di pojok kanan panel.",
   "Visual Table. Kolom berurutan: [Mov Nomor], Movers[product_name], Movers[sub_category], [Mov Teks Delta], [Mov Teks Persen], [Mov Delta Rp].",
   "Filter visual: DimMonth[is_latest_month] = TRUE dan [Mov Tampil] = 1 (tarik measure ke panel Filters, pilih 'is' 1).",
   "Urutkan: klik judul kolom [Mov Nomor] sampai urut naik (1 = kenaikan terbesar). Dengan begitu lima teratas (naik) dan lima terbawah (turun) berurutan.",
   "Kolom [Mov Delta Rp]: Conditional formatting > Data bars > Positive bar dan Negative bar > fx > Field value > [Mov Warna Batang]. Matikan Show value only agar angkanya disembunyikan, atau tampilkan.",
   "Kolom [Mov Teks Delta] dan [Mov Teks Persen]: Font color > fx > Field value > [Mov Warna Batang]. Hasil: hijau-teal untuk naik dan oranye untuk turun.",
   "Table style: Minimal, header tebal, tanpa garis vertikal, Row padding 8 px.",
   "Judul: Siapa naik, siapa turun. Subjudul: SKU, Net GMV bulan terakhir vs bulan lalu. Diurutkan menurut selisih rupiah; persentase hanya pendamping. SKU dengan basis di bawah Rp5 juta dikeluarkan.",
   "Text box insight di bawah tabel: nilai dinamis [Insight SKU Turun]."])
P("Hasil uji (Top/Bottom 5): Daily Sunscreen SPF50 40ml di puncak kenaikan (+Rp10,07 jt); Anti-Dandruff Shampoo 340ml di puncak penurunan (−Rp11,90 jt, −33 %).")

# ------------------------------------------------------------------ 12
H("12. Apa yang terjadi di layar ketika tab dipilih")
T(["Elemen", "Tab Net GMV", "Tab Margin (CM2)", "Tab Iklan"],
  [["Warna aksen", "teal #1F6F78", "oranye #B8541F", "ungu #5B4B9A"],
   ["Tombol aktif", "Net GMV terisi teal", "Margin (CM2) terisi oranye", "Iklan terisi ungu"],
   ["Judul kartu 1", "Net GMV · Okt 2026", "CM2 · Okt 2026", "Belanja iklan · Okt 2026"],
   ["Angka kartu 1", "Rp838,9 jt (teal)", "Rp280,8 jt (oranye)", "Rp53,8 jt (ungu)"],
   ["Rata-rata", "Rp728,0 jt", "Rp244,9 jt", "Rp45,5 jt · TACOS 6,42 %"],
   ["Bulan terbaik", "Sep (Rp848,9 jt)", "Okt (Rp280,8 jt)", "Sep (Rp55,2 jt), puncak"],
   ["Kartu 2 (selisih)", "▼ −Rp10,0 jt, −1,2 %", "▲ +Rp19,6 jt, +7,5 %", "▼ −Rp1,3 jt, −2,4 %"],
   ["Keterangan kartu 2", "Net GMV valid, tanpa batal dan retur", "Net sales − COGS − biaya platform − iklan", "TACOS Jan 6,15 %"],
   ["Grafik", "Garis/kolom teal, skala 0–~900", "Garis/kolom oranye, skala 0–~300", "Garis/kolom ungu, skala 0–~60"],
   ["Batang sub-kategori", "teal", "oranye", "ungu"],
   ["Garis kiri kartu", "teal", "oranye", "ungu"],
   ["Insight", "Net GMV tumbuh 40 % dari Jan (Rp599 jt) ke Okt (Rp839 jt). Sep menjadi puncak; Okt turun 1,2 %.", "CM2 naik 7,5 % di Okt sementara Net GMV turun 1,2 %: margin bergerak lebih baik daripada penjualan.", "Belanja iklan turun 2,4 % di Okt, TACOS 6,42 % di atas Jan (6,15 %): iklan makin mahal relatif terhadap penjualan."],
   ["Tabel naik/turun, TopN", "tidak berubah", "tidak berubah", "tidak berubah"],
   ["Warna selisih (▲ teal, ▼ oranye)", "mengikuti tanda selisih", "mengikuti tanda selisih", "mengikuti tanda selisih"]],
  [3.4, 4.3, 4.3, 4.0])
P("Bila Anda memilih Palet Ramah buta warna (slicer Palette), measure Warna Aksen Tab, Warna Naik, dan Warna Turun otomatis mengembalikan palet Okabe-Ito (biru, oranye-merah, merah muda). Elemen yang warnanya tetap (tombol tab dan seri grafik) tidak ikut berganti; untuk mode itu sediakan salinan dengan warna Okabe-Ito dan tukar lewat bookmark palet seperti di panduan sebelumnya.")

# ------------------------------------------------------------------ 13
H("13. Uji dan pemecahan masalah")
T(["Gejala", "Penyebab", "Solusi"],
  [["Klik tab tidak mengubah apa pun", "Bookmark tab belum Data On, atau slicer TabSel tidak punya pilihan tersimpan", "Pilih tab di slicer, Update bookmark, pastikan Data On dan Display Off"],
   ["Semua tab menampilkan Net GMV", "Tab Aktif memakai nilai bawaan (0) karena tidak ada pilihan tunggal", "Pastikan slicer TabSel Single select dan ada satu pilihan"],
   ["Warna kartu tidak berubah", "fx belum memakai Field value, atau measure Warna Aksen Tab lama", "Edit measure sesuai lampiran, lalu ulangi fx > Field value"],
   ["Grafik kosong di satu tab", "Measure Seri untuk tab itu belum dibuat atau salah relasi", "Cek tiga measure Seri dan relasi DimMonth ke KPIMonth"],
   ["Grafik kolom bergeser/ada ruang kosong", "Memakai Clustered, bukan Stacked", "Ubah ke Stacked column"],
   ["Kartu menampilkan 'Rp0,0 jt'", "Bulan Akhir kosong (KPIMonth tidak termuat)", "Cek tabel KPIMonth dan sumbernya v_kpi_month_all"],
   ["Tabel naik/turun menampilkan semua SKU", "Filter [Mov Tampil] belum dipasang", "Tarik measure ke Filters, pilih is 1"],
   ["Error 'PLACEHOLDER'", "Measure dipakai langsung di filter CALCULATE", "Simpan ke VAR dulu"]],
  [4.2, 5.8, 6.0])

# ------------------------------------------------------------------ Lampiran
H("Lampiran A. Measure halaman Analisis (tempel di _Measures)")
txt = open(os.path.join(ROOT, "powerbi", "measures_dashboard.dax"), encoding="utf-8").read()
blk = txt.split("// HALAMAN ANALISIS")[1]
blk = blk.split("\n", 1)[1]
C(blk)
H("Lampiran B. Warna Aksen Tab (ganti measure lama)")
m = re.search(r"Warna Aksen Tab =\n.*?\"#1F6F78\" \)\n", txt, re.S)
C(m.group(0) if m else "Lihat measures_dashboard.dax")

out = os.path.join(ROOT, "docs", "Panduan_Halaman_Analisis.docx")
doc.save(out)
print("saved", out)
