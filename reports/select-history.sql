-- pgbench SELECT history: host-local select script rows for CPU × major
-- progression. Face filter (sockets prepared) is applied in
-- reports/select-history.py from conn and/or batch labels.
-- Reads tests/testset directly so a fresh ./download is enough (no
-- submission rebuild required).

SELECT
  t.server,
  t.test,
  t.set AS batch_id,
  s.info AS batch,
  to_char(t.start_time, 'YYYY/MM/DD') AS run,
  t.server_cpu AS cpu,
  srv.server_cpu AS server_cpu,
  t.server_version AS server_ver,
  substring(t.server_version FROM 'PostgreSQL ([0-9]+)')::int AS major,
  t.script,
  t.conn_method AS conn,
  t.clients,
  t.scale,
  t.tps
FROM tests t
LEFT JOIN testset s ON s.server = t.server AND s.set = t.set
LEFT JOIN server srv ON srv.server = t.server
WHERE
  t.script = 'select'
  AND t.tps > 0
  AND (
    t.conn_method IS NULL
    OR btrim(t.conn_method) = ''
    OR t.conn_method IN ('host', 'sockets', 'sockets prepared', 'host prepared')
  )
ORDER BY t.server, t.start_time, t.set, t.test;
