# Kamus Data & Keunikan Tiap Platform

## Lapisan
| Schema | Isi |
|---|---|
| `stg` | Landing mentah, semua kolom TEXT, ditambah `_src_file`, `_loaded_at`, `_row_id` |
| `etl` | Fungsi parsing (`parse_ts`, `num_id`, `num_plain`, `num_comma`, `norm_sku`, …), registri file, tabel perantara |
| `dwh` | Model bersih: dimensi (`dim_*`) + fakta (`fact_order`, `fact_order_line`, `fact_ads_daily`, `fact_settlement`, `fact_erp_sales`, `fact_program_statement`, `fact_price_snapshot`) |
| `mart` | View/materialized view KPI siap dashboard |
| `ops` | Kepatuhan, order mencurigakan, rekonsiliasi, banding, DQ, karantina |
| `qa` | Kunci jawaban + hasil uji akurasi (opsional) |

## Keunikan ekspor per platform (dan cara pembersihannya)
| Platform | Keunikan | Penanganan |
|---|---|---|
| Shopee | Angka titik ribuan (`1.250.000`); dd/mm/yyyy; voucher level-order diulang di setiap baris | `num_id`; voucher order diambil sekali per order (bukan dijumlah per baris) |
| TikTok Shop/Tokopedia | Timestamp UTC (+7 jam); "SKU Subtotal After Discount" sudah net voucher; ID order rusak jadi notasi ilmiah (`5.71E+17`); Delivered = Completed | konversi zona waktu; rekonstruksi nilai sebelum voucher; ID rusak dikarantina |
| Lazada | Desimal titik; nama bulan Inggris; tidak ada total baris, qty harus dipulihkan | `num_plain`; qty dari total; yang tak terpulihkan dikarantina |
| Blibli | Delimiter `;`; MM/DD/YYYY 12 jam; nilai string "Rp"; voucher order hanya di baris pertama | delimiter loader; `parse_ts`; voucher dari baris pertama |

## Jenis data kotor yang disuntikkan (lihat `answer_key/gt_dirty_injection_summary.csv`)
Duplikat baris (satu file & lintas file), SKU varian/kosong (dipulihkan dari judul listing), qty 0/−1 (diperbaiki dari total), order uji (test), alias & salah ketik kota (pg_trgm ≥ 0,45), iklan: spend negatif (tanda salah → ABS), spend 0 dengan klik, klik > impresi, hari Lazada hilang 5–7 Agu, duplikat; monitor harga: harga null/nol, duplikat, snapshot hilang, format timestamp/harga campur.

## Tabel penting
| Tabel | Grain | Kunci |
|---|---|---|
| `dwh.fact_order` | 1 order | (platform_code, order_id) |
| `dwh.fact_order_line` | 1 baris SKU | (platform_code, order_id, line_no) |
| `dwh.fact_ads_daily` | tanggal × platform × jenis iklan × sub-kategori | — (flag `dq_flag`, `spend_reliable`) |
| `dwh.fact_settlement` | 1 baris settlement | `settlement_row_id` (`dup_rank` untuk duplikat) |
| `dwh.fact_price_snapshot` | snapshot 3-jam × listing × penjual | — |
| `mart.mv_sales_daily` | tanggal × platform × SKU | unique index |
| `ops.quarantine_row` | baris yang dibuang + alasan + payload JSON | audit trail |

## Keterbatasan yang sengaja didokumentasikan
1. ±18 order TikTok dengan ID notasi ilmiah dikarantina; settlement-nya tampil sebagai orphan (±15 baris). *Latihan lanjutan:* pulihkan ID lewat sidik jari (tanggal+nilai+kota) terhadap ERP.
2. Baris iklan `spend=0` dengan klik tidak bisa dipulihkan → toleransi rekonsiliasi kredit iklan 3 %.
3. Order salah-harga dengan qty ≥ 12 menyala di R1 dan R4 sekaligus (skor bertumpuk — wajar).
4. Over-quota pada order dengan timestamp persis sama bisa berbeda urutan; validasi di level voucher/order-kode.
