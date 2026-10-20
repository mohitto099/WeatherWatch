import { useEffect, useMemo, useRef, useState } from "react";

// Small deterministic random generator so a scene looks the same every time it appears.
function seeded(seed) {
  let s = seed;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

const DROPS = { drizzle: 38, rain: 75, storm: 100 };
const CLOUDS = { idle: 3, clear: 2, partly: 5, cloudy: 7, drizzle: 6, rain: 7, storm: 7, snow: 5, fog: 0 };

function Scene({ kind, night }) {
  const parts = useMemo(() => {
    const r = seeded(11);
    const drops = Array.from({ length: DROPS[kind] || 0 }, () => ({ x: r() * 105, d: r(), s: r() }));
    const flakes = Array.from({ length: kind === "snow" ? 55 : 0 }, () => ({ x: r() * 100, d: r(), s: r(), w: r() }));
    const clouds = Array.from({ length: CLOUDS[kind] ?? 4 }, (_, i) => ({
      top: 4 + r() * 52,
      scale: 0.6 + r() * 1.1,
      dur: 70 + r() * 80,
      delay: r() * 120,
      opacity: 0.55 + r() * 0.4,
      key: i,
    }));
    const stars = Array.from({ length: night && (kind === "clear" || kind === "partly") ? 50 : 0 }, () => ({
      x: r() * 100, y: r() * 60, d: r() * 4, s: 1 + r() * 2,
    }));
    return { drops, flakes, clouds, stars };
  }, [kind, night]);

  const showSun = !night && (kind === "clear" || kind === "partly" || kind === "idle");
  const showMoon = night && (kind === "clear" || kind === "partly");

  return (
    <div className={`bg-layer bg-${kind} ${night ? "night" : "day"}`}>
      {parts.stars.map((s, i) => (
        <span key={i} className="star" style={{ left: `${s.x}%`, top: `${s.y}%`, width: s.s, height: s.s, animationDelay: `${s.d}s` }} />
      ))}
      {showSun && <div className="sun" />}
      {showMoon && <div className="moon" />}

      {parts.clouds.map((c) => (
        <div
          key={c.key}
          className="cloud"
          style={{ top: `${c.top}%`, "--s": c.scale, opacity: c.opacity, animationDuration: `${c.dur}s`, animationDelay: `-${c.delay}s` }}
        />
      ))}

      {kind === "fog" && (
        <>
          <div className="mist" style={{ top: "12%", animationDuration: "34s" }} />
          <div className="mist" style={{ top: "38%", animationDuration: "42s", animationDirection: "alternate-reverse" }} />
          <div className="mist" style={{ top: "64%", animationDuration: "38s" }} />
        </>
      )}

      {parts.drops.map((d, i) => (
        <span
          key={i}
          className="drop"
          style={{ left: `${d.x}%`, animationDuration: `${0.55 + d.s * 0.45}s`, animationDelay: `-${d.d * 2}s`, opacity: 0.35 + d.s * 0.5 }}
        />
      ))}

      {parts.flakes.map((f, i) => (
        <span
          key={i}
          className="flake"
          style={{ left: `${f.x}%`, width: 3 + f.s * 6, height: 3 + f.s * 6, animationDuration: `${7 + f.s * 8}s`, animationDelay: `-${f.d * 12}s` }}
        >
          <i style={{ animationDuration: `${2.5 + f.w * 3}s` }} />
        </span>
      ))}

      {kind === "storm" && <div className="flash" />}
    </div>
  );
}

/**
 * Full-screen animated scene behind the page. When the weather changes, the new
 * scene fades in over the old one, and the old one is removed once it is covered.
 */
export default function WeatherBackground({ kind, night }) {
  const [layers, setLayers] = useState([{ id: 0, kind, night }]);
  const nextId = useRef(1);
  const current = `${kind}-${night}`;
  const shown = useRef(current);

  useEffect(() => {
    if (shown.current === current) return;
    shown.current = current;
    const id = nextId.current++;
    setLayers((prev) => [...prev, { id, kind, night }]);
    const t = setTimeout(() => setLayers((prev) => prev.filter((l) => l.id === id)), 1500);
    return () => clearTimeout(t);
  }, [current, kind, night]);

  return (
    <div className="bg" aria-hidden="true">
      {layers.map((l) => (
        <Scene key={l.id} kind={l.kind} night={l.night} />
      ))}
    </div>
  );
}
