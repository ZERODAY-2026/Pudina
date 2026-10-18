/**
 * src/components/EmptyState.tsx
 * Welcomes the user, explains the tool, and presents example question chips.
 */
import { Dataset } from "../types";

interface Props {
  dataset: Dataset | null;
  onSelectQuestion: (question: string) => void;
  disabled?: boolean;
}

export function EmptyState({ dataset, onSelectQuestion, disabled }: Props) {
  const exampleQuestions = dataset?.example_questions ?? [];

  return (
    <div className="empty-state">
      <div className="empty-state__glyph" aria-hidden="true">
        🧠
      </div>
      <h2 className="empty-state__heading">Ask your data anything</h2>
      <p className="empty-state__body">
        DataMind turns plain-English questions into Snowflake queries and returns
        real answers — with the SQL it ran and the rows it found.
      </p>

      {exampleQuestions.length > 0 && (
        <div
          className="empty-state__chips"
          role="group"
          aria-label="Example question suggestions"
        >
          {exampleQuestions.map((q) => (
            <button
              key={q}
              type="button"
              className="chip-btn"
              disabled={disabled}
              onClick={() => onSelectQuestion(q)}
            >
              {q}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
