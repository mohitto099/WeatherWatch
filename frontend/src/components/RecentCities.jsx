import { iconFor, isNightAt, minutesSince, timeAgo } from "../weatherUtils.js";

// Cards for cities anyone has searched. Clicking one loads that city
// (instant if it is under 15 minutes old, otherwise it refreshes through the pipeline).
export default function RecentCities({ cities, activeCity, busy, onPick }) {
  if (!cities.length) return null;

  return (
    <section className="recent">
      <h3>Recently searched by everyone</h3>
      <div className="recent-grid">
        {cities.map((c, i) => {
          const stale = minutesSince(c.fetched_at) >= 15;
          return (
            <button
              key={c.city}
              type="button"
              className={`mini ${activeCity === c.city ? "active" : ""}`}
              style={{ animationDelay: `${i * 60}ms` }}
              disabled={busy}
              onClick={() => onPick(c.city)}
              title={stale ? "Click to refresh this city" : "Fresh data, loads instantly"}
            >
              <span className="mini-icon">{iconFor(c.weather_code, isNightAt(c.observation_time))}</span>
              <span className="mini-city">{c.city}</span>
              <span className="mini-temp">{Math.round(c.temperature)}°</span>
              <span className="mini-cond">{c.condition}</span>
              <span className={`mini-age ${stale ? "stale" : ""}`}>{timeAgo(c.fetched_at)}{stale ? " · tap to refresh" : ""}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
