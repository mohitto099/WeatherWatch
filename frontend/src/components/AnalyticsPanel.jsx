import { useEffect, useState } from "react";
import { useAnalytics, useTrend } from "../useAnalytics.js";
import TrendChart from "./TrendChart.jsx";

const WINDOWS = [
  { label: "1W", days: 7, name: "Last week" },
  { label: "1M", days: 30, name: "Last month" },
  { label: "6M", days: 182, name: "Last 6 months" },
  { label: "1Y", days: 365, name: "Last year" },
];

const fmt = (iso, withYear = false) =>
  new Date(iso).toLocaleDateString([], { day: "numeric", month: "short", ...(withYear ? { year: "numeric" } : {}) });

/**
 * Historical analytics computed by Apache Spark: city comparison for a chosen window,
 * plus a daily temperature trend for one city. Hidden until the Spark job has produced results.
 */
export default function AnalyticsPanel({ focusCity }) {
  const [windowLabel, setWindowLabel] = useState("1M");
  const [picked, setPicked] = useState(null);
  const summary = useAnalytics(windowLabel);
  const win = WINDOWS.find((w) => w.label === windowLabel);

  // Follow the city on screen unless the user picked a row themselves
  useEffect(() => setPicked(null), [focusCity]);
  const cities = summary?.cities ?? [];
  const active = picked ?? (cities.some((c) => c.city === focusCity) ? focusCity : cities[0]?.city);
  const trend = useTrend(active, win.days);

  if (!summary || cities.length === 0) return null;

  const temps = cities.map((c) => c.avg_temp);
  const lo = Math.min(...temps), hi = Math.max(...temps);
  const bar = (v) => (hi === lo ? 70 : 18 + ((v - lo) / (hi - lo)) * 82);
  const hottest = cities.reduce((a, b) => (b.avg_temp > a.avg_temp ? b : a));
  const coldest = cities.reduce((a, b) => (b.avg_temp < a.avg_temp ? b : a));
  const rainiest = cities.reduce((a, b) => (b.rainy_pct > a.rainy_pct ? b : a));

  return (
    <section className="analytics">
      <div className="an-head">
        <h3>Historical analytics <span className="an-tag">Apache Spark</span></h3>
        <div className="seg" role="group" aria-label="Time window">
          {WINDOWS.map((w) => (
            <button key={w.label} type="button" className={w.label === windowLabel ? "on" : ""} onClick={() => setWindowLabel(w.label)}>
              {w.label}
            </button>
          ))}
        </div>
      </div>

      <div className="card an-card">
        <p className="an-sub">
          {win.name}: {fmt(summary.window_start)} to {fmt(summary.window_end, true)} · {cities[0].observations.toLocaleString()} hourly observations per city
        </p>

        <div className="an-chips">
          <span className="an-chip hot">🔥 Hottest <b>{hottest.city}</b> {hottest.avg_temp}°</span>
          <span className="an-chip cold">❄️ Coldest <b>{coldest.city}</b> {coldest.avg_temp}°</span>
          <span className="an-chip rain">🌧️ Rainiest <b>{rainiest.city}</b> {rainiest.rainy_pct}%</span>
        </div>

        <div className="an-table" role="table">
          <div className="an-row an-th" role="row">
            <span>City</span><span>Average</span><span className="hide-sm">Range</span><span className="hide-sm">Humidity</span><span>Rain</span>
          </div>
          {cities.map((c) => (
            <button key={c.city} type="button" role="row" className={`an-row an-data ${c.city === active ? "sel" : ""}`} onClick={() => setPicked(c.city)}>
              <span className="an-city">{c.city}</span>
              <span className="an-avg">
                <span className="an-bar"><i style={{ width: `${bar(c.avg_temp)}%` }} /></span>
                <b>{c.avg_temp}°</b>
              </span>
              <span className="hide-sm">{c.min_temp}° to {c.max_temp}°</span>
              <span className="hide-sm">{Math.round(c.avg_humidity)}%</span>
              <span>{c.rainy_pct}%</span>
            </button>
          ))}
        </div>

        {trend.length > 1 && (
          <div className="an-trend">
            <p className="an-trend-title">
              Daily temperature in <b>{active}</b> <span>(faint: daily average, bold: rolling 7-day average)</span>
            </p>
            <TrendChart points={trend} label={`${active} ${windowLabel}`} />
          </div>
        )}

        <p className="foot">Computed by Spark on {fmt(summary.computed_at, true)} from the weather_history table. Click a city to chart it.</p>
      </div>
    </section>
  );
}
