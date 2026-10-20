"""
main.py - WeatherWatch API

GET /api/weather?city=X              cache hit  -> {"status": "cached", "data": {...}}
                                     cache miss -> triggers the Airflow DAG and returns
                                                   {"status": "triggered", "run_id": "..."} immediately
GET /api/pipeline/status/{run_id}    live stage of the running pipeline (React polls this)
GET /api/weather/latest?city=X       newest stored record (call once status is "done")
GET /api/weather/recent?limit=8      cities anyone searched recently, newest first
GET /health
"""

import os
import threading

from dotenv import load_dotenv

load_dotenv()  # must run before the modules below read their settings

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

import airflow_client as af  # noqa: E402
import db  # noqa: E402
from geo import canonical_city  # noqa: E402
from status import build_status  # noqa: E402

CACHE_MINUTES = int(os.getenv("CACHE_MINUTES", "15"))

app = FastAPI(title="WeatherWatch API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# city -> run_id of a pipeline run we started. Stops a double-click (or React
# dev-mode double request) from launching two pipelines for the same city.
_inflight: dict[str, str] = {}
_lock = threading.Lock()


def _clean_city(city: str) -> str:
    city = city.strip()
    if not city:
        raise HTTPException(status_code=400, detail="city must not be empty")
    return city


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/weather")
def get_weather(city: str = Query(..., max_length=100)):
    typed = _clean_city(city)
    city = canonical_city(typed)   # "Washington" -> "Washington, D.C." (the name the pipeline stores)

    try:
        cached = db.get_fresh_record(city, CACHE_MINUTES)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {e}")

    if cached:
        return {"status": "cached", "data": cached}

    key = city.lower()
    try:
        with _lock:
            existing = _inflight.get(key)
            if existing:
                try:
                    run = af.get_dag_run(existing)
                    if run["state"] in ("queued", "running"):
                        return {"status": "triggered", "run_id": existing, "city": city}
                except af.AirflowError:
                    pass  # stale entry - fall through and start a fresh run
            run_id = af.trigger_dag_run(typed)   # the pipeline geocodes the typed name itself
            _inflight[key] = run_id
    except af.AirflowError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {"status": "triggered", "run_id": run_id, "city": city}


@app.get("/api/pipeline/status/{run_id}")
def pipeline_status(run_id: str):
    try:
        run = af.get_dag_run(run_id)
        tasks = af.get_task_instances(run_id)
    except af.RunNotFound:
        raise HTTPException(status_code=404, detail="Unknown run_id")
    except af.AirflowError as e:
        raise HTTPException(status_code=502, detail=str(e))

    result = build_status(run["state"], tasks)
    result["run_id"] = run_id
    result["city"] = (run.get("conf") or {}).get("city")
    return result


@app.get("/api/weather/recent")
def recent_weather(limit: int = Query(8, ge=1, le=24)):
    """Cities anyone has searched recently, newest first (powers the cards under the search box)."""
    try:
        return {"data": db.list_recent(limit)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {e}")


@app.get("/api/weather/latest")
def latest_weather(city: str = Query(..., max_length=100)):
    city = canonical_city(_clean_city(city))
    try:
        record = db.get_latest_record(city)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {e}")
    if not record:
        raise HTTPException(status_code=404, detail=f"No stored weather for '{city}'")
    return {"data": record}
