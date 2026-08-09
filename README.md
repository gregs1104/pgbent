# pgbent

Benchmarking toolkit for PostgreSQL: repeatable workloads, one-second system and database metrics, and a results database for regression testing and tuning studies.

- **[Documentation](https://getbent.io)** — setup, workloads, tuning research, troubleshooting
- **[Results explorer](https://pgbent.streamlit.app/)** — browse published Postgres 14–18 benchmark data
- **[AGENTS.md](AGENTS.md)** — architecture, workflows, and development plans (for contributors and coding agents)

![osm2pgsql workload](reports/images/samples/twilight-1494-read-write.png)

## Quick start

```bash
createdb results && psql -f init/resultdb.sql -d results
./newset 'my first set'
./runset
./webreport
```

See [Setup](https://getbent.io/setup/) and [Running tests](https://getbent.io/running/) on the docs site.

## Workloads

| Workload | Location |
|----------|----------|
| pgbench client × size grids | [Workloads](https://getbent.io/workloads/) |
| OpenStreetMap import (osm2pgsql) | [OSM workload](https://getbent.io/workloads/osm) |
| Complete Block Check | [tests/cbc/README.md](tests/cbc/README.md) |

## Contact

- Repository: https://github.com/gregs1104/pgbent
- Greg Smith — gregs1104@gmail.com

Historical pgbench-tools copies: [git.postgresql.org](http://git.postgresql.org/git/pgbench-tools.git)

### Notable forks

- https://github.com/emerichunter/pgbench-tools
- https://github.com/rugging24/pg_pybench (bash → Python, Windows)

## Credits

Copyright (c) 2007–2025, Gregory Smith. See [COPYRIGHT](COPYRIGHT) and [HISTORY](HISTORY).

Major contributors: Josh Kupershmidt, Emeric Tabakhoff

References: [Emeric's intro (EN)](https://emerichunter.github.io/pgbench-tools-p1/) · [FR](https://www.loxodata.com/post/benchmarking-pratique/)
