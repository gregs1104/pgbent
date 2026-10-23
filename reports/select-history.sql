-- pgbench SELECT history: host-local select script rows for CPU × major
-- progression. Face filter (sockets prepared) is applied in
-- reports/select-history.py from conn and/or batch labels.

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
  s.clients,
  s.scale,
  s.tps
FROM submission s
LEFT JOIN server srv ON srv.server = s.server
WHERE
  s.script = 'select'
  AND s.tps > 0
  AND (
    s.conn IS NULL
    OR btrim(s.conn) = ''
    OR s.conn IN ('host', 'sockets', 'sockets prepared', 'host prepared')
  )
ORDER BY s.server, s.run, s.batch_id, s.test;
