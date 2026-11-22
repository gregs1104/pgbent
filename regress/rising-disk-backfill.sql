-- Backfill rising tests.server_disk from set names + chronological carry-forward.
-- Re-apply after any rising archive re-import (with rising-cpu-backfill.sql).
--
-- Canonical labels (Greg 2026-11-22):
--   Intel 750p              — every "Intel" / "Intel 750" set
--   Inland Performance 2TB  — Inland / Inland Perf / Inland 4.0 (dmirow EGFM11.0)
--   Sabrent Rocket 4 Plus 2TB — Rocket / Rocket Plus / Rocket 4 Plus / Rocket 2TB
--   IronWolf 510x4          — 4×512GB = 2TB on PCIe passthrough RAID
--
-- Unnamed sets inherit the last named disk. Set 86 "OSM Two Server 7700X" was
-- remote Postgres on the 7700X; leave server_disk blank there (unknown guest
-- disk) and do not let that row poison later carry.

BEGIN;

WITH sets AS (
  SELECT
    set,
    info,
    CASE
      WHEN info ~* 'IronWolf' OR info ~* '510x4' THEN 'IronWolf 510x4'
      WHEN info ~* 'Rocket' THEN 'Sabrent Rocket 4 Plus 2TB'
      WHEN info ~* 'Inland' THEN 'Inland Performance 2TB'
      WHEN info ~* 'Intel' THEN 'Intel 750p'
    END AS parsed,
    (info ~* 'Two[[:space:]]+Server' AND info ~* '7700X') AS remote_guest
  FROM testset
  WHERE server = 'rising'
),
carry_token AS (
  -- Remote-guest rows must not contribute a chassis disk token.
  SELECT
    set,
    parsed,
    remote_guest,
    CASE WHEN remote_guest THEN NULL ELSE parsed END AS token
  FROM sets
),
resolved AS (
  SELECT
    s.set,
    s.info,
    s.remote_guest,
    s.parsed,
    CASE
      WHEN s.remote_guest THEN NULL
      ELSE coalesce(
        s.parsed,
        (
          SELECT c.token
          FROM carry_token c
          WHERE c.set <= s.set AND c.token IS NOT NULL
          ORDER BY c.set DESC
          LIMIT 1
        )
      )
    END AS disk
  FROM sets s
)
UPDATE tests t
SET server_disk = r.disk
FROM resolved r
WHERE t.server = 'rising' AND t.set = r.set;

UPDATE server
SET server_disk = 'Inland Performance 2TB'
WHERE server = 'rising';

UPDATE submission s
SET disk = t.server_disk
FROM tests t
WHERE s.server = 'rising'
  AND t.server = s.server
  AND t.test = s.test;

COMMIT;

-- Sanity
SELECT server_disk, count(*) AS tests
FROM tests
WHERE server = 'rising'
GROUP BY 1
ORDER BY 2 DESC;

SELECT set, info, server_disk, count(*) AS tests
FROM tests t
JOIN testset s USING (server, set)
WHERE t.server = 'rising'
  AND (
    s.info ~* 'Intel|Inland|Rocket|IronWolf|Two[[:space:]]+Server'
    OR t.server_disk IS NULL
  )
GROUP BY 1, 2, 3
ORDER BY 1;

SELECT disk, count(*) AS rows
FROM submission
WHERE server = 'rising'
GROUP BY 1
ORDER BY 2 DESC;
