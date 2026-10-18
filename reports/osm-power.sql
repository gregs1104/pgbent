-- OSM load throughput vs package power on the current Planet (nodes >= 10e9).
-- One host-local winner per CPU (best score_kips), requiring package watts.
-- Ranked by score_kips; charts use max_pkg (peak) and avg_pkg (relation efficiency).

WITH
best AS
  (SELECT
    cpu,mem_gb,disk,server_ver,client,script,clients,conn,hours,nodes,
    score_kips,overall_kips,index_kips,polygon_kips,line_kips,point_kips,node_kps,rel_ps,
    fsync,wal_level,max_wal_gb,db_gb,
    wal_mbps, avg_write_mbps, max_write_mbps, avg_read_mbps, max_read_mbps,
    avg_package_watts, max_package_watts,
    ROW_NUMBER()
    OVER(
        PARTITION BY cpu,conn,client
        ORDER BY score_kips DESC,overall_kips DESC,index_kips DESC
    )  AS r
    FROM submission
    WHERE
      max_write_mbps IS NOT NULL AND
      category IS NULL AND
      script like 'osm2pgsql%' AND
      conn = 'host' AND
      client IS NULL AND
      nodes >= 10000000000
  )
SELECT
    cpu,
    mem_gb,
    substring(server_ver FROM 'PostgreSQL ([0-9]+)') AS ver,
    score_kips,overall_kips,index_kips,polygon_kips,line_kips,point_kips,node_kps,rel_ps,
    CASE
      WHEN (avg_package_watts IS NULL) AND (max_package_watts IS NOT NULL)
      THEN 'est' ELSE ''
    END AS pwr_est,
    round(max_package_watts) AS max_pkg,
    round(avg_package_watts) AS avg_pkg,
    fsync, wal_level,
    wal_mbps AS wal,
    avg_write_mbps AS avg_write, max_write_mbps AS max_write,
    avg_read_mbps AS avg_read, max_read_mbps AS max_read,
    CASE
      WHEN cpu LIKE 'NVIDIA%' THEN '#76B900'
      WHEN SUBSTRING(cpu FROM 1 FOR 1) = 'A' THEN '#000000'
      WHEN SUBSTRING(cpu FROM 1 FOR 1) = 'i' THEN '#0071C5'
      WHEN SUBSTRING(cpu FROM 1 FOR 1) = 'R' THEN '#ED1C24'
    END AS cpu_c
FROM best WHERE r = 1
  AND max_package_watts IS NOT NULL
ORDER BY score_kips DESC, overall_kips DESC, index_kips DESC;
