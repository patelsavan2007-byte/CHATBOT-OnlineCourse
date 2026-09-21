/**
 * AssistantMessage — renders the assistant's response.
 * Rich text, copy, feedback (thumbs), suggested follow-ups, error retry,
 * source chips and a timestamp. Theme-aware throughout.
 */
import { useState, useCallback } from "react";
import RichText from "../RichText.jsx";
import SuggestedQuestions from "./SuggestedQuestions.jsx";

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

/* ---- Thumbs up / down (best-effort, stored locally) ---- */
function FeedbackButtons({ messageId }) {
  const [feedback, setFeedback] = useState(null);

  const send = (value) => {
    if (feedback) return;
    setFeedback(value);
    try {
      const key = `charusat_feedback_${messageId}`;
      localStorage.setItem(key, value);
    } catch {/* ignore */}
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

export default function AssistantMessage({
  content,
  sources,
  isError,
  timestamp,
  suggestions,
  onSelectSuggestion,
  suggestionsEnabled,
  onDisableSuggestions,
  onRetry,
}) {
  const pdfSources = (sources || []).filter((s) => /\.pdf$/i.test(String(s?.source || "")));

  return (
    <div className="flex gap-3 animate-fade-up">
      {/* Avatar */}
      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-primary)]/15 ring-1 ring-[var(--border-primary)]">
        <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 fill-[var(--accent-primary)]" aria-hidden>
          <path d="M12 3 1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
        </svg>
      </div>

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

            {/* Source chips (official PDFs only) */}
            {pdfSources.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {pdfSources.slice(0, 4).map((src, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1.5 rounded-md border border-[var(--border-primary)] bg-[var(--surface-hover)] px-2 py-0.5 text-[11px] text-[var(--text-tertiary)]"
                    title={src.score ? `Relevance: ${Math.round(src.score * 100)}%` : undefined}
                  >
                    <svg className="h-3 w-3 text-[var(--accent-primary)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                    </svg>
                    {src.source}
                    {src.page != null && <span className="text-[var(--text-muted)]"> p.{src.page}</span>}
                  </span>
                ))}
              </div>
            )}

            {/* Actions — copy + feedback + timestamp */}
            <div className="mt-2 flex items-center gap-1">
              <CopyButton text={content} />
              <FeedbackButtons messageId={timestamp ? `${timestamp}` : "msg"} />
              <span className="ml-1 text-[10px] text-[var(--text-tertiary)]">
                {formatTime(timestamp)}
              </span>
            </div>

            {/* Suggested follow-ups */}
            {!isError && suggestionsEnabled && onSelectSuggestion && (
              <SuggestedQuestions
                suggestions={suggestions}
                messageId={timestamp ? `${timestamp}` : "msg"}
                onSelect={onSelectSuggestion}
                onDisable={onDisableSuggestions}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}