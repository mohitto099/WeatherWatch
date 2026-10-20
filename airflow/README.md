# WeatherWatch - Phase 2: Airflow (Docker)

Runs the Phase 1 ETL as an on-demand Airflow 3 DAG:

    extract_validate -> transform_quality_check -> load -> log_result

`schedule=None`: it never runs on a timer, only when triggered.

## Setup (PowerShell, from this `airflow` folder)

1. Download the official compose file (Airflow 3.3.2):

       Invoke-WebRequest -Uri "https://airflow.apache.org/docs/apache-airflow/3.3.2/docker-compose.yaml" -OutFile docker-compose.yaml

2. (Optional) hide Airflow's sample DAGs so only yours shows:

       (Get-Content docker-compose.yaml) -replace "LOAD_EXAMPLES: 'true'", "LOAD_EXAMPLES: 'false'" | Set-Content docker-compose.yaml

3. Add your Supabase URL for the DAG:

       Copy-Item dags\.env.example dags\.env
       notepad dags\.env

4. Initialise, then start (first start takes several minutes):

       docker compose up airflow-init
       docker compose up -d

5. Wait until `docker compose ps` shows the services as healthy, then open
   http://localhost:8080  (login: airflow / airflow).

## Run the pipeline

1. Find `weather_watch_dag`, switch the pause toggle ON.
2. Click Trigger, enter a city (e.g. London), confirm.
3. Watch the 4 tasks turn green. Click a task -> Logs to see its output.
4. Check Supabase -> Table Editor -> current_weather (latest row per city) and weather_history (every observation).

## Useful commands

    docker compose ps                         # container health
    docker compose logs airflow-dag-processor # DAG import errors show up here
    docker compose down                       # stop (keeps data)
    docker compose down --volumes             # stop and wipe Airflow's database

## Notes
- `dags/weather_pipeline/` is a copy of the Phase 1 `pipeline/` modules. Airflow uses this copy.
- If the DAG cannot connect to Supabase, use the **Session pooler** connection string
  (Supabase -> Settings -> Database), because Docker on Windows is often IPv4-only.
