-- Contiguous heap range (readahead-friendly contrast to select-scatter).
-- 64 consecutive aids starting at a random aligned offset → sequential
-- index/heap reads rather than scattered NL fetches.
-- Prefer with enable_seqscan=off so the planner stays on the aid index.
--
-- :scale is pgbench scale (rows ≈ scale * 100000).

\set limit 100000 * :scale
\set start random(1, :limit - 64)
\set a01 :start + 0
\set a02 :start + 1
\set a03 :start + 2
\set a04 :start + 3
\set a05 :start + 4
\set a06 :start + 5
\set a07 :start + 6
\set a08 :start + 7
\set a09 :start + 8
\set a10 :start + 9
\set a11 :start + 10
\set a12 :start + 11
\set a13 :start + 12
\set a14 :start + 13
\set a15 :start + 14
\set a16 :start + 15
\set a17 :start + 16
\set a18 :start + 17
\set a19 :start + 18
\set a20 :start + 19
\set a21 :start + 20
\set a22 :start + 21
\set a23 :start + 22
\set a24 :start + 23
\set a25 :start + 24
\set a26 :start + 25
\set a27 :start + 26
\set a28 :start + 27
\set a29 :start + 28
\set a30 :start + 29
\set a31 :start + 30
\set a32 :start + 31
\set a33 :start + 32
\set a34 :start + 33
\set a35 :start + 34
\set a36 :start + 35
\set a37 :start + 36
\set a38 :start + 37
\set a39 :start + 38
\set a40 :start + 39
\set a41 :start + 40
\set a42 :start + 41
\set a43 :start + 42
\set a44 :start + 43
\set a45 :start + 44
\set a46 :start + 45
\set a47 :start + 46
\set a48 :start + 47
\set a49 :start + 48
\set a50 :start + 49
\set a51 :start + 50
\set a52 :start + 51
\set a53 :start + 52
\set a54 :start + 53
\set a55 :start + 54
\set a56 :start + 55
\set a57 :start + 56
\set a58 :start + 57
\set a59 :start + 58
\set a60 :start + 59
\set a61 :start + 60
\set a62 :start + 61
\set a63 :start + 62
\set a64 :start + 63

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
