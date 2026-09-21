/**
 * SuggestedQuestions — context-aware follow-up chips.
 * Shown after assistant responses.
 * - Per-message "×" dismisses chips for that single message.
 * - "Turn off suggestions" disables them for the whole session.
 */
import { useState } from "react";

export default function SuggestedQuestions({ suggestions, onSelect, onDisable, messageId }) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed || !suggestions || suggestions.length === 0) return null;

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 animate-fade-up" style={{ animationDelay: "200ms" }}>
      <span className="text-[10px] font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
        Related
      </span>
      {suggestions.map((q, idx) => (
        <button
          key={`${messageId}-${idx}`}
          onClick={() => onSelect(q)}
          className="suggestion-chip"
          title={q}
          type="button"
        >
          <svg className="h-3 w-3 shrink-0 opacity-50" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01" />
          </svg>
          <span className="truncate">{q}</span>
        </button>
      ))}
      <button
        onClick={() => setDismissed(true)}
        className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[var(--text-tertiary)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--text-muted)]"
        aria-label="Dismiss suggestions for this message"
        title="Hide suggestions for this reply"
        type="button"
      >
        <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden>
          <path d="M18 6 6 18M6 6l12 12" />
        </svg>
      </button>
      {onDisable && (
        <button
          onClick={onDisable}
          className="ml-1 inline-flex items-center gap-1 text-[11px] text-[var(--text-tertiary)] transition hover:text-[var(--text-muted)]"
          type="button"
        >
          Turn off suggestions
        </button>
      )}
    </div>
  );
}