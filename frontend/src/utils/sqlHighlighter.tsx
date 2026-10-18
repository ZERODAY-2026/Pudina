/**
 * src/utils/sqlHighlighter.tsx
 * Pure React component for rendering syntax-highlighted SQL.
 */
import React from "react";
import { tokenizeSql } from "./sqlTokenizer";

export function HighlightedSql({ sql }: { sql: string }): React.ReactElement {
  const tokens = tokenizeSql(sql);

  return (
    <code className="sql-code">
      {tokens.map((token, idx) => {
        if (token.type === "keyword") {
          return (
            <span key={idx} className="sql-token sql-token--keyword">
              {token.value}
            </span>
          );
        }
        if (token.type === "string") {
          return (
            <span key={idx} className="sql-token sql-token--string">
              {token.value}
            </span>
          );
        }
        if (token.type === "identifier") {
          return (
            <span key={idx} className="sql-token sql-token--identifier">
              {token.value}
            </span>
          );
        }
        if (token.type === "number") {
          return (
            <span key={idx} className="sql-token sql-token--number">
              {token.value}
            </span>
          );
        }
        return <span key={idx}>{token.value}</span>;
      })}
    </code>
  );
}
