import { useCountUp } from "../useCountUp.js";
import { adviceFor, iconFor, isNightAt, minutesSince } from "../weatherUtils.js";

// Open-Meteo times are the city's local wall-clock time, so show them as written.
function formatObserved(iso) {
  const d = new Date(iso);
  return d.toLocaleString([], { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
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
  const ago = minutesSince(data.fetched_at);
  const fromCache = source === "cache";
  const night = isNightAt(data.observation_time);
  const tip = adviceFor(data);
  const temp = useCountUp(data.temperature);

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

      <div className="hero-row">
        <div className="temp">
          {Math.round(temp)}
          <small>°C</small>
        </div>
        <div className="wx-icon" aria-hidden="true">{iconFor(data.weather_code, night)}</div>
      </div>

      <div className="tip" role="note">
        <span className="tip-icon" aria-hidden="true">{tip.icon}</span>
        <span>{tip.text}</span>
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
