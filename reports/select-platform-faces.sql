-- Sockets prepared SELECT per CPU × clients at scale 100 (90s pin cells).
-- Best TPS among repeats. Pin sets match select-platform.sql / the SELECT
-- power page. Sockets prepared is the top face on every current pin cell.

WITH runs AS (
  SELECT
    coalesce(nullif(btrim(t.server_cpu), ''), srv.server_cpu) AS cpu,
    t.server,
    t.clients,
    t.tps
  FROM tests t
  JOIN testset s ON s.server = t.server AND s.set = t.set
  JOIN server srv ON srv.server = t.server
  WHERE t.script = 'select'
    AND t.scale = 100
    AND t.conn_method = 'sockets prepared'
    AND t.tps > 0
    -- Include nproc / 2× points in the 1–64 window (pgsysinfo core_sweep)
    -- so mixed-core boxes are not judged only at unlucky powers of two
    -- (court: 10, 20, 40). Skip 4× (80) — this chart stays visually 1–64.
    -- Max TPS across sets/repeats at each point (highest-only when piling on).
    AND t.clients IN (1, 2, 4, 8, 10, 16, 20, 32, 40, 64)
    AND (
      (t.server = 'siren' AND s.info IN ('PG19 rc1', '9600X SELECT'))
      OR (t.server = 'twilight' AND s.info = 'PG19 rc1')
      OR (t.server = 'court' AND (
            s.info = 'PG19 rc1 SELECT four faces'
            OR s.info LIKE 'SELECT four faces fill — clients %'
          ))
      OR (t.server = 'abbey' AND s.info = 'PG18 SELECT four faces')
    )
),
best AS (
  SELECT
    cpu,
    server,
    clients,
    tps,
    row_number() OVER (PARTITION BY cpu, clients ORDER BY tps DESC) AS rn
  FROM runs
)
SELECT
  cpu,
  server,
  clients,
  round(tps) AS tps,
  'sockets prepared'::text AS face
FROM best
WHERE rn = 1
ORDER BY cpu, clients;
