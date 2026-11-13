-- Apply buffercache detail/summary views to an existing results DB.
-- Also refresh test_stats (adds dirty_pct/unused_pct; LEFT JOIN summary).
-- Source of truth: init/resultdb.sql (mirrored in prequel.sql for node upgrades).
--
--   psql -f reports/buffercache-views.sql -d results
--   psql -f reports/write_internals.sql -d results
--   # or: psql -f prequel.sql -d results  (full upgrade path; then write_internals)

-- End-of-run pg_buffercache snapshot, relation grain (dirty and clean rows separate).
DROP VIEW IF EXISTS test_buffercache_detail CASCADE;
CREATE OR REPLACE VIEW test_buffercache_detail AS
SELECT
  tests.server,
  tests.set,
  testset.info,
  tests.test,
  tests.script,
  tests.clients,
  tests.scale,
  pg_size_pretty(tests.dbsize) AS dbsize,
  round(tests.tps) AS tps,
  CASE WHEN (test_bgwriter.checkpoints_timed + test_bgwriter.checkpoints_req) > 0
    THEN round(extract(epoch FROM (tests.end_time - tests.start_time))
         / (test_bgwriter.checkpoints_timed + test_bgwriter.checkpoints_req) / 60)
    ELSE 0 END AS min_per_chkp,
  bc.schemaname,
  bc.relname,
  pg_size_pretty(bc.bytes) AS bytes,
  bc.bytes AS bytes_raw,
  CASE WHEN coalesce(tests.dbsize, 0) > 0
    THEN round(100.0 * bc.bytes / tests.dbsize, 2)
    ELSE 0 END AS pct_db,
  CASE WHEN (test_stat_database.blks_hit + test_stat_database.blks_read) > 0
    THEN round(100.0 * test_stat_database.blks_hit
         / (test_stat_database.blks_hit + test_stat_database.blks_read), 2)
    ELSE 0 END AS hit_pct,
  bc.avg_usage,
  bc.max_usage,
  bc.isdirty,
  CASE WHEN bc.isdirty THEN 100.0 ELSE 0.0 END AS dirty_pct_row
FROM test_buffercache bc
JOIN tests ON bc.test = tests.test AND bc.server = tests.server
JOIN testset ON testset.server = tests.server AND testset.set = tests.set
LEFT JOIN test_stat_database ON
  tests.test = test_stat_database.test AND tests.server = test_stat_database.server
LEFT JOIN test_bgwriter ON
  tests.test = test_bgwriter.test AND tests.server = test_bgwriter.server
;

-- Test-level buffercache rollup: byte-weighted avg usagecount, % dirty of
-- occupied cache, and unused_pct of shared_buffers (NULL relname = empty slots).
DROP VIEW IF EXISTS test_buffercache_summary CASCADE;
CREATE OR REPLACE VIEW test_buffercache_summary AS
WITH usage_detail AS (
  SELECT server, test, schemaname, relname, bytes, avg_usage, isdirty
  FROM test_buffercache
  GROUP BY server, test, schemaname, relname, bytes, avg_usage, max_usage, isdirty
),
rolled AS (
  SELECT
    server,
    test,
    sum(CASE WHEN relname IS NOT NULL THEN bytes ELSE 0 END) AS cached,
    sum(CASE WHEN relname IS NULL THEN bytes ELSE 0 END) AS empty,
    bool_or(relname IS NULL) AS captured_empty,
    round(sum(CASE WHEN relname IS NOT NULL THEN avg_usage * bytes ELSE 0 END)
          / nullif(sum(CASE WHEN relname IS NOT NULL THEN bytes ELSE 0 END), 0), 2) AS avg_usage,
    round(100.0 * sum(CASE WHEN isdirty THEN bytes ELSE 0 END)
          / nullif(sum(CASE WHEN relname IS NOT NULL THEN bytes ELSE 0 END), 0), 2) AS dirty_pct
  FROM usage_detail
  GROUP BY server, test
),
shared AS (
  SELECT server, test,
    CASE
      WHEN unit = '8kB' THEN setting::numeric * 8192
      WHEN unit = 'kB' THEN setting::numeric * 1024
      ELSE setting::numeric
    END AS shared_bytes
  FROM test_settings
  WHERE name = 'shared_buffers'
)
SELECT
  r.server,
  r.test,
  r.cached,
  r.empty,
  r.avg_usage,
  r.dirty_pct,
  -- Prefer measured empty slots; legacy runs never stored them so fall back to
  -- shared_buffers - cached (includes catalog/toast/other DB, still flags oversize).
  round(100.0 * CASE
      WHEN r.captured_empty THEN r.empty
      ELSE greatest(coalesce(s.shared_bytes, 0) - r.cached, 0)
    END / nullif(coalesce(s.shared_bytes, r.cached + r.empty), 0), 2) AS unused_pct
