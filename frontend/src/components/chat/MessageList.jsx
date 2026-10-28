/**
 * MessageList — scrolling container for chat messages.
 * Auto-scrolls to bottom; shows a scroll-to-bottom button when the user is
 * scrolled away from the latest message. Theme-aware.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import UserMessage      from "./UserMessage.jsx";
import AssistantMessage from "./AssistantMessage.jsx";
import { ASSISTANT_AVATAR, DEFAULT_THINKING_MESSAGE } from "../../config/branding.js";

function TypingIndicator({ status }) {
  return (
    <div className="flex gap-3">
      <img
        src={ASSISTANT_AVATAR}
        alt=""
        className="mt-0.5 h-7 w-7 shrink-0 rounded-lg object-cover ring-1 ring-[var(--border-primary)]"
      />
      <div
        className="mt-1 flex items-center gap-2 px-1 text-[13px] text-[var(--text-tertiary)]"
        role="status"
        aria-live="polite"
        aria-label={status || "Assistant is thinking"}
      >
        <span className="flex items-center gap-1.5">
          <span className="typing-dot" />
          <span className="typing-dot" />
          <span className="typing-dot" />
        </span>
        <span className="animate-pulse">{status || DEFAULT_THINKING_MESSAGE}</span>
      </div>
    </div>
  );
}

export default function MessageList({
  messages,
  isLoading,
  thinkingStatus,
  onRetry,
  onRegenerate,
  onSuggestedQuestion,
}) {

  const scrollRef  = useRef(null);
  const bottomRef  = useRef(null);
  const [stickToBottom, setStickToBottom] = useState(true);

  const isNearBottom = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  }, []);

  // Auto-scroll whenever content grows, but only if the user is already near
  // the bottom. Direct scrollTop updates avoid the jitter of smooth scrolling
  // during token streaming.
  useEffect(() => {
    if (!stickToBottom) return;
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, isLoading, thinkingStatus, stickToBottom]);

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
          {messages.map((msg, idx) => {
            const isLastAssistant =
              msg.role === "assistant" &&
              idx === messages.length - 1 &&
              !isLoading;
            return msg.role === "user" ? (
              <UserMessage key={msg.id} content={msg.content} timestamp={msg.timestamp} />
            ) : (
              <AssistantMessage
                key={msg.id}
                messageId={msg.id}
                content={msg.content}
                isError={msg.isError}
                timestamp={msg.timestamp}
                onRetry={msg.isError ? (() => onRetry?.(msg)) : undefined}
                onRegenerate={idx === messages.length - 1 && !msg.isError && !msg.isStreaming ? onRegenerate : undefined}
                isStreaming={msg.isStreaming}
                suggestedQuestions={isLastAssistant ? (msg.suggestedQuestions || []) : []}
                quickReplies={isLastAssistant ? (msg.quickReplies || []) : []}
                onSuggestedQuestion={onSuggestedQuestion}
              />
            );
          })}


          {isLoading && <TypingIndicator status={thinkingStatus} />}

          <div ref={bottomRef} className="h-1" aria-hidden />
        </div>
      </div>

      {/* Scroll-to-bottom FAB */}
      {!stickToBottom && !isLoading && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-4 right-6 flex h-8 w-8 items-center justify-center rounded-full border border-[var(--border-primary)] bg-[var(--surface-elevated)] text-[var(--text-secondary)] shadow-md transition hover:bg-[var(--surface-active)] hover:text-[var(--text-primary)] animate-scale-in" /* allow-round: scroll FAB circle is a standard UI convention */
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