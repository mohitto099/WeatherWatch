"""
db.py
-----
Read-only access to weather_observations for the API.
(Writing is done only by the Airflow pipeline - the API never inserts.)
"""

import os
from contextlib import contextmanager

import psycopg2

COLUMNS = [
    "city", "country", "latitude", "longitude", "temperature", "humidity",
    "pressure", "wind_speed", "weather_code", "observation_time", "fetched_at",
]
_SELECT = f"SELECT {', '.join(COLUMNS)} FROM weather_observations"

# WMO weather codes used by Open-Meteo -> readable text
WMO = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Freezing fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    56: "Freezing drizzle", 57: "Heavy freezing drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    66: "Freezing rain", 67: "Heavy freezing rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Light rain showers", 81: "Rain showers", 82: "Violent rain showers",
    85: "Light snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Severe thunderstorm with hail",
}


@contextmanager
def _cursor():
    url = os.getenv("SUPABASE_DB_URL")
    if not url:
        raise RuntimeError("SUPABASE_DB_URL not set - check backend/.env")
    conn = psycopg2.connect(url)
    try:
        with conn.cursor() as cur:
            yield cur
    finally:
        conn.close()


def _to_dict(row) -> dict:
    record = dict(zip(COLUMNS, row))
    record["condition"] = WMO.get(record["weather_code"], "Unknown")
    return record


def get_fresh_record(city: str, max_age_minutes: int) -> dict | None:
    """Newest record for `city` fetched within the last `max_age_minutes`, else None."""
    with _cursor() as cur:
        cur.execute(
            _SELECT + """
            WHERE lower(city) = lower(%s)
              AND fetched_at > NOW() - make_interval(mins => %s)
            ORDER BY fetched_at DESC LIMIT 1""",
            (city, max_age_minutes),
        )
        row = cur.fetchone()
        return _to_dict(row) if row else None


def get_latest_record(city: str) -> dict | None:
    """Newest stored record for `city`, regardless of age."""
    with _cursor() as cur:
        cur.execute(
            _SELECT + " WHERE lower(city) = lower(%s) ORDER BY observation_time DESC LIMIT 1",
            (city,),
        )
        row = cur.fetchone()
        return _to_dict(row) if row else None
