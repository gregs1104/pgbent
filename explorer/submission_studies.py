"""
SQL for published submission explorer studies.

Shared by submission-explore.py (Streamlit) and archive-results.py (static Markdown export).
"""

from __future__ import annotations

# Optional suffix: filter submission rows to one PostgreSQL major version.
# Applied only when pg_major is set (e.g. "18").
PG_VERSION_FILTER = """
  AND (
    substring(server_ver FROM 'PostgreSQL ([0-9]+)') = '{pg_major}'
    OR server_ver LIKE '%PostgreSQL {pg_major}.%'
  )
"""

STUDIES: dict[str, dict[str, str]] = {
    "osm-leaderboard": {
        "title": "OSM Leaderboard",
        "description": "Best OSM planet load per CPU/configuration (throughput and index build rate).",
        "sql": """
WITH
best AS
  (SELECT
    cpu,mem_gb,disk,server_ver,client,script,clients,conn,hours,nodes,nodes_kips,index_kips,csum,
        w_p_g,p_m_w,
        fsync,wal_level,max_wal_gb,db_gb,
        wal_mbps,  chkp_mbph, avg_write_mbps, max_write_mbps, avg_read_mbps, max_read_mbps,avg_package_watts, max_package_watts,
    ROW_NUMBER()
    OVER(
        PARTITION BY cpu,mem_gb,server_ver,script,conn,clients,nodes,csum,fsync,wal_level,max_wal_gb,w_p_g,p_m_w
        ORDER BY nodes_kips DESC,index_kips DESC
    )  AS r
    FROM submission
    WHERE
      max_write_mbps IS NOT NULL AND
      category IS NULL AND
      script like 'osm2pgsql%'
      {pg_filter}
  )
SELECT
    cpu,
    mem_gb,
    substr(disk,1,12) AS disk,
    substring(server_ver FROM 'PostgreSQL ([0-9]+)') AS ver,
    conn,
    hours AS hours,
    nodes_kips,index_kips,csum,
    w_p_g,p_m_w,
    fsync,wal_level,max_wal_gb,
    wal_mbps AS wal,
    round(chkp_mbph / 1024,2) AS chkp_gbph,
    avg_write_mbps AS avg_write, max_write_mbps AS max_write,
    avg_read_mbps AS avg_read, max_read_mbps AS max_read,
    round(avg_package_watts) AS avg_pkg,
    round(max_package_watts) AS max_pkg
FROM best WHERE r=1
ORDER BY nodes_kips DESC,index_kips DESC,script,db_gb;
""",
    },
    "osm-network": {
        "title": "OSM Network",
        "description": "OSM load speed: database server vs remote client (network path comparison).",
        "sql": """
WITH
best AS
  (SELECT
    cpu,mem_gb,disk,server_ver,client,script,clients,conn,hours,nodes,nodes_kips,index_kips,fsync,wal_level,max_wal_gb,db_gb,
      wal_mbps, avg_write_mbps, max_write_mbps, avg_read_mbps, max_read_mbps,avg_package_watts, max_package_watts,
    ROW_NUMBER()
    OVER(
        PARTITION BY cpu,conn,client
        ORDER BY nodes_kips DESC,index_kips DESC
    )  AS r
    FROM submission
    WHERE
      max_write_mbps IS NOT NULL AND
      (category IS NULL OR category='2023') AND
      script like 'osm2pgsql%' AND
      (client IS NOT NULL OR cpu='R9 9950X' OR cpu='i5-13600K' OR cpu='Apple M4 Max')
      {pg_filter}
  )
SELECT
    CASE WHEN client is NULL
      THEN cpu || '  ' || mem_gb || 'GB ' || disk
      ELSE client::text END AS client,
    cpu AS server,
    substring(server_ver FROM 'PostgreSQL ([0-9]+)') AS ver,
    conn,
    nodes_kips,index_kips,
    wal_mbps AS wal_mbps
FROM best WHERE r=1
ORDER BY server,client,cpu,nodes_kips DESC;
""",
    },
    "osm-power": {
        "title": "OSM Power",
        "description": "OSM load throughput vs package power draw (CPU speed vs watts).",
        "sql": """
WITH
best AS
  (SELECT
    cpu,mem_gb,disk,server_ver,client,script,clients,conn,hours,nodes,nodes_kips,index_kips,fsync,wal_level,max_wal_gb,db_gb,
      wal_mbps, avg_write_mbps, max_write_mbps, avg_read_mbps, max_read_mbps,avg_package_watts, max_package_watts,
    ROW_NUMBER()
    OVER(
        PARTITION BY cpu,conn,client
        ORDER BY nodes_kips DESC,index_kips DESC
    )  AS r
    FROM submission
    WHERE
      max_write_mbps IS NOT NULL AND
      (category IS NULL OR category='2023') AND
      script like 'osm2pgsql%' AND
      conn='host' AND client is NULL
      {pg_filter}
  )
SELECT
    cpu,
    mem_gb,
    substring(server_ver FROM 'PostgreSQL ([0-9]+)') AS ver,
    nodes_kips,index_kips,
    CASE WHEN (avg_package_watts IS NULL) AND (NOT max_package_watts IS NULL) THEN 'est' ELSE '' END AS pwr_est,
    round(max_package_watts) AS max_pkg,
    round(avg_package_watts) AS avg_pkg,
    fsync,
    wal_mbps AS wal, avg_write_mbps AS avg_write, max_write_mbps AS max_write,
    avg_read_mbps AS avg_read, max_read_mbps AS max_read,
    CASE
      WHEN SUBSTRING(cpu FROM 1 FOR 1)='A' then '#555555'
      WHEN SUBSTRING(cpu FROM 1 FOR 1)='i' then '#0071C5'
      WHEN SUBSTRING(cpu FROM 1 FOR 1)='R' then '#ED1C24'
    END AS cpu_c
FROM best WHERE r=1
  AND max_package_watts IS NOT null
ORDER BY nodes_kips DESC,index_kips DESC,script,db_gb;
""",
    },
    "osm-checkpoint": {
        "title": "OSM Checkpoint",
        "description": "Checkpoint tuning study: WAL, checkpoint timing, write rates, buffer behavior.",
        "sql": """
WITH
best AS
  (SELECT
    cpu,server_ver,mem_gb,disk,client,script,clients,conn,hours,nodes,nodes_kips,index_kips,fsync,wal_level,max_wal_gb,db_gb,
    timeout,chkp_mins,timed_pct,chkp_mbph,clean_mbph,backend_mbph,cleaned_pct,
    max_dirty,hit_pct,hit_mbps,read_mbps,
    wal_mbps, avg_write_mbps, max_write_mbps, avg_read_mbps, max_read_mbps,avg_package_watts, max_package_watts,
    ROW_NUMBER()
    OVER(
        PARTITION BY cpu,conn,client,timeout,max_wal_gb
        ORDER BY nodes_kips DESC,index_kips DESC
    )  AS r
    FROM submission
    WHERE
      max_write_mbps IS NOT NULL AND
      (category IS NULL) AND
      script like 'osm2pgsql%'
      {pg_filter}
  )
SELECT
    cpu,
    substring(server_ver FROM 'PostgreSQL ([0-9]+)') AS ver,
    nodes_kips,index_kips,fsync,
    wal_level,max_wal_gb,
    timeout,chkp_mins,timed_pct,
    chkp_mbph,
    clean_mbph,
    backend_mbph,
    cleaned_pct,
    max_dirty,hit_pct,hit_mbps,read_mbps AS miss_mbps,
    wal_mbps AS wal, avg_write_mbps AS avg_write, max_write_mbps AS max_write,
    avg_read_mbps AS avg_read, max_read_mbps AS max_read
FROM best WHERE r=1 AND
  (server_ver IS NOT NULL) AND
  (server_ver != '') AND
  (server_ver NOT LIKE 'macOS%') AND
  conn='host'
ORDER BY cpu,timeout DESC,max_wal_gb DESC;
""",
    },
    "osm-dirty-memory": {
        "title": "OSM Dirty Memory",
        "description": "Linux dirty memory limits during OSM load (siren server, batches 35–41).",
        "sql": """
SELECT
    batch,
    hours,
    nodes,
    nodes_kips,index_kips,
    max_dirty,
    wal_mbps, avg_write_mbps, max_write_mbps
FROM submission
WHERE
  server='siren' AND batch_id>=35 AND batch_id<=41 AND
  script like 'osm2pgsql%'
  {pg_filter}
ORDER BY batch_id;
""",
    },
    "pgbench-build": {
        "title": "pgbench Build Time",
        "description": "pgbench initialization (:-i) runs from submission history.",
        "sql": """
SELECT *
FROM submission
WHERE script LIKE ':-i%'
{pg_filter}
ORDER BY cpu, scale, clients;
""",
    },
    "pgbench-select": {
        "title": "pgbench SELECT",
        "description": "Standard pgbench SELECT grid submissions.",
        "sql": """
SELECT *
FROM submission
WHERE script = 'select'
{pg_filter}
ORDER BY cpu, scale, clients;
""",
    },
}


def study_sql(study_id: str, pg_major: str | None = None) -> str:
    if study_id not in STUDIES:
        raise KeyError(f"Unknown study {study_id!r}; choose from {list(STUDIES)}")
    pg_filter = PG_VERSION_FILTER.format(pg_major=pg_major) if pg_major else ""
    return STUDIES[study_id]["sql"].format(pg_filter=pg_filter)
