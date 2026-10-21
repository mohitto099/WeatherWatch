import { useEffect, useState } from "react";
import AnalyticsPanel from "./components/AnalyticsPanel.jsx";
import RecentCities from "./components/RecentCities.jsx";
import SearchBar from "./components/SearchBar.jsx";
import StepTracker from "./components/StepTracker.jsx";
import WeatherBackground from "./components/WeatherBackground.jsx";
import WeatherCard from "./components/WeatherCard.jsx";
import { useRecent } from "./useRecent.js";
import { usePipeline } from "./usePipeline.js";
import { isNightAt, sceneKind } from "./weatherUtils.js";

const IDLE_SCENE = { kind: "idle", night: false };

export default function App() {
  const { phase, city, stages, message, data, source, elapsedMs, error, search } = usePipeline();
  const recent = useRecent(phase === "done" ? `${data?.city}:${data?.fetched_at}` : "");
  const busy = phase === "loading" || phase === "running";

  // The background follows the weather of the city on screen, and keeps the last scene while a new search runs.
  const [scene, setScene] = useState(IDLE_SCENE);
  useEffect(() => {
    if (phase === "done" && data) {
      setScene({ kind: sceneKind(data.weather_code), night: isNightAt(data.observation_time) });
    }
  }, [phase, data]);

  const pickRecent = (name) => {
    window.scrollTo({ top: 0, behavior: "smooth" });
    search(name);
  };

  return (
    <>
      <WeatherBackground kind={scene.kind} night={scene.night} />
      <main className="page">
        <header className="hero">
          <h1>WeatherWatch</h1>
          <p>An on-demand data pipeline: Airflow, PostgreSQL and Spark</p>
        </header>

        <SearchBar onSearch={search} busy={busy} />

        {phase === "loading" && <p className="status">{message}</p>}

        {phase === "running" && <StepTracker stages={stages} message={message} />}

        {phase === "error" && (
          <>
            {stages.some((s) => s.state !== "pending") && <StepTracker stages={stages} message="" failed />}
            <div className="card error" role="alert">
              {error}
            </div>
          </>
        )}

        {phase === "done" && data && <WeatherCard data={data} source={source} elapsedMs={elapsedMs} />}

        <RecentCities cities={recent} activeCity={phase === "done" ? data?.city : city} busy={busy} onPick={pickRecent} />

        <AnalyticsPanel focusCity={phase === "done" ? data?.city : null} />
      </main>
    </>
  );
}
