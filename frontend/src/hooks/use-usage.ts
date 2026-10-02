import { useEffect, useState, useCallback, useRef } from "react";
import type { UsagePayload, MetricSummary } from "@/types";
import { translate, type Locale } from "@/lib/i18n";

function getLocale(): Locale { return "en"; }

/**
 * Compute cache hit rate: cache_read / (input + cache_read + cache_write) * 100
 * cache_write (newly created cache) counts toward the denominator (billed
 * input) but not the numerator — a write is not a hit. Matches deepseek-harness.
 * Returns a number like 65.3 meaning 65.3%.
 */
function computeCacheHitRate(entry: { input: number; cache_read: number; cache_write: number }): number {
  const inputTotal = (entry.input || 0) + (entry.cache_read || 0) + (entry.cache_write || 0);
  if (inputTotal === 0) return 0;
  return Math.round((entry.cache_read || 0) / inputTotal * 1000) / 10;
}

function enrichPayload(payload: UsagePayload): UsagePayload {
  const addHitRate = (e: MetricSummary) => {
    e.cache_hit_rate = computeCacheHitRate(e);
  };
  addHitRate(payload.summary);
  payload.days.forEach(addHitRate);
  payload.models.forEach(addHitRate);
  payload.providers.forEach(addHitRate);
  (payload.providerModels || []).forEach(addHitRate);
  (payload.providerModelTrends || []).forEach((trend) => trend.days.forEach(addHitRate));
  (payload.heatmap?.data || []).forEach(addHitRate);
  return payload;
}

export function useUsage(range: string, model: string) {
  const [data, setData] = useState<UsagePayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  const fetchData = useCallback(
    async (force = false) => {
      const id = ++requestId.current;
      setLoading(true);
      setError(null);
      try {
        if (force) {
          const scan = await fetch("/api/refresh", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
          if (!scan.ok) throw new Error("Could not refresh local sources");
        }
        const url = new URL("/api/usage", window.location.origin);
        url.searchParams.set("range", range);
        if (model !== "all") url.searchParams.set("model", model);
        if (force) url.searchParams.set("_t", String(Date.now()));

        const res = await fetch(url);
        const json = await res.json();
        if (!res.ok) throw new Error(json.error || translate(getLocale(), "format.loadFailed"));

        if (id === requestId.current) setData(enrichPayload(json));
      } catch (err) {
        if (id === requestId.current) setError(err instanceof Error ? err.message : translate(getLocale(), "format.loadError"));
      } finally {
        if (id === requestId.current) setLoading(false);
      }
    },
    [range, model],
  );

  useEffect(() => {
    fetchData();
    return () => { requestId.current += 1; };
  }, [fetchData]);

  return { data, loading, error, refresh: () => fetchData(true) };
}
