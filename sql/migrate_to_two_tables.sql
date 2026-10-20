-- WeatherWatch migration: weather_observations  ->  weather_history + current_weather
-- Run ONCE in the Supabase SQL Editor. Safe to run again (it skips what is already done).
-- Nothing is deleted: every existing row is kept in weather_history, and the newest
-- row per city is copied into current_weather.

-- 1) The old table becomes the history table (all rows, indexes and constraints are kept)
DO $$
BEGIN
    IF to_regclass('public.weather_observations') IS NOT NULL
       AND to_regclass('public.weather_history') IS NULL THEN
        ALTER TABLE weather_observations RENAME TO weather_history;
        ALTER INDEX IF EXISTS idx_weather_city_time RENAME TO idx_history_city_time;
        ALTER TABLE weather_history RENAME CONSTRAINT uq_city_time TO uq_history_city_time;
        ALTER SEQUENCE IF EXISTS weather_observations_id_seq RENAME TO weather_history_id_seq;
    END IF;
END $$;

-- 2) New table: exactly one row per city
CREATE TABLE IF NOT EXISTS current_weather (
    city              VARCHAR(100) PRIMARY KEY,
    country           VARCHAR(100),
    latitude          DOUBLE PRECISION,
    longitude         DOUBLE PRECISION,
    temperature       DOUBLE PRECISION NOT NULL,
    humidity          INTEGER NOT NULL,
    pressure          DOUBLE PRECISION,
    wind_speed        DOUBLE PRECISION NOT NULL,
    weather_code      INTEGER,
    observation_time  TIMESTAMP NOT NULL,
    fetched_at        TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 3) Fill it with the newest existing reading for each city
INSERT INTO current_weather
    (city, country, latitude, longitude, temperature, humidity, pressure,
     wind_speed, weather_code, observation_time, fetched_at)
SELECT DISTINCT ON (city)
     city, country, latitude, longitude, temperature, humidity, pressure,
     wind_speed, weather_code, observation_time, fetched_at
FROM weather_history
ORDER BY city, observation_time DESC
ON CONFLICT (city) DO NOTHING;

-- 4) Block anonymous access through Supabase's public REST API (the app is not affected)
ALTER TABLE current_weather ENABLE ROW LEVEL SECURITY;
ALTER TABLE weather_history ENABLE ROW LEVEL SECURITY;

-- 5) Check: one row per city in current_weather, everything kept in weather_history
SELECT 'current_weather' AS table_name, count(*) AS row_count FROM current_weather
UNION ALL
SELECT 'weather_history', count(*) FROM weather_history;
