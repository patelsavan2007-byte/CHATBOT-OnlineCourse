/**
 * AssistantMessage — renders the assistant's response.
 * Rich text, copy, feedback (thumbs), suggested follow-ups, error retry,
 * source chips and a timestamp. Theme-aware throughout.
 */
import { useState, useCallback } from "react";
import RichText from "../RichText.jsx";
import { apiFetch } from "../../services/api.js";
import { ASSISTANT_AVATAR, ASSISTANT_NAME } from "../../config/branding.js";


function formatTime(t) {
  try {
    return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(new Date(t));
  } catch {
    return "";
  }
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);

  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {/* ignore */}
  }, [text]);

  return (
    <button
      onClick={copy}
      className={`flex h-6 w-6 items-center justify-center rounded text-[var(--text-muted)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--text-secondary)] ${
        copied ? "text-emerald-500" : ""
      }`}
      aria-label={copied ? "Copied" : "Copy response"}
      title={copied ? "Copied!" : "Copy"}
      type="button"
    >
      {copied ? (
        <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      ) : (
        <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
          <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
        </svg>
      )}
    </button>
  );
}

/* ---- Thumbs up / down (persisted in local state and synced to /api/chat/feedback) ---- */
function FeedbackButtons({ messageId }) {
  const [feedback, setFeedback] = useState(() => {
    try {
      return localStorage.getItem(`charusat_feedback_${messageId}`) || null;
    } catch {
      return null;
    }
  });

  const send = async (value) => {
    if (feedback) return;
    setFeedback(value);
    try {
      const key = `charusat_feedback_${messageId}`;
      localStorage.setItem(key, value);
    } catch {/* ignore */}

    if (messageId && messageId !== "msg") {
      try {
        await apiFetch("/api/chat/feedback", {
          method: "POST",
          body: JSON.stringify({
            message_id: String(messageId),
            feedback: value === "up" ? "thumbs_up" : "thumbs_down",
          }),
        });
      } catch (err) {
        // Best-effort; message may be guest session
        console.warn("Feedback sync failed:", err.message);
      }
    }
  };

  return (
    <div className="flex items-center gap-0.5" role="group" aria-label="Rate this response">
      <button
        onClick={() => send("up")}
        className={`flex h-6 w-6 items-center justify-center rounded transition ${
          feedback === "up"
            ? "text-emerald-500"
            : "text-[var(--text-muted)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-secondary)]"
        }`}
        aria-label="Helpful response"
        title={feedback === "up" ? "Thanks for the feedback!" : "Good response"}
        type="button"
      >
        {feedback === "up" ? (
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
            <path d="M2 21h3V10H2v11zm18-10h-6.5l.93-4.677c.06-.394-.032-.8-.25-1.11-.254-.36-.687-.578-1.13-.578H10l-4.36 5.14A1.98 1.98 0 005 11.937V19c0 1.103.897 2 2 2h8.36c.83 0 1.555-.505 1.842-1.286l2.85-7.84A2 2 0 0118 9.82V11z" />
          </svg>
        ) : (
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
            <path d="M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3zM7 22H4a2 2 0 01-2-2v-7a2 2 0 012-2h3" />
          </svg>
        )}
      </button>
      <button
        onClick={() => send("down")}
        className={`flex h-6 w-6 items-center justify-center rounded transition ${
          feedback === "down"
            ? "text-rose-500"
            : "text-[var(--text-muted)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-secondary)]"
        }`}
        aria-label="Unhelpful response"
        title={feedback === "down" ? "Thanks for the feedback!" : "Could be better"}
        type="button"
      >
        {feedback === "down" ? (
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
            <path d="M22 3H9.64c-.83 0-1.555.505-1.842 1.286l-2.85 7.84A2.001 2.001 0 005.36 14H8v9h11a2 2 0 002-2l1.9-10.93A2 2 0 0010.86 8 2.014 2.014 0 0011 8.063V11h8.36c.692 0 1.353.365 1.72.995L22 12V3zM2 3h3v11H2V3z" />
          </svg>
        ) : (
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
            <path d="M10 15v4a3 3 0 003 3l4-9V2H5.72a2 2 0 00-2 1.7l-1.38 9a2 2 0 002 2.3zM17 2h3a2 2 0 012 2v7a2 2 0 01-2 2h-3" />
          </svg>
        )}
      </button>
    </div>
  );
}

