-- Backfill rising tests.server_cpu from set names + chronological carry-forward.
-- Early unnamed sets are still the 3950X era; set 32+ names 5950X.
-- Set 86 "OSM Two Server 7700X": rising was the client (5950X); Postgres was
-- the 7700X box. client_info / server_cpu did not exist on the original
-- archive — fill them in the modern shape (client_info = rising, server_cpu
-- = remote 7700X). The 7700X token does not carry into later sets.
-- Also normalizes server.server_cpu and mirrors into submission.

BEGIN;

WITH sets AS (
  SELECT
    set,
    info,
    CASE
      WHEN info ~* '7700X' THEN 'R9 7700X'
      WHEN info ~* '5950X' THEN 'R9 5950X'
      WHEN info ~* '3950X' THEN 'R9 3950X'
    END AS parsed,
    (info ~* 'Two[[:space:]]+Server') AS two_server
  FROM testset
  WHERE server = 'rising'
),
carry_token AS (
  -- Guest/remote chip names must not poison later chassis carry.
  SELECT
    set,
    parsed,
    two_server,
    CASE WHEN info ~* '7700X' THEN NULL ELSE parsed END AS token
  FROM sets
),
resolved AS (
  SELECT
    s.set,
    s.info,
    s.two_server,
    s.parsed,
    coalesce(
      CASE WHEN s.info ~* '7700X' THEN NULL ELSE s.parsed END,
      (
        SELECT c.token
        FROM carry_token c
        WHERE c.set <= s.set AND c.token IS NOT NULL
        ORDER BY c.set DESC
        LIMIT 1
      ),
      'R9 3950X'
    ) AS chassis_cpu
  FROM sets s
)
UPDATE tests t
SET server_cpu = r.chassis_cpu
FROM resolved r
WHERE t.server = 'rising' AND t.set = r.set;

-- Remote Postgres on the 7700X; rising (5950X) was the osm2pgsql client.
UPDATE tests t
SET
  server_cpu = 'R9 7700X',
  client_info = 'R9 5950X  125GB'
FROM testset ts
WHERE t.server = 'rising'
  AND ts.server = t.server
  AND ts.set = t.set
  AND ts.info ~* '7700X'
  AND ts.info ~* 'Two[[:space:]]+Server';

UPDATE server
SET server_cpu = 'R9 5950X'
WHERE server = 'rising';

UPDATE submission s
SET
  cpu = t.server_cpu,
  client = t.client_info
FROM tests t
WHERE s.server = 'rising'
  AND t.server = s.server
  AND t.test = s.test;

COMMIT;

-- Sanity
SELECT server_cpu, count(*) AS tests,
       count(*) FILTER (WHERE coalesce(client_info, '') <> '') AS with_client
FROM tests
WHERE server = 'rising'
GROUP BY 1
ORDER BY 2 DESC;

SELECT cpu, client, count(*) AS rows
FROM submission
WHERE server = 'rising'
GROUP BY 1, 2
ORDER BY 3 DESC;
