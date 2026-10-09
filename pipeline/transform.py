"""
transform.py
------------
Stage 2 of the pipeline: TRANSFORM + DATA QUALITY CHECK (merged, per the
simplified 4-task DAG).

Responsibilities:
- Flatten the raw extract() output into a single clean record using Pandas
- Standardize timestamp, types, and field names to match weather_observations
- Run data quality checks (ranges, required fields, valid timestamp)

Raises DataQualityError if a record fails validation - the caller decides
whether to log-and-skip or stop the pipeline.
"""

from datetime import datetime
import pandas as pd


class DataQualityError(Exception):
    """Raised when a transformed record fails a data quality check."""
    pass


def transform(extracted: dict, source: str = "live") -> dict:
    """
    Turn extract.extract()'s output into a flat dict matching the
    weather_observations table schema.
    """
    location = extracted["location"]
    current = extracted["raw"]["current"]

    # A one-row DataFrame here is deliberate: it's overkill for a single record,
    # but it's the same transform shape we'll reuse for batch/backfill data,
    # where many rows come in at once and this becomes genuinely useful.
    df = pd.DataFrame([{
        "city": location["name"],
        "country": location["country"],
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "temperature": current["temperature_2m"],
        "humidity": current["relative_humidity_2m"],
        "pressure": current["surface_pressure"],
        "wind_speed": current["wind_speed_10m"],
        "weather_code": current["weather_code"],
        "observation_time": current["time"],
        "source": source,
    }])

    # Type casting / standardization
    df["observation_time"] = pd.to_datetime(df["observation_time"])
    df["humidity"] = df["humidity"].astype(int)
    df["weather_code"] = df["weather_code"].astype(int)

    # Drop rows missing anything critical (handles missing-value case generically)
    required = ["city", "temperature", "humidity", "wind_speed", "observation_time"]
    df = df.dropna(subset=required)

    if df.empty:
        raise DataQualityError("Record dropped: missing one or more required fields")

    record = df.iloc[0].to_dict()
    record["observation_time"] = record["observation_time"].to_pydatetime()

    _run_quality_checks(record)
    return record


def _run_quality_checks(record: dict) -> None:
    """Raises DataQualityError on the first failed check."""
    if not (0 <= record["humidity"] <= 100):
        raise DataQualityError(f"humidity out of range: {record['humidity']}")

    if record["pressure"] is not None and record["pressure"] <= 0:
        raise DataQualityError(f"pressure must be > 0, got {record['pressure']}")

    if record["wind_speed"] < 0:
        raise DataQualityError(f"wind_speed cannot be negative: {record['wind_speed']}")

    if not record["city"]:
        raise DataQualityError("city is required")


if __name__ == "__main__":
    # Quick manual test: python transform.py
    from extract import extract
    raw = extract("Mumbai")
    clean = transform(raw)
    print(clean)
