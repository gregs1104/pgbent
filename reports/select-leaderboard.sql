-- Starter pgbench SELECT leaderboard: siren PG19 rc1, every conn_method
-- face on the same box (sockets vs localhost TCP, prepared vs simple).
-- Mean TPS and transactions/joule across repeats. Joules are the same
-- 1-second PkgWatt integral as OSM package_joules. Beta builds stay off
-- this board.

SELECT
  t.conn_method AS conn,
  t.clients,
  round(avg(t.tps)) AS tps,
  round(avg(p.avg_w)::numeric, 1) AS avg_pkg,
  round(avg(p.max_w)::numeric, 1) AS max_pkg,
  round(avg(p.joules)) AS joules,
  round(avg(t.trans / NULLIF(p.joules, 0))) AS txn_per_j,
  count(*) AS n
FROM tests t
JOIN testset s ON s.server = t.server AND s.set = t.set
LEFT JOIN LATERAL (
  SELECT
    avg(x.watts) AS avg_w,
    max(x.watts) AS max_w,
    sum(x.watts * x.dt) AS joules
  FROM (
    SELECT
      d.value AS watts,
      LEAST(5.0, GREATEST(0.0, extract(epoch FROM (
        coalesce(
          lead(d.collected) OVER (ORDER BY d.collected),
          d.collected + interval '1 second'
        ) - d.collected)))) AS dt
    FROM test_metrics_data d
    WHERE d.server = t.server
      AND d.test = t.test
      AND d.metric = 'PkgWatt'
      AND d.collected >= t.start_time
      AND d.collected <= t.end_time
  ) x
) p ON true
WHERE t.server = 'siren'
  AND s.info = 'PG19 rc1'
  AND t.script = 'select'
  AND t.tps > 0
GROUP BY t.conn_method, t.clients
ORDER BY t.conn_method, t.clients;
