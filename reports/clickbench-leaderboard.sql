-- Best ClickBench pair per host: highest query score (tps), plus load sibling
-- in the same set. Package watts use the same 1-second integral metrics as
-- SELECT/OSM (PkgWatt / Darwin Combined_Power_mW / Spark soc_pkg_power2_input).
-- Starter board filters to court; omit the server predicate for multi-host.

WITH query_ranked AS (
  SELECT
    t.server,
    t.set,
    t.test,
    t.tps AS score,
    (t.artifacts->>'hot_geomean')::double precision AS hot_geomean,
    (t.artifacts->>'hot_max')::double precision AS hot_max,
    t.max_latency,
    (t.artifacts->>'query_count')::int AS query_count,
    t.artifacts->'queries' AS queries,
    t.server_version,
    t.start_time,
    t.end_time,
    coalesce(nullif(btrim(t.server_cpu), ''), srv.server_cpu) AS cpu,
    srv.server_mem_gb AS mem_gb,
    srv.server_disk AS disk,
    ts.info AS set_info,
    row_number() OVER (
      PARTITION BY t.server
      ORDER BY t.tps DESC, t.test DESC
    ) AS rn
  FROM tests t
  JOIN server srv ON srv.server = t.server
  JOIN testset ts ON ts.server = t.server AND ts.set = t.set
  WHERE t.script LIKE 'clickbench%'
    AND t.script NOT LIKE 'clickbench-load%'
    AND t.tps > 0
    AND t.artifacts ? 'hot_geomean'
    AND t.end_time IS NOT NULL
    AND t.server = 'court'
),
best AS (
  SELECT * FROM query_ranked WHERE rn = 1
),
phases AS (
  SELECT
    b.server,
    b.cpu,
    b.mem_gb,
    b.disk,
    b.server_version AS ver,
    b.set,
    b.set_info,
    'query'::text AS phase,
    b.test,
    b.score AS tps,
    b.hot_geomean,
    coalesce(b.max_latency, b.hot_max) AS max_latency,
    b.query_count,
    b.queries,
    NULL::double precision AS load_time_s,
    NULL::bigint AS data_size,
    b.start_time,
    b.end_time
  FROM best b
  UNION ALL
  SELECT
    b.server,
    b.cpu,
    b.mem_gb,
    b.disk,
    b.server_version AS ver,
    b.set,
    b.set_info,
    'load'::text AS phase,
    l.test,
    l.tps,
    NULL::double precision AS hot_geomean,
    NULL::double precision AS max_latency,
    NULL::int AS query_count,
    NULL::jsonb AS queries,
    (l.artifacts->>'load_time')::double precision AS load_time_s,
    (l.artifacts->>'data_size')::bigint AS data_size,
    l.start_time,
    l.end_time
  FROM best b
  JOIN tests l
    ON l.server = b.server
   AND l.set = b.set
   AND l.script LIKE 'clickbench-load%'
   AND l.end_time IS NOT NULL
   AND l.tps > 0
)
SELECT
  p.server,
  p.cpu,
  p.mem_gb,
  p.disk,
  p.ver,
  p.set,
  p.set_info,
  p.phase,
  p.test,
  round(p.tps) AS tps,
  round(p.hot_geomean::numeric, 3) AS hot_geomean,
  round(p.max_latency::numeric, 3) AS max_latency,
  p.query_count,
  p.queries,
  round(p.load_time_s::numeric, 0) AS load_time_s,
  p.data_size,
  round((p.data_size::numeric / (1024 * 1024 * 1024)), 2) AS data_gb,
  round(extract(epoch FROM (p.end_time - p.start_time))) AS wall_s,
  round(pwr.avg_w::numeric, 1) AS avg_pkg,
  round(pwr.max_w::numeric, 1) AS max_pkg,
  round(pwr.joules) AS joules
FROM phases p
LEFT JOIN LATERAL (
  SELECT
    avg(x.watts) AS avg_w,
    max(x.watts) AS max_w,
    sum(x.watts * x.dt) AS joules
  FROM (
    SELECT
      CASE
        WHEN d.metric = 'Combined_Power_mW' THEN d.value * 0.001
        ELSE d.value
      END AS watts,
      LEAST(5.0, GREATEST(0.0, extract(epoch FROM (
        coalesce(
          lead(d.collected) OVER (ORDER BY d.collected),
          d.collected + interval '1 second'
        ) - d.collected)))) AS dt
    FROM test_metrics_data d
    WHERE d.server = p.server
      AND d.test = p.test
      AND d.metric IN ('PkgWatt', 'Combined_Power_mW', 'soc_pkg_power2_input')
      AND d.collected >= p.start_time
      AND d.collected <= p.end_time
  ) x
) pwr ON true
ORDER BY p.server, CASE p.phase WHEN 'load' THEN 0 ELSE 1 END;
