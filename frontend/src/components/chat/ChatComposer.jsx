/**
 * ChatComposer — message input bar for the chat application.
 * Auto-resizing textarea, Enter / Ctrl+Enter to send, character counter,
 * theme-aware styling.
 */
import { useCallback, useRef, useEffect, useState } from "react";

const MAX_ROWS = 8;
const CHAR_WARN = 200;

export default function ChatComposer({ onSend, disabled }) {
  const [text, setText]   = useState("");
  const textareaRef       = useRef(null);

  /* Auto-resize */
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const lineH  = 24;
    const maxH   = lineH * MAX_ROWS + 24; // padding
    el.style.height = Math.min(el.scrollHeight, maxH) + "px";
    el.style.overflowY = el.scrollHeight > maxH ? "auto" : "hidden";
  }, [text]);

  /* Auto-focus: on mount and whenever the input becomes usable again
     (i.e. right after a response arrives), so the cursor is always back in
     the chat box without the user having to click it manually. */
  useEffect(() => {
    const el = textareaRef.current;
    if (el && !disabled) {
      el.focus({ preventScroll: true });
    }
  }, [disabled]);

  const submit = useCallback(() => {
    const q = text.trim();
    if (!q || disabled) return;
    onSend(q);
    setText("");
  }, [text, disabled, onSend]);

  const handleKeyDown = (e) => {
    const sendShortcut = e.key === "Enter" && !e.shiftKey && !e.ctrlKey && !e.metaKey && !e.altKey;
    const ctrlSend     = e.key === "Enter" && (e.ctrlKey || e.metaKey);
    if (sendShortcut || ctrlSend) {
      e.preventDefault();
      submit();
    }
  };

  const canSend = text.trim().length > 0 && !disabled;
  const charLen = text.length;
  const showCount = charLen > CHAR_WARN;

  return (
    <div className="shrink-0 border-t border-[var(--border-primary)] bg-[var(--surface-primary)] px-3 py-3 sm:px-4 sm:py-4">
      {/* Wrapper */}
      <div className="mx-auto max-w-3xl">
        <div
          className={`flex items-end gap-2 rounded-xl border bg-[var(--composer-bg)] px-3 py-2.5 transition ${
            disabled
              ? "border-[var(--border-primary)] opacity-70"
              : "border-[var(--composer-border)] focus-within:border-[var(--composer-focus-border)] focus-within:shadow-[0_0_0_3px_var(--composer-focus-ring)]"
          }`}
        >
          <textarea
            ref={textareaRef}
            id="chat-input"
            rows={1}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about fees, eligibility, curriculum…"
            disabled={disabled}
            className="flex-1 resize-none bg-transparent text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] outline-none leading-6 py-0.5 disabled:cursor-not-allowed"
            aria-label="Chat message"
            aria-multiline="true"
            enterKeyHint="send"
          />

          {showCount && (
            <span
              className={`shrink-0 select-none text-[10px] ${
                charLen > CHAR_WARN + 200 ? "text-[var(--error)]" : "text-[var(--text-muted)]"
              }`}
              aria-hidden
            >
              {charLen}
            </span>
          )}

          <button
            onClick={submit}
            disabled={!canSend}
            className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition focus-visible:outline-2 ${
              canSend
                ? "bg-[var(--accent-primary)] text-white hover:bg-[var(--accent-primary-hover)]"
                : "bg-[var(--surface-hover)] text-[var(--text-muted)] cursor-not-allowed"
            }`}
            aria-label="Send message"
            type="button"
          >
            {disabled ? (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--text-muted)] border-t-[var(--text-secondary)]" />
            ) : (
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 19V5M5 12l7-7 7 7" />
              </svg>
            )}
          </button>
        </div>

        {/* Keyboard hint */}
        <p className="mt-1.5 text-center text-[10px] text-[var(--text-muted)]">
          <kbd className="rounded border border-[var(--border-primary)] bg-[var(--surface-hover)] px-1 py-0.5 text-[9px]">↵ Enter</kbd> to send ·{" "}
          <kbd className="rounded border border-[var(--border-primary)] bg-[var(--surface-hover)] px-1 py-0.5 text-[9px]">Ctrl + ↵</kbd> also sends ·{" "}
          <kbd className="rounded border border-[var(--border-primary)] bg-[var(--surface-hover)] px-1 py-0.5 text-[9px]">Shift + ↵</kbd> for new line
        </p>
      </div>
    </div>
  );
}