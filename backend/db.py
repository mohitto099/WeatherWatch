"""
db.py
-----
Read-only access to current_weather (one row per city) for the API.
(Writing is done only by the Airflow pipeline - the API never inserts.)
"""

import os
from contextlib import contextmanager

import psycopg2

COLUMNS = [
    "city", "country", "latitude", "longitude", "temperature", "humidity",
    "pressure", "wind_speed", "weather_code", "observation_time", "fetched_at",
]
_SELECT = f"SELECT {', '.join(COLUMNS)} FROM current_weather"

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
    """The stored current record for `city`, regardless of age."""
    with _cursor() as cur:
        cur.execute(
            _SELECT + " WHERE lower(city) = lower(%s) LIMIT 1",
            (city,),
        )
        row = cur.fetchone()
        return _to_dict(row) if row else None


def list_recent(limit: int) -> list[dict]:
    """The most recently refreshed cities (one row each), newest first. Shared by all users."""
    with _cursor() as cur:
        cur.execute(_SELECT + " ORDER BY fetched_at DESC LIMIT %s", (limit,))
        return [_to_dict(row) for row in cur.fetchall()]


ANALYTICS_COLUMNS = [
    "city", "observations", "avg_temp", "min_temp", "max_temp", "avg_humidity", "avg_pressure",
    "avg_wind_speed", "max_wind_speed", "rainy_hours", "rainy_pct",
]


def get_analytics(window: str) -> dict | None:
    """All analysed cities for one window (1W/1M/6M/1Y), hottest first. None until the Spark job has run."""
    with _cursor() as cur:
        cur.execute(
            f"""SELECT {', '.join(ANALYTICS_COLUMNS)}, window_start, window_end, computed_at
                FROM weather_analytics WHERE window_label = %s ORDER BY avg_temp DESC""",
            (window,),
        )
        rows = cur.fetchall()
    if not rows:
        return None
    n = len(ANALYTICS_COLUMNS)
    first = rows[0]
    return {
        "window": window,
        "window_start": first[n],
        "window_end": first[n + 1],
        "computed_at": first[n + 2],
        "cities": [dict(zip(ANALYTICS_COLUMNS, r[:n])) for r in rows],
    }


def get_trend(city: str, days: int) -> list[dict]:
    """Daily average temperature (+ rolling 7-day average) for the last `days` days of the city's data."""
    with _cursor() as cur:
        cur.execute(
            """SELECT day, avg_temp, rolling_7d_avg_temp FROM weather_daily_trend
               WHERE lower(city) = lower(%s)
                 AND day > (SELECT max(day) FROM weather_daily_trend WHERE lower(city) = lower(%s)) - %s
               ORDER BY day""",
            (city, city, days),
        )
        return [{"day": d, "avg_temp": a, "rolling_7d_avg_temp": r} for d, a, r in cur.fetchall()]
