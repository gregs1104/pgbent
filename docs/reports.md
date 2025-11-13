---
layout: home
title: Reports
permalink: /reports/
nav_order: 5
---

# Reports

* limited_webreport followed by a comma seperated list of sets
* rates_webreport in the same manner but **only for fixed tps tests**
* **cleanups** (singlevalue, all dirty values, from a value till the end) see "Removing Bad Tests"
* latest_set:  list of tests of the current/latest set (ordered)
* list_orderbyset : lists sets ordered
* lowest_latency (and fastest tests with different degrees of compromise)
* **compromise_params**: allows to see a particular area of scale/client/tps/latency using only sql and no graph

      psql -d results -v lat=15 -v tps=700 -v lscale=900 -v hscale=1000 -v lclients=1 -v hclients=16 -f reports/compromise_params.sql
