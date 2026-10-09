# WeatherWatch — Phase 1: Core ETL

This is the foundation layer: extract → transform → quality-check → load,
running as a plain Python script (no Airflow, no FastAPI yet). The goal is
to prove the core data engineering logic works against real data before
wrapping it in orchestration.

## Setup

1. **Create the database table**
   Open your Supabase project → SQL Editor → paste and run `sql/schema.sql`.

2. **Install dependencies**
   ```bash
   cd weather-watch
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure secrets**
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and paste your real Supabase connection string
   (Supabase → Settings → Database → Connection string → URI).
   Open-Meteo needs no API key.

## Run it

```bash
cd pipeline
python run_pipeline.py "Mumbai"
python run_pipeline.py "Mumbai" "London" "Tokyo"
```

Expected output: one line per city showing `OK - inserted row id N`,
`SKIPPED - duplicate record`, or `FAILED - <reason>`.

You can also run each stage on its own to debug it in isolation:
```bash
python extract.py      # prints raw geocoded + weather JSON
python transform.py    # prints the cleaned, validated record
python load.py         # runs the full chain and inserts one row
```

## What's next (not in this phase)

- Wrap `extract → transform → load` into an Airflow DAG (4 tasks)
- Add the FastAPI backend (cache check, trigger DAG, status polling)
- Add the React frontend
- Backfill historical data + add Spark analytics

## File map

```
weather-watch/
├── .env.example       # template for secrets (safe to commit)
├── .gitignore         # keeps .env and junk out of git
├── requirements.txt
├── sql/
│   └── schema.sql     # weather_observations table definition
└── pipeline/
    ├── extract.py       # Task 1: extract + validate
    ├── transform.py     # Task 2: transform + quality check
    ├── load.py           # Task 3: load (+ cache-check helper for FastAPI later)
    └── run_pipeline.py   # ties the three stages together, standalone
```
