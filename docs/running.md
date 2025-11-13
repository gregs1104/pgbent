---
layout: home
title: Running
permalink: /running/
nav_order: 3
---

# Running tests

* Edit the config file to reference the test and results database, as
  well as list the test you want to run.  The default test is a
  SELECT-only one that runs for 60 seconds.

* Execute::

      ./runset

  In order to execute all the tests

HINT:: change the pg_hba.conf or setup a pgpass file to avoid password prompt for each connection (there's a lot of them). You can also `export` the password in your shell session.
