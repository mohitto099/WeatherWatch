"""
run_pipeline.py
---------------
Phase 1 standalone runner. This is NOT Airflow yet - it's the same logic
Airflow will later orchestrate as a 4-task DAG:

    extract_validate  ->  transform_quality_check  ->  load  ->  log_result

Running this file end-to-end proves the core ETL + data quality logic works
against the real Open-Meteo API and a real Supabase Postgres table, before
we add any orchestration layer on top.

Usage:
    python run_pipeline.py "Mumbai"
    python run_pipeline.py "Mumbai" "London" "Tokyo"
"""

import sys
from datetime import datetime

from extract import extract, WeatherAPIError
from transform import transform, DataQualityError
from load import load


def run_for_city(city: str) -> dict:
    """Runs one full pipeline pass for a single city. Returns a result summary."""
    result = {"city": city, "status": "failed", "detail": None, "row_id": None}

    try:
        # Task 1: extract + validate
        raw = extract(city)

        # Task 2: transform + quality check
        clean = transform(raw)

        # Task 3: load
        row_id = load(clean)

        # Task 4: log result (here, just printed - Airflow will capture this
        # in its own task logs later)
        result["status"] = "success" if row_id else "duplicate_skipped"
        result["row_id"] = row_id
        result["detail"] = clean

    except WeatherAPIError as e:
        result["detail"] = f"Extraction/validation failed: {e}"
    except DataQualityError as e:
        result["detail"] = f"Data quality check failed: {e}"
    except Exception as e:
        result["detail"] = f"Unexpected error: {e}"

    return result


def main():
    cities = sys.argv[1:] or ["Mumbai"]
    print(f"--- WeatherWatch pipeline run: {datetime.now().isoformat()} ---\n")

    for city in cities:
        print(f"[{city}] running pipeline...")
        result = run_for_city(city)

        if result["status"] == "success":
            print(f"[{city}] OK - new history row id {result['row_id']}")
        elif result["status"] == "duplicate_skipped":
            print(f"[{city}] REFRESHED - observation already in history, current_weather updated")
        else:
            print(f"[{city}] FAILED - {result['detail']}")
        print()


if __name__ == "__main__":
    main()
