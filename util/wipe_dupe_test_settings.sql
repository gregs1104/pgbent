-- Remove duplicates from test_settings where there's more than one entry
-- for a test/server/name set.  These came from a bug in earlier pgbent
-- code that saved multiple copies of the settings.
--
-- These have been accomidated until now by using "LIMIT 1" on queries.
-- They need to be eliminated before a unique index can be created.

\timing

DELETE FROM test_settings ts1
  USING test_settings ts2
WHERE
  ts1.ctid    < ts2.ctid AND
  ts1.server=ts2.server AND
  ts1.test=ts2.test AND
  ts1.name=ts2.name
  ;
