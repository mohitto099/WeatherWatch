import { useEffect, useState } from "react";
import { getAnalytics, getTrend } from "./api.js";

// Both hooks keep showing the previous result while a new one loads, so the panel never flashes empty.
// If the Spark job has not run yet (or the API fails) they return null / [] and the panel stays hidden.

export function useAnalytics(windowLabel) {
  const [data, setData] = useState(null);
  useEffect(() => {
    let alive = true;
    getAnalytics(windowLabel)
      .then((res) => alive && setData(res.data))
      .catch(() => alive && setData(null));
    return () => { alive = false; };
  }, [windowLabel]);
  return data;
}

export function useTrend(city, days) {
  const [points, setPoints] = useState([]);
  useEffect(() => {
    if (!city) return undefined;
    let alive = true;
    getTrend(city, days)
      .then((res) => alive && setPoints(res.data || []))
      .catch(() => alive && setPoints([]));
    return () => { alive = false; };
  }, [city, days]);
  return points;
}
