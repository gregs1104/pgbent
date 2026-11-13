-- Rising set 65: pgbench SELECT scale ladder vs buffercache usagecount.
-- Used by reports/shared-buffers-usage.py → docs/images/shared-buffers-usage.png
--
--   COPY ( … ) TO STDOUT WITH CSV HEADER

SELECT
  t.scale,
  round(avg(t.dbsize) / (1024^3)::numeric, 1) AS db_gb,
  round(avg(b.avg_usage)::numeric, 2) AS avg_usage,
  round(avg(pkey.avg_usage)::numeric, 2) AS pkey_usage,
  round(avg(t.tps)) AS tps
FROM tests t
JOIN test_buffercache_summary b
  ON b.server = t.server AND b.test = t.test
LEFT JOIN LATERAL (
  SELECT
    sum(bc.avg_usage * bc.bytes) / nullif(sum(bc.bytes), 0) AS avg_usage
  FROM test_buffercache bc
  WHERE bc.server = t.server
    AND bc.test = t.test
    AND bc.relname = 'pgbench_accounts_pkey'
) pkey ON true
WHERE t.server = 'rising'
  AND t.set = 65
  AND t.script = 'select'
  AND t.clients = 128
GROUP BY t.scale
ORDER BY t.scale;
