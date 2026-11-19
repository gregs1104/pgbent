-- Range length from MULTI / -Dmultiplier (one script suits all sizes).
-- Contrast: select-scatter-N fixes batch size in the script name instead.
\set range 67 * (:multiplier + 1)
\set limit 100000 * :scale
\set limit :limit - :range
\set aid random(1, :limit)
SELECT aid,abalance FROM pgbench_accounts WHERE aid >= :aid ORDER BY aid LIMIT :range;
