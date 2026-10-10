const ICON = { done: "\u2713", failed: "\u2715", skipped: "\u2013", pending: "", active: "" };

export default function StepTracker({ stages, message, failed }) {
  return (
    <section className="card tracker" aria-live="polite">
      <h2>{failed ? "Pipeline failed" : "Pipeline running"}</h2>
      <p className="tracker-msg">{message}</p>
      <ol className="steps">
        {stages.map((s, i) => (
          <li key={s.id} className={`step ${s.state}`}>
            <span className="dot">
              {s.state === "active" ? <span className="spinner" /> : ICON[s.state] || i + 1}
            </span>
            <span className="step-label">{s.label}</span>
          </li>
        ))}
      </ol>
      <p className="hint">Powered by an on-demand Apache Airflow DAG</p>
    </section>
  );
}
