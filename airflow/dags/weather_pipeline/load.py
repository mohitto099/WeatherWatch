"""
load.py
-------
Stage 3 of the pipeline: LOAD (two-table design).

For every live observation, ONE transaction does two things:
  1. weather_history  : append the observation (duplicates are ignored, so history stays clean)
  2. current_weather  : upsert the single row for this city and refresh its fetched_at
                        (that timestamp drives the 15-minute cache)

If either statement fails, both are rolled back.

Returns the new weather_history row id, or None if that exact observation was
already in history. current_weather is refreshed in both cases.
"""

import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

HISTORY_INSERT_SQL = """
    INSERT INTO weather_history
        (city, country, latitude, longitude, temperature, humidity,
         pressure, wind_speed, weather_code, observation_time, source)
    VALUES
        (%(city)s, %(country)s, %(latitude)s, %(longitude)s, %(temperature)s,
         %(humidity)s, %(pressure)s, %(wind_speed)s, %(weather_code)s,
         %(observation_time)s, %(source)s)
    ON CONFLICT (city, observation_time) DO NOTHING
    RETURNING id;
"""

# The WHERE clause stops an older observation from overwriting a newer one.
# "<=" (not "<") lets a repeat of the same observation still refresh fetched_at.
CURRENT_UPSERT_SQL = """
    INSERT INTO current_weather
        (city, country, latitude, longitude, temperature, humidity,
         pressure, wind_speed, weather_code, observation_time, fetched_at)
    VALUES
        (%(city)s, %(country)s, %(latitude)s, %(longitude)s, %(temperature)s,
         %(humidity)s, %(pressure)s, %(wind_speed)s, %(weather_code)s,
         %(observation_time)s, NOW())
    ON CONFLICT (city) DO UPDATE SET
        country          = EXCLUDED.country,
        latitude         = EXCLUDED.latitude,
        longitude        = EXCLUDED.longitude,
        temperature      = EXCLUDED.temperature,
        humidity         = EXCLUDED.humidity,
        pressure         = EXCLUDED.pressure,
        wind_speed       = EXCLUDED.wind_speed,
        weather_code     = EXCLUDED.weather_code,
        observation_time = EXCLUDED.observation_time,
        fetched_at       = NOW()
    WHERE current_weather.observation_time <= EXCLUDED.observation_time;
"""


def get_connection():
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise RuntimeError("SUPABASE_DB_URL not set - check your .env file")
    return psycopg2.connect(db_url)


def load(record: dict) -> int | None:
    """Write one clean record to weather_history and current_weather in a single transaction."""
    conn = get_connection()
    try:
        with conn:  # commits if the block succeeds, rolls back if anything raises
            with conn.cursor() as cur:
                cur.execute(HISTORY_INSERT_SQL, record)
                row = cur.fetchone()

                # Only live readings define "current weather" (a future backfill must not overwrite it)
                if record.get("source", "live") == "live":
                    cur.execute(CURRENT_UPSERT_SQL, record)

                return row[0] if row else None
    finally:
        conn.close()


if __name__ == "__main__":
    # Quick manual test: python load.py
    from extract import extract
    from transform import transform

    clean = transform(extract("Mumbai"))
    new_id = load(clean)
    print(f"New history row id: {new_id}" if new_id else "Already in history - current_weather refreshed")
