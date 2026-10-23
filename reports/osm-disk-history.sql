-- OSM disk history: host-local planet loads for peak read/write MB/s by
-- CPU × PostgreSQL major. CPU identity is reconstructed in
-- reports/osm-disk-history.py from batch names.

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
  s.max_write_mbps,
  s.max_read_mbps,
  GREATEST(
    coalesce(s.max_write_mbps, 0),
    coalesce(s.max_read_mbps, 0)
  ) AS max_rw_mbps
FROM submission s
LEFT JOIN server srv ON srv.server = s.server
WHERE
  s.script ILIKE '%osm%'
  AND (s.max_write_mbps IS NOT NULL OR s.max_read_mbps IS NOT NULL)
  AND (s.conn IS NULL OR s.conn = 'host')
ORDER BY s.server, s.run, s.batch_id, s.test;