FROM rolled r
LEFT JOIN shared s ON s.server = r.server AND s.test = r.test
;

DROP VIEW IF EXISTS test_stats CASCADE;
CREATE OR REPLACE VIEW test_stats AS
WITH test_wrap AS
  (SELECT *,
      CASE WHEN extract(epoch FROM (end_time - start_time))::bigint<1
          THEN 1::bigint ELSE extract(epoch FROM (end_time - start_time))::bigint END AS seconds
   FROM TESTS)
SELECT
  testset.set, testset.info, server.server,script,scale,clients,multi,rate_limit,test_wrap.test,
  round(dbsize / (1024 * 1024)) as dbsize_mb,
  round(tps) as tps, max_latency,
  round(blks_hit           * 8192 / seconds) AS hit_Bps,
  round(blks_read          * 8192 / seconds) AS read_Bps,
  round(buffers_checkpoint * 8192 / seconds) AS check_Bps,
  round(buffers_clean      * 8192 / seconds) AS clean_Bps,
  round(buffers_backend    * 8192 / seconds) AS backend_Bps,
  round(wal_written / seconds) AS wal_written_Bps,
  CASE WHEN (blks_hit + blks_read) > 0
      THEN round(100.0 * blks_hit / (blks_hit + blks_read),2)
      ELSE 0 END AS blk_cached_pct,
  CASE WHEN (buffers_checkpoint + buffers_clean + buffers_backend + buffers_alloc)  > 0
      THEN round(100.0 * buffers_alloc / (buffers_checkpoint + buffers_clean + buffers_backend + buffers_alloc),2)
      ELSE 0 END AS blk_read_pct,
  buf.cached, buf.empty, buf.avg_usage, buf.dirty_pct, buf.unused_pct,
  max_dirty,
  server_version,
  server_info,
  server_num_proc,
  test_wrap.server_mem_gb,
  server_disk_gb,
  server_details
FROM
  test_wrap
  FULL OUTER JOIN test_bgwriter ON
      test_wrap.test=test_bgwriter.test AND test_wrap.server=test_bgwriter.server
  FULL OUTER JOIN test_stat_database ON
      test_wrap.test=test_stat_database.test AND test_wrap.server=test_stat_database.server
  JOIN testset ON testset.set=test_wrap.set and testset.server=test_wrap.server
  LEFT JOIN test_buffercache_summary buf ON
      buf.test=test_wrap.test AND buf.server=test_wrap.server
  FULL OUTER JOIN server on test_wrap.server=server.server
ORDER BY server,set,info,script,scale,clients,test_wrap.test
;

DROP VIEW IF EXISTS test_metric_summary;
CREATE VIEW test_metric_summary AS
  WITH ts AS (
    SELECT test_stats.info,test_stats.server,test_stats.set,
      test_stats.script,test_stats.scale,test_stats.clients,
      test_stats.multi,test_stats.rate_limit,test_stats.test,test_stats.tps,
      hit_bps,read_bps,check_bps,clean_bps,backend_bps,wal_written_bps,dbsize_mb,
      server_num_proc,server_mem_gb,server_disk_gb
    FROM test_stats
    ORDER BY test_stats.server,test_stats.set,
      test_stats.script,test_stats.scale,test_stats.clients,test_stats.multi,test_stats.rate_limit,test_stats.test)
  SELECT ts.server,ts.set,ts.script,ts.scale,ts.clients,ts.test,ts.multi,ts.rate_limit,ts.tps,
    hit_bps,read_bps,check_bps,clean_bps,backend_bps,wal_written_bps,dbsize_mb,
    server_num_proc,server_mem_gb,server_disk_gb,
    round(100.0 * dbsize_mb / 1024 / server_mem_gb) AS ram_pct,
    metric,min(value) as min,round(avg(value)) as avg,max(value) as max
  FROM ts
  JOIN test_metrics_data ON ts.test=test_metrics_data.test AND ts.server=test_metrics_data.server
  GROUP BY test_metrics_data.metric,ts.server,ts.set,ts.info,ts.script,ts.scale,ts.clients,ts.multi,ts.rate_limit,ts.test,ts.tps,
    hit_bps,read_bps,check_bps,clean_bps,backend_bps,wal_written_bps,dbsize_mb,
    server_num_proc,server_mem_gb,server_disk_gb
  ORDER BY test_metrics_data.metric,ts.server,ts.set,ts.info,ts.script,ts.scale,ts.clients,ts.multi,ts.rate_limit,ts.test,ts.tps,
    hit_bps,read_bps,check_bps,clean_bps,backend_bps,wal_written_bps,dbsize_mb,
    server_num_proc,server_mem_gb,server_disk_gb;

