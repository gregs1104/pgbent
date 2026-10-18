-- OSM planet leaderboard: one best host-local run per machine × version ×
-- durability cell on the current Planet (nodes >= 10e9).
-- Config set is cpu/memory/disk, PostgreSQL major, fsync, wal_level, max_wal_gb.
-- Average and peak disk (MB/s) and package power (W) travel with the row
-- for the follow-on efficiency study.
-- Ranked by score_kips (node_count / (relation_seconds + polygon + line) / 1000).

WITH
best AS
  (SELECT
    server,test,
    cpu,mem_gb,disk,server_ver,client,script,clients,conn,hours,nodes,
    score_kips,overall_kips,index_kips,rel_ps,
    fsync,wal_level,max_wal_gb,db_gb,
    wal_mbps, avg_write_mbps, max_write_mbps, avg_read_mbps, max_read_mbps,
    avg_package_watts, max_package_watts, package_joules,
    ROW_NUMBER()
    OVER(
        PARTITION BY
          cpu, mem_gb, disk, conn,
          substring(server_ver FROM 'PostgreSQL ([0-9]+)'),
          fsync, wal_level, max_wal_gb
        ORDER BY
          score_kips DESC, overall_kips DESC, index_kips DESC,
          max_package_watts DESC NULLS LAST
    )  AS r
    FROM submission
    WHERE
      max_write_mbps IS NOT NULL AND
      category IS NULL AND
      script like 'osm2pgsql%' AND
      conn = 'host' AND
      nodes >= 10000000000
  )
SELECT
    server,
    test,
    cpu,
    mem_gb,
    substr(disk,1,12) AS disk,
    substring(server_ver FROM 'PostgreSQL ([0-9]+)') AS ver,
    fsync,
    wal_level,
    max_wal_gb,
    conn,
    hours,
    score_kips, overall_kips, index_kips, rel_ps,
    avg_write_mbps AS avg_write, max_write_mbps AS max_write,
    avg_read_mbps AS avg_read, max_read_mbps AS max_read,
    CASE
      WHEN (avg_package_watts IS NULL) AND (max_package_watts IS NOT NULL)
      THEN 'est' ELSE ''
    END AS pwr_est,
    round(avg_package_watts) AS avg_pkg,
    round(max_package_watts) AS max_pkg,
    round((package_joules / 1000.0)::numeric, 0) AS kj,
    round((score_kips / NULLIF(max_package_watts, 0))::numeric, 1) AS score_per_watt,
    round((overall_kips / NULLIF(max_package_watts, 0))::numeric, 1) AS overall_per_watt,
    round((index_kips / NULLIF(max_package_watts, 0))::numeric, 1) AS index_per_watt,
    wal_mbps AS wal
FROM best WHERE r=1
ORDER BY score_kips DESC,overall_kips DESC,index_kips DESC;
