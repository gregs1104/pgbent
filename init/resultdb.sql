BEGIN;

DROP TABLE IF EXISTS testset CASCADE;
CREATE TABLE testset(
  server text NOT NULL,
  set serial NOT NULL,
  info text,
  category text
  );

DROP TABLE IF EXISTS tests CASCADE;
CREATE TABLE tests(
  server text NOT NULL,
  test serial,
  set int NOT NULL,
  scale int,
  dbsize int8,
  start_time timestamp default now(),
  end_time timestamp default null,
  tps decimal default 0,
  script text,
  clients int,
  workers int,
  trans int,
  avg_latency float,
  max_latency float,
  percentile_90_latency float,
  wal_written numeric,
  cleanup interval default null,
  rate_limit numeric default null,
  start_latency timestamp default null,
  end_latency timestamp default null,
  trans_latency int default null,
  server_version text default version(),
  client_limit numeric default null,
  multi numeric default 0,
  artifacts jsonb,
  server_mem_gb int,
  server_cpu text,
  server_os_release text,
  conn_method text,
  uname text,
  server_disk text,
  client_info text,
  category text
  );

DROP TABLE IF EXISTS timing;
-- Staging table, for loading in data from CSV
CREATE TABLE timing(
  ts timestamp,
  filenum int,
  latency double precision,
  test int NOT NULL,
  server text,
  schedule_lag double precision
  );

CREATE INDEX idx_timing_test on timing(test,ts);
CREATE INDEX idx_test_latency ON timing (test,latency);

DROP TABLE IF EXISTS test_bgwriter;
CREATE TABLE test_bgwriter(
  test int NOT NULL,
  checkpoints_timed bigint,
  checkpoints_req bigint,
  buffers_checkpoint bigint,
  buffers_clean bigint,
  maxwritten_clean bigint,
  buffers_backend bigint,
  buffers_alloc bigint,
  buffers_backend_fsync bigint,
  max_dirty bigint,
  server text NOT NULL
);

DROP TABLE IF EXISTS test_stat_database;
CREATE TABLE test_stat_database(
  test int NOT NULL,
  collected timestamp,
  last_reset timestamp,
  numbackends int,
  xact_commit bigint, xact_rollback bigint,
  blks_read bigint, blks_hit bigint,
  tup_returned bigint, tup_fetched bigint, tup_inserted bigint,
  tup_updated bigint, tup_deleted bigint,
  conflicts bigint,
  temp_files bigint, temp_bytes bigint,
  deadlocks bigint,
  blk_read_time double precision, blk_write_time double precision,
  server text NOT NULL
  );

DROP TABLE IF EXISTS test_statio;
CREATE TABLE test_statio(
  test int NOT NULL,
  collected timestamp,
  nspname name,
  tablename name,
  indexname name,
  size bigint,
  rel_blks_read bigint,
  rel_blks_hit bigint,
  server text NOT NULL
);

DROP TABLE IF EXISTS buckets;
CREATE TABLE buckets (
    bucket_left numeric,
    bucket_right numeric,
    offset_left numeric,
    offset_right numeric,
    latency_left numeric,
    latency_right numeric
);

DROP TABLE IF EXISTS server;
CREATE TABLE server(
    server text NOT NULL PRIMARY KEY,
    server_info text,
    server_cpu text,
    server_mem text,
    server_disk text,
    server_num_proc int,
    server_mem_gb int,
    server_disk_gb int,
    server_details jsonb,
    server_os_release text
  );

DROP TABLE IF EXISTS tmp_metric_import;
CREATE TABLE tmp_metric_import (
    collected timestamp,
    value float,
    metric text NOT NULL
);

DROP TABLE IF EXISTS test_metrics_data;
CREATE TABLE test_metrics_data (
    collected TIMESTAMP,
    value float,
    metric text NOT NULL,
    test integer NOT NULL,
    server text NOT NULL
);

