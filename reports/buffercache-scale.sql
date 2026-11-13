-- Buffercache scale-sweep readout (avg_usage vs scale).
-- Intended for sets run via wl/buffercache-scale.
--
--   psql -d results -v server=twilight -v set=124 -f reports/buffercache-scale.sql

\if :{?server}
\else
\set server `hostname`
\endif

SELECT
  t.set,
  t.scale,
  pg_size_pretty(avg(t.dbsize)::bigint) AS dbsize,
  t.clients,
  round(avg(t.tps)) AS tps,
  round(avg(b.avg_usage)::numeric, 2) AS avg_usage,
  round(avg(b.dirty_pct)::numeric, 2) AS dirty_pct,
  round(avg(b.unused_pct)::numeric, 1) AS unused_pct,
  pg_size_pretty(avg(b.cached)::bigint) AS cached,
  round(avg(pkey.avg_usage)::numeric, 2) AS pkey_usage,
  pg_size_pretty(avg(pkey.bytes)::bigint) AS pkey_cached
FROM tests t
LEFT JOIN test_buffercache_summary b
  ON b.server = t.server AND b.test = t.test
LEFT JOIN LATERAL (
  SELECT
    sum(bc.bytes) AS bytes,
    sum(bc.avg_usage * bc.bytes) / nullif(sum(bc.bytes), 0) AS avg_usage
  FROM test_buffercache bc
  WHERE bc.server = t.server AND bc.test = t.test
    AND bc.relname = 'pgbench_accounts_pkey'
) pkey ON true
WHERE t.server = :'server'
  AND t.script = 'select'
\if :{?set}
  AND t.set = :set
\endif
GROUP BY t.set, t.scale, t.clients
ORDER BY t.set, t.scale, t.clients;
