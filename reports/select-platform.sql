-- Platform SELECT energy comparison: one row per reference system.
-- Sockets prepared, scale-100 / 90s pin cells. Best TPS run at 1 and 32
-- clients, with that run's package_joules (1-second power integral).
-- Abbey (Apple M4 Max Studio) joins when a PG18/19 SELECT pin lands.

WITH runs AS (
  SELECT
    t.server,
    coalesce(nullif(btrim(t.server_cpu), ''), srv.server_cpu) AS cpu,
    t.test,
    t.clients,
    t.tps,
    t.trans,
    (
      SELECT round(sum(x.watts * x.dt)::numeric)
      FROM (
        SELECT
          CASE
            WHEN d.metric = 'Combined_Power_mW' THEN d.value * 0.001
            ELSE d.value
          END AS watts,
          LEAST(5.0, GREATEST(0.0, extract(epoch FROM (
            coalesce(
              lead(d.collected) OVER (ORDER BY d.collected),
              d.collected + interval '1 second'
            ) - d.collected)))) AS dt
        FROM test_metrics_data d
        WHERE d.server = t.server
          AND d.test = t.test
          AND d.metric IN ('PkgWatt', 'Combined_Power_mW', 'soc_pkg_power2_input')
          AND d.collected >= t.start_time
          AND d.collected <= t.end_time
      ) x
    ) AS joules
  FROM tests t
  JOIN testset s ON s.server = t.server AND s.set = t.set
  JOIN server srv ON srv.server = t.server
  WHERE t.server IN ('siren', 'twilight', 'abbey', 'court')
    AND t.script = 'select'
    AND t.conn_method = 'sockets prepared'
    AND t.clients IN (1, 32)
    AND t.tps > 0
    AND (
      s.info = 'PG19 rc1'
      OR s.info = 'PG19 rc1 SELECT four faces'
      OR (t.server = 'abbey' AND s.info ~* 'PG1[89]')
    )
),
ranked AS (
  SELECT
    server,
    cpu,
    clients,
    tps,
    joules,
    trans,
    row_number() OVER (PARTITION BY server, clients ORDER BY tps DESC) AS rn
  FROM runs
  WHERE joules IS NOT NULL AND joules > 0
),
best AS (
  SELECT
    server,
    cpu,
    clients,
    tps,
    joules,
    round(trans / NULLIF(joules, 0)) AS txn_per_j
  FROM ranked
  WHERE rn = 1
)
SELECT
  b1.cpu,
  b1.server,
  round(b1.tps) AS tps_1,
  b1.joules AS joules_1,
  b1.txn_per_j AS txn_j_1,
  round(b32.tps) AS tps_32,
  b32.joules AS joules_32,
  b32.txn_per_j AS txn_j_32,
  round((b32.joules / 1000.0)::numeric, 1) AS kj_32
FROM best b1
JOIN best b32 ON b32.server = b1.server AND b32.clients = 32
WHERE b1.clients = 1
ORDER BY b32.tps DESC;
