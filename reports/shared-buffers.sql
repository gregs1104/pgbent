-- shared_buffers OSM sweep: twilight set 98 (PG16.3, i5-13600K @ ~128GB).
-- Parameter conclusions still apply on later majors; this set is the last
-- multi-value study before the lab standardized on 48GB.
SELECT
  t.test,
  round(sb.numeric_value / 1024 / 1024 / 1024, 0)::int AS shared_gb,
  fsync.setting AS fsync,
  wal.setting AS wal_level,
  round(
    EXTRACT(EPOCH FROM (t.end_time - t.start_time)) / 3600.0,
    2
  ) AS hours,
  round(
    (t.artifacts->>'node_count')::numeric
      / NULLIF((t.artifacts->>'overall')::numeric, 0)
      / 1000,
    0
  ) AS overall_kips,
  CASE
    WHEN fsync.setting = 'on' AND wal.setting = 'replica' THEN 'durable'
    WHEN fsync.setting = 'off' AND wal.setting = 'minimal' THEN 'fast'
    ELSE 'other'
  END AS face
FROM tests t
JOIN test_settings sb
  ON sb.server = t.server AND sb.test = t.test AND sb.name = 'shared_buffers'
JOIN test_settings fsync
  ON fsync.server = t.server AND fsync.test = t.test AND fsync.name = 'fsync'
JOIN test_settings wal
  ON wal.server = t.server AND wal.test = t.test AND wal.name = 'wal_level'
WHERE t.server = 'twilight'
  AND t.set = 98
  AND t.script LIKE 'osm2pgsql%'
ORDER BY shared_gb, face, overall_kips DESC;
