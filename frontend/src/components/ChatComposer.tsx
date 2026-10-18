/**
 * src/components/ChatComposer.tsx
 * Message composer textarea with 1000-char limit, keyboard shortcuts
 * (Enter to send, Shift+Enter for newline), character counter, and loading state.
 */
import React, { useRef, useEffect } from "react";

interface Props {
  value: string;
  onChange: (val: string) => void;
  onSend: (text: string) => void;
  disabled?: boolean;
  loading?: boolean;
  focusTrigger?: number;
}

const MAX_CHARS = 1000;

export function ChatComposer({
  value,
  onChange,
  onSend,
  disabled = false,
  loading = false,
  focusTrigger = 0,
}: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const trimmed = value.trim();
  const canSend = !disabled && !loading && trimmed.length > 0 && value.length <= MAX_CHARS;

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (canSend) {
        onSend(trimmed);
      }
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (canSend) {
      onSend(trimmed);
    }
  };

  // Auto-focus textarea when focusTrigger changes or disabled becomes false
  useEffect(() => {
    if (!disabled && !loading) {
      textareaRef.current?.focus();
    }
  }, [disabled, loading, focusTrigger]);

  const charCount = value.length;
  const isNearLimit = charCount >= 900 && charCount < MAX_CHARS;
  const isAtLimit = charCount >= MAX_CHARS;

  let counterClass = "composer-counter";
  if (isAtLimit) {
    counterClass += " composer-counter--at";
  } else if (isNearLimit) {
    counterClass += " composer-counter--near";
  }

  return (
    <div className="composer-area">
      <form onSubmit={handleSubmit}>
        <div className="composer-wrap">
          <textarea
            ref={textareaRef}
            className="composer-textarea"
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            disabled={disabled || loading}
            maxLength={MAX_CHARS}
            placeholder={
              disabled
                ? "Select a dataset to begin..."
                : "Ask a question about your data... (Enter to send, Shift+Enter for newline)"
            }
            rows={2}
            aria-label="Ask a question"
          />

          <div className="composer-footer">
            <span
              className={counterClass}
              aria-live="polite"
              aria-label={`${charCount} of ${MAX_CHARS} characters used`}
            >
              {charCount} / {MAX_CHARS}
            </span>

            <div className="composer-actions">
              <button
                type="submit"
                className="btn btn--primary"
                disabled={!canSend}
                aria-label="Send question"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      </form>
      <div className="composer-hint" aria-hidden="true">
        Press <strong>Enter</strong> to send, <strong>Shift + Enter</strong> for a new line
      </div>
    </div>
  );
}
