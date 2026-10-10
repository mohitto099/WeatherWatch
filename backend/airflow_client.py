"""
airflow_client.py
-----------------
Thin wrapper around Airflow 3's REST API (/api/v2).

Airflow 3 uses JWT auth: POST /auth/token with username/password returns an
access token that is then sent as "Authorization: Bearer <token>".
The token is cached and refreshed automatically if Airflow rejects it (401).
"""

import os
import uuid

import requests

BASE_URL = os.getenv("AIRFLOW_BASE_URL", "http://localhost:8080").rstrip("/")
USERNAME = os.getenv("AIRFLOW_USERNAME", "airflow")
PASSWORD = os.getenv("AIRFLOW_PASSWORD", "airflow")
DAG_ID = os.getenv("AIRFLOW_DAG_ID", "weather_watch_dag")

_token: str | None = None


class AirflowError(Exception):
    """Airflow is unreachable or returned an unexpected response."""


class RunNotFound(AirflowError):
    """The requested DAG run does not exist."""


def _fetch_token() -> str:
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/token",
            json={"username": USERNAME, "password": PASSWORD},
            timeout=10,
        )
    except requests.RequestException as e:
        raise AirflowError(f"Cannot reach Airflow at {BASE_URL}: {e}")

    if resp.status_code not in (200, 201):
        raise AirflowError(f"Airflow login failed (HTTP {resp.status_code}) - check AIRFLOW_USERNAME/PASSWORD")
    return resp.json()["access_token"]


def _request(method: str, path: str, **kwargs) -> requests.Response:
    global _token
    for attempt in (1, 2):
        if _token is None or attempt == 2:
            _token = _fetch_token()
        try:
            resp = requests.request(
                method,
                f"{BASE_URL}/api/v2{path}",
                headers={"Authorization": f"Bearer {_token}"},
                timeout=10,
                **kwargs,
            )
        except requests.RequestException as e:
            raise AirflowError(f"Cannot reach Airflow at {BASE_URL}: {e}")
        if resp.status_code == 401 and attempt == 1:
            continue  # token expired - refresh once and retry
        return resp
    return resp


def trigger_dag_run(city: str) -> str:
    """Start the pipeline for `city`. Returns the new run id immediately (does not wait)."""
    run_id = f"ww_{uuid.uuid4().hex[:12]}"
    resp = _request(
        "POST",
        f"/dags/{DAG_ID}/dagRuns",
        json={"dag_run_id": run_id, "logical_date": None, "conf": {"city": city}},
    )
    if resp.status_code == 404:
        raise AirflowError(f"DAG '{DAG_ID}' not found in Airflow")
    if resp.status_code not in (200, 201):
        raise AirflowError(f"Could not trigger DAG (HTTP {resp.status_code}): {resp.text[:200]}")
    return resp.json().get("dag_run_id", run_id)


def get_dag_run(run_id: str) -> dict:
    resp = _request("GET", f"/dags/{DAG_ID}/dagRuns/{run_id}")
    if resp.status_code == 404:
        raise RunNotFound(run_id)
    if resp.status_code != 200:
        raise AirflowError(f"Could not read DAG run (HTTP {resp.status_code})")
    return resp.json()


def get_task_instances(run_id: str) -> list[dict]:
    resp = _request("GET", f"/dags/{DAG_ID}/dagRuns/{run_id}/taskInstances")
    if resp.status_code == 404:
        raise RunNotFound(run_id)
    if resp.status_code != 200:
        raise AirflowError(f"Could not read task instances (HTTP {resp.status_code})")
    return resp.json().get("task_instances", [])
