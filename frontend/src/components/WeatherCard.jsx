// Open-Meteo times are the city's local wall-clock time, so show them as written.
function formatObserved(iso) {
  const d = new Date(iso);
  return d.toLocaleString([], { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

// fetched_at is stored in UTC without a timezone marker.
function minutesAgo(iso) {
  const utc = /Z|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + "Z";
  return Math.max(0, Math.round((Date.now() - new Date(utc).getTime()) / 60000));
}

function Metric({ label, value, unit }) {
  return (
    <div className="metric">
      <span className="metric-label">{label}</span>
      <span className="metric-value">
        {value}
        <small>{unit}</small>
      </span>
    </div>
  );
}

export default function WeatherCard({ data, source, elapsedMs }) {
  const ago = minutesAgo(data.fetched_at);
  const fromCache = source === "cache";

  return (
    <section className="card weather">
      <div className="weather-head">
        <div>
          <h2>
            {data.city}
            {data.country ? <span className="country">, {data.country}</span> : null}
          </h2>
          <p className="condition">{data.condition}</p>
        </div>
        <span className={`badge ${fromCache ? "cache" : "fresh"}`}>
          {fromCache ? "Served from cache" : "Fresh from pipeline"}
        </span>
      </div>

      <div className="temp">
        {Math.round(data.temperature)}
        <small>°C</small>
      </div>

      <div className="metrics">
        <Metric label="Humidity" value={data.humidity} unit="%" />
        <Metric label="Pressure" value={Math.round(data.pressure)} unit=" hPa" />
        <Metric label="Wind" value={Math.round(data.wind_speed)} unit=" km/h" />
      </div>

      <p className="foot">
        Observed {formatObserved(data.observation_time)} (local time) · stored {ago === 0 ? "just now" : `${ago} min ago`}
        {" · "}
        {fromCache
          ? `answered from the database in ${(elapsedMs / 1000).toFixed(1)}s, no pipeline run`
          : `pipeline run took ${(elapsedMs / 1000).toFixed(1)}s`}
      </p>
    </section>
  );
}
