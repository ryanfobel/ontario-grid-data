# CLAUDE.md — AI Assistant Guide for ontario-grid-data

## Project Overview

Data collection and analysis project that downloads, cleans, and publishes hourly electricity grid data for Ontario, Canada. Tracks power generation mix (nuclear, hydro, wind, solar, gas, biofuel), CO2 emissions intensity, demand, and electricity rates from multiple public sources.

Historical data spans 2010–present with ~132K hourly records. An interactive Panel-based PWA dashboard is published to `docs/`.

## Repository Structure

```
src/ontario_grid_data/       # Python modules (one per data source)
├── gridwatch.py             # Scrapes gridwatch.ca via Selenium (live grid data)
├── ieso/                    # IESO historical hourly production data
│   ├── __main__.py          # Entry point: download + cleanup + fetch latest
│   ├── core.py              # Download/parse logic (Excel pre-2019, CSV 2019+)
│   └── CA.py                # XML report parser (from Electricity Maps)
├── oeb.py                   # Ontario Energy Board rates (HTML scraping)
├── co2signal.py             # CO2 signal API (currently disabled in CI)
└── utilities.py             # Shared helpers (git history, hourly CSV building)

data/
├── raw/                     # Unprocessed scraped files (cached downloads)
└── clean/                   # Processed data, organized by source
    ├── gridwatch.ca/        # Summary, output, capability CSVs + latest JSON
    ├── ieso.ca/hourly/output/  # Yearly CSVs (2010.csv–2026.csv) + latest JSON
    ├── co2signal.com/       # CO2 intensity time series
    └── oeb.ca/              # Electricity and natural gas rate tables

notebooks/                   # Jupyter notebooks for analysis and dashboard
├── index.ipynb              # Main interactive Panel dashboard (builds to docs/)
├── Download IESO data.ipynb
├── Download energy price data.ipynb
├── Fit models.ipynb
├── Gridwatch scraper.ipynb
└── Plot data.ipynb

docs/                        # Built PWA dashboard (auto-generated, do not edit manually)
```

## Development Setup

### Environment

```bash
conda env create -f environment.yml   # Creates 'gridwatch' conda environment
conda activate gridwatch
pip install -e .                       # Install package in editable mode
```

Key dependencies: pandas, selenium, openpyxl, arrow, beautifulsoup4, scipy, scikit-learn, matplotlib

### Running Scrapers

Each data source is a runnable module:

```bash
python -m src.ontario_grid_data.gridwatch   # Requires Firefox + geckodriver
python -m src.ontario_grid_data.ieso        # Downloads IESO data
python -m src.ontario_grid_data.oeb         # Scrapes OEB rates
python -m src.ontario_grid_data.co2signal   # Requires CO2SIGNAL_API_TOKEN in .env
```

### Secrets

API tokens are loaded from `.env` (gitignored) via `python-dotenv`. Currently only `CO2SIGNAL_API_TOKEN` is used.

## CI/CD

GitHub Actions workflow (`.github/workflows/scheduled-update.yml`):
- **Schedule:** Runs every 15 minutes via cron + on push to main
- **Steps:** Install deps → run gridwatch/ieso/oeb scrapers → build Panel dashboard → auto-commit changes to `data/`, `notebooks/`, `docs/`
- **Dashboard build:** Converts `notebooks/index.ipynb` to PWA via `panel convert` with Pyodide
- Uses `continue-on-error: true` for scraper steps (no data change = no commit)

## Code Conventions

### Architecture
- **One module per data source** with a `main()` function and `if __name__ == "__main__"` entry point
- **Separation:** raw download → data cleaning → CSV/JSON storage
- Data flows: scrape/download → `data/raw/` → clean → `data/clean/` → latest JSON snapshots

### Timezone Handling
- All timestamps use **America/Toronto** timezone
- IESO data uses UTC-5 (EST year-round, no DST) — converted to Toronto tz on ingestion
- Use `pandas.Timestamp.tz_localize()` and `.tz_convert()` consistently

### Data Formats
- **Historical data:** CSV files with datetime index, organized by year (IESO) or as single files (gridwatch, co2signal)
- **Latest snapshots:** JSON files in `latest/` subdirectories for dashboard consumption
- **Plant-level data:** Wide format with plant names as columns, hourly rows

### Error Handling
- Graceful degradation preferred (continue-on-error in CI)
- `try/finally` for resource cleanup (Selenium driver)
- Git operations wrapped in `CalledProcessError` catches

### Versioning
- Base version in `VERSION` file (currently `0.1`)
- Dynamic versioning via `setuptools-git-versioning` (commit counting from git tags)
- Version injected into dashboard at build time

## Important Notes

- **Do not manually edit files in `docs/`** — they are auto-generated from `notebooks/index.ipynb`
- **Do not commit `.env` files** or API tokens
- The gridwatch scraper requires a **headless Firefox browser** (Selenium) — it won't work without Firefox + geckodriver installed
- The `utilities.py` module uses **git history as a data source** (`git show` to retrieve historical JSON snapshots) — be careful with git history rewriting
- No test suite or linter is currently configured
- Commit messages for automated updates are simply "update"
