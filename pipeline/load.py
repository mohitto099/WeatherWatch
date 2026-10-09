"""
load.py
-------
Stage 3 of the pipeline: LOAD.

Responsibilities:
- Connect to Supabase PostgreSQL using the connection string in .env
- Insert the clean record, relying on the UNIQUE(city, observation_time)
  constraint to silently avoid duplicate rows (ON CONFLICT DO NOTHING)
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

INSERT_SQL = """
    INSERT INTO weather_observations
        (city, country, latitude, longitude, temperature, humidity,
         pressure, wind_speed, weather_code, observation_time, source)
    VALUES
        (%(city)s, %(country)s, %(latitude)s, %(longitude)s, %(temperature)s,
         %(humidity)s, %(pressure)s, %(wind_speed)s, %(weather_code)s,
         %(observation_time)s, %(source)s)
    ON CONFLICT (city, observation_time) DO NOTHING
    RETURNING id;
"""

FETCH_FRESH_SQL = """
    SELECT city, country, latitude, longitude, temperature, humidity,
           pressure, wind_speed, weather_code, observation_time, fetched_at
    FROM weather_observations
    WHERE city = %(city)s
      AND fetched_at > NOW() - INTERVAL '15 minutes'
    ORDER BY fetched_at DESC
    LIMIT 1;
"""


def get_connection():
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise RuntimeError("SUPABASE_DB_URL not set - check your .env file")
    return psycopg2.connect(db_url)


def load(record: dict) -> int | None:
    """Insert one record. Returns the new row's id, or None if it was a duplicate."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(INSERT_SQL, record)
            result = cur.fetchone()
            conn.commit()
            return result[0] if result else None


def get_fresh_cached_record(city: str) -> dict | None:
    """
    Used by the FastAPI caching layer: returns a record for `city` if one was
    fetched in the last 15 minutes, else None. Keeps the cache rule in one place.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(FETCH_FRESH_SQL, {"city": city})
            row = cur.fetchone()
            if not row:
                return None
            columns = [
                "city", "country", "latitude", "longitude", "temperature",
                "humidity", "pressure", "wind_speed", "weather_code",
                "observation_time", "fetched_at",
            ]
            return dict(zip(columns, row))


if __name__ == "__main__":
    # Quick manual test: python load.py
    from extract import extract
    from transform import transform

    raw = extract("Mumbai")
    clean = transform(raw)
    new_id = load(clean)
    print(f"Inserted row id: {new_id}" if new_id else "Duplicate - skipped")
