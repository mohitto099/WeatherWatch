-- WeatherWatch: tables that the Spark analytics job writes to.
-- Run ONCE in the Supabase SQL Editor before the first Spark run. Safe to run again.
-- Spark empties and refills them on every run (TRUNCATE + INSERT), so these definitions are kept.

-- One row per city per window (1W, 1M, 6M, 1Y)
CREATE TABLE IF NOT EXISTS weather_analytics (
    city             VARCHAR(100)     NOT NULL,
    window_label     VARCHAR(4)       NOT NULL,      -- '1W', '1M', '6M', '1Y'
    window_days      INTEGER          NOT NULL,
    window_start     TIMESTAMP        NOT NULL,
    window_end       TIMESTAMP        NOT NULL,
    observations     BIGINT           NOT NULL,
    avg_temp         DOUBLE PRECISION,
    min_temp         DOUBLE PRECISION,
    max_temp         DOUBLE PRECISION,
    avg_humidity     DOUBLE PRECISION,
    avg_pressure     DOUBLE PRECISION,
    avg_wind_speed   DOUBLE PRECISION,
    max_wind_speed   DOUBLE PRECISION,
    rainy_hours      BIGINT,
    rainy_pct        DOUBLE PRECISION,
    computed_at      TIMESTAMP        NOT NULL,
    PRIMARY KEY (city, window_label)
);

-- Daily average temperature per city, with a rolling 7-day average (a Spark window function)
CREATE TABLE IF NOT EXISTS weather_daily_trend (
    city                 VARCHAR(100)     NOT NULL,
    day                  DATE             NOT NULL,
    avg_temp             DOUBLE PRECISION NOT NULL,
    rolling_7d_avg_temp  DOUBLE PRECISION,
    PRIMARY KEY (city, day)
);

-- Same protection as the other tables: blocks anonymous access through Supabase's public REST API
-- (the app and the Spark job connect with the owner role, which is not affected).
ALTER TABLE weather_analytics   ENABLE ROW LEVEL SECURITY;
ALTER TABLE weather_daily_trend ENABLE ROW LEVEL SECURITY;
