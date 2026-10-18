/**
 * src/components/ChatSessionsList.tsx
 * Displays recent saved chat sessions, allows switching conversations,
 * deleting sessions, and starting a fresh chat.
 */
import { ChatSession } from "../types";

interface Props {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
  onNewChat: () => void;
  disabled?: boolean;
}

export function ChatSessionsList({
  sessions,
  activeSessionId,
  onSelectSession,
  onDeleteSession,
  onNewChat,
  disabled = false,
}: Props) {
  return (
    <div className="chat-sessions-section" role="region" aria-label="Saved Chat Sessions">
      <div className="chat-sessions-header">
        <button
          type="button"
          className="btn btn--primary btn--sm new-chat-btn"
          onClick={onNewChat}
          disabled={disabled}
          aria-label="Start a new chat"
        >
          <span aria-hidden="true">+</span> New Chat
        </button>
      </div>

      <div className="sidebar-label">Recent Chats</div>

      {sessions.length === 0 ? (
        <div className="no-sessions-hint">No saved sessions yet.</div>
      ) : (
        <div className="sessions-list" role="list">
          {sessions.map((session) => {
            const isActive = session.id === activeSessionId;
            const dateStr = new Date(session.updatedAt).toLocaleDateString([], {
              month: "short",
              day: "numeric",
            });

            return (
              <div
                key={session.id}
                role="listitem"
                className={`session-item ${isActive ? "session-item--active" : ""}`}
              >
                <button
                  type="button"
                  className="session-select-btn"
                  onClick={() => onSelectSession(session.id)}
                  aria-current={isActive ? "true" : undefined}
                  title={session.title}
                >
                  <span className="session-title">{session.title}</span>
                  <div className="session-meta">
                    <span className="session-badge">{session.datasetName}</span>
                    <span className="session-date">{dateStr}</span>
                  </div>
                </button>

                <button
                  type="button"
                  className="session-delete-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteSession(session.id);
                  }}
                  aria-label={`Delete chat: ${session.title}`}
                  title="Delete chat"
                >
                  ✕
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
