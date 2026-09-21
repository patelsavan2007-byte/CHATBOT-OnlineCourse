/**
 * MessageList — scrolling container for chat messages.
 * Auto-scrolls to bottom; shows a scroll-to-bottom button when the user is
 * scrolled away from the latest message. Theme-aware.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import UserMessage      from "./UserMessage.jsx";
import AssistantMessage from "./AssistantMessage.jsx";

function TypingIndicator() {
  return (
    <div className="flex gap-3 animate-fade-up">
      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-primary)]/15 ring-1 ring-[var(--border-primary)]">
        <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 fill-[var(--accent-primary)]" aria-hidden>
          <path d="M12 3 1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
        </svg>
      </div>
      <div className="mt-1 flex items-center gap-1.5 px-1" role="status" aria-label="Assistant is typing">
        <span className="typing-dot" />
        <span className="typing-dot" />
        <span className="typing-dot" />
      </div>
    </div>
  );
}

export default function MessageList({
  messages,
  isLoading,
  onSendPrompt,
  suggestionsEnabled,
  onDisableSuggestions,
  onRetry,
}) {
  const scrollRef  = useRef(null);
  const bottomRef  = useRef(null);
  const [stickToBottom, setStickToBottom] = useState(true);

  const isNearBottom = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  }, []);

  // Auto-scroll whenever new content arrives (if already near the bottom)
  useEffect(() => {
    if (stickToBottom) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messages, isLoading, stickToBottom]);

  const handleScroll = () => {
    setStickToBottom(isNearBottom());
  };

  const scrollToBottom = () => {
    setStickToBottom(true);
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  };

  return (
    <div className="relative flex min-h-0 flex-1">
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto chat-scroll"
        role="log"
        aria-live="polite"
        aria-label="Conversation"
      >
        <div className="mx-auto max-w-3xl space-y-6 px-4 py-6 sm:px-6">
          {messages.map((msg, idx) => (
            msg.role === "user" ? (
              <UserMessage key={msg.id} content={msg.content} timestamp={msg.timestamp} />
            ) : (
              <AssistantMessage
                key={msg.id}
                content={msg.content}
                sources={msg.sources}
                isError={msg.isError}
                timestamp={msg.timestamp}
                suggestions={msg.suggested_questions}
                onSelectSuggestion={onSendPrompt}
                suggestionsEnabled={suggestionsEnabled && !msg.isError}
                onDisableSuggestions={onDisableSuggestions}
                onRetry={msg.isError ? (() => onRetry?.(msg)) : undefined}
              />
            )
          ))}

          {isLoading && <TypingIndicator />}

          <div ref={bottomRef} className="h-1" aria-hidden />
        </div>
      </div>

      {/* Scroll-to-bottom FAB */}
      {!stickToBottom && !isLoading && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-4 right-6 flex h-8 w-8 items-center justify-center rounded-full border border-[var(--border-primary)] bg-[var(--surface-elevated)] text-[var(--text-secondary)] shadow-md transition hover:bg-[var(--surface-active)] hover:text-[var(--text-primary)] animate-scale-in"
          aria-label="Scroll to latest message"
          title="Scroll to latest"
          type="button"
        >
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
            <path d="M12 5v14M19 12l-7 7-7-7" />
          </svg>
        </button>
      )}
    </div>
  );
}