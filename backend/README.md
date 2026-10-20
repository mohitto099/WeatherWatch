# WeatherWatch - Phase 3: FastAPI backend

Runs on your machine (not in Docker) and talks to:
- Supabase PostgreSQL (read-only: freshness cache + latest record)
- Airflow in Docker at http://localhost:8080 (trigger the DAG, read run status)

## Endpoints
| Endpoint | What it does |
|---|---|
| `GET /api/weather?city=X` | Fresh record (< 15 min) -> `{"status":"cached","data":{...}}`. Otherwise triggers the Airflow DAG and returns `{"status":"triggered","run_id":"..."}` immediately. |
| `GET /api/pipeline/status/{run_id}` | Live stage: `queued` / `running` / `done` / `failed`, the current stage, and a 4-step `stages` list for the React step tracker. |
| `GET /api/weather/latest?city=X` | Newest stored record. Call it once status is `done`. |
| `GET /api/weather/recent?limit=8` | Cities anyone searched recently, newest first (the cards under the search box). |
| `GET /health` | Liveness check. |

## Setup (PowerShell, from this `backend` folder)

    python -m venv venv
    venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    Copy-Item .env.example .env
    notepad .env        # paste the same Supabase Session pooler URI you use in airflow\dags\.env

Make sure Docker Desktop is running and Airflow is up (`docker compose ps` in the `airflow` folder).

## Run

    python -m uvicorn main:app --reload --port 8000

Open http://localhost:8000/docs - an interactive page to try every endpoint.

## Try it
1. `GET /api/weather` with a city you have NOT loaded recently (e.g. `Paris`) -> `"status": "triggered"` + a `run_id`.
2. `GET /api/pipeline/status/{run_id}` with that run_id. Press Execute every second or two and watch the stages move.
3. When status is `done`: `GET /api/weather/latest?city=Paris` returns the record.
4. `GET /api/weather?city=Paris` again -> `"status": "cached"` instantly (no pipeline run).

## Notes
- Airflow login defaults to airflow/airflow. Change `AIRFLOW_USERNAME` / `AIRFLOW_PASSWORD` in `.env` if you changed it.
