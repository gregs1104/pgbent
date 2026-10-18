-- Depends on write_internals view defined in reports/write_internals.sql
DROP TABLE IF EXISTS submission_author;
CREATE TABLE submission_author (
  submitter text,
  email text,
  affiliation text
);

INSERT INTO submission_author(submitter,email,affiliation) VALUES
  ('Greg Smith','gregs1104@gmail.com','Delayed Groups Lab');

DROP TABLE IF EXISTS submission;
CREATE TABLE submission AS
SELECT
  0 AS submit_id,
  submitter,affiliation,
  write_internals.*
FROM write_internals,submission_author
LIMIT 0;

CREATE SEQUENCE submission_seq;
ALTER TABLE submission ALTER COLUMN submit_id SET DEFAULT nextval('submission_seq');
ALTER TABLE submission ALTER COLUMN submit_id SET NOT NULL;
ALTER SEQUENCE submission_seq OWNED BY submission.submit_id;

\timing
INSERT INTO submission (
    submitter, affiliation,
    server, test,
    batch_id, batch, category, ref_info, run,
    cpu, mem_gb, disk, os_rel, server_ver,
    conn, client,
    script, clients, scale, nodes, db_gb,
    tps, avg_latency, percentile_90_latency, max_latency, rate_limit,
    hours, score_kips, overall_kips, index_kips, polygon_kips, line_kips, point_kips, node_kps, way_kps, rel_ps,
    shared_gb, maint_gb, max_wal_gb,
    w_p_g,p_m_w,
    csum, fsync, wal_level, timeout,
    timed_pct, chkp_mins, chkp_mbph, clean_mbph, backend_mbph, cleaned_pct, max_dirty,
    hit_pct, hit_mbps, read_mbps, wal_mbps,
    avg_write_mbps, max_write_mbps, avg_read_mbps, max_read_mbps,
    avg_package_watts, max_package_watts, package_joules)
SELECT
  submitter,affiliation,
  write_internals.*
FROM write_internals,submission_author;
