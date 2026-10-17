WITH
best AS
  (SELECT
    server,test,cpu,disk,script,clients,hours,nodes,score_kips,overall_kips,index_kips,fsync,wal_level,max_wal_gb,db_gb,
      wal_mbps, avg_write_mbps, max_write_mbps, avg_read_mbps, max_read_mbps,avg_package_watts, max_package_watts,
    ROW_NUMBER()
    OVER(
        PARTITION BY server_ver,script,conn,clients,nodes,fsync,wal_level,max_wal_gb
        ORDER BY score_kips DESC,overall_kips DESC
    )  AS r
    FROM submission
    WHERE max_write_mbps IS NOT NULL
      AND script like 'osm2pgsql%'
  )
SELECT
    server,test,
    cpu,
    substr(disk,1,12) AS disk,
    --substring(server_ver,1,16) AS server_version,conn,script,
    clients,
    --tps,
    hours AS hours,
    round(nodes/1000000000,1) AS nodes_m,
    score_kips,overall_kips,index_kips,fsync,wal_level,max_wal_gb,
      wal_mbps AS wal, avg_write_mbps AS avg_write, max_write_mbps AS max_write, avg_read_mbps AS avg_read, max_read_mbps AS max_read, 
      round(avg_package_watts) AS avg_pkg, 
      round(max_package_watts) AS max_pkg
FROM best WHERE r=1
ORDER BY score_kips DESC,overall_kips DESC,script,db_gb;
