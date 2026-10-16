\set ON_ERROR_STOP on
\if :{?server}
\else
\echo art-import.sql requires -v server= and -v test=
\quit 1
\endif
\if :{?test}
\else
\echo art-import.sql requires -v server= and -v test=
\quit 1
\endif

\set content `cat results.json`
-- Bind to this benchwarmer's server/test. Write-once: a populated cell is
-- as durable as an upload archive. Failed OSM parses emit {} and used to
-- land on the last good row (latest start_time / max(test) reuse).
UPDATE tests SET artifacts = :'content'::jsonb
WHERE server = :'server'
  AND test = :test
  AND :'content'::jsonb <> '{}'::jsonb
  AND (artifacts IS NULL OR artifacts = '{}'::jsonb);
