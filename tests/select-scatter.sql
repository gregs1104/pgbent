-- Scattered index probes + heap fetches (Relations-shaped miniature).
-- Unsorted random aids → NL/index lookups rather than a contiguous range walk.
-- Prefer with enable_seqscan=off / enable_bitmapscan=off so the planner
-- stays on index nested-loop heap fetches (see wl/arm-miss-isolation).
--
-- :scale is pgbench scale (rows ≈ scale * 100000).
-- Fixed 64-aid unsorted IN list (MULTI/multiplier recorded as 64 in the run).

\set limit 100000 * :scale
\set a01 random(1, :limit)
\set a02 random(1, :limit)
\set a03 random(1, :limit)
\set a04 random(1, :limit)
\set a05 random(1, :limit)
\set a06 random(1, :limit)
\set a07 random(1, :limit)
\set a08 random(1, :limit)
\set a09 random(1, :limit)
\set a10 random(1, :limit)
\set a11 random(1, :limit)
\set a12 random(1, :limit)
\set a13 random(1, :limit)
\set a14 random(1, :limit)
\set a15 random(1, :limit)
\set a16 random(1, :limit)
\set a17 random(1, :limit)
\set a18 random(1, :limit)
\set a19 random(1, :limit)
\set a20 random(1, :limit)
\set a21 random(1, :limit)
\set a22 random(1, :limit)
\set a23 random(1, :limit)
\set a24 random(1, :limit)
\set a25 random(1, :limit)
\set a26 random(1, :limit)
\set a27 random(1, :limit)
\set a28 random(1, :limit)
\set a29 random(1, :limit)
\set a30 random(1, :limit)
\set a31 random(1, :limit)
\set a32 random(1, :limit)
\set a33 random(1, :limit)
\set a34 random(1, :limit)
\set a35 random(1, :limit)
\set a36 random(1, :limit)
\set a37 random(1, :limit)
\set a38 random(1, :limit)
\set a39 random(1, :limit)
\set a40 random(1, :limit)
\set a41 random(1, :limit)
\set a42 random(1, :limit)
\set a43 random(1, :limit)
\set a44 random(1, :limit)
\set a45 random(1, :limit)
\set a46 random(1, :limit)
\set a47 random(1, :limit)
\set a48 random(1, :limit)
\set a49 random(1, :limit)
\set a50 random(1, :limit)
\set a51 random(1, :limit)
\set a52 random(1, :limit)
\set a53 random(1, :limit)
\set a54 random(1, :limit)
\set a55 random(1, :limit)
\set a56 random(1, :limit)
\set a57 random(1, :limit)
\set a58 random(1, :limit)
\set a59 random(1, :limit)
\set a60 random(1, :limit)
\set a61 random(1, :limit)
\set a62 random(1, :limit)
\set a63 random(1, :limit)
\set a64 random(1, :limit)

SELECT sum(a.abalance)
FROM unnest(ARRAY[
  :a01,:a02,:a03,:a04,:a05,:a06,:a07,:a08,
  :a09,:a10,:a11,:a12,:a13,:a14,:a15,:a16,
  :a17,:a18,:a19,:a20,:a21,:a22,:a23,:a24,
  :a25,:a26,:a27,:a28,:a29,:a30,:a31,:a32,
  :a33,:a34,:a35,:a36,:a37,:a38,:a39,:a40,
  :a41,:a42,:a43,:a44,:a45,:a46,:a47,:a48,
  :a49,:a50,:a51,:a52,:a53,:a54,:a55,:a56,
  :a57,:a58,:a59,:a60,:a61,:a62,:a63,:a64
]::bigint[]) AS u(aid)
JOIN pgbench_accounts a ON a.aid = u.aid;