DROP TABLE IF EXISTS test_settings;
CREATE TABLE test_settings (
    server text,
    test integer,
    name text,
    setting text,
    unit text,
    source text,
    boot_val text,
    value text,
    numeric_value numeric,
    numeric_unit text
);

DROP TABLE IF EXISTS test_statements;
CREATE TABLE test_statements (
    server text,
    test integer,
    queryid bigint,
    query text,
    plans bigint,
    total_plan_time double precision,
    min_plan_time double precision,
    max_plan_time double precision,
    mean_plan_time double precision,
    stddev_plan_time double precision,
    calls bigint,
    total_exec_time double precision,
    min_exec_time double precision,
    max_exec_time double precision,
    mean_exec_time double precision,
    stddev_exec_time double precision,
    rows bigint,
    shared_blks_hit bigint,
    shared_blks_read bigint,
    shared_blks_dirtied bigint,
    shared_blks_written bigint,
    local_blks_hit bigint,
    local_blks_read bigint,
    local_blks_dirtied bigint,
    local_blks_written bigint,
    temp_blks_read bigint,
    temp_blks_written bigint,
    blk_read_time double precision,
    blk_write_time double precision,
    wal_records bigint,
    wal_fpi bigint,
    wal_bytes numeric
);

DROP TABLE IF EXISTS test_buffercache;
CREATE TABLE public.test_buffercache (
    server text,
    test integer,
    schemaname text,
    relname text,
    bytes bigint,
    avg_usage numeric,
    max_usage smallint,
    isdirty boolean
);

CREATE INDEX idx_test_metrics_test on test_metrics_data(server,test);

CREATE UNIQUE INDEX idx_server_set on testset(server,set);
ALTER TABLE testset ADD UNIQUE USING INDEX idx_server_set;

CREATE UNIQUE INDEX idx_server_test on tests(server,test);
ALTER TABLE tests ADD UNIQUE USING INDEX idx_server_test;

CREATE UNIQUE INDEX idx_server_test_2 on test_bgwriter(server,test);
ALTER TABLE test_bgwriter ADD UNIQUE USING INDEX idx_server_test_2;

CREATE UNIQUE INDEX idx_server_test_3 on test_stat_database(server,test);
ALTER TABLE test_stat_database ADD UNIQUE USING INDEX idx_server_test_3;

CREATE INDEX idx_server_test_4 ON test_settings (server,test);
CREATE INDEX idx_test_statio on test_statio(server,test);
CREATE INDEX idx_buffercache on test_buffercache(server,test);

ALTER TABLE test_bgwriter ADD CONSTRAINT testfk FOREIGN KEY (server,test) REFERENCES tests (server,test) MATCH SIMPLE;
ALTER TABLE test_stat_database ADD CONSTRAINT testfk FOREIGN KEY (server,test) REFERENCES tests (server,test) MATCH SIMPLE;
ALTER TABLE test_statio ADD CONSTRAINT testfk FOREIGN KEY (server,test) REFERENCES tests (server,test) MATCH SIMPLE;
ALTER TABLE timing ADD CONSTRAINT testfk FOREIGN KEY (server,test) REFERENCES tests (server,test) MATCH SIMPLE;

DROP VIEW IF EXISTS test_metrics;
CREATE VIEW test_metrics AS
  SELECT tests.test,tests.server,script,scale,clients,
    tps,dbsize,wal_written,collected,value,metric
  FROM test_metrics_data,tests
  WHERE tests.test=test_metrics_data.test AND
    tests.server=test_metrics_data.server
;

DROP VIEW IF EXISTS test_stats CASCADE;
CREATE OR REPLACE VIEW test_stats AS
WITH test_wrap AS
  (SELECT *,
      CASE WHEN extract(epoch FROM (end_time - start_time))::bigint<1
          THEN 1::bigint ELSE extract(epoch FROM (end_time - start_time))::bigint END AS seconds
   FROM TESTS),
