---
layout: home
title: Troubleshooting
permalink: /troubleshooting/
nav_order: 6
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
