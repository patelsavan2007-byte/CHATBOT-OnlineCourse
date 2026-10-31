/**
 * AssistantMessage - renders the assistant's response.
 * Rich text, sources disclosure, feedback (thumbs with optional reason and rollback),
 * copy, regenerate (last only), quick replies, dynamic suggested questions.
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

function AssistantAvatar() {
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <div
        className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border text-xs font-semibold select-none"
        style={{
          borderColor: "var(--border)",
          background: "var(--accent-surface)",
          color: "var(--accent)",
        }}
        aria-hidden="true"
      >
        C
      </div>
    );
  }

  return (
    <img
      src={ASSISTANT_AVATAR}
      alt={ASSISTANT_NAME}
      onError={() => setFailed(true)}
      className="mt-0.5 h-7 w-7 shrink-0 rounded-lg object-cover ring-1 ring-[var(--border)]"
    />
  );
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);

  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore clipboard error */
    }
  }, [text]);

  return (
    <button
      onClick={copy}
      className="flex h-6 w-6 items-center justify-center rounded-md text-[var(--muted)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--text)] focus-visible:outline-2"
      aria-label={copied ? "Copied" : "Copy response"}
      title={copied ? "Copied" : "Copy"}
      type="button"
    >
      {copied ? (
        <svg className="h-3.5 w-3.5 text-emerald-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden>
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

/* Thumbs up / down with optimistic update, rollback on error, and optional reason on Bad */
function FeedbackButtons({ messageId }) {
  const [feedback, setFeedback] = useState(() => {
    try {
      return localStorage.getItem(`charusat_feedback_${messageId}`) || null;
    } catch {
      return null;
    }
  });
  const [showReasonInput, setShowReasonInput] = useState(false);
  const [reasonText, setReasonText] = useState("");
  const [submittingReason, setSubmittingReason] = useState(false);

  const handleFeedback = async (value) => {
    if (feedback === value) return;
    const prevFeedback = feedback;
    setFeedback(value);

    try {
      localStorage.setItem(`charusat_feedback_${messageId}`, value);
    } catch {
      /* ignore */
    }

    if (value === "down") {
      setShowReasonInput(true);
    } else {
      setShowReasonInput(false);
    }

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
        // Rollback on failure
        setFeedback(prevFeedback);
        try {
          if (prevFeedback) {
            localStorage.setItem(`charusat_feedback_${messageId}`, prevFeedback);
          } else {
            localStorage.removeItem(`charusat_feedback_${messageId}`);
          }
        } catch {
          /* ignore */
        }
        setShowReasonInput(false);
        console.warn("Feedback sync failed:", err.message);
      }
    }
  };

  const handleReasonSubmit = async (e) => {
    e.preventDefault();
    if (!reasonText.trim() || submittingReason) {
      setShowReasonInput(false);
      return;
    }
    setSubmittingReason(true);
    try {
      if (messageId && messageId !== "msg") {
        await apiFetch("/api/chat/feedback", {
          method: "POST",
          body: JSON.stringify({
            message_id: String(messageId),
            feedback: "thumbs_down",
            reason: reasonText.trim(),
          }),
        });
      }
    } catch (err) {
      console.warn("Failed to submit reason:", err.message);
    } finally {
      setSubmittingReason(false);
      setShowReasonInput(false);
    }
  };

  return (
    <div className="relative flex flex-col gap-1">
      <div className="flex items-center gap-0.5" role="group" aria-label="Rate this response">
        <button
          onClick={() => handleFeedback("up")}
          className={`flex h-6 w-6 items-center justify-center rounded-md transition focus-visible:outline-2 ${
            feedback === "up"
              ? "text-emerald-600 bg-[var(--surface-hover)]"
              : "text-[var(--muted)] hover:bg-[var(--surface-hover)] hover:text-[var(--text)]"
          }`}
          aria-label="Good response"
          title={feedback === "up" ? "Marked as good response" : "Good response"}
          type="button"
        >
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill={feedback === "up" ? "currentColor" : "none"} stroke="currentColor" strokeWidth={feedback === "up" ? "0" : "1.75"} aria-hidden>
            <path d="M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3zM7 22H4a2 2 0 01-2-2v-7a2 2 0 012-2h3" />
          </svg>
        </button>

        <button
          onClick={() => handleFeedback("down")}
          className={`flex h-6 w-6 items-center justify-center rounded-md transition focus-visible:outline-2 ${
            feedback === "down"
              ? "text-rose-600 bg-[var(--surface-hover)]"
              : "text-[var(--muted)] hover:bg-[var(--surface-hover)] hover:text-[var(--text)]"
          }`}
          aria-label="Bad response"
          title={feedback === "down" ? "Marked as bad response" : "Bad response"}
          type="button"
        >
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill={feedback === "down" ? "currentColor" : "none"} stroke="currentColor" strokeWidth={feedback === "down" ? "0" : "1.75"} aria-hidden>
            <path d="M10 15v4a3 3 0 003 3l4-9V2H5.72a2 2 0 00-2 1.7l-1.38 9a2 2 0 002 2.3zM17 2h3a2 2 0 012 2v7a2 2 0 01-2 2h-3" />
          </svg>
        </button>
      </div>

      {showReasonInput && (
        <form
          onSubmit={handleReasonSubmit}
          className="mt-1 flex flex-col gap-1.5 rounded-lg border p-2 text-xs shadow-sm"
          style={{ borderColor: "var(--border)", background: "var(--surface)" }}
        >
          <label htmlFor={`reason-${messageId}`} className="text-[11px] font-medium" style={{ color: "var(--text)" }}>
            What was wrong with this answer? (optional)
          </label>
          <input
            id={`reason-${messageId}`}
            type="text"
            value={reasonText}
            onChange={(e) => setReasonText(e.target.value)}
            placeholder="Inaccurate, incomplete, confusing..."
            className="rounded border px-2 py-1 text-xs outline-none"
            style={{
              borderColor: "var(--border)",
              background: "var(--page)",
              color: "var(--text)",
            }}
          />
          <div className="flex justify-end gap-1.5 pt-0.5">
            <button
              type="button"
              onClick={() => setShowReasonInput(false)}
              className="rounded-md border px-2 py-0.5 text-[11px]"
              style={{ borderColor: "var(--border)", color: "var(--muted)" }}
            >
              Skip
            </button>
            <button
              type="submit"
              disabled={submittingReason}
              className="rounded-md px-2 py-0.5 text-[11px] font-medium text-white"
              style={{ background: "var(--accent)" }}
            >
              {submittingReason ? "Sending..." : "Submit"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

function RegenerateButton({ onRegenerate }) {
  if (!onRegenerate) return null;
  return (
    <button
      onClick={onRegenerate}
      className="flex h-6 w-6 items-center justify-center rounded-md text-[var(--muted)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--text)] focus-visible:outline-2"
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

function SourcesDisclosure({ sources }) {
  if (!sources || !Array.isArray(sources) || sources.length === 0) return null;

  return (
    <details className="mt-2.5 rounded-lg border px-3 py-2 text-xs" style={{ borderColor: "var(--border)", background: "var(--surface-2)" }}>
      <summary className="cursor-pointer select-none font-medium hover:underline focus-visible:outline-none" style={{ color: "var(--muted)" }}>
        Sources ({sources.length})
      </summary>
      <ul className="mt-2 space-y-1 pl-4 list-disc" style={{ color: "var(--text-2)" }}>
        {sources.map((src, i) => {
          if (typeof src === "string") {
            return <li key={i}>{src}</li>;
          }
          const docName = src.document_name || src.document || src.title || src.name || "CHARUSAT Document";
          const pageStr = src.page !== undefined && src.page !== null ? ` (p. ${src.page})` : "";
          return (
            <li key={i}>
              {src.url ? (
                <a
                  href={src.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline hover:opacity-80"
                  style={{ color: "var(--accent)" }}
                >
                  {docName}{pageStr}
                </a>
              ) : (
                <span>{docName}{pageStr}</span>
              )}
            </li>
          );
        })}
      </ul>
    </details>
  );
}

function QuickReplies({ replies, onSelect }) {
  if (!replies || replies.length === 0) return null;
  return (
    <div className="mt-3 grid grid-cols-4 gap-2 max-w-sm" role="group" aria-label="Choose a programme">
      {replies.map((reply) => (
        <button
          key={reply}
          onClick={() => onSelect?.(reply)}
          className="inline-flex h-8 items-center justify-center rounded-md border px-3 text-xs font-semibold transition cursor-pointer hover:bg-[var(--surface-hover)] focus-visible:outline-2"
          style={{
            borderColor: "var(--border)",
            background: "var(--surface-2)",
            color: "var(--accent)",
          }}
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
  sources,
  isError,
  timestamp,
  onRetry,
  onRegenerate,
  isStreaming,
  quickReplies,
  onSuggestedQuestion,
}) {
  return (
    <div className="group flex gap-3">
      {/* Avatar */}
      <AssistantAvatar />

      {/* Content */}
      <div className="min-w-0 flex-1">
        {isError ? (
          <div
            className="flex items-start gap-2.5 rounded-lg border px-4 py-3 text-sm"
            style={{
              borderColor: "var(--danger-border)",
              background: "var(--danger-surface)",
              color: "var(--danger)",
            }}
          >
            <svg className="mt-0.5 h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <div className="flex-1">{content}</div>
            {onRetry && (
              <button
                onClick={onRetry}
                className="inline-flex shrink-0 items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition hover:opacity-80 cursor-pointer"
                style={{ borderColor: "var(--danger-border)", color: "var(--danger)" }}
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

            <SourcesDisclosure sources={sources} />

            {!isStreaming && (
              <>
                {/* Actions: copy + feedback + regenerate + timestamp */}
                <div className="mt-2 flex items-center gap-1 opacity-90 transition sm:opacity-0 sm:group-hover:opacity-100 focus-within:opacity-100">
                  <CopyButton text={content} />
                  <FeedbackButtons messageId={messageId || (timestamp ? `${timestamp}` : "msg")} />
                  <RegenerateButton onRegenerate={onRegenerate} />
                  <span className="ml-1 text-[10px]" style={{ color: "var(--muted)" }}>
                    {formatTime(timestamp)}
                  </span>
                </div>

                <QuickReplies replies={quickReplies} onSelect={onSuggestedQuestion} />
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
