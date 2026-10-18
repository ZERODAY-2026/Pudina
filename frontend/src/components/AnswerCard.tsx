/**
 * src/components/AnswerCard.tsx
 * Renders an assistant response card with status badge, execution latency,
 * answer text, and a unified "All Details" inspector toggle.
 */
import { useEffect, useId, useState } from "react";
import { AskStatus, AssistantMessage } from "../types";
import { QueryIdBadge } from "./QueryIdBadge";
import { ResultTable } from "./ResultTable";
import { SqlPanel } from "./SqlPanel";

interface Props {
  message: AssistantMessage;
  userQuestion?: string;
  exampleQuestions?: string[];
  onSelectQuestion?: (question: string) => void;
  onFocusComposer?: () => void;
  defaultShowDetails?: boolean;
}

interface BadgeConfig {
  icon: string;
  label: string;
  className: string;
}

const BADGE_CONFIG: Record<AskStatus, BadgeConfig> = {
  answered: {
    icon: "✓",
    label: "Answered",
    className: "status-badge status-badge--answered",
  },
  clarify: {
    icon: "?",
    label: "Needs clarification",
    className: "status-badge status-badge--clarify",
  },
  unsupported: {
    icon: "⊘",
    label: "Not supported",
    className: "status-badge status-badge--unsupported",
  },
  empty: {
    icon: "∅",
    label: "No results",
    className: "status-badge status-badge--empty",
  },
  error: {
    icon: "✕",
    label: "Error",
    className: "status-badge status-badge--error",
  },
};

export function AnswerCard({
  message,
  userQuestion,
  exampleQuestions = [],
  onSelectQuestion,
  onFocusComposer,
  defaultShowDetails = false,
}: Props) {
  const { response, timestamp } = message;
  const [showAllDetails, setShowAllDetails] = useState(defaultShowDetails);
  const detailsId = useId();

  const config = BADGE_CONFIG[response.status] ?? {
    icon: "•",
    label: response.status,
    className: "status-badge",
  };

  // Move focus to composer automatically on clarify response
  useEffect(() => {
    if (response.status === "clarify") {
      onFocusComposer?.();
    }
  }, [response.status, onFocusComposer]);

  const hasExplanation = Boolean(response.explanation);
  const hasAssumptions = Boolean(response.assumptions && response.assumptions.length > 0);
  const hasSql = Boolean(response.sql);
  const hasRows = Boolean(response.columns && response.columns.length > 0 && response.rows);
  const showQueryId =
    Boolean(response.query_id) &&
    (response.status === "answered" || response.status === "empty");

  const hasEvidence = hasExplanation || hasAssumptions || hasSql || hasRows || showQueryId;

  const isUnsupportedOrEmptyOrError =
    response.status === "unsupported" ||
    response.status === "empty" ||
    response.status === "error";

  const timeString = new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  // Build summary meta for the toggle button
  const metaParts: string[] = [];
  if (hasSql) metaParts.push("SQL");
  if (hasRows) {
    metaParts.push(`${response.row_count} ${response.row_count === 1 ? "row" : "rows"}`);
  }
  if (showQueryId) metaParts.push("Query ID");
  const metaSuffix = metaParts.length > 0 ? ` • ${metaParts.join(" • ")}` : "";

  return (
    <div
      className="chat-message chat-message--assistant"
      role="article"
      aria-label={`Assistant response: ${config.label}`}
    >
      <div className="answer-card">
        {/* Header with status badge and execution duration */}
        <div className="answer-card__header">
          <span className={config.className} role="status">
            <span className="status-badge__icon" aria-hidden="true">
              {config.icon}
            </span>
            <span>{config.label}</span>
          </span>

          {response.elapsed_ms > 0 && (
            <span className="answer-card__elapsed" title="Execution duration">
              {response.elapsed_ms}ms
            </span>
          )}
        </div>

        <div className="answer-card__body">
          {/* Main Answer text */}
          {response.answer && (
            <div className="answer-text">{response.answer}</div>
          )}

          {/* Clarify status: prominent clarifying question quoting original */}
          {response.status === "clarify" && (
            <div className="clarify-box" role="region" aria-label="Clarification request">
              {userQuestion && (
                <div className="clarify-original">
                  <span className="clarify-original__label">Regarding your question:</span>
                  <blockquote className="clarify-original__quote">“{userQuestion}”</blockquote>
                </div>
              )}
              <div className="clarify-question">
                <strong>Clarification needed:</strong> {response.clarifying_question}
              </div>
              <div className="clarify-hint">
                <button
                  type="button"
                  className="btn btn--primary btn--sm"
                  onClick={() => onFocusComposer?.()}
                >
                  Reply in composer
                </button>
              </div>
            </div>
          )}

          {/* Unsupported, Empty, or Error: Suggestions of what the system can answer */}
          {isUnsupportedOrEmptyOrError && exampleQuestions.length > 0 && (
            <div className="card-suggestions" role="group" aria-label="Suggested valid queries">
              <span className="card-suggestions__title">Questions I can answer:</span>
              <div className="card-suggestions__chips">
                {exampleQuestions.map((q) => (
                  <button
                    key={q}
                    type="button"
                    className="chip-btn"
                    onClick={() => onSelectQuestion?.(q)}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Single Unified "All Details" Evidence Toggle */}
          {hasEvidence && (
            <div className="answer-card__details-action">
              <button
                type="button"
                className={`btn btn--details-toggle ${showAllDetails ? "btn--details-toggle--open" : ""}`}
                onClick={() => setShowAllDetails((prev) => !prev)}
                aria-expanded={showAllDetails}
                aria-controls={detailsId}
                aria-label="All Details"
              >
                <span className="details-toggle-icon" aria-hidden="true">
                  {showAllDetails ? "▼" : "▶"}
                </span>
                <span className="details-toggle-label">
                  {showAllDetails ? "Hide Details" : "All Details"}
                </span>
                <span className="details-toggle-meta">{metaSuffix}</span>
              </button>
            </div>
          )}

          {/* Unified Details Container */}
          {hasEvidence && showAllDetails && (
            <div
              id={detailsId}
              className="all-details-container"
              role="region"
              aria-label="Query evidence and details"
            >
              {/* How I got this & Assumptions */}
              {(hasExplanation || hasAssumptions) && (
                <div className="details-section">
                  <div className="details-section__title">How I got this</div>
                  {response.explanation && (
                    <div className="evidence-explanation">{response.explanation}</div>
                  )}
                  {hasAssumptions && (
                    <div className="assumptions-section">
                      <span className="assumptions-label">Assumptions:</span>
                      <div className="assumption-chips">
                        {response.assumptions.map((item, idx) => (
                          <span key={idx} className="assumption-chip">
                            {item}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* SQL Executed */}
              {hasSql && (
                <div className="details-section">
                  <div className="details-section__title">SQL Executed</div>
                  <SqlPanel sql={response.sql as string} />
                </div>
              )}

              {/* Result Rows & Visualization */}
              {hasRows && (
                <div className="details-section">
                  <div className="details-section__title">
                    Result Rows & Visualization
                  </div>
                  <ResultTable
                    columns={response.columns}
                    rows={response.rows}
                    rowCount={response.row_count}
                    truncated={response.truncated}
                    queryId={response.query_id}
                  />
                </div>
              )}

              {/* Snowflake Query ID */}
              {showQueryId && (
                <div className="details-section details-section--footer">
                  <QueryIdBadge queryId={response.query_id as string} />
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <time className="message-time" dateTime={new Date(timestamp).toISOString()}>
        {timeString}
      </time>
    </div>
  );
}
