/**
 * src/hooks/useChat.ts
 * Core chat state machine.  Components are purely presentational; all
 * conversation logic lives here.
 *
 * Flow:
 *   send(q)  → adds UserMessage, calls API with last-10-turn history
 *           → on success: appends AssistantMessage
 *           → on abort:  removes the pending UserMessage (clean cancel)
 *           → on error:  records ChatError (user message stays for retry)
 *
 *   cancel() → aborts in-flight request; removes the pending user message.
 *   retry()  → re-issues the last failed question without a new user message.
 *
 * When datasetId changes the conversation is automatically cleared.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { ask } from "../api/client";
import {
  ApiError,
  AssistantMessage,
  ChatError,
  ChatMessage,
  HistoryMessage,
  UserMessage,
} from "../types";

export interface UseChatResult {
  messages: ChatMessage[];
  loading: boolean;
  error: ChatError | null;
  send: (question: string) => Promise<void>;
  cancel: () => void;
  retry: () => Promise<void>;
  clearMessages: () => void;
  loadMessages: (msgs: ChatMessage[]) => void;
}

/** Maximum history entries sent per request (per API contract). */
const HISTORY_LIMIT = 10;

/** Convert stored messages → HistoryMessage[] capped at HISTORY_LIMIT. */
function buildHistory(messages: ChatMessage[]): HistoryMessage[] {
  const entries: HistoryMessage[] = messages.map((msg) => {
    if (msg.role === "user") {
      return { role: "user", content: msg.question };
    }
    const content =
      msg.response.answer ?? msg.response.clarifying_question ?? "";
    return { role: "assistant", content };
  });
  return entries.slice(-HISTORY_LIMIT);
}

function buildChatError(
  err: unknown,
  lastQuestion: string,
  lastDatasetId: string,
): ChatError {
  if (err instanceof ApiError) {
    const canRetry =
      err.code === "UPSTREAM_TIMEOUT" || err.code === "INTERNAL_ERROR";
    return {
      message: err.message,
      code: err.code,
      canRetry,
      lastQuestion,
      lastDatasetId,
    };
  }
  // Network error or unexpected throw.
  return {
    message: "Network error. Check your connection and try again.",
    canRetry: true,
    lastQuestion,
    lastDatasetId,
  };
}

export function useChat(datasetId: string | null): UseChatResult {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ChatError | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Clear conversation whenever the selected dataset changes.
  const prevDatasetRef = useRef(datasetId);
  useEffect(() => {
    if (prevDatasetRef.current !== datasetId) {
      prevDatasetRef.current = datasetId;
      setMessages([]);
      setError(null);
    }
  }, [datasetId]);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  const loadMessages = useCallback((msgs: ChatMessage[]) => {
    setMessages(msgs);
    setError(null);
  }, []);

  const _issue = useCallback(
    async (
      question: string,
      targetDatasetId: string,
      historyMessages: ChatMessage[],
      isPending: boolean, // true = user message already in `messages`
    ) => {
      setLoading(true);
      setError(null);

      const ac = new AbortController();
      abortRef.current = ac;

      const history = buildHistory(
        isPending ? historyMessages.slice(0, -1) : historyMessages,
      );

      try {
        const response = await ask(
          question,
          targetDatasetId,
          history,
          ac.signal,
        );
        const assistantMsg: AssistantMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          response,
          timestamp: Date.now(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          // User-initiated cancel: remove the pending user message.
          if (isPending) {
            setMessages((prev) => prev.slice(0, -1));
          }
          return;
        }
        setError(buildChatError(err, question, targetDatasetId));
      } finally {
        setLoading(false);
        abortRef.current = null;
      }
    },
    [],
  );

  const send = useCallback(
    async (question: string) => {
      if (!datasetId || loading) return;

      const trimmed = question.trim();
      if (!trimmed || trimmed.length > 1000) return;

      const userMsg: UserMessage = {
        id: crypto.randomUUID(),
        role: "user",
        question: trimmed,
        timestamp: Date.now(),
      };

      // Snapshot messages before the state update for history building.
      let snapshot: ChatMessage[] = [];
      setMessages((prev) => {
        snapshot = prev;
        return [...prev, userMsg];
      });

      // Wait one tick so `snapshot` is populated before _issue reads it.
      await Promise.resolve();

      await _issue(trimmed, datasetId, [...snapshot, userMsg], true);
    },
    [datasetId, loading, _issue],
  );

  const retry = useCallback(async () => {
    if (!error || loading) return;
    const { lastQuestion, lastDatasetId } = error;

    // The pending user message is already the last item in messages.
    let snapshot: ChatMessage[] = [];
    setMessages((prev) => {
      snapshot = prev;
      return prev;
    });
    setError(null);

    await Promise.resolve();
    await _issue(lastQuestion, lastDatasetId, snapshot, true);
  }, [error, loading, _issue]);

  return { messages, loading, error, send, cancel, retry, clearMessages, loadMessages };
}
