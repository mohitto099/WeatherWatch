"""
backfill_history.py
-------------------
Loads REAL historical hourly weather from Open-Meteo's archive API into
weather_history, so Spark has a dataset worth analysing.

What it does, per city:
  1. Geocode the name (same call as the live pipeline, so city names match)
  2. ONE archive API request for the whole date range (hourly data)
  3. Transform with Pandas and apply the same data-quality rules as the live pipeline
  4. Bulk-insert into weather_history with source = 'backfill'

Safe to re-run: the UNIQUE (city, observation_time) constraint skips rows that already exist.
It never touches current_weather, so it cannot affect the 15-minute cache.

Usage (from the pipeline folder, venv active):
    python backfill_history.py                         # 8 default cities, last 365 days
    python backfill_history.py --days 180
    python backfill_history.py --cities "Mumbai,Pune"
    python backfill_history.py --dry-run               # fetch + validate, write nothing
"""

import argparse
import sys
import time
from datetime import date, timedelta

import pandas as pd
import requests
from psycopg2.extras import execute_values

from extract import WeatherAPIError, geocode_city
from load import get_connection

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
DEFAULT_CITIES = ["Mumbai", "Delhi", "Bengaluru", "London", "New York", "Tokyo", "Sydney", "Dubai"]
ARCHIVE_LAG_DAYS = 7   # the archive runs a few days behind real time
HOURLY_VARS = ["temperature_2m", "relative_humidity_2m", "surface_pressure", "wind_speed_10m", "weather_code"]
PAUSE_BETWEEN_CITIES = 1.0   # seconds, keeps us well inside Open-Meteo's per-minute limit

COLUMNS = [
    "city", "country", "latitude", "longitude", "temperature", "humidity",
    "pressure", "wind_speed", "weather_code", "observation_time", "source",
]

INSERT_SQL = f"""
    INSERT INTO weather_history ({', '.join(COLUMNS)})
    VALUES %s
    ON CONFLICT (city, observation_time) DO NOTHING
    RETURNING id
"""


def fetch_hourly(location: dict, start: date, end: date) -> dict:
    """One archive request for the whole range. Retries a few times on temporary errors."""
    params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": ",".join(HOURLY_VARS),
        "timezone": "auto",   # same local-time convention as the live data
    }
    last_error = None
    for attempt in range(1, 4):
        try:
            resp = requests.get(ARCHIVE_URL, params=params, timeout=60)
            if resp.status_code == 200:
                hourly = resp.json().get("hourly")
                if not hourly or "time" not in hourly:
                    raise WeatherAPIError("Archive response has no hourly data")
                return hourly
            if resp.status_code == 429:
                raise WeatherAPIError("Open-Meteo rate limit reached (HTTP 429). Wait a while and run again.")
            last_error = f"HTTP {resp.status_code}"
        except requests.RequestException as e:
            last_error = str(e)
        time.sleep(2 * attempt)
    raise WeatherAPIError(f"Archive request failed after 3 tries ({last_error})")


def to_frame(location: dict, hourly: dict) -> tuple[pd.DataFrame, int]:
    """Hourly arrays -> clean rows. Returns (rows, number_of_rows_rejected)."""
    df = pd.DataFrame({
        "observation_time": pd.to_datetime(hourly["time"]),
        "temperature": hourly["temperature_2m"],
        "humidity": hourly["relative_humidity_2m"],
        "pressure": hourly["surface_pressure"],
        "wind_speed": hourly["wind_speed_10m"],
        "weather_code": hourly["weather_code"],
    })
    total = len(df)

    # Same rules as the live pipeline's quality gate
    df = df.dropna(subset=["temperature", "humidity", "pressure", "wind_speed", "weather_code"])
    df = df[(df["humidity"] >= 0) & (df["humidity"] <= 100) & (df["pressure"] > 0) & (df["wind_speed"] >= 0)]

    df = df.assign(
        humidity=df["humidity"].round().astype(int),
        weather_code=df["weather_code"].astype(int),
        city=location["name"],
        country=location["country"],
        latitude=location["latitude"],
        longitude=location["longitude"],
        source="backfill",
    )
    return df[COLUMNS], total - len(df)


def insert_rows(conn, df: pd.DataFrame) -> int:
    """Bulk insert in one transaction. Returns how many rows were actually new."""
    rows = df.astype(object).values.tolist()
    with conn:   # commit on success, roll back on error
        with conn.cursor() as cur:
            inserted = execute_values(cur, INSERT_SQL, rows, page_size=2000, fetch=True)
    return len(inserted)


def summary(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT city, count(*), min(observation_time)::date, max(observation_time)::date
            FROM weather_history WHERE source = 'backfill'
            GROUP BY city ORDER BY city""")
        print("\nweather_history (backfill rows):")
        for city, n, first, last in cur.fetchall():
            print(f"  {city:<16} {n:>7,} rows   {first} -> {last}")
        cur.execute("SELECT count(*), pg_size_pretty(pg_total_relation_size('weather_history')) FROM weather_history")
        total, size = cur.fetchone()
        print(f"\nTotal rows in weather_history: {total:,}   (table + indexes: {size})")


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill weather_history from Open-Meteo's archive API")
    parser.add_argument("--days", type=int, default=365, help="how many days of history (default 365)")
    parser.add_argument("--cities", type=str, default=",".join(DEFAULT_CITIES), help="comma-separated city names")
    parser.add_argument("--dry-run", action="store_true", help="fetch and validate only, write nothing")
    args = parser.parse_args()

    end = date.today() - timedelta(days=ARCHIVE_LAG_DAYS)
    start = end - timedelta(days=args.days - 1)
    cities = [c.strip() for c in args.cities.split(",") if c.strip()]
    print(f"Backfilling {len(cities)} cities, {start} -> {end} ({args.days} days, hourly)"
          f"{'  [DRY RUN]' if args.dry_run else ''}\n")

    conn = None if args.dry_run else get_connection()
    failed = []
    try:
        for i, name in enumerate(cities):
            if i:
                time.sleep(PAUSE_BETWEEN_CITIES)
            try:
                location = geocode_city(name)
                hourly = fetch_hourly(location, start, end)
                df, rejected = to_frame(location, hourly)
                if args.dry_run:
                    print(f"[{location['name']}] OK (dry run): {len(df):,} valid rows, {rejected} rejected")
                    continue
                new = insert_rows(conn, df)
                print(f"[{location['name']}] {len(df):,} valid rows, {rejected} rejected, "
                      f"{new:,} new, {len(df) - new:,} already stored")
            except WeatherAPIError as e:
                print(f"[{name}] FAILED: {e}")
                failed.append(name)
        if conn:
            summary(conn)
    finally:
        if conn:
            conn.close()

    if failed:
        print(f"\nFailed cities (run again to retry just these): {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
