/**
 * ChatComposer — message input bar with real-time typing suggestions.
 * Auto-growing textarea (1 to 6 lines), rounded floating style,
 * 1000-character limit with counter near limit, keyboard navigation (Up/Down/Enter/Esc),
 * accessible ARIA combobox + listbox dropdown.
 */
import { useCallback, useRef, useEffect, useState, useMemo } from "react";
import TypingSuggestions from "./TypingSuggestions.jsx";
import { getTypingSuggestions } from "../../lib/questionBank.js";

const MAX_ROWS = 6;
const MAX_CHAR_LIMIT = 1000;
const CHAR_WARN_THRESHOLD = 800;

export default function ChatComposer({
  onSend,
  onStop,
  disabled,
  typingSuggestionsEnabled = true,
  currentProgramme = null,
  questionBank = [],
}) {
  const [text, setText] = useState("");
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [suggestionsOpen, setSuggestionsOpen] = useState(true);
  const textareaRef = useRef(null);

  /* Auto-resize textarea between 1 and MAX_ROWS lines */
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const lineH = 24;
    const maxH = lineH * MAX_ROWS + 16;
    el.style.height = `${Math.min(el.scrollHeight, maxH)}px`;
    el.style.overflowY = el.scrollHeight > maxH ? "auto" : "hidden";
  }, [text]);

  /* Auto-focus on mount and when re-enabled */
  useEffect(() => {
    const el = textareaRef.current;
    if (el && !disabled) {
      el.focus({ preventScroll: true });
    }
  }, [disabled]);

  /* Calculate suggestions client-side */
  const suggestions = useMemo(() => {
    if (!typingSuggestionsEnabled || !suggestionsOpen || disabled) return [];
    if (text.trim().length < 2) return [];
    return getTypingSuggestions(text, currentProgramme, questionBank);
  }, [text, typingSuggestionsEnabled, suggestionsOpen, disabled, currentProgramme, questionBank]);

  /* Reset highlight index when suggestions change */
  useEffect(() => {
    setHighlightedIndex(-1);
  }, [suggestions]);

  const submit = useCallback(
    (overrideText) => {
      const q = (typeof overrideText === "string" ? overrideText : text).trim();
      if (!q || disabled) return;
      onSend(q);
      setText("");
      setSuggestionsOpen(false);
      setHighlightedIndex(-1);
    },
    [text, disabled, onSend]
  );

  const handleSelectSuggestion = useCallback(
    (suggestionText) => {
      submit(suggestionText);
    },
    [submit]
  );

  const handleKeyDown = (e) => {
    // Ignore IME composition events
    if (e.nativeEvent.isComposing) return;

    if (suggestions.length > 0 && suggestionsOpen) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setHighlightedIndex((prev) => (prev + 1 < suggestions.length ? prev + 1 : 0));
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setHighlightedIndex((prev) => (prev - 1 >= 0 ? prev - 1 : suggestions.length - 1));
        return;
      }
      if (e.key === "Escape") {
        e.preventDefault();
        setSuggestionsOpen(false);
        setHighlightedIndex(-1);
        return;
      }
    }

    // Enter behavior: if suggestion highlighted, send suggestion; else send typed text
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (suggestions.length > 0 && suggestionsOpen && highlightedIndex >= 0) {
        handleSelectSuggestion(suggestions[highlightedIndex].text);
      } else {
        submit();
      }
    }
  };

  const handleChange = (e) => {
    const val = e.target.value;
    if (val.length <= MAX_CHAR_LIMIT) {
      setText(val);
      setSuggestionsOpen(true);
    }
  };

  const canSend = text.trim().length > 0 && !disabled;
  const charLen = text.length;
  const showCount = charLen >= CHAR_WARN_THRESHOLD;
  const isNearLimit = charLen >= MAX_CHAR_LIMIT - 50;

  const listId = "composer-typing-suggestions-list";
  const highlightedOptionId =
    highlightedIndex >= 0 && suggestions[highlightedIndex]
      ? `${listId}-item-${highlightedIndex}`
      : undefined;

  return (
    <div className="shrink-0 border-t px-3 py-3 sm:px-4 sm:py-4" style={{ borderColor: "var(--border)", background: "var(--surface)" }}>
      <div className="mx-auto max-w-3xl relative">
        {/* Typing Suggestions Dropdown */}
        {suggestions.length > 0 && suggestionsOpen && (
          <TypingSuggestions
            suggestions={suggestions}
            highlightedIndex={highlightedIndex}
            onSelect={handleSelectSuggestion}
            listId={listId}
          />
        )}

        {/* Floating Composer Bar (radius: 12px = rounded-xl) */}
        <div
          role="combobox"
          aria-haspopup="listbox"
          aria-expanded={suggestions.length > 0 && suggestionsOpen}
          aria-owns={listId}
          aria-controls={listId}
          className={`flex items-end gap-2 rounded-xl border px-3.5 py-2 shadow-xs transition ${
            disabled
              ? "opacity-75"
              : "focus-within:border-[var(--border-focus)] focus-within:ring-1 focus-within:ring-[var(--border-focus)]"
          }`}
          style={{
            borderColor: "var(--composer-border)",
            background: "var(--composer-bg)",
          }}
        >
          <textarea
            ref={textareaRef}
            id="chat-input"
            rows={1}
            value={text}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask about fees, eligibility, syllabus, admissions..."
            disabled={disabled}
            maxLength={MAX_CHAR_LIMIT}
            aria-label="Ask about fees, eligibility, syllabus, admissions"
            aria-autocomplete="list"
            aria-activedescendant={highlightedOptionId}
            aria-multiline="true"
            enterKeyHint="send"
            className="flex-1 resize-none bg-transparent text-xs sm:text-sm outline-none leading-5 py-1 disabled:cursor-not-allowed"
            style={{ color: "var(--text)" }}
          />

          {showCount && (
            <span
              className={`shrink-0 select-none text-[10px] font-mono px-1 py-1 ${
                isNearLimit ? "font-semibold" : ""
              }`}
              style={{ color: isNearLimit ? "var(--danger)" : "var(--muted)" }}
              aria-live="polite"
              aria-label={`${charLen} of ${MAX_CHAR_LIMIT} characters`}
            >
              {charLen}/{MAX_CHAR_LIMIT}
            </span>
          )}

          {/* When loading: show Stop button. When idle: show Send button. */}
          {disabled ? (
            <button
              onClick={onStop}
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border text-xs transition hover:opacity-80 focus-visible:outline-2 cursor-pointer"
              style={{
                borderColor: "var(--border)",
                background: "var(--surface-2)",
                color: "var(--danger)",
              }}
              aria-label="Stop generating"
              title="Stop"
              type="button"
            >
              <svg className="h-3 w-3" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <rect x="5" y="5" width="14" height="14" rx="1" />
              </svg>
            </button>
          ) : (
            <button
              onClick={() => submit()}
              disabled={!canSend}
              className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md transition focus-visible:outline-2 cursor-pointer ${
                canSend
                  ? "text-white shadow-xs hover:opacity-90"
                  : "cursor-not-allowed opacity-40"
              }`}
              style={{
                background: canSend ? "var(--accent)" : "var(--surface-3)",
                color: canSend ? "white" : "var(--muted)",
              }}
              aria-label="Send message"
              type="button"
            >
              <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 19V5M5 12l7-7 7 7" />
              </svg>
            </button>
          )}
        </div>

        {/* Keyboard hint -- hidden while loading */}
        {!disabled && (
          <p className="mt-1.5 text-center text-[10px]" style={{ color: "var(--muted)" }}>
            <kbd className="rounded border px-1 py-0.5 text-[9px]" style={{ borderColor: "var(--border)", background: "var(--surface-hover)" }}>Enter</kbd> to send
            {" "}&middot;{" "}
            <kbd className="rounded border px-1 py-0.5 text-[9px]" style={{ borderColor: "var(--border)", background: "var(--surface-hover)" }}>Shift + Enter</kbd> for new line
          </p>
        )}
      </div>
    </div>
  );
}