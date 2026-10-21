"""
analytics_job.py - WeatherWatch historical analytics with Apache Spark
----------------------------------------------------------------------
Reads weather_history from Supabase PostgreSQL (JDBC), computes statistics over
1-week / 1-month / 6-month / 1-year windows, and writes the results back to two
small tables that the API serves:

    weather_analytics    one row per city per window (averages, min/max, rain share ...)
    weather_daily_trend  daily average temperature + a rolling 7-day average per city

Three Spark APIs are used on purpose:
    DataFrame API   windowed aggregations (groupBy / agg)
    Spark SQL       a window function (rolling average, ranking)
    RDD API         map / filter / reduceByKey, cross-checked against the DataFrame result

Windows end at the latest timestamp covered by EVERY analysed city, so all cities are
compared over exactly the same period (the archive runs a few days behind real time).
A city needs at least MIN_ROWS observations to be analysed.

Run:  docker compose run --rm spark-job        (from the spark folder)
"""

import os
import sys
from datetime import timedelta
from functools import reduce
from urllib.parse import parse_qs, unquote, urlparse

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

WINDOWS = [("1W", 7), ("1M", 30), ("6M", 182), ("1Y", 365)]
MIN_ROWS = 24 * 30   # about a month of hourly data


def jdbc_settings():
    """Turn SUPABASE_DB_URL (postgresql://user:pass@host:port/db) into what Spark's JDBC reader needs."""
    raw = os.getenv("SUPABASE_DB_URL")
    if not raw:
        sys.exit("SUPABASE_DB_URL is not set. Check the env_file path in docker-compose.yml.")
    u = urlparse(raw)
    sslmode = parse_qs(u.query).get("sslmode", ["require"])[0]
    url = f"jdbc:postgresql://{u.hostname}:{u.port or 5432}{u.path or '/postgres'}?sslmode={sslmode}"
    return url, unquote(u.username or ""), unquote(u.password or "")


def read_query(spark, jdbc, query):
    url, user, password = jdbc
    return (spark.read.format("jdbc")
            .option("url", url).option("user", user).option("password", password)
            .option("driver", "org.postgresql.Driver")
            .option("query", query).option("fetchsize", "10000").load())


def write_table(df, jdbc, table):
    """Empty the table and refill it (TRUNCATE keeps the table definition and its security settings)."""
    url, user, password = jdbc
    (df.write.format("jdbc")
        .option("url", url).option("user", user).option("password", password)
        .option("driver", "org.postgresql.Driver")
        .option("dbtable", table).option("truncate", "true")
        .mode("overwrite").save())


def banner(text):
    print(f"\n{'=' * 78}\n{text}\n{'=' * 78}")


