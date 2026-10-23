---
layout: home
title: Troubleshooting
permalink: /troubleshooting/
nav_order: 8
---

# Troubleshooting

## Removing bad tests

If you abort a test in the middle of running, you will end up with a
bad test result entry in the results database.  These will look odd
and can distort averages and graphs.  Ideally you would erase
the entire directory each of those bad test results are in, followed by
removing their main entry from the results database.  You can do that
at a shell prompt like this::

    ./cleanup
    ./webreport 

To cleanup a single value use `./cleanup_singlevalue <testvaluenumber>`
To cleanup all values from a particular starting point use `./cleanup_fromvalue <startingvalue>`

## `dateutil` / Homebrew Python (macOS)

`pgsysinfo` failing with `No module named 'dateutil'`, or OSM post-process dying in `csv2gnuplot` with `init_sys_streams` / `Bad file descriptor`, usually means pgbent is on **brew `python3`**. That interpreter moves; collector scripts should not.

Fix: `./util/setup-python` and put `.venv/bin` first on PATH. See [Setup]({{ '/setup/#python-for-collectors' | relative_url }}). Do not `sudo pip3 install` into brew or Apple Python. `repair-osm-result` still recovers a finished OSM load whose post-process crashed.
