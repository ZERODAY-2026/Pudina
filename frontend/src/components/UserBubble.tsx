/**
 * src/components/UserBubble.tsx
 * Renders a user's question bubble in the transcript.
 */
import { UserMessage } from "../types";

interface Props {
  message: UserMessage;
}

export function UserBubble({ message }: Props) {
  const timeString = new Date(message.timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className="chat-message chat-message--user" role="article" aria-label="User question">
      <div className="user-bubble">{message.question}</div>
      <time className="message-time" dateTime={new Date(message.timestamp).toISOString()}>
        {timeString}
      </time>
    </div>
  );
}