function RegenerateButton({ onRegenerate }) {
  if (!onRegenerate) return null;
  return (
    <button
      onClick={onRegenerate}
      className="flex h-6 w-6 items-center justify-center rounded text-[var(--text-muted)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--text-secondary)] focus-visible:outline-2"
      aria-label="Regenerate response"
      title="Regenerate response"
      type="button"
    >
      <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      </svg>
    </button>
  );
}

function QuickReplies({ replies, onSelect }) {
  if (!replies || replies.length === 0) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-2" role="group" aria-label="Choose a programme">
      {replies.map((reply) => (
        <button
          key={reply}
          onClick={() => onSelect?.(reply)}
          className="inline-flex items-center rounded-full border border-[var(--accent-primary)]/40 bg-[var(--accent-primary)]/10 px-3.5 py-1.5 text-xs font-medium text-[var(--accent-primary)] transition hover:bg-[var(--accent-primary)] hover:text-white"
          type="button"
        >
          {reply}
        </button>
      ))}
    </div>
  );
}

export default function AssistantMessage({
  messageId,
  content,
  isError,
  timestamp,
  onRetry,
  onRegenerate,
  isStreaming,
  suggestedQuestions,
  quickReplies,
  onSuggestedQuestion,
}) {
  return (
    <div className="group flex gap-3">
      {/* Avatar */}
      <img
        src={ASSISTANT_AVATAR}
        alt={ASSISTANT_NAME}
        className="mt-0.5 h-7 w-7 shrink-0 rounded-lg object-cover ring-1 ring-[var(--border-primary)]"
      />

      {/* Content */}
      <div className="min-w-0 flex-1">
        {isError ? (
          <div className="flex items-start gap-2.5 rounded-xl border border-[var(--error-border)] bg-[var(--error-surface)] px-4 py-3 text-sm text-[var(--error)]">
            <svg className="mt-0.5 h-4 w-4 shrink-0 text-[var(--error)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <div className="flex-1">{content}</div>
            {onRetry && (
              <button
                onClick={onRetry}
                className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-[var(--error-border)] px-2.5 py-1 text-xs font-medium text-[var(--error)] transition hover:opacity-80"
                type="button"
              >
                <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                  <path d="M1 4v6h6M23 20v-6h-6" />
                  <path d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15" />
                </svg>
                Retry
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="prose-chat">
              <RichText text={content} />
            </div>

            {!isStreaming && (
              <>
                {/* Actions — copy + feedback + regenerate + timestamp */}
                <div className="mt-2 flex items-center gap-1 opacity-90 transition sm:opacity-0 sm:group-hover:opacity-100 focus-within:opacity-100">
                  <CopyButton text={content} />
                  <FeedbackButtons messageId={messageId || (timestamp ? `${timestamp}` : "msg")} />
                  <RegenerateButton onRegenerate={onRegenerate} />
                  <span className="ml-1 text-[10px] text-[var(--text-tertiary)]">
                    {formatTime(timestamp)}
                  </span>
                </div>

                <QuickReplies replies={quickReplies} onSelect={onSuggestedQuestion} />

                {/* Dynamic suggested follow-up questions */}
                {suggestedQuestions && suggestedQuestions.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {suggestedQuestions.map((q, i) => (
                      <button
                        key={i}
                        onClick={() => onSuggestedQuestion?.(q)}
                        className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border-primary)] bg-[var(--surface-hover)] px-3 py-1.5 text-xs text-[var(--text-secondary)] transition hover:border-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/10 hover:text-[var(--accent-primary)] cursor-pointer"
                        type="button"
                      >
                        <svg className="h-3 w-3 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                          <circle cx="11" cy="11" r="8" />
                          <path d="m21 21-4.35-4.35" />
                        </svg>
                        {q}
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}