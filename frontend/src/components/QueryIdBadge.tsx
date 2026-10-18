/**
 * src/components/QueryIdBadge.tsx
 * Monospace Snowflake Query ID badge with clipboard copy button.
 */
import { useState } from "react";

interface Props {
  queryId: string;
}

export function QueryIdBadge({ queryId }: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(queryId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const el = document.createElement("textarea");
      el.value = queryId;
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="query-id-bar" aria-label="Snowflake query ID">
      <span className="query-id-bar__label">Query ID:</span>
      <code className="query-id-bar__code">{queryId}</code>
      <button
        type="button"
        className="btn btn--ghost btn--sm query-id-bar__btn"
        onClick={handleCopy}
        aria-label={copied ? "Query ID copied" : "Copy Query ID"}
      >
        {copied ? "Copied!" : "Copy"}
      </button>
    </div>
  );
}
