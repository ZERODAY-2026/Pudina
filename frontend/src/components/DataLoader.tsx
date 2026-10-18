/** Explains how configured datasets are loaded and queried by the backend. */
import type { Dataset } from "../types";

interface Props {
  selectedDataset: Dataset | null;
}

export function DataLoader({ selectedDataset }: Props) {
  return (
    <div className="data-loader-panel" role="region" aria-label="Data & Snowflake Loader">
      <div className="sidebar-section">
        <div className="sidebar-label">Active Dataset</div>
        {selectedDataset && (
          <div className="schema-summary">
            <span className="schema-badge">TABLE: {selectedDataset.id.toUpperCase()}</span>
            <p className="dataset-description">{selectedDataset.description}</p>
          </div>
        )}
      </div>
      <div className="sidebar-section data-sync-box">
        <div className="sidebar-label">Data access</div>
        <p className="dataset-description">
          Questions run against the selected Snowflake dataset in real time.
          Data loading is an administrative task performed on the backend; this
          browser app does not upload files or modify tables.
        </p>
        <p className="dataset-description">
          Configure datasets with their schema in <code>config/*.yaml</code>.
          Any Snowflake data loading is managed outside this browser app.
        </p>
      </div>
    </div>
  );
}
