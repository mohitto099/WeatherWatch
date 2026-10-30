"""
airflow_client.py
-----------------
In-process pipeline runner replacing the external Airflow server.
Executes the ETL tasks (extract_validate -> transform_quality_check -> load -> log_result)
in a background thread while keeping the exact same function signatures
(trigger_dag_run, get_dag_run, get_task_instances) and task_id names
expected by backend/status.py and backend/main.py.
"""

import sys
import threading
import time
import uuid
from pathlib import Path

# Ensure repo root and pipeline directories are on sys.path
_repo_root = Path(__file__).resolve().parent.parent
_pipeline_dir = _repo_root / "pipeline"
for _path in [str(_repo_root), str(_pipeline_dir)]:
    if _path not in sys.path:
        sys.path.insert(0, _path)

try:
    from pipeline.extract import extract, WeatherAPIError
    from pipeline.transform import transform, DataQualityError
    from pipeline.load import load
except ImportError:
    from extract import extract, WeatherAPIError
    from transform import transform, DataQualityError
    from load import load


class AirflowError(Exception):
    """Pipeline execution error or unexpected failure."""


class RunNotFound(AirflowError):
    """The requested DAG run does not exist."""


_lock = threading.Lock()
_runs: dict[str, dict] = {}

TASK_IDS = [
    "extract_validate",
    "transform_quality_check",
    "load",
    "log_result",
]


def _execute_pipeline(run_id: str, city: str) -> None:
    """Executes the 4 pipeline tasks sequentially in a background thread."""

    def _set_task(task_id: str, state: str) -> None:
        with _lock:
            if run_id in _runs:
                _runs[run_id]["tasks"][task_id] = state

    def _fail_from(failed_task_id: str, error_msg: str) -> None:
        with _lock:
            if run_id not in _runs:
                return
            tasks = _runs[run_id]["tasks"]
            failed_seen = False
            for tid in TASK_IDS:
                if tid == failed_task_id:
                    tasks[tid] = "failed"
                    failed_seen = True
                elif failed_seen:
                    tasks[tid] = "upstream_failed"
            _runs[run_id]["state"] = "failed"
            _runs[run_id]["error"] = error_msg

    try:
        # Task 1: extract_validate
        _set_task("extract_validate", "running")
        try:
            extracted = extract(city)
        except Exception as e:
            _fail_from("extract_validate", str(e))
            return
        _set_task("extract_validate", "success")
        time.sleep(0.5)

        # Task 2: transform_quality_check
        _set_task("transform_quality_check", "running")
        time.sleep(0.5)
        try:
            record = transform(extracted)
        except Exception as e:
            _fail_from("transform_quality_check", str(e))
            return
        _set_task("transform_quality_check", "success")
        time.sleep(0.5)

        # Task 3: load
        _set_task("load", "running")
        try:
            row_id = load(record)
        except Exception as e:
            _fail_from("load", str(e))
            return
        _set_task("load", "success")
        time.sleep(0.5)

        # Task 4: log_result
        _set_task("log_result", "running")
        time.sleep(0.4)
        outcome = (
            f"new observation stored (id: {row_id})"
            if row_id
            else "same observation as before, current record refreshed"
        )
        print(f"[log_result] PIPELINE SUCCEEDED for '{city}': {outcome}")
        _set_task("log_result", "success")

        with _lock:
            if run_id in _runs:
                _runs[run_id]["state"] = "success"

    except Exception as e:
        print(f"[PIPELINE FAILURE] Unexpected error in run '{run_id}' for '{city}': {e}")
        with _lock:
            if run_id in _runs:
                _runs[run_id]["state"] = "failed"
                _runs[run_id]["error"] = str(e)


def trigger_dag_run(city: str) -> str:
    """Start the pipeline for `city`. Returns the new run id immediately (does not wait)."""
    run_id = f"ww_{uuid.uuid4().hex[:12]}"
    with _lock:
        _runs[run_id] = {
            "dag_run_id": run_id,
            "city": city,
            "state": "running",
            "tasks": {
                "extract_validate": "running",
                "transform_quality_check": "none",
                "load": "none",
                "log_result": "none",
            },
            "error": None,
        }
        # Keep _runs within reasonable bounds
        if len(_runs) > 200:
            oldest = next(iter(_runs))
            del _runs[oldest]

    thread = threading.Thread(target=_execute_pipeline, args=(run_id, city), daemon=True)
    thread.start()
    return run_id


def get_dag_run(run_id: str) -> dict:
    with _lock:
        run = _runs.get(run_id)
        if not run:
            raise RunNotFound(run_id)
        return {
            "dag_run_id": run_id,
            "state": run["state"],
            "conf": {"city": run["city"]},
        }


def get_task_instances(run_id: str) -> list[dict]:
    with _lock:
        run = _runs.get(run_id)
        if not run:
            raise RunNotFound(run_id)
        return [
            {"task_id": tid, "state": state}
            for tid, state in run["tasks"].items()
        ]
