# Ontario Grid Data — Refactor Plan

## Context

The existing repo (`ontario-grid-data`) stores hourly electricity grid data for Ontario by committing CSV rows every 15 minutes. This causes git performance degradation over time and uses git history as a makeshift time-series database (via `utilities.py`). The goal is to replace this with a proper data pipeline.

## New Repo

**`https://github.com/ryanfobel/ontario-grid-pipelines`**

A `bootstrap.sh` scaffold was generated covering the full structure below. Run it from inside an empty clone of the new repo.

## Chosen Architecture

```
Sources                     Load (dlt)         Store          Transform (dbt)
─────────────────────────   ────────────────   ────────────   ───────────────
IESO XML reports        ──►                    ┌──────────┐   staging/
gridwatch.ca (Selenium) ──► dlt pipeline   ──► │ DuckDB   │ ► marts/
co2signal API           ──►                    └──────────┘     hourly_generation
OEB HTML rates          ──►                         │           plant_capacity_factors
                                              data branch
                                              (force-pushed,
                                               single commit)
```

### Storage: DuckDB on an orphan `data` branch

- Single file `ontario_grid.duckdb` on a `data` branch with exactly **one commit** (force-pushed each run)
- Old git objects become unreferenced and are GC'd by GitHub — branch never grows unbounded
- The DuckDB file itself grows with the dataset (expected), but git history does not accumulate
- Each CI run: download DB from `data` branch → append rows → dbt transform → force-push back

### Why not object storage (S3/GCS)?

Orphan branch (Option A) chosen over S3 to avoid cloud infrastructure and credentials.
Tradeoff: concurrent CI runs could race. Mitigated with GitHub Actions `concurrency` group
(`cancel-in-progress: false` queues runs rather than dropping them).

## Scaffolded Project Structure

```
ontario-grid-pipelines/
├── pipelines/
│   ├── __init__.py
│   ├── ieso.py          # dlt source: IESO XML → production_by_fuel, production_by_plant, hoep_price
│   ├── gridwatch.py     # dlt source: Selenium → grid_summary
│   ├── co2signal.py     # dlt source: API → carbon_intensity
│   └── oeb.py           # dlt source: HTML scrape → electricity_rates
├── transform/           # dbt project (profile: ontario_grid, adapter: dbt-duckdb)
│   ├── dbt_project.yml
│   ├── profiles.yml     # reads DUCKDB_PATH env var
│   └── models/
│       ├── staging/     # materialized: view
│       │   ├── sources.yml
│       │   ├── stg_ieso_production_by_fuel.sql
│       │   ├── stg_ieso_production_by_plant.sql
│       │   ├── stg_ieso_hoep_price.sql
│       │   ├── stg_gridwatch.sql
│       │   ├── stg_co2signal.sql
│       │   └── stg_oeb_rates.sql
│       └── marts/       # materialized: table
│           ├── hourly_generation.sql       # pivot by fuel + join price + CO2
│           └── plant_capacity_factors.sql  # energy_mw / capability_mw per plant
├── scripts/
│   └── migrate_historical.py   # one-time load of old CSVs → DuckDB
├── .github/workflows/
│   └── scheduled-update.yml    # cron every 15 min
├── pipeline.py          # entry: python pipeline.py --source ieso,gridwatch,oeb
├── pyproject.toml
├── environment.yml
└── README.md
```

## dlt Design

Each scraper maps to a dlt `@dlt.source` / `@dlt.resource`:

| Old module | dlt resource | write_disposition | primary_key |
|---|---|---|---|
| `ieso/CA.py` | `production_by_fuel` | merge | `[fuel, datetime]` |
| `ieso/CA.py` | `production_by_plant` | merge | `[plant_name, datetime]` |
| `ieso/CA.py` | `hoep_price` | merge | `[datetime]` |
| `gridwatch.py` | `grid_summary` | merge | `[datetime]` |
| `co2signal.py` | `carbon_intensity` | merge | `[datetime]` |
| `oeb.py` | `electricity_rates` | merge | `[effective_date, rate_type]` |

dlt handles incremental state — replaces the `utilities.py` git-history trick entirely.

Raw tables in DuckDB are named `{source}__{resource}`, e.g. `ieso__production_by_fuel`.

## dbt Design

- **staging models** (views): cast datetimes to `timestamptz`, add `datetime_toronto` column,
  normalize fuel name casing, clean column names
- **mart models** (tables):
  - `hourly_generation`: pivot fuel rows → columns, join HOEP price + CO2 intensity
  - `plant_capacity_factors`: `energy_mw / capability_mw` per plant per hour

## CI Workflow (`.github/workflows/scheduled-update.yml`)

```
1. checkout@v4 (code branch)
2. git fetch origin data --depth=1 && checkout ontario_grid.duckdb
3. setup-python 3.11
4. setup-firefox + setup-geckodriver
5. pip install -e .
6. python pipeline.py --source ieso,gridwatch,oeb
7. pip install dbt-duckdb && dbt run
8. git checkout --orphan data-new
   git reset --hard
   cp ontario_grid.duckdb .
   git add ontario_grid.duckdb
   git commit -m "data snapshot <timestamp>"
   git push --force origin HEAD:data
```

Concurrency group `pipeline` with `cancel-in-progress: false` serializes runs.

## What to Keep from Old Repo

The Selenium/XML/HTML parsing logic in these files is still valid — it just needs to be
wrapped in dlt resources rather than writing CSVs directly:

- `src/ontario_grid_data/gridwatch.py` → XPath selectors, time string parser
- `src/ontario_grid_data/ieso/CA.py` → XML namespace parsing, hour-ending convention
- `src/ontario_grid_data/oeb.py` → BeautifulSoup table extraction

## What's Replaced

| Old | New |
|---|---|
| `utilities.py` (git checkout loop) | dlt incremental state |
| Per-scraper CSV write logic | dlt `duckdb` destination |
| `ieso/core.py` cleanup logic | dbt staging models |
| Yearly CSVs in `data/clean/ieso.ca/` | `ieso__production_by_plant` table in DuckDB |
| `data/` directory committed to git | orphan `data` branch (single-commit, force-pushed) |
| Latest JSON snapshots | dbt mart tables queryable via DuckDB |

## Remaining Tasks

- [ ] Run `bootstrap.sh` in the new repo and push to `main`
- [ ] Run migration: `python scripts/migrate_historical.py --old-repo /path/to/ontario-grid-data`
- [ ] Verify dbt models run cleanly against migrated data
- [ ] Re-wire the Panel dashboard (`notebooks/index.ipynb`) to read from DuckDB instead of CSVs
- [ ] Enable co2signal source once `CO2SIGNAL_API_TOKEN` secret is set in new repo
- [ ] Archive or redirect `ontario-grid-data` repo
