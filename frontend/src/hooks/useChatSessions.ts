/**
 * src/hooks/useChatSessions.ts
 * Manages persisted chat history sessions in localStorage.
 * Auto-titles sessions from the first user question and tracks the active session.
 */
import { useCallback, useEffect, useState } from "react";
import { ChatMessage, ChatSession } from "../types";

const STORAGE_KEY = "datamind_chat_sessions";
const ACTIVE_SESSION_KEY = "datamind_active_session_id";

function loadStoredSessions(): ChatSession[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as ChatSession[];
  } catch {
    return [];
  }
}

function loadStoredActiveId(): string | null {
  try {
    return localStorage.getItem(ACTIVE_SESSION_KEY);
  } catch {
    return null;
  }
}

export interface UseChatSessionsResult {
  sessions: ChatSession[];
  activeSession: ChatSession | null;
  activeSessionId: string | null;
  createSession: (datasetId: string, datasetName: string) => ChatSession;
  selectSession: (sessionId: string) => ChatSession | null;
  syncMessages: (messages: ChatMessage[], datasetId: string, datasetName: string) => void;
  deleteSession: (sessionId: string) => void;
  startNewChat: () => void;
}

export function useChatSessions(): UseChatSessionsResult {
  const [sessions, setSessions] = useState<ChatSession[]>(loadStoredSessions);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(loadStoredActiveId);

  // Sync sessions to localStorage
  const persistSessions = useCallback((updated: ChatSession[]) => {
    setSessions(updated);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    } catch {
      // Storage quota or disabled in private browsing
    }
  }, []);

  // Sync activeSessionId to localStorage
  useEffect(() => {
    try {
      if (activeSessionId) {
        localStorage.setItem(ACTIVE_SESSION_KEY, activeSessionId);
      } else {
        localStorage.removeItem(ACTIVE_SESSION_KEY);
      }
    } catch {
      // Ignore storage errors
    }
  }, [activeSessionId]);

  const activeSession =
    sessions.find((s) => s.id === activeSessionId) ?? null;

  const createSession = useCallback(
    (datasetId: string, datasetName: string): ChatSession => {
      const newSession: ChatSession = {
        id: crypto.randomUUID ? crypto.randomUUID() : `session-${Date.now()}`,
        title: "New Conversation",
        datasetId,
        datasetName,
        createdAt: Date.now(),
        updatedAt: Date.now(),
        messages: [],
      };
      persistSessions([newSession, ...sessions]);
      setActiveSessionId(newSession.id);
      return newSession;
    },
    [sessions, persistSessions],
  );

  const selectSession = useCallback(
    (sessionId: string): ChatSession | null => {
      const found = sessions.find((s) => s.id === sessionId);
      if (found) {
        setActiveSessionId(sessionId);
        return found;
      }
      return null;
    },
    [sessions],
  );

  const syncMessages = useCallback(
    (messages: ChatMessage[], datasetId: string, datasetName: string) => {
      if (messages.length === 0) return;

      const firstUserMsg = messages.find((m) => m.role === "user");
      const title = firstUserMsg
        ? firstUserMsg.question.slice(0, 42) + (firstUserMsg.question.length > 42 ? "…" : "")
        : "Conversation";

      setSessions((prev) => {
        let updated: ChatSession[];
        const existingIdx = prev.findIndex((s) => s.id === activeSessionId);

        if (existingIdx >= 0) {
          const current = prev[existingIdx];
          const updatedSession: ChatSession = {
            ...current,
            title: current.title === "New Conversation" ? title : current.title,
            datasetId,
            datasetName,
            updatedAt: Date.now(),
            messages,
          };
          updated = [...prev];
          updated[existingIdx] = updatedSession;
        } else {
          const newId = activeSessionId || (crypto.randomUUID ? crypto.randomUUID() : `session-${Date.now()}`);
          setActiveSessionId(newId);
          const newSession: ChatSession = {
            id: newId,
            title,
            datasetId,
            datasetName,
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messages,
          };
          updated = [newSession, ...prev];
        }

        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
        } catch {
          // Ignore
        }
        return updated;
      });
    },
    [activeSessionId],
  );

  const deleteSession = useCallback(
    (sessionId: string) => {
      const updated = sessions.filter((s) => s.id !== sessionId);
      persistSessions(updated);
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
      }
    },
    [sessions, activeSessionId, persistSessions],
  );

  const startNewChat = useCallback(() => {
    setActiveSessionId(null);
  }, []);

  return {
    sessions,
    activeSession,
    activeSessionId,
    createSession,
    selectSession,
    syncMessages,
    deleteSession,
    startNewChat,
  };
}
