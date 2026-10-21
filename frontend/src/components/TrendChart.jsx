// A dependency-free SVG line chart: faint daily average, bold rolling 7-day average (computed by Spark).
const W = 640, H = 190, PAD = { l: 38, r: 10, t: 12, b: 26 };

function fmtDay(iso) {
  return new Date(iso + "T00:00:00").toLocaleDateString([], { day: "numeric", month: "short" });
}

export default function TrendChart({ points, label }) {
  if (points.length < 2) return null;

  const values = points.flatMap((p) => [p.avg_temp, p.rolling_7d_avg_temp ?? p.avg_temp]);
  let min = Math.min(...values);
  let max = Math.max(...values);
  if (max - min < 1) { max += 0.5; min -= 0.5; }

  const x = (i) => PAD.l + (i / (points.length - 1)) * (W - PAD.l - PAD.r);
  const y = (v) => PAD.t + (1 - (v - min) / (max - min)) * (H - PAD.t - PAD.b);
  const path = (key) =>
    points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(p[key] ?? p.avg_temp).toFixed(1)}`).join(" ");
  const rolling = path("rolling_7d_avg_temp");
  const area = `${rolling} L${x(points.length - 1).toFixed(1)} ${H - PAD.b} L${x(0).toFixed(1)} ${H - PAD.b} Z`;
  const ticks = [min, (min + max) / 2, max];

  return (
    <svg className="trend" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label}>
      <defs>
        <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#fff" stopOpacity="0.32" />
          <stop offset="100%" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
      </defs>
      {ticks.map((t) => (
        <g key={t}>
          <line className="tc-grid" x1={PAD.l} x2={W - PAD.r} y1={y(t)} y2={y(t)} />
          <text className="tc-label" x={PAD.l - 6} y={y(t) + 4} textAnchor="end">{Math.round(t)}°</text>
        </g>
      ))}
      <path d={area} fill="url(#trendFill)" />
      <path className="tc-daily" d={path("avg_temp")} />
      <path key={`${points[0].day}-${points.length}-${label}`} className="tc-roll" pathLength="1" d={rolling} />
      <text className="tc-label" x={PAD.l} y={H - 6}>{fmtDay(points[0].day)}</text>
      <text className="tc-label" x={W - PAD.r} y={H - 6} textAnchor="end">{fmtDay(points[points.length - 1].day)}</text>
    </svg>
  );
}
