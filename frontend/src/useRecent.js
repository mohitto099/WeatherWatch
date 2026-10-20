import { useCallback, useEffect, useState } from "react";
import { getRecent } from "./api.js";

const REFRESH_MS = 45_000;

/** Cities anyone searched recently. Reloads when `refreshKey` changes and every 45 seconds. */
export function useRecent(refreshKey) {
  const [cities, setCities] = useState([]);

  const load = useCallback(async () => {
    try {
      const res = await getRecent(8);
      setCities(res.data || []);
    } catch {
      // The cards are a nice-to-have: if this fails, keep showing the last list.
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, REFRESH_MS);
    return () => clearInterval(id);
  }, [load]);

  useEffect(() => {
    if (refreshKey) load();
  }, [refreshKey, load]);

  return cities;
}
