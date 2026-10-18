/**
 * src/components/AppSidebar.tsx
 * Persistent navigation sidebar & drawer containing:
 * - Persistent Dataset selector
 * - Section A: Chat history & "+ New Chat" session manager
 * - Section B: Dataset access and loading guidance
 * - Section C: System Health & Starter questions
 */
import { useState } from "react";
import { ChatSession, Dataset, HealthResponse } from "../types";
import { ChatSessionsList } from "./ChatSessionsList";
import { DataLoader } from "./DataLoader";
import { HealthIndicator } from "./HealthIndicator";

interface Props {
  datasets: Dataset[];
  selectedDataset: Dataset | null;
  onSelectDataset: (datasetId: string) => void;
  onSelectQuestion: (question: string) => void;
  health: HealthResponse | null;
  healthLoading?: boolean;
  disabled?: boolean;
  isOpen?: boolean;
  onClose?: () => void;
  sessions?: ChatSession[];
  activeSessionId?: string | null;
  onSelectSession?: (id: string) => void;
  onDeleteSession?: (id: string) => void;
  onNewChat?: () => void;
}

type SidebarTab = "chats" | "data";

export function AppSidebar({
  datasets,
  selectedDataset,
  onSelectDataset,
  onSelectQuestion,
  health,
  healthLoading = false,
  disabled = false,
  isOpen = false,
  onClose,
  sessions = [],
  activeSessionId = null,
  onSelectSession = () => {},
  onDeleteSession = () => {},
  onNewChat = () => {},
}: Props) {
  const [activeTab, setActiveTab] = useState<SidebarTab>("chats");
  const exampleQuestions = selectedDataset?.example_questions ?? [];

  const handleSelectQuestion = (q: string) => {
    onSelectQuestion(q);
    onClose?.();
  };

  const handleSelectSession = (id: string) => {
    onSelectSession(id);
    onClose?.();
  };

  const handleNewChat = () => {
    onNewChat();
    onClose?.();
  };

  return (
    <aside
      id="app-sidebar-panel"
      className={`app-sidebar ${isOpen ? "app-sidebar--open" : ""}`}
      aria-label="Dataset settings, chat history, and health"
    >
      {/* Mobile Drawer Header with Close Button */}
      <div className="sidebar-mobile-header">
        <span className="sidebar-mobile-title">DataMind Terminal</span>
        {onClose && (
          <button
            type="button"
            className="sidebar-close-btn"
            onClick={onClose}
            aria-label="Close sidebar panel"
          >
            ✕
          </button>
        )}
      </div>

      {/* Dataset selector section - always visible */}
      <section className="sidebar-section" aria-labelledby="sidebar-dataset-label">
        <label id="sidebar-dataset-label" htmlFor="dataset-select" className="sidebar-label">
          Dataset
        </label>
        <select
          id="dataset-select"
          className="dataset-select"
          value={selectedDataset?.id ?? ""}
          onChange={(e) => onSelectDataset(e.target.value)}
          disabled={disabled || datasets.length === 0}
          aria-label="Select dataset"
        >
          {datasets.length === 0 ? (
            <option value="" disabled>
              Loading datasets…
            </option>
          ) : (
            <>
              {!selectedDataset && (
                <option value="" disabled>
                  Select a dataset…
                </option>
              )}
              {datasets.map((ds) => (
                <option key={ds.id} value={ds.id}>
                  {ds.name}
                </option>
              ))}
            </>
          )}
        </select>

        {selectedDataset?.description && (
          <p className="dataset-description" aria-label="Dataset description">
            {selectedDataset.description}
          </p>
        )}
      </section>

      {/* Navigation Tabs: Chats vs Data Loader */}
      <div className="sidebar-tabs" role="tablist" aria-label="Sidebar sections">
        <button
          type="button"
          role="tab"
          id="tab-chats"
          aria-selected={activeTab === "chats"}
          aria-controls="panel-chats"
          className={`sidebar-tab-btn ${activeTab === "chats" ? "sidebar-tab-btn--active" : ""}`}
          onClick={() => setActiveTab("chats")}
        >
          Chats
        </button>
        <button
          type="button"
          role="tab"
          id="tab-data"
          aria-selected={activeTab === "data"}
          aria-controls="panel-data"
          className={`sidebar-tab-btn ${activeTab === "data" ? "sidebar-tab-btn--active" : ""}`}
          onClick={() => setActiveTab("data")}
        >
          Load Data
        </button>
      </div>

      {/* Section A: Chat History & New Chat */}
      {activeTab === "chats" && (
        <div id="panel-chats" role="tabpanel" aria-labelledby="tab-chats" className="tab-content">
          <ChatSessionsList
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSelectSession={handleSelectSession}
            onDeleteSession={onDeleteSession}
            onNewChat={handleNewChat}
            disabled={disabled}
          />

          {exampleQuestions.length > 0 && (
            <div className="sidebar-section starter-prompts-section">
              <div className="sidebar-label">Sample Prompts</div>
              <div className="example-questions" role="group" aria-label="Suggested starter questions">
                {exampleQuestions.map((q) => (
                  <button
                    key={q}
                    type="button"
                    className="example-question-btn"
                    disabled={disabled}
                    onClick={() => handleSelectQuestion(q)}
                    title={q}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Section B: Data & Snowflake Loader */}
      {activeTab === "data" && (
        <div id="panel-data" role="tabpanel" aria-labelledby="tab-data" className="tab-content">
          <DataLoader
            selectedDataset={selectedDataset}
          />
        </div>
      )}

      <div className="sidebar-spacer" />
      <hr className="sidebar-divider" />

      {/* Section C: Service Health Indicator */}
      <HealthIndicator health={health} loading={healthLoading} />
    </aside>
  );
}
