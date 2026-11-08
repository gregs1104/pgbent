-- OSM history: host-local planet loads for CPU × PostgreSQL major progression.
-- reports/osm-history.py uses submission.cpu; server.server_cpu is fallback.

SELECT
  s.server,
  s.test,
  s.batch_id,
  s.batch,
  s.run,
  s.cpu,
  srv.server_cpu AS server_cpu,
  s.server_ver,
  substring(s.server_ver FROM 'PostgreSQL ([0-9]+)')::int AS major,
  s.script,
  s.conn,
  s.nodes,
  s.score_kips,
  s.overall_kips,
  s.hours
FROM submission s
LEFT JOIN server srv ON srv.server = s.server
WHERE
  s.script ILIKE '%osm%'
  AND s.score_kips > 0
  AND (s.conn IS NULL OR s.conn = 'host')
ORDER BY s.server, s.run, s.batch_id, s.test;
