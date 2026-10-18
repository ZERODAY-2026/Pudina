/**
 * src/hooks/useHealth.ts
 * Fetches GET /api/health on mount, every 30 s, and whenever the window
 * regains focus.  Components receive a ready-to-render HealthResponse.
 */
import { useCallback, useEffect, useState } from "react";
import { getHealth } from "../api/client";
import type { HealthResponse } from "../types";

export interface UseHealthResult {
  health: HealthResponse | null;
  /** True if the last fetch failed (network error). */
  fetchError: boolean;
}

const POLL_INTERVAL_MS = 30_000;

export function useHealth(): UseHealthResult {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [fetchError, setFetchError] = useState(false);

  const fetchNow = useCallback((signal?: AbortSignal) => {
    getHealth(signal)
      .then((res) => {
        setHealth(res);
        setFetchError(false);
      })
      .catch((err: Error) => {
        if (err.name !== "AbortError") setFetchError(true);
      });
  }, []);

  useEffect(() => {
    const ac = new AbortController();
    fetchNow(ac.signal);

    const timer = setInterval(() => fetchNow(), POLL_INTERVAL_MS);

    const handleFocus = () => fetchNow();
    window.addEventListener("focus", handleFocus);

    return () => {
      ac.abort();
      clearInterval(timer);
      window.removeEventListener("focus", handleFocus);
    };
  }, [fetchNow]);

  return { health, fetchError };
}