usage AS
  (SELECT
    server,test,sum(bytes) AS cached,round(sum(weighted) / sum(bytes),2) AS avg_usage
    FROM
    (SELECT
      server,test,
      bytes,
      avg_usage,
      avg_usage * bytes AS weighted
     FROM test_buffercache
     GROUP BY server,test,relname,bytes,avg_usage,max_usage,isdirty  -- Eliminate accidental duplicates
    ) AS usage_detail
    GROUP BY server,test
  )
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
  cached,avg_usage,
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
  JOIN usage ON usage.test=test_wrap.test AND usage.server=test_wrap.server
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

DROP TABLE IF EXISTS metrics_info;
CREATE TABLE metrics_info (
  uname text,
  metric text,
  category text,
  multi numeric,
  metric_label text,
  units text,
  style text,
  visibility int,
  prefix text,
  scale text
);

DROP VIEW IF EXISTS test_metrics_decode;
CREATE OR REPLACE VIEW test_metrics_decode AS
SELECT
  d.server,
  d.test,
  d.metric,
  CASE WHEN mi.prefix='disk' THEN split_part(d.metric,'_',1) ELSE '' END AS disk,
  CASE WHEN mi.metric_label IS null THEN d.metric ELSE mi.metric_label END AS label,
  d.collected,
  CASE WHEN mi.multi IS null THEN d.value ELSE d.value * mi.multi END AS value,
  CASE WHEN mi.multi IS null THEN pg_size_pretty(d.value::int8) ELSE
    pg_size_pretty((d.value * mi.multi)::int8) END AS value_p,
  mi.units,
  mi.category AS cat,
  mi.visibility AS vis
FROM
  tests t,test_metrics_data d
  LEFT OUTER JOIN metrics_info mi ON 
    (d.metric=mi.metric OR (mi.prefix='disk' AND d.metric LIKE ('%' || mi.metric)))
WHERE
  t.server=d.server AND t.test=d.test AND
  (mi.uname=t.uname OR mi.uname IS null OR mi.uname='Database') AND
  mi.scale='bytes'
--ORDER BY t.server,t.test,d.metric,d.collected
;

--
-- Convert hex value to a decimal one.  It's possible to do this using
-- undocumented features of the bit type, such as:
--
--     "SELECT 'xff'::text::bit(8)::int;"
--
-- This function relies on that only to convert single hex digits, meaning
-- it handles abitrarily large numbers too.  The code is inspired by the hex
-- to decimal examples at http://postgres.cz and is not case sensitive.
--
-- Sample tests:
--
-- SELECT hex_to_dec('FF');
-- SELECT hex_to_dec('ffff');
-- SELECT hex_to_dec('FFff');
-- SELECT hex_to_dec('FFFFFFFFFFFFFFFF');
--
CREATE OR REPLACE FUNCTION hex_to_dec (text)
RETURNS numeric AS
$$
DECLARE 
    r numeric;
    i int;
    digit int;
BEGIN
    r := 0;
    FOR i in 1..length($1) LOOP 
        EXECUTE E'SELECT x\''||substring($1 from i for 1)|| E'\'::integer' INTO digit;
        r := r * 16 + digit;
        END LOOP;
    RETURN r;
END
;
$$ LANGUAGE plpgsql IMMUTABLE
;

--
-- Process the output from pg_current_xlog_location() or
-- pg_current_xlog_insert_location() and return a WAL Logical Serial Number
-- from that information.  That represents an always incrementing offset
-- within the WAL stream, proportional to how much data has been written
-- there.  The input will look like '2/13BDE690'.
--
-- Sample use:
--
-- SELECT wal_lsn(pg_current_xlog_location());
-- SELECT wal_lsn(pg_current_xlog_insert_location());
--
-- There's no error checking here.  If you input a hex string without a "/"
-- in it, the function will process it without complaint, returning a large
-- number as if that were the left hand side of a valid pair.
--
CREATE OR REPLACE FUNCTION wal_lsn (text)
RETURNS numeric AS $$
SELECT hex_to_dec(split_part($1,'/',1)) * 16 * 1024 * 1024 * 255
    + hex_to_dec(split_part($1,'/',2));
$$ language sql
;

COMMIT;
