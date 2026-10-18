/**
 * src/hooks/useDatasets.ts
 * Fetches the available datasets once on mount and tracks the selected dataset.
 * Auto-selects the first dataset when only one is returned.
 */
import { useEffect, useState } from "react";
import { getDatasets } from "../api/client";
import type { Dataset } from "../types";

export interface UseDatasetsResult {
  datasets: Dataset[];
  loading: boolean;
  error: string | null;
  selectedDatasetId: string | null;
  selectedDataset: Dataset | null;
  setSelectedDatasetId: (id: string) => void;
}

export function useDatasets(): UseDatasetsResult {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null);

  useEffect(() => {
    const ac = new AbortController();

    getDatasets(ac.signal)
      .then((res) => {
        setDatasets(res.datasets);
        // Auto-select when there is exactly one dataset.
        if (res.datasets.length === 1) {
          setSelectedDatasetId(res.datasets[0].id);
        }
      })
      .catch((err: Error) => {
        if (err.name !== "AbortError") {
          setError("Failed to load datasets. Please refresh the page.");
        }
      })
      .finally(() => setLoading(false));

    return () => ac.abort();
  }, []);

  const selectedDataset =
    datasets.find((d) => d.id === selectedDatasetId) ?? null;

  return {
    datasets,
    loading,
    error,
    selectedDatasetId,
    selectedDataset,
    setSelectedDatasetId,
  };
}
