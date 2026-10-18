/**
 * src/App.tsx
 * Root component: DataMind analytical dashboard with persistent hamburger drawer,
 * chat session history, data ingestion panel, transcript, and composer.
 */
import { useEffect, useRef, useState } from "react";
import { AppHeader } from "./components/AppHeader";
import { AppSidebar } from "./components/AppSidebar";
import { ChatComposer } from "./components/ChatComposer";
import { ChatTranscript } from "./components/ChatTranscript";
import { useDatasets } from "./hooks/useDatasets";
import { useHealth } from "./hooks/useHealth";
import { useChat } from "./hooks/useChat";
import { useChatSessions } from "./hooks/useChatSessions";

const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";

export default function App() {
  const { health } = useHealth();
  const { datasets, selectedDataset, setSelectedDatasetId, loading: datasetsLoading } =
    useDatasets();
  const [draftQuestion, setDraftQuestion] = useState("");
  const [focusTrigger, setFocusTrigger] = useState(0);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [announcement, setAnnouncement] = useState("");

  const menuButtonRef = useRef<HTMLButtonElement>(null);

  const {
    messages,
    loading: chatLoading,
    error,
    send,
    cancel,
    retry,
    clearMessages,
    loadMessages,
  } = useChat(selectedDataset?.id ?? null);

  const {
    sessions,
    activeSessionId,
    selectSession,
    syncMessages,
    deleteSession,
    startNewChat,
  } = useChatSessions();

  // Sync messages into the active session
  useEffect(() => {
    if (messages.length > 0 && selectedDataset) {
      syncMessages(messages, selectedDataset.id, selectedDataset.name);
    }
  }, [messages, selectedDataset, syncMessages]);

  // Announce incoming answers and errors to screen readers
  useEffect(() => {
    if (messages.length > 0) {
      const last = messages[messages.length - 1];
      if (last.role === "assistant") {
        const text =
          last.response.answer ??
          last.response.clarifying_question ??
          "Answer received.";
        setAnnouncement(`New response: ${text.slice(0, 120)}`);
      }
    }
  }, [messages]);

  useEffect(() => {
    if (error) {
      setAnnouncement(`Error occurred: ${error.message}`);
    }
  }, [error]);

  // Handle Escape key to close mobile/desktop drawer and return focus
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isSidebarOpen) {
        setIsSidebarOpen(false);
        menuButtonRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isSidebarOpen]);

  const handleToggleSidebar = () => {
    setIsSidebarOpen((prev) => !prev);
  };

  const handleCloseSidebar = () => {
    setIsSidebarOpen(false);
    menuButtonRef.current?.focus();
  };

  const handleNewChat = () => {
    startNewChat();
    clearMessages();
    setDraftQuestion("");
  };

  const handleSelectSession = (sessionId: string) => {
    const session = selectSession(sessionId);
    if (session) {
      if (session.datasetId !== selectedDataset?.id) {
        setSelectedDatasetId(session.datasetId);
      }
      loadMessages(session.messages);
      setDraftQuestion("");
    }
  };

  const handleDeleteSession = (sessionId: string) => {
    deleteSession(sessionId);
    if (activeSessionId === sessionId) {
      clearMessages();
    }
  };

  const handleSelectDataset = (newDatasetId: string) => {
    if (newDatasetId === selectedDataset?.id) return;
    const hasUnsentInput = draftQuestion.trim().length > 0;
    const hasMessages = messages.length > 0;
    if (hasUnsentInput || hasMessages) {
      const confirmed = window.confirm(
        "Switching datasets will start a new conversation and discard any unsent input. Do you want to continue?",
      );
      if (!confirmed) return;
    }
    handleNewChat();
    setSelectedDatasetId(newDatasetId);
  };

  const handleSend = (text: string) => {
    setDraftQuestion("");
    send(text);
  };

  const handleSelectQuestion = (q: string) => {
    send(q);
  };

  const handleFocusComposer = () => {
    setFocusTrigger((prev) => prev + 1);
  };

  const healthStatus = health?.status ?? (health ? "unknown" : "loading");

  return (
    <>
      {/* Skip to main content link for keyboard users */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      {/* Polite live region for screen readers */}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {announcement}
      </div>

      <div className="app-layout">
        <AppHeader
          healthStatus={healthStatus}
          isSidebarOpen={isSidebarOpen}
          onToggleSidebar={handleToggleSidebar}
          menuButtonRef={menuButtonRef}
        />

        {/* Sidebar backdrop when drawer is open */}
        {isSidebarOpen && (
          <div
            className="sidebar-backdrop"
            onClick={handleCloseSidebar}
            aria-hidden="true"
          />
        )}

        <AppSidebar
          datasets={datasets}
          selectedDataset={selectedDataset}
          onSelectDataset={handleSelectDataset}
          health={health}
          healthLoading={healthStatus === "loading"}
          disabled={chatLoading}
          isOpen={isSidebarOpen}
          onClose={handleCloseSidebar}
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={handleSelectSession}
          onDeleteSession={handleDeleteSession}
          onNewChat={handleNewChat}
        />

        <main className="app-main" id="main-content" tabIndex={-1} aria-label="Main content area">
          {selectedDataset ? (
            <div
              className="chat-area"
              onMouseMove={(event) => {
                const bounds = event.currentTarget.getBoundingClientRect();
                event.currentTarget.style.setProperty(
                  "--chat-pointer-x",
                  `${event.clientX - bounds.left}px`,
                );
                event.currentTarget.style.setProperty(
                  "--chat-pointer-y",
                  `${event.clientY - bounds.top}px`,
                );
              }}
              onMouseLeave={(event) => {
                event.currentTarget.style.setProperty(
                  "--chat-pointer-x",
                  "-1000px",
                );
                event.currentTarget.style.setProperty(
                  "--chat-pointer-y",
                  "-1000px",
                );
              }}
            >
              <ChatTranscript
                messages={messages}
                loading={chatLoading}
                error={error}
                dataset={selectedDataset}
                onSelectQuestion={handleSelectQuestion}
                onCancel={cancel}
                onRetry={retry}
                onFocusComposer={handleFocusComposer}
              />
              <ChatComposer
                value={draftQuestion}
                onChange={setDraftQuestion}
                onSend={handleSend}
                disabled={!selectedDataset}
                loading={chatLoading}
                focusTrigger={focusTrigger}
              />
            </div>
          ) : (
            <div className="main-placeholder">
              <div className="main-placeholder__icon" aria-hidden="true">
                📊
              </div>
              <h1 className="main-placeholder__heading">DataMind Analytical Engine</h1>
              <p className="main-placeholder__body">
                {datasetsLoading
                  ? "Loading available datasets…"
                  : "Open the menu or select a dataset to begin querying structured database records."}
              </p>
            </div>
          )}
        </main>
      </div>

      {USE_MOCK && (
        <div className="mock-banner" role="status" aria-label="Mock mode active">
          Mock mode
        </div>
      )}
    </>
  );
}
