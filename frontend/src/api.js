// All calls to the WeatherWatch FastAPI backend live here.
// By default requests go to the same address as the page ("/api/..."), and the Vite dev
// server forwards them to FastAPI (see vite.config.js). Set VITE_API_URL only to bypass that.
const BASE = import.meta.env.VITE_API_URL ?? "";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path) {
  let res;
  try {
    res = await fetch(BASE + path);
  } catch {
    throw new ApiError("Can't reach the WeatherWatch API. Is the backend running?");
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    throw new ApiError(body?.detail || `Request failed (HTTP ${res.status})`, res.status);
  }
  return body;
}

const q = encodeURIComponent;

// Cache hit -> {status:"cached", data}. Cache miss -> {status:"triggered", run_id}
export const getWeather = (city) => request(`/api/weather?city=${q(city)}`);
// {status: queued|running|done|failed, message, stages:[{id,label,state}]}
export const getStatus = (runId) => request(`/api/pipeline/status/${q(runId)}`);
// Newest stored record -> {data}
export const getLatest = (city) => request(`/api/weather/latest?city=${q(city)}`);
// Cities anyone searched recently, newest first -> {data: [record, ...]}
export const getRecent = (limit = 8) => request(`/api/weather/recent?limit=${limit}`);
