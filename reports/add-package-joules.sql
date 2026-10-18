-- Add total package energy to an existing submission table and backfill
-- from 1-second collectors. New databases pick this up from write_internals.
ALTER TABLE submission ADD COLUMN IF NOT EXISTS package_joules double precision;

UPDATE submission s
SET package_joules = src.package_joules
FROM (
  SELECT server, test, round(sum(watts * dt)::numeric) AS package_joules
  FROM (
    SELECT
      d.server,
      d.test,
      CASE WHEN d.metric = 'Combined_Power_mW' THEN d.value * 0.001 ELSE d.value END AS watts,
      LEAST(5.0, GREATEST(0.0, extract(epoch FROM (
        coalesce(
          lead(d.collected) OVER (PARTITION BY d.server, d.test ORDER BY d.collected),
          d.collected + interval '1 second'
        ) - d.collected)))) AS dt
    FROM test_metrics_data d
    JOIN tests t ON t.server = d.server AND t.test = d.test
    JOIN submission s2 ON s2.server = d.server AND s2.test = d.test
    WHERE
      d.metric IN ('PkgWatt', 'Combined_Power_mW', 'soc_pkg_power2_input') AND
      d.collected >= t.start_time AND
      d.collected <= t.end_time
  ) x
  GROUP BY server, test
) src
WHERE s.server = src.server AND s.test = src.test;
