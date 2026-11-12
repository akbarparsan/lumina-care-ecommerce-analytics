-- =====================================================================================
-- 10_reconciliation_appeal.sql : rekonsiliasi platform vs data internal + paket banding (schema ops)
--   A. Audit settlement vs order  (komisi, subsidi voucher, duplikat, orphan, belum cair)
--   B. Rekonsiliasi ERP vs order  (nilai beda, hilang, hanya-batal)
--   C. Rekonsiliasi benefit program JBP (rebate, co-fund Brand Day, kredit iklan) expected vs dibayar
--   D. Paket banding (v_appeal_pack) + papan status kasus
-- Konvensi impact_idr: positif = uang yang seharusnya kita terima / belum diakui; negatif = kelebihan/tidak berdasar.
-- =====================================================================================
SET search_path = ops, public;

CREATE OR REPLACE VIEW ops.v_asof AS SELECT max(order_date) AS as_of FROM dwh.fact_order;

-- Parameter aturan (dapat diubah tanpa mengubah logika)
CREATE TABLE IF NOT EXISTS ops.recon_param (param text PRIMARY KEY, value numeric NOT NULL, note text);
INSERT INTO ops.recon_param VALUES
  ('unsettled_grace_days', 14, 'Order selesai tanpa settlement setelah N hari dianggap terlambat cair'),
  ('fee_tolerance_idr', 2, 'Toleransi pembulatan biaya per order'),
  ('erp_tolerance_idr', 1, 'Toleransi pembulatan nilai ERP per order'),
  ('program_due_days', 30, 'Program dianggap jatuh tempo N hari setelah akhir periode')
ON CONFLICT (param) DO NOTHING;

-- ---------------------------------------------------------------- A. Audit settlement
CREATE OR REPLACE VIEW ops.v_settlement_primary AS      -- 1 baris per order (baris pertama), tanpa duplikat
SELECT * FROM dwh.fact_settlement WHERE dup_rank = 1;

CREATE OR REPLACE VIEW ops.v_settlement_audit AS
WITH p AS (SELECT (SELECT value FROM ops.recon_param WHERE param = 'fee_tolerance_idr') AS tol_fee,
                  (SELECT value FROM ops.recon_param WHERE param = 'unsettled_grace_days') AS grace),
exp AS (
    SELECT e.platform_code, e.order_id, e.order_date, e.net_sales, e.platform_voucher_amt, e.seller_voucher_amt,
           e.commission_fee_exp, e.service_fee_exp, e.payment_fee_exp, e.commission_rate_pct
    FROM mart.v_order_econ e WHERE e.is_completed)
SELECT s.platform_code, s.order_id, 'COMMISSION_OVERCHARGE'::text AS discrepancy_type, (s.commission_fee - x.commission_fee_exp)::numeric AS impact_idr,
       format('komisi dipotong %s vs seharusnya %s (tarif kontrak %s%%)', s.commission_fee, x.commission_fee_exp, x.commission_rate_pct) AS detail, x.order_date AS ref_date
FROM ops.v_settlement_primary s JOIN exp x USING (platform_code, order_id), p
WHERE s.commission_fee - x.commission_fee_exp > p.tol_fee
UNION ALL
SELECT s.platform_code, s.order_id, 'VOUCHER_SUBSIDY_MISSING', (x.platform_voucher_amt - s.platform_voucher_credit)::numeric,
       format('voucher platform %s, kredit di settlement %s', x.platform_voucher_amt, s.platform_voucher_credit), x.order_date
FROM ops.v_settlement_primary s JOIN exp x USING (platform_code, order_id), p
WHERE x.platform_voucher_amt > 0 AND x.platform_voucher_amt - s.platform_voucher_credit > p.tol_fee
UNION ALL
SELECT s.platform_code, s.order_id, 'DUPLICATE_SETTLEMENT_ROW', -s.net_payout::numeric, format('baris settlement ganda (rank %s) src %s', s.dup_rank, s.src_file), s.settle_date
FROM dwh.fact_settlement s WHERE s.dup_rank > 1
UNION ALL
SELECT s.platform_code, s.order_id, 'ORPHAN_SETTLEMENT', -s.net_payout::numeric, 'settlement tanpa order padanan di data order bersih', s.settle_date
FROM ops.v_settlement_primary s LEFT JOIN dwh.fact_order o USING (platform_code, order_id) WHERE o.order_id IS NULL
UNION ALL
SELECT x.platform_code, x.order_id, 'UNSETTLED_AGING',
       (x.net_sales - x.commission_fee_exp - x.service_fee_exp - x.payment_fee_exp + x.platform_voucher_amt)::numeric,
       format('order selesai %s, belum ada settlement (umur %s hari)', x.order_date, (SELECT as_of FROM ops.v_asof) - x.order_date), x.order_date
FROM exp x LEFT JOIN ops.v_settlement_primary s USING (platform_code, order_id), p
WHERE s.order_id IS NULL AND (SELECT as_of FROM ops.v_asof) - x.order_date > p.grace;

