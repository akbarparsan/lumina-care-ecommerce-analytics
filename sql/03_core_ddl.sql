-- =====================================================================================
-- 03_core_ddl.sql : tabel pendukung operasional (quarantine, hasil DQ, log ETL, kasus banding).
-- Tabel fakta/dimensi dwh dibuat oleh skrip transformasi (CREATE TABLE AS) agar full-refresh idempoten.
-- =====================================================================================

-- Baris yang DITOLAK/DISINGKIRKAN saat cleaning, lengkap dengan alasan & muatan mentahnya (bisa diaudit)
CREATE TABLE IF NOT EXISTS ops.quarantine_row (
    quarantine_id  bigserial PRIMARY KEY,
    domain         text NOT NULL,                 -- ORDERS | ADS | MONITOR | SETTLEMENT | ERP
    platform_code  text,
    src_file       text,
    src_row_id     bigint,
    reason         text NOT NULL,
    business_key   text,
    payload        jsonb,
    quarantined_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_quarantine_domain_reason ON ops.quarantine_row (domain, reason);

-- Hasil pemeriksaan kualitas data (diisi ops.run_dq_checks() pada 11_data_quality.sql)
CREATE TABLE IF NOT EXISTS ops.dq_result (
    run_id       bigint NOT NULL,
    run_at       timestamptz NOT NULL DEFAULT now(),
    check_code   text NOT NULL,
    domain       text NOT NULL,
    severity     text NOT NULL CHECK (severity IN ('CRITICAL','WARNING','INFO')),
    status       text NOT NULL CHECK (status IN ('PASS','FAIL','INFO')),
    metric_value numeric,
    threshold    numeric,
    detail       text
);

-- Log eksekusi pipeline
CREATE TABLE IF NOT EXISTS etl.run_log (
    run_id      bigserial PRIMARY KEY,
    step        text NOT NULL,
    started_at  timestamptz NOT NULL DEFAULT clock_timestamp(),
    finished_at timestamptz,
    rows_out    bigint,
    status      text NOT NULL DEFAULT 'RUNNING',
    message     text
);

-- Pelacakan kasus banding/dispute ke platform (diisi dari ops.v_appeal_pack)
CREATE TABLE IF NOT EXISTS ops.appeal_case (
    case_id         bigserial PRIMARY KEY,
    platform_code   text NOT NULL,
    category        text NOT NULL,
    reference       text NOT NULL,                -- order_id / program period
    claim_idr       numeric NOT NULL,
    status          text NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','SUBMITTED','APPROVED','REJECTED','PARTIAL','CLOSED')),
    submitted_on    date,
    resolved_on     date,
    recovered_idr   numeric DEFAULT 0,
    owner           text,
    notes           text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (platform_code, category, reference)
);

-- Toleransi rekonsiliasi per program (rupiah absolut ATAU persen dari expected, mana yang lebih besar)
CREATE TABLE IF NOT EXISTS ops.recon_tolerance (
    program_code text PRIMARY KEY,
    abs_tol_idr  numeric NOT NULL,
    pct_tol      numeric NOT NULL,
    note         text
);
INSERT INTO ops.recon_tolerance VALUES
    ('QUARTERLY_REBATE', 10000, 0.005, 'Selisih pembulatan + baris kuarantina ID rusak'),
    ('BRAND_DAY_COFUND', 5000, 0.005, 'Selisih pembulatan'),
    ('ADS_CREDIT',       100000, 0.03, 'Baris iklan dengan spend=0 tidak bisa dipulihkan -> toleransi lebih longgar')
ON CONFLICT (program_code) DO NOTHING;
