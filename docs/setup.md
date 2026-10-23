---
layout: home
title: Setup
permalink: /setup/
nav_order: 3
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

## Python for collectors

`pgsysinfo`, `csv2gnuplot`, and `timed-os-stats` are `#!/usr/bin/env python3` and need **python-dateutil**. That is the whole collector dependency. Graphing (Pandas/Matplotlib) is a separate laptop venv (`.venv-graph`), not required on the machine under test.

**Linux** — distro `python3` plus `python3-dateutil` (or the equivalent pip package). PGDG boxes already work this way.

**macOS** — do **not** use Homebrew’s `python3` for pgbent. Brew upgrades it (abbey’s login `python3` is currently 3.15), `dateutil` vanishes under PEP 668, and Darwin post-process (`init_sys_streams` / bad FD) is then impossible to bisect. Apple `/usr/bin/python3` is too old. conda is another PATH fight.

Pin a CPython 3.12 in the checkout:

```bash
./util/setup-python
```

That installs **uv** if needed, downloads an official 3.12 (not a brew keg), creates `.venv`, and installs `requirements-collect.txt`. Put the venv **first** on PATH so `python3` is pinned while `psql`/`pgbench` stay Homebrew:

```bash
# after: eval "$(/opt/homebrew/bin/brew shellenv)"
export PATH="$HOME/repos/pgbent/.venv/bin:$PATH"
```

Smoke test: `./pgsysinfo` prints version / `SETCLIENTS` / `SCALES`. Agent SSH on the Mac must be `bash -lc` or it still hits Apple 3.9.

Homebrew PostgreSQL majors lag PGDG. Test each new major on brew **after** the release bottles exist (PostGIS linked). During RC, the four-face SELECT / `nothing` / `constant` pack on abbey runs on **PG18**.

