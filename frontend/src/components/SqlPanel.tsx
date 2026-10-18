/**
 * src/components/SqlPanel.tsx
 * Displays executed SQL with syntax highlighting and a clipboard copy button.
 */
import { useState } from "react";
import { HighlightedSql } from "../utils/sqlHighlighter";

interface Props {
  sql: string;
}

export function SqlPanel({ sql }: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback if clipboard API is unavailable
      const el = document.createElement("textarea");
      el.value = sql;
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="sql-panel">
      <div className="sql-panel__toolbar">
        <span className="sql-panel__label">SQL Query</span>
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={handleCopy}
          aria-label={copied ? "SQL query copied" : "Copy SQL query"}
        >
          {copied ? "Copied!" : "Copy SQL"}
        </button>
      </div>
      <pre className="sql-panel__code" tabIndex={0} aria-label="SQL code">
        <HighlightedSql sql={sql} />
      </pre>
    </div>
  );
}
