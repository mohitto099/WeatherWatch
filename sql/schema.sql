-- WeatherWatch: core table for storing weather observations
-- Run this once against your Supabase PostgreSQL database (SQL Editor or psql)

CREATE TABLE IF NOT EXISTS weather_observations (
    id                  SERIAL PRIMARY KEY,
    city                VARCHAR(100) NOT NULL,
    country             VARCHAR(100),
    latitude            DOUBLE PRECISION,
    longitude           DOUBLE PRECISION,
    temperature         DOUBLE PRECISION NOT NULL,   -- Celsius
    humidity            INTEGER NOT NULL,            -- percent, 0-100
    pressure            DOUBLE PRECISION,             -- hPa
    wind_speed          DOUBLE PRECISION NOT NULL,    -- km/h
    weather_code        INTEGER,                      -- Open-Meteo WMO weather code
    observation_time    TIMESTAMP NOT NULL,            -- when the reading is FOR
    fetched_at          TIMESTAMP NOT NULL DEFAULT NOW(), -- when WE pulled it
    source              VARCHAR(20) NOT NULL DEFAULT 'live', -- 'live' or 'backfill'

    -- Prevents duplicate rows for the same city + timestamp
    CONSTRAINT uq_city_time UNIQUE (city, observation_time)
);

-- Speeds up "give me history for city X" queries used by Spark later
CREATE INDEX IF NOT EXISTS idx_weather_city_time
    ON weather_observations (city, observation_time DESC);
