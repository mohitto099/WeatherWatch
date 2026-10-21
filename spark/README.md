# WeatherWatch - Spark analytics

Reads `weather_history`, computes 1-week / 1-month / 6-month / 1-year statistics per city with
Apache Spark (DataFrames, Spark SQL window functions, and an RDD cross-check), and writes
the results to `weather_analytics` and `weather_daily_trend`, which the app's analytics panel shows.

## One-time setup
1. In the Supabase SQL Editor, run `sql\analytics_tables.sql` (creates the two result tables).
2. Make sure `backend\.env` has your `SUPABASE_DB_URL` (the compose file reuses it).
   If your password contains a `$`, wrap the whole value in single quotes in that file.

## Run (PowerShell, Docker Desktop running)

    cd C:\Projects\weather-watch\spark
    docker compose run --rm spark-job

The first run downloads the Spark image (about 1 GB) and builds, so it takes a few minutes.
Later runs take roughly a minute. Run it again whenever you add more history.

## What it prints
Five stages: read, DataFrame windows, Spark SQL window functions, RDD cross-check
("RDD result matches DataFrame result: YES"), and write-back. Good to show your mentor.

## Notes
- Spark runs in local mode inside Docker (no cluster, no Java on your PC).
- Windows end at the latest timestamp that every analysed city has, so cities are compared over the same period.
- A city needs at least 30 days of hourly rows to be analysed; the few cities you only searched live are skipped.

## If something goes wrong
- **"SUPABASE_DB_URL is not set"**: the compose file reads `..\backend\.env`. Check that file exists and has the line.
- **Authentication or connection errors**: use the same Session pooler connection string the backend uses
  (Supabase -> Settings -> Database -> Connection string). Special characters in the password must be URL-encoded (`@` becomes `%40`).
- **"relation weather_analytics does not exist"**: run `sql\analytics_tables.sql` in the Supabase SQL Editor first.
- **"No city has enough history yet"**: run `pipeline\backfill_history.py` first.
- **The image fails to pull**: the `FROM` line in `Dockerfile` names the Spark version; try another tag from Docker Hub's `apache/spark` page.