-- Ringkasan identitas net payout (kontrol internal pada data platform itu sendiri)
CREATE OR REPLACE VIEW ops.v_settlement_identity_check AS
SELECT platform_code, count(*) AS rows, count(*) FILTER (WHERE NOT net_identity_ok) AS identity_breaks, sum(net_payout) AS net_payout
FROM dwh.fact_settlement GROUP BY 1;

-- ---------------------------------------------------------------- B. Rekonsiliasi ERP
CREATE OR REPLACE VIEW ops.v_erp_audit AS
WITH tol AS (SELECT value AS t FROM ops.recon_param WHERE param = 'erp_tolerance_idr'),
erp AS (SELECT DISTINCT ON (platform_code, order_id) * FROM dwh.fact_erp_sales ORDER BY platform_code, order_id, erp_doc_no)
SELECT o.platform_code, o.order_id, 'ERP_MISSING'::text AS discrepancy_type, o.net_sales::numeric AS impact_idr, 'order selesai tidak tercatat di ERP' AS detail, o.order_date AS ref_date
FROM mart.v_order_econ o LEFT JOIN erp USING (platform_code, order_id) WHERE o.is_completed AND erp.order_id IS NULL
UNION ALL
SELECT o.platform_code, o.order_id, 'ERP_AMOUNT_MISMATCH', (erp.net_amount - o.net_sales)::numeric,
       format('ERP net %s vs order net %s', erp.net_amount, o.net_sales), o.order_date
FROM mart.v_order_econ o JOIN erp USING (platform_code, order_id), tol WHERE o.is_completed AND abs(erp.net_amount - o.net_sales) > tol.t
UNION ALL
SELECT erp.platform_code, erp.order_id, 'ERP_ONLY_CANCELLED', erp.net_amount::numeric, format('ERP mencatat penjualan padahal status order %s', o.status), erp.ship_date
FROM erp JOIN dwh.fact_order o USING (platform_code, order_id) WHERE o.status = 'CANCELLED';

-- ---------------------------------------------------------------- C. Rekonsiliasi program JBP
CREATE OR REPLACE VIEW ops.v_program_expected AS
WITH j AS (SELECT * FROM dwh.dim_jbp),
due AS (SELECT (SELECT as_of FROM ops.v_asof) - (SELECT value FROM ops.recon_param WHERE param = 'program_due_days')::int AS cutoff),
rebate AS (
    SELECT a.platform_code, 'QUARTERLY_REBATE'::text AS program_code, format('2026-Q%s', a.quarter) AS period_label,
           make_date(2026, (a.quarter - 1) * 3 + 1, 1) AS period_start, (make_date(2026, a.quarter * 3, 1) + interval '1 month - 1 day')::date AS period_end,
           a.expected_rebate_idr::numeric AS expected_idr, format('completed GMV %s -> %s (rate %s%%)', a.completed_gmv, a.tier_achieved, a.rebate_rate_pct) AS basis
    FROM mart.v_jbp_attainment a WHERE NOT a.is_in_progress),
cofund AS (
    SELECT c.platform_code, 'BRAND_DAY_COFUND', c.campaign_id, c.start_date, c.end_date,
           least(j.cap_amount, round(j.tier1_rate_pct / 100 * coalesce(sum(o.seller_voucher_amt) FILTER (WHERE o.is_completed), 0))),
           format('biaya voucher penjual (order selesai) %s x %s%%, cap %s', coalesce(sum(o.seller_voucher_amt) FILTER (WHERE o.is_completed), 0), j.tier1_rate_pct, j.cap_amount)
    FROM dwh.dim_campaign c JOIN j ON j.platform_code = c.platform_code AND j.program_code = 'BRAND_DAY_COFUND'
    LEFT JOIN dwh.fact_order o ON o.platform_code = c.platform_code AND o.order_date BETWEEN c.start_date AND c.end_date
    WHERE c.campaign_type = 'BRAND_DAY' GROUP BY c.platform_code, c.campaign_id, c.start_date, c.end_date, j.cap_amount, j.tier1_rate_pct),
ads AS (
    SELECT q.platform_code, 'ADS_CREDIT', format('2026-Q%s', q.qtr), make_date(2026, (q.qtr - 1) * 3 + 1, 1), (make_date(2026, q.qtr * 3, 1) + interval '1 month - 1 day')::date,
           least(j.cap_amount, round(j.tier1_rate_pct / 100 * q.spend)), format('belanja iklan %s x %s%%, cap %s', q.spend, j.tier1_rate_pct, j.cap_amount)
    FROM (SELECT platform_code, extract(quarter FROM ad_date)::int AS qtr, sum(spend) AS spend FROM dwh.fact_ads_daily GROUP BY 1, 2) q
    JOIN j ON j.platform_code = q.platform_code AND j.program_code = 'ADS_CREDIT')
