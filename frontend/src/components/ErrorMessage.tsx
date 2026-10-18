/**
 * src/components/ErrorMessage.tsx
 * Displays network or API error messages with optional Retry action.
 */
import { ChatError } from "../types";

interface Props {
  error: ChatError;
  onRetry?: () => void;
}

export function ErrorMessage({ error, onRetry }: Props) {
  return (
    <div className="error-message" role="alert" aria-live="assertive">
      <div className="error-card">
        <div className="error-card__header">
          <span aria-hidden="true">⚠️</span>
          <span>Request Failed</span>
        </div>

        <div className="error-card__body">{error.message}</div>

        {error.code && (
          <div className="error-card__code">
            Error Code: <code>{error.code}</code>
          </div>
        )}

        {error.canRetry && onRetry && (
          <div>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={onRetry}
              aria-label="Retry failed request"
            >
              Retry
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
