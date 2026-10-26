-- Expanded siren PG19 rc1 faces: four SELECT conn_methods plus sockets
-- nothing (;) and constant (SELECT 1). Same box / scale / 90s cell as the
-- ranking board. Supports the latency-piece story — take the executor out
-- and rates nearly double. Mean TPS across repeats.

SELECT
  t.script,
  t.conn_method AS conn,
  t.clients,
  round(avg(t.tps)) AS tps,
  count(*) AS n
FROM tests t
JOIN testset s ON s.server = t.server AND s.set = t.set
WHERE t.server = 'siren'
  AND s.info = 'PG19 rc1'
  AND t.script IN ('select', 'nothing', 'constant')
  AND t.tps > 0
GROUP BY t.script, t.conn_method, t.clients
ORDER BY t.script, t.conn_method, t.clients;