SELECT * FROM rebate UNION ALL SELECT * FROM cofund UNION ALL SELECT * FROM ads;

CREATE OR REPLACE VIEW ops.v_program_reconciliation AS
SELECT e.platform_code, e.program_code, e.period_label, e.period_start, e.period_end, e.expected_idr, coalesce(s.paid_amount, 0) AS paid_idr,
       (e.expected_idr - coalesce(s.paid_amount, 0)) AS shortfall_idr, e.basis,
       t.abs_tol_idr, t.pct_tol,
       CASE WHEN e.expected_idr = 0 AND s.statement_id IS NULL THEN 'NO_BENEFIT_EXPECTED'
            WHEN e.period_end + (SELECT value FROM ops.recon_param WHERE param = 'program_due_days')::int > (SELECT as_of FROM ops.v_asof) THEN 'NOT_YET_DUE'
            WHEN s.statement_id IS NULL THEN 'UNPAID'
            WHEN e.expected_idr - s.paid_amount > greatest(t.abs_tol_idr, t.pct_tol * e.expected_idr) THEN 'SHORT_PAID'
            WHEN s.paid_amount - e.expected_idr > greatest(t.abs_tol_idr, t.pct_tol * e.expected_idr) THEN 'OVER_PAID'
            ELSE 'MATCHED' END AS recon_status,
       round(coalesce(s.paid_amount, 0)::numeric / NULLIF(e.expected_idr, 0), 4) AS paid_ratio
FROM ops.v_program_expected e
JOIN ops.recon_tolerance t USING (program_code)
LEFT JOIN dwh.fact_program_statement s ON s.platform_code = e.platform_code AND s.program_code = e.program_code AND s.period_label = e.period_label;

-- ---------------------------------------------------------------- D. Paket banding
CREATE OR REPLACE VIEW ops.v_appeal_candidates AS
SELECT platform_code, discrepancy_type AS category, order_id AS reference, impact_idr AS claim_idr, detail, ref_date, 'SETTLEMENT' AS domain
FROM ops.v_settlement_audit WHERE discrepancy_type IN ('COMMISSION_OVERCHARGE', 'VOUCHER_SUBSIDY_MISSING', 'UNSETTLED_AGING') AND impact_idr > 0
UNION ALL
SELECT platform_code, 'PROGRAM_' || recon_status, program_code || ' ' || period_label, shortfall_idr, basis, period_end, 'PROGRAM'
FROM ops.v_program_reconciliation WHERE recon_status IN ('SHORT_PAID', 'UNPAID') AND shortfall_idr > 0;

-- Satu baris per platform x kategori : angka yang dibawa ke account manager
CREATE OR REPLACE VIEW ops.v_appeal_pack AS
SELECT c.platform_code, c.category, c.domain, count(*) AS cases, sum(c.claim_idr) AS claim_idr, min(c.ref_date) AS oldest_ref, max(c.ref_date) AS newest_ref,
       coalesce(sum(a.claim_idr) FILTER (WHERE a.status IN ('SUBMITTED', 'OPEN')), 0) AS already_tracked_idr,
       count(a.case_id) AS tracked_cases
FROM ops.v_appeal_candidates c LEFT JOIN ops.appeal_case a ON a.platform_code = c.platform_code AND a.category = c.category AND a.reference = c.reference
GROUP BY 1, 2, 3;

-- Papan status kasus banding (diisi lewat ops.sp_open_appeals)
CREATE OR REPLACE VIEW ops.v_appeal_board AS
SELECT platform_code, category, status, count(*) AS cases, sum(claim_idr) AS claim_idr, sum(recovered_idr) AS recovered_idr,
       round(sum(recovered_idr) / NULLIF(sum(claim_idr), 0), 4) AS recovery_rate
FROM ops.appeal_case GROUP BY 1, 2, 3;

CREATE OR REPLACE PROCEDURE ops.sp_open_appeals(p_min_claim numeric DEFAULT 5000)
LANGUAGE sql AS $$
    INSERT INTO ops.appeal_case (platform_code, category, reference, claim_idr, notes)
    SELECT platform_code, category, reference, claim_idr, detail FROM ops.v_appeal_candidates WHERE claim_idr >= p_min_claim
    ON CONFLICT (platform_code, category, reference) DO UPDATE SET claim_idr = EXCLUDED.claim_idr, notes = EXCLUDED.notes
        WHERE ops.appeal_case.status = 'OPEN';
$$;

SELECT discrepancy_type, count(*) AS n, sum(impact_idr) AS impact FROM (SELECT * FROM ops.v_settlement_audit UNION ALL SELECT * FROM ops.v_erp_audit) x GROUP BY 1 ORDER BY 1;
SELECT platform_code, program_code, period_label, expected_idr, paid_idr, shortfall_idr, recon_status FROM ops.v_program_reconciliation WHERE recon_status NOT IN ('MATCHED') ORDER BY 1, 2, 3;
