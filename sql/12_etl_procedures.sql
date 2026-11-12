-- =====================================================================================
-- 12_etl_procedures.sql : orkestrasi refresh lapisan mart + DQ + log, siap dijadwalkan (pg_cron / Task Scheduler)
--   Urutan penuh (lihat run_all.sql / automation/run_pipeline.sh):
--     load_raw.py (stg) -> 04..06 (dwh) -> 07..11 (mart/ops) -> etl.sp_refresh_marts()
--   Refresh harian ringan cukup memanggil:  CALL etl.sp_refresh_marts();
-- =====================================================================================
CREATE OR REPLACE PROCEDURE etl.sp_log_step(p_step text, p_rows bigint, p_status text, p_message text DEFAULT NULL, p_started timestamptz DEFAULT clock_timestamp())
LANGUAGE sql AS $$
    INSERT INTO etl.run_log (step, started_at, finished_at, rows_out, status, message) VALUES (p_step, p_started, clock_timestamp(), p_rows, p_status, p_message);
$$;

CREATE OR REPLACE PROCEDURE etl.sp_refresh_marts()
LANGUAGE plpgsql AS $$
DECLARE t0 timestamptz; n bigint; rid bigint; crit int; nchk bigint;
BEGIN
    t0 := clock_timestamp();
    REFRESH MATERIALIZED VIEW mart.mv_sales_daily;
    SELECT count(*) INTO n FROM mart.mv_sales_daily;
    CALL etl.sp_log_step('refresh mart.mv_sales_daily', n, 'OK', NULL, t0);

    t0 := clock_timestamp();
    rid := ops.run_dq_checks();
    SELECT critical_failed INTO crit FROM ops.v_dq_scorecard WHERE run_id = rid;
    SELECT count(*) INTO nchk FROM ops.dq_result WHERE run_id = rid;
    CALL etl.sp_log_step('dq checks run ' || rid, nchk, CASE WHEN crit > 0 THEN 'CRITICAL_FAIL' ELSE 'OK' END,
                         format('critical failed = %s', crit), t0);
    IF crit > 0 THEN
        RAISE WARNING 'DQ gate: % pemeriksaan CRITICAL gagal - tahan publikasi dashboard', crit;
    END IF;
END $$;

-- Ringkasan eksekusi terakhir untuk halaman "Kesehatan Pipeline" di Power BI
CREATE OR REPLACE VIEW ops.v_pipeline_health AS
SELECT run_id, step, started_at, finished_at, round(extract(epoch FROM (finished_at - started_at))::numeric, 2) AS seconds, rows_out, status, message
FROM etl.run_log ORDER BY run_id DESC;

-- Fresh-ness per sumber (tanggal data terbaru) -> alarm bila ada platform yang tertinggal
CREATE OR REPLACE VIEW ops.v_source_freshness AS
SELECT 'ORDERS' AS source, platform_code, max(order_date)::date AS latest_data_date, (SELECT max(order_date) FROM dwh.fact_order) - max(order_date) AS lag_days FROM dwh.fact_order GROUP BY 2
UNION ALL SELECT 'ADS', platform_code, max(ad_date), (SELECT max(order_date) FROM dwh.fact_order) - max(ad_date) FROM dwh.fact_ads_daily GROUP BY 2
UNION ALL SELECT 'SETTLEMENT', platform_code, max(settle_date), (SELECT max(order_date) FROM dwh.fact_order) - max(settle_date) FROM dwh.fact_settlement GROUP BY 2
UNION ALL SELECT 'PRICE_MONITOR', platform_code, max(snapshot_date), (SELECT max(order_date) FROM dwh.fact_order) - max(snapshot_date) FROM dwh.fact_price_snapshot GROUP BY 2;

-- Opsional (butuh ekstensi pg_cron di server): jadwalkan refresh tiap jam
--   SELECT cron.schedule('refresh-marts', '5 * * * *', 'CALL etl.sp_refresh_marts()');

CALL etl.sp_refresh_marts();
SELECT step, rows_out, status FROM ops.v_pipeline_health LIMIT 3;
SELECT * FROM ops.v_source_freshness ORDER BY 1, 2;
