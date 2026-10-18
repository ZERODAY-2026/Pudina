/**
 * src/components/CollapsiblePanel.tsx
 * Accessible collapsible disclosure panel with aria-expanded and aria-controls.
 */
import React, { useId, useState } from "react";

interface Props {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  badge?: string | number;
  action?: React.ReactNode;
}

export function CollapsiblePanel({
  title,
  defaultOpen = false,
  children,
  badge,
  action,
}: Props) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const panelId = useId();
  const buttonId = useId();

  return (
    <div className={`evidence-panel ${isOpen ? "evidence-panel--open" : ""}`}>
      <div className="evidence-panel__header">
        <button
          type="button"
          id={buttonId}
          aria-expanded={isOpen}
          aria-controls={panelId}
          className="evidence-panel__toggle"
          onClick={() => setIsOpen(!isOpen)}
        >
          <span
            className={`evidence-panel__chevron ${isOpen ? "evidence-panel__chevron--open" : ""}`}
            aria-hidden="true"
          >
            ▶
          </span>
          <span className="evidence-panel__title">{title}</span>
          {badge !== undefined && (
            <span className="evidence-panel__badge">{badge}</span>
          )}
        </button>

        {action && <div className="evidence-panel__action">{action}</div>}
      </div>

      <div
        id={panelId}
        role="region"
        aria-labelledby={buttonId}
        className="evidence-panel__body"
        hidden={!isOpen}
      >
        {children}
      </div>
    </div>
  );
}
