-- WeatherWatch schema (two-table design). For a brand-new database.
-- Already have the old weather_observations table? Run migrate_to_two_tables.sql instead.

-- One row per city: the latest reading. The cache, the weather card and the
-- "previous searches" cards read from here. Overwritten on every pipeline run.
CREATE TABLE IF NOT EXISTS current_weather (
    city              VARCHAR(100) PRIMARY KEY,
    country           VARCHAR(100),
    latitude          DOUBLE PRECISION,
    longitude         DOUBLE PRECISION,
    temperature       DOUBLE PRECISION NOT NULL,   -- Celsius
    humidity          INTEGER NOT NULL,            -- percent, 0-100
    pressure          DOUBLE PRECISION,            -- hPa
    wind_speed        DOUBLE PRECISION NOT NULL,   -- km/h
    weather_code      INTEGER,                     -- Open-Meteo WMO weather code
    observation_time  TIMESTAMP NOT NULL,          -- when the reading is FOR
    fetched_at        TIMESTAMP NOT NULL DEFAULT NOW()  -- when WE last refreshed it (drives the 15-minute cache)
);

-- Append-only record of every observation. Spark reads from here.
CREATE TABLE IF NOT EXISTS weather_history (
    id                SERIAL PRIMARY KEY,
    city              VARCHAR(100) NOT NULL,
    country           VARCHAR(100),
    latitude          DOUBLE PRECISION,
    longitude         DOUBLE PRECISION,
    temperature       DOUBLE PRECISION NOT NULL,
    humidity          INTEGER NOT NULL,
    pressure          DOUBLE PRECISION,
    wind_speed        DOUBLE PRECISION NOT NULL,
    weather_code      INTEGER,
    observation_time  TIMESTAMP NOT NULL,
    fetched_at        TIMESTAMP NOT NULL DEFAULT NOW(),
    source            VARCHAR(20) NOT NULL DEFAULT 'live',   -- 'live' or 'backfill'
    CONSTRAINT uq_history_city_time UNIQUE (city, observation_time)
);

CREATE INDEX IF NOT EXISTS idx_history_city_time
    ON weather_history (city, observation_time DESC);

-- The app connects with the database owner role, which is not affected by RLS.
-- Enabling it (with no policies) blocks anonymous access through Supabase's public REST API.
ALTER TABLE current_weather ENABLE ROW LEVEL SECURITY;
ALTER TABLE weather_history ENABLE ROW LEVEL SECURITY;
