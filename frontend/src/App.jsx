import SearchBar from "./components/SearchBar.jsx";
import StepTracker from "./components/StepTracker.jsx";
import WeatherCard from "./components/WeatherCard.jsx";
import { usePipeline } from "./usePipeline.js";

export default function App() {
  const { phase, stages, message, data, source, elapsedMs, error, search } = usePipeline();
  const busy = phase === "loading" || phase === "running";

  return (
    <main className="page">
      <header className="hero">
        <h1>WeatherWatch</h1>
        <p>On-demand weather data pipeline: Airflow, PostgreSQL and Spark</p>
      </header>

      <SearchBar onSearch={search} busy={busy} />

      {phase === "loading" && <p className="status">{message}</p>}

      {phase === "running" && <StepTracker stages={stages} message={message} />}

      {phase === "error" && (
        <>
          {stages.some((s) => s.state !== "pending") && (
            <StepTracker stages={stages} message="" failed />
          )}
          <div className="card error" role="alert">
            {error}
          </div>
        </>
      )}

      {phase === "done" && data && <WeatherCard data={data} source={source} elapsedMs={elapsedMs} />}
    </main>
  );
}
