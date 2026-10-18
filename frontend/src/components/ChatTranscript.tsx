/**
 * src/components/ChatTranscript.tsx
 * Transcript container for the chat history, handling empty state,
 * user/assistant messages, loading indicator, and error notifications.
 */
import { useEffect, useRef } from "react";
import { ChatError, ChatMessage, Dataset, UserMessage } from "../types";
import { AnswerCard } from "./AnswerCard";
import { EmptyState } from "./EmptyState";
import { ErrorMessage } from "./ErrorMessage";
import { LoadingMessage } from "./LoadingMessage";
import { UserBubble } from "./UserBubble";

interface Props {
  messages: ChatMessage[];
  loading: boolean;
  error: ChatError | null;
  dataset: Dataset | null;
  onSelectQuestion: (question: string) => void;
  onCancel: () => void;
  onRetry: () => void;
  onFocusComposer?: () => void;
}

export function ChatTranscript({
  messages,
  loading,
  error,
  dataset,
  onSelectQuestion,
  onCancel,
  onRetry,
  onFocusComposer,
}: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom whenever messages change, loading starts, or an error is recorded
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading, error]);

  const isEmpty = messages.length === 0 && !loading && !error;

  if (isEmpty) {
    return (
      <EmptyState
        dataset={dataset}
        onSelectQuestion={onSelectQuestion}
        disabled={loading}
      />
    );
  }

  return (
    <div
      ref={scrollRef}
      className="chat-transcript"
      role="log"
      aria-label="Conversation history"
      aria-live="polite"
    >
      {messages.map((msg, index) => {
        if (msg.role === "user") {
          return <UserBubble key={msg.id} message={msg} />;
        }

        // Locate previous user question to provide context for clarification
        let userQuestion: string | undefined;
        for (let i = index - 1; i >= 0; i--) {
          if (messages[i].role === "user") {
            userQuestion = (messages[i] as UserMessage).question;
            break;
          }
        }

        return (
          <AnswerCard
            key={msg.id}
            message={msg}
            userQuestion={userQuestion}
            exampleQuestions={dataset?.example_questions}
            onSelectQuestion={onSelectQuestion}
            onFocusComposer={onFocusComposer}
          />
        );
      })}

      {loading && <LoadingMessage onCancel={onCancel} />}

      {error && <ErrorMessage error={error} onRetry={onRetry} />}
    </div>
  );
}
