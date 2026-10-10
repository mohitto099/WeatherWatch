# WeatherWatch - Phase 4: React frontend

City search, a live 4-step pipeline tracker, and a weather card.

## Needs
- Node.js 20.19+ or 22.12+  (check: `node --version`)
- Backend running at http://localhost:8000  (Phase 3)
- Airflow running in Docker  (Phase 2)

## Run (PowerShell, from this `frontend` folder)

    npm install
    npm run dev

Open http://localhost:5173

## What you'll see
- Search a city you haven't loaded recently -> the tracker lights up stage by stage
  (Fetching -> Cleaning -> Saving -> Finalizing), then the weather card appears with a
  "Fresh from pipeline" badge and how long the run took.
- Search the same city again within 15 minutes -> instant result with a
  "Served from cache" badge. No pipeline run.
- Search a nonsense city -> the tracker stops at the failed stage and shows an error.

## Notes
- Backend at a different address? Copy `.env.example` to `.env` and edit `VITE_API_URL`.
- While a pipeline is running the search button is disabled, so one city is processed at a time.
