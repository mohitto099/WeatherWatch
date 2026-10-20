"""
weather_watch_dag.py
--------------------
WeatherWatch on-demand pipeline (Airflow 3.x).

    extract_validate  ->  transform_quality_check  ->  load  ->  log_result

- schedule=None  : the DAG NEVER runs on a timer. It only runs when triggered
                   (Airflow UI now, FastAPI via the REST API later).
- The city comes from the trigger payload:  {"conf": {"city": "Mumbai"}}
- Task ids below are what the FastAPI status endpoint will map to the
  user-facing stages ("Fetching...", "Cleaning...", "Saving...", "Done").
"""

from datetime import datetime, timedelta

from airflow.sdk import dag, task, Param

from weather_pipeline.extract import extract, WeatherAPIError
from weather_pipeline.transform import transform, DataQualityError
from weather_pipeline.load import load


def _json_safe(record: dict) -> dict:
    """Make a record safe to pass between tasks (XCom): numpy -> python, datetime -> ISO string."""
    clean = {}
    for key, value in record.items():
        if hasattr(value, "item"):          # numpy scalar -> plain python
            value = value.item()
        if isinstance(value, datetime):     # datetime -> string
            value = value.isoformat()
        clean[key] = value
    return clean


def _log_task_failure(context):
    """Runs when any task fails - leaves a clear line in the task log."""
    ti = context.get("task_instance")
    task_id = getattr(ti, "task_id", "unknown")
    print(f"[PIPELINE FAILURE] task '{task_id}' failed: {context.get('exception')}")


def _get_city(dag_run, params) -> str:
    """City from the trigger payload if present, else the default param."""
    conf = (dag_run.conf or {}) if dag_run else {}
    return conf.get("city") or params.get("city") or "Mumbai"


@dag(
    dag_id="weather_watch_dag",
    schedule=None,                      # on-demand only - NOT scheduled
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=3,
    params={"city": Param("Mumbai", type="string", description="City to fetch weather for")},
    default_args={"retries": 1, "retry_delay": timedelta(seconds=5), "on_failure_callback": _log_task_failure},
    tags=["weather-watch"],
)
def weather_watch_dag():

    @task(task_id="extract_validate")
    def extract_validate(dag_run=None, params=None):
        city = _get_city(dag_run, params)
        try:
            extracted = extract(city)
        except WeatherAPIError as e:
            # Re-raise as a plain error so Airflow marks the task failed with a clear message
            raise RuntimeError(f"Extract/validate failed for '{city}': {e}")
        print(f"[extract_validate] fetched weather for {city}")
        return extracted

    @task(task_id="transform_quality_check")
    def transform_quality_check(extracted: dict):
        try:
            record = transform(extracted)
        except DataQualityError as e:
            raise RuntimeError(f"Data quality check failed: {e}")
        print(f"[transform_quality_check] record passed all checks: {record['city']} {record['observation_time']}")
        return _json_safe(record)

    @task(task_id="load")
    def load_to_postgres(record: dict):
        record = dict(record)
        record["observation_time"] = datetime.fromisoformat(record["observation_time"])
        row_id = load(record)
        if row_id:
            print(f"[load] current_weather updated; added weather_history row {row_id}")
        else:
            print("[load] current_weather refreshed; this observation was already in weather_history")
        return {"row_id": row_id, "city": record["city"]}

    @task(task_id="log_result")
    def log_result(loaded: dict, dag_run=None, params=None):
        # Only reached if every upstream task succeeded. If any task fails, this task is
        # marked upstream_failed and the whole DAG run is marked failed (which is exactly
        # what the status endpoint needs to report). Failure details are logged by
        # _log_task_failure above.
        city = _get_city(dag_run, params)
        outcome = "new observation stored" if loaded.get("row_id") else "same observation as before, current record refreshed"
        print(f"[log_result] PIPELINE SUCCEEDED for '{city}': {outcome}")

    extracted = extract_validate()
    record = transform_quality_check(extracted)
    loaded = load_to_postgres(record)
    log_result(loaded)


weather_watch_dag()
