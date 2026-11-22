-- Scattered index probes + heap fetches (Relations-shaped miniature).
-- Unsorted random aids → NL/index lookups rather than a contiguous range walk.
-- Prefer with enable_seqscan=off / enable_bitmapscan=off so the planner
-- stays on index nested-loop heap fetches (see wl/arm-miss-isolation).
--
-- :scale is pgbench scale (rows ≈ scale * 100000).
-- Fixed 4-aid unsorted list. Size lives in the script name (select-scatter-N);
-- setup writes MULTI=N into tests.multi. Unlike select-pages (one script, vary
-- MULTI / :multiplier), more scatter sizes are more scripts. benchwarmer also
-- derives MULTI from the name when SCRIPT=select-scatter-N.

\set limit 100000 * :scale
\set a01 random(1, :limit)
\set a02 random(1, :limit)
\set a03 random(1, :limit)
\set a04 random(1, :limit)

SELECT sum(a.abalance)
FROM unnest(ARRAY[
  :a01,:a02,:a03,:a04
]::bigint[]) AS u(aid)
JOIN pgbench_accounts a ON a.aid = u.aid;
