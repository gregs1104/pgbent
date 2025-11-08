WITH lastset AS (
  SELECT max(set) as lastset from tests
)
SELECT
  set,script,scale,
  pg_size_pretty(dbsize::int8) AS db_size,
  substring(server_version FROM 'PostgreSQL ([0-9]+)') AS ver,
  test,
  round(extract(epoch from (tests.end_time - tests.start_time))::numeric/60/60,2) AS hours,
  clients,multi,
  rate_limit AS limit,
  client_limit AS client_limit,
  round(tps) AS tps,
  1000*round(1000*avg_latency)/1000 AS avg_latency,
  1000*round(1000*percentile_90_latency)/1000 AS "90%<",
  1000*round(1000*max_latency)/1000 AS max_latency
FROM tests
WHERE set = (SELECT lastset FROM lastset)
ORDER BY set,script,scale,clients,rate_limit,multi,test; 
