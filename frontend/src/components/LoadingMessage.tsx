/**
 * src/components/LoadingMessage.tsx
 * Displays a loading state with spinner, animated skeletons, and an abort/Cancel button.
 */
interface Props {
  onCancel: () => void;
}

export function LoadingMessage({ onCancel }: Props) {
  return (
    <div
      className="loading-message"
      role="status"
      aria-live="polite"
      aria-label="Generating answer"
    >
      <div className="loading-card">
        <div className="loading-label">
          <span className="spinner" aria-hidden="true" />
          <span>Thinking…</span>
        </div>
        <div className="skeleton skeleton--wide" aria-hidden="true" />
        <div className="skeleton skeleton--mid" aria-hidden="true" />
        <div className="skeleton skeleton--short" aria-hidden="true" />

        <div>
          <button
            type="button"
            className="btn btn--danger-ghost btn--sm"
            onClick={onCancel}
            aria-label="Cancel question request"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
