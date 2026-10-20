-- Run these in the Supabase SQL Editor to inspect weather_history.
-- The editor shows only the last result, so select ONE statement and click Run each time.

-- 1) Rows per city and source, with the date range covered
SELECT city, source, count(*) AS row_count,
       min(observation_time)::date AS first_day, max(observation_time)::date AS last_day
FROM weather_history
GROUP BY city, source
ORDER BY city, source;

-- 2) How much of your 500 MB free quota the history uses
SELECT pg_size_pretty(pg_total_relation_size('weather_history')) AS history_table_with_indexes,
       pg_size_pretty(pg_database_size(current_database()))      AS whole_database;
