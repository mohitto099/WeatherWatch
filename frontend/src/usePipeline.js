import { useCallback, useRef, useState } from "react";
import { ApiError, getLatest, getStatus, getWeather } from "./api.js";

export const DEFAULT_STAGES = [
  { id: "fetching", label: "Fetching weather data", state: "pending" },
  { id: "cleaning", label: "Cleaning and validating", state: "pending" },
  { id: "saving", label: "Saving to database", state: "pending" },
  { id: "finalizing", label: "Finalizing", state: "pending" },
];

const POLL_MS = 1200;
const TIMEOUT_MS = 120_000;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const INITIAL = {
  phase: "idle", // idle | loading | running | done | error
  city: "",
  stages: DEFAULT_STAGES,
  message: "",
  data: null,
  source: null, // "cache" | "pipeline"
  elapsedMs: null,
  error: null,
};

/**
 * One search = cache check -> (if miss) pipeline run + status polling -> final record.
 * A newer search cancels the polling of an older one.
 */
export function usePipeline() {
  const [state, setState] = useState(INITIAL);
  const latestSearch = useRef(0);

  const search = useCallback(async (rawCity) => {
    const city = rawCity.trim();
    if (!city) return;

    const mine = ++latestSearch.current;
    const alive = () => latestSearch.current === mine;
    const started = performance.now();
    const elapsed = () => Math.round(performance.now() - started);

    setState({ ...INITIAL, phase: "loading", city, message: "Checking for recent data..." });

    try {
      const first = await getWeather(city);
      if (!alive()) return;

      if (first.status === "cached") {
        setState({ ...INITIAL, phase: "done", city, data: first.data, source: "cache", elapsedMs: elapsed() });
        return;
      }

      setState((s) => ({ ...s, phase: "running", message: "Starting pipeline..." }));
      const deadline = Date.now() + TIMEOUT_MS;

      while (alive()) {
        await sleep(POLL_MS);
        if (!alive()) return;

        const status = await getStatus(first.run_id);
        if (!alive()) return;

        if (status.status === "done") {
          const latest = await getLatest(city);
          if (!alive()) return;
          setState({
            ...INITIAL,
            phase: "done",
            city,
            stages: status.stages,
            data: latest.data,
            source: "pipeline",
            elapsedMs: elapsed(),
          });
          return;
        }

        if (status.status === "failed") {
          setState({
            ...INITIAL,
            phase: "error",
            city,
            stages: status.stages,
            error: `${status.message}. Please check the city name and try again.`,
          });
          return;
        }

        setState((s) => ({ ...s, stages: status.stages, message: status.message }));

        if (Date.now() > deadline) {
          throw new ApiError("The pipeline is taking too long. Please try again.");
        }
      }
    } catch (e) {
      if (alive()) {
        setState({ ...INITIAL, phase: "error", city, error: e.message || "Something went wrong." });
      }
    }
  }, []);

  return { ...state, search };
}
