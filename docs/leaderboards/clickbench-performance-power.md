---
layout: home
title: "ClickBench Leaders: Performance vs. Power"
permalink: /leaderboards/clickbench-performance-power/
parent: Leaderboards
nav_order: 3
---

# ClickBench Leaders: Performance vs. Power

Totals and phase breakdown behind ClickBench runs on the pgbent farm. Query **score** is the absolute higher-is-better take on ClickBench’s hot geometric mean: `round(1000 / geomean(min(try2, try3)))` across the 43 queries. Load **tps** is MB/s from `data_size / load_time`. Methodology notes: [ClickBench README](https://github.com/ClickHouse/ClickBench/blob/main/README.md).

Regenerate: `python3 reports/clickbench-leaderboard.py --from-db` (runs `reports/clickbench-leaderboard.sql`).

<!-- clickbench-leaderboard:begin -->

Starter board from **court** (NVIDIA P4242, 119 GB, Samsung MZAL), PostgreSQL **19.0**, set **33** — ClickBench. Best finished **query** cell by score (**149** = `1000 / geomean(hot)`), paired with the **load** sibling in the same set. Package watts are the owned 1-second collectors (`PkgWatt` / Darwin / Spark `soc_pkg_power2_input`).

**Totals**

| cpu | mem_gb | disk | ver | set | score | cold_score | hot_geomean | max_hot | load_mbs | load_s | data_gb | avg_pkg_q | max_pkg_q | kj_q |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NVIDIA P4242 | 119 | Samsung MZAL | 19.0 | 33 | 149 | 143 | 6.721 | 126.609 | 198 | 347 | 67.1 | 41.4 | 86 | 74.9 |

**Phase breakdown**

| phase | test | tps | meaning | wall_s | avg_pkg | max_pkg | kj | detail |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| load | 332 | 198 | MB/s | 350 | 21.6 | 26.7 | 7.6 | load_time 347s, data 67.1 GB |
| query | 333 | 149 | 1000/geomean(hot) | 1,811 | 41.4 | 86 | 74.9 | hot_geomean 6.721s, cold_geomean 7s, queries 43 |

**Query runs** (seconds; **cold** = try1, **hot** = min(try2, try3))

| q | cold | try2 | try3 | hot |
| --- | --- | --- | --- | --- |
| 1 | 4.966 | 1.94 | 1.941 | 1.94 |
| 2 | 2.837 | 2.813 | 2.735 | 2.735 |
| 3 | 2.822 | 2.854 | 2.757 | 2.757 |
| 4 | 2.845 | 2.551 | 2.488 | 2.488 |
| 5 | 9.084 | 9.231 | 9.024 | 9.024 |
| 6 | 23.764 | 21.799 | 25.112 | 21.799 |
| 7 | 2.471 | 2.534 | 2.455 | 2.455 |
| 8 | 2.79 | 2.702 | 2.682 | 2.682 |
| 9 | 15.017 | 14.285 | 14.225 | 14.225 |
| 10 | 16.889 | 16.084 | 16.098 | 16.084 |
| 11 | 3.526 | 3.502 | 3.68 | 3.502 |
| 12 | 3.69 | 3.789 | 3.819 | 3.789 |
| 13 | 12.704 | 12.889 | 12.924 | 12.889 |
| 14 | 16.084 | 16.75 | 15.787 | 15.787 |
| 15 | 13.03 | 14.022 | 13.178 | 13.178 |
| 16 | 7.206 | 7.084 | 7.177 | 7.084 |
| 17 | 31.512 | 30.338 | 31.447 | 30.338 |
| 18 | 5.036 | 5.21 | 5.098 | 5.098 |
| 19 | 56.131 | 60.286 | 56.214 | 56.214 |
| 20 | 2.672 | 2.507 | 2.498 | 2.498 |
| 21 | 3.182 | 3.238 | 3.127 | 3.127 |
| 22 | 3.441 | 3.423 | 3.584 | 3.423 |
| 23 | 3.459 | 3.431 | 3.61 | 3.431 |
| 24 | 3.31 | 3.384 | 3.307 | 3.307 |
| 25 | 2.818 | 2.846 | 2.826 | 2.826 |
| 26 | 2.899 | 2.876 | 2.85 | 2.85 |
| 27 | 2.85 | 2.853 | 2.971 | 2.853 |
| 28 | 4.204 | 4.267 | 4.269 | 4.267 |
| 29 | 35.992 | 35.918 | 35.931 | 35.918 |
| 30 | 7.924 | 8.064 | 7.93 | 7.93 |
| 31 | 17.908 | 19.386 | 18.851 | 18.851 |
| 32 | 6.776 | 6.949 | 6.646 | 6.646 |
| 33 | 126.199 | 131.879 | 126.609 | 126.609 |
| 34 | 58.289 | 55.721 | 56.334 | 55.721 |
| 35 | 56.727 | 57.459 | 56.132 | 56.132 |
| 36 | 6.682 | 6.751 | 6.679 | 6.679 |
| 37 | 3.997 | 4.171 | 3.836 | 3.836 |
| 38 | 3.473 | 3.369 | 3.299 | 3.299 |
| 39 | 3.08 | 3.124 | 3.088 | 3.088 |
| 40 | 3.945 | 4.131 | 4.003 | 4.003 |
| 41 | 3.769 | 3.722 | 3.435 | 3.435 |
| 42 | 3.509 | 3.547 | 3.592 | 3.547 |
| 43 | 3.255 | 3.07 | 3.011 | 3.011 |

<!-- clickbench-leaderboard:end -->
