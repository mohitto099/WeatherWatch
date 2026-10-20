# WeatherWatch - frontend (React + Vite)

City search, a live 4-step pipeline tracker, an animated weather card, and cards for recently searched cities.

## Needs
- Node.js 20.19+ or 22.12+  (check: `node --version`)
- Backend running at http://localhost:8000
- Airflow running in Docker

## Run (PowerShell, from this `frontend` folder)

    npm install
    npm run dev

Open http://localhost:5173

## What it shows
- **Animated background** that follows the weather of the city on screen: sun, moon and stars, drifting clouds,
  rain, snow, fog and thunderstorm flashes, with day/night from the city's local time.
- **A tip** for the current weather ("Thunderstorms in the area. Stay indoors...", "Sunny day. Great weather to plan a hike.").
- **Recently searched cities**: shared by everyone using the app. Click a card to load it
  (instant if under 15 minutes old, otherwise it refreshes through the pipeline).
- Live pipeline tracker, and a "Served from cache" / "Fresh from pipeline" badge with timing.
- Animations stop automatically for users who set "reduce motion" in their operating system.

## Notes
- The dev server forwards `/api` to FastAPI on port 8000 (see `vite.config.js`), so the browser only ever talks to one
  address. That is also what lets a cloudflared tunnel work with a single link.
- Backend at a different address? Copy `.env.example` to `.env` and set `VITE_API_URL`.