def main():
    spark = (SparkSession.builder.appName("WeatherWatch-analytics")
             .config("spark.sql.session.timeZone", "UTC")
             .config("spark.sql.shuffle.partitions", "8")
             .getOrCreate())
    spark.sparkContext.setLogLevel("WARN")
    jdbc = jdbc_settings()

    # ---------------------------------------------------------------- 1. read
    banner("1/5  Reading weather_history from Supabase over JDBC")
    hist = read_query(spark, jdbc, """
        SELECT city, observation_time, temperature, humidity, pressure, wind_speed, weather_code
        FROM weather_history""").cache()
    print(f"rows read: {hist.count():,}")

    per_city = hist.groupBy("city").agg(F.count("*").alias("n"), F.max("observation_time").alias("last_obs"))
    eligible = per_city.filter(F.col("n") >= MIN_ROWS).cache()
    skipped = [r["city"] for r in per_city.filter(F.col("n") < MIN_ROWS).collect()]
    if eligible.count() == 0:
        sys.exit("No city has enough history yet. Run pipeline/backfill_history.py first.")
    if skipped:
        print(f"skipped (fewer than {MIN_ROWS} observations): {', '.join(sorted(skipped))}")

    anchor = eligible.agg(F.min("last_obs")).first()[0]
    print(f"analysed cities: {eligible.count()}   windows end at: {anchor}")
    hist = hist.join(F.broadcast(eligible.select("city")), "city")

    # ---------------------------------------------------------------- 2. DataFrame windows
    banner("2/5  DataFrame API: 1W / 1M / 6M / 1Y window aggregations")
    code = F.col("weather_code")
    is_rainy = ((code >= 51) & (code <= 67)) | ((code >= 80) & (code <= 82)) | (code >= 95)

    frames = []
    for label, days in WINDOWS:
        start = anchor - timedelta(days=days)
        agg = (hist.filter((F.col("observation_time") > F.lit(start)) & (F.col("observation_time") <= F.lit(anchor)))
               .groupBy("city")
               .agg(F.count("*").alias("observations"),
                    F.round(F.avg("temperature"), 2).alias("avg_temp"),
                    F.round(F.min("temperature"), 1).alias("min_temp"),
                    F.round(F.max("temperature"), 1).alias("max_temp"),
                    F.round(F.avg("humidity"), 1).alias("avg_humidity"),
                    F.round(F.avg("pressure"), 1).alias("avg_pressure"),
                    F.round(F.avg("wind_speed"), 1).alias("avg_wind_speed"),
                    F.round(F.max("wind_speed"), 1).alias("max_wind_speed"),
                    F.sum(F.when(is_rainy, 1).otherwise(0)).alias("rainy_hours"))
               .withColumn("rainy_pct", F.round(F.col("rainy_hours") / F.col("observations") * 100, 1))
               .withColumn("window_label", F.lit(label))
               .withColumn("window_days", F.lit(days))
               .withColumn("window_start", F.lit(start))
               .withColumn("window_end", F.lit(anchor)))
        frames.append(agg)

    analytics = (reduce(DataFrame.unionByName, frames)
                 .withColumn("computed_at", F.current_timestamp())
                 .select("city", "window_label", "window_days", "window_start", "window_end", "observations",
                         "avg_temp", "min_temp", "max_temp", "avg_humidity", "avg_pressure",
                         "avg_wind_speed", "max_wind_speed", "rainy_hours", "rainy_pct", "computed_at")
                 .cache())
    analytics.filter("window_label = '1M'").select(
        "city", "observations", "avg_temp", "min_temp", "max_temp", "avg_humidity", "rainy_pct"
    ).orderBy(F.desc("avg_temp")).show(truncate=False)

    # ---------------------------------------------------------------- 3. Spark SQL window functions
    banner("3/5  Spark SQL: rolling 7-day average (window function) and city ranking")
    hist.createOrReplaceTempView("history")
    analytics.createOrReplaceTempView("analytics")
    year_start = (anchor - timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
    anchor_s = anchor.strftime("%Y-%m-%d %H:%M:%S")

    trend = spark.sql(f"""
        WITH daily AS (
            SELECT city, CAST(observation_time AS DATE) AS day, AVG(temperature) AS avg_temp
            FROM history
            WHERE observation_time > TIMESTAMP'{year_start}' AND observation_time <= TIMESTAMP'{anchor_s}'
            GROUP BY city, CAST(observation_time AS DATE)
        )
        SELECT city, day,
               ROUND(avg_temp, 2) AS avg_temp,
               ROUND(AVG(avg_temp) OVER (PARTITION BY city ORDER BY day
                                         ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS rolling_7d_avg_temp
        FROM daily
        ORDER BY city, day""").cache()
    print(f"daily trend rows: {trend.count():,}")

    print("Hottest and coldest city per window (RANK() OVER window):")
    spark.sql("""
        SELECT window_label, city, avg_temp,
               RANK() OVER (PARTITION BY window_label ORDER BY avg_temp DESC) AS hottest_rank,
               RANK() OVER (PARTITION BY window_label ORDER BY avg_temp ASC)  AS coldest_rank
        FROM analytics""").filter("hottest_rank = 1 OR coldest_rank = 1") \
        .orderBy("window_label", "hottest_rank").show(50, truncate=False)

    # ---------------------------------------------------------------- 4. RDD cross-check
    banner("4/5  RDD API: map / filter / reduceByKey, checked against the DataFrame result")
    month_start = anchor - timedelta(days=30)
    rdd = (hist.filter((F.col("observation_time") > F.lit(month_start)) & (F.col("observation_time") <= F.lit(anchor)))
           .select("city", "temperature").rdd)
    totals = (rdd.filter(lambda r: r["temperature"] is not None)               # filter
                 .map(lambda r: (r["city"], (r["temperature"], 1)))            # map -> (city, (sum, count))
                 .reduceByKey(lambda a, b: (a[0] + b[0], a[1] + b[1])))        # reduce per city
    rdd_avg = dict(totals.mapValues(lambda t: round(t[0] / t[1], 2)).collect())

    df_avg = {r["city"]: r["avg_temp"] for r in analytics.filter("window_label = '1M'").collect()}
    mismatches = {c: (rdd_avg.get(c), v) for c, v in df_avg.items() if abs(rdd_avg.get(c, 1e9) - v) > 0.011}
    for city in sorted(rdd_avg):
        print(f"  {city:<16} RDD avg {rdd_avg[city]:>6.2f}   DataFrame avg {df_avg[city]:>6.2f}")
    print("RDD result matches DataFrame result:", "YES" if not mismatches else f"NO {mismatches}")

    # ---------------------------------------------------------------- 5. write
    banner("5/5  Writing results back to Supabase")
    write_table(analytics, jdbc, "weather_analytics")
    write_table(trend, jdbc, "weather_daily_trend")
    print(f"weather_analytics:   {analytics.count()} rows")
    print(f"weather_daily_trend: {trend.count()} rows")
    print("\nDone. The app's analytics panel now shows these results.")
    spark.stop()


if __name__ == "__main__":
    main()
