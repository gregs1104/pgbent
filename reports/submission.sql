-- Depends on write_internals view defined in reports/write_internals.sql
--
-- Build submission as author × write_internals without hard-coding the
-- internals column list.  An explicit INSERT column list drifted when
-- buffercache fields (avg_usage / dirty_pct / unused_pct) landed in
-- write_internals while a stale view was still installed on the assembly
-- DB — CREATE TABLE took the live view shape, then INSERT named columns
-- the empty table did not have.
DROP TABLE IF EXISTS submission_author;
CREATE TABLE submission_author (
  submitter text,
  email text,
  affiliation text
);

INSERT INTO submission_author(submitter,email,affiliation) VALUES
  ('Greg Smith','gregs1104@gmail.com','Delayed Groups Lab');

DROP TABLE IF EXISTS submission;
DROP SEQUENCE IF EXISTS submission_seq;
CREATE SEQUENCE submission_seq;

\timing
CREATE TABLE submission AS
SELECT
  nextval('submission_seq') AS submit_id,
  submitter,affiliation,
  write_internals.*
FROM write_internals,submission_author;

ALTER TABLE submission ALTER COLUMN submit_id SET DEFAULT nextval('submission_seq');
ALTER TABLE submission ALTER COLUMN submit_id SET NOT NULL;
ALTER SEQUENCE submission_seq OWNED BY submission.submit_id;
