-- Starter pgbench SELECT leaderboard: siren PG19 rc1, every conn_method
-- face on the same box (sockets vs localhost TCP, prepared vs simple).
-- Mean TPS across repeats. Beta builds stay off this board.

SELECT
  t.conn_method AS conn,
  t.clients,
  round(avg(t.tps)) AS tps,
  round(avg(p.avg_w)::numeric) AS avg_pkg,
  round(avg(p.max_w)::numeric) AS max_pkg,
  count(*) AS n
FROM tests t
JOIN testset s ON s.server = t.server AND s.set = t.set
LEFT JOIN LATERAL (
  SELECT avg(d.value) AS avg_w, max(d.value) AS max_w
  FROM test_metrics_data d
  WHERE d.server = t.server
    AND d.test = t.test
    AND d.metric = 'PkgWatt'
) p ON true
WHERE t.server = 'siren'
  AND s.info = 'PG19 rc1'
  AND t.script = 'select'
  AND t.tps > 0
GROUP BY t.conn_method, t.clients
ORDER BY t.conn_method, t.clients;
