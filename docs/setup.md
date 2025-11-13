---
layout: home
title: Setup
permalink: /setup/
nav_order: 2
---

# Setup

* Install GNUplot.

* Create databases for your test and for the results::

      createdb results
      createdb pgbench

  *  Both databases can be the same, but there may be more shared_buffers
     cache churn in that case.  Some amount of cache disruption
     is unavoidable unless the result database is remote, because
     of the OS cache.  The recommended and default configuration
     is to have a pgbench database and a results database.  This also
     keeps the size of the result dataset from being included in the
     total database size figure recorded by the test.

* Initialize the results database by executing::

      psql -f init/resultdb.sql -d results

  Make sure to reference the correct database.

* You need to create a test set with a descritption::

      ./newset 'Initial Config'

  Running the "newset" utility without any parameters will list all of the
  existing test sets.
  
  * Allow linux user to fire the tools::
  
        chmod +x benchwarmer
        chmod +x cleanup

