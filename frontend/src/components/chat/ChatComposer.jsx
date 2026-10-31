/**
 * ChatComposer - message input bar with real-time typing suggestions.
 * Auto-growing textarea (1 to 6 lines), rounded floating style,
 * 1000-character limit with counter near limit, keyboard navigation (Up/Down/Enter/Esc),
 * accessible ARIA combobox + listbox dropdown.
 */
import { useCallback, useRef, useEffect, useState } from "react";
import TypingSuggestions from "./TypingSuggestions.jsx";
import { apiFetch } from "../../services/api.js";
import { shouldShowTip, selectNextTip } from "../../lib/tipSelector.js";

const MAX_ROWS = 6;
const MAX_CHAR_LIMIT = 1000;
const CHAR_WARN_THRESHOLD = 800;

// Client LRU cache of 100 entries
const clientSuggestionsCache = new Map();
const CLIENT_CACHE_LIMIT = 100;

function getFromCache(key) {
  if (!clientSuggestionsCache.has(key)) return null;
  const val = clientSuggestionsCache.get(key);
  clientSuggestionsCache.delete(key);
  clientSuggestionsCache.set(key, val);
  return val;
}

function setInCache(key, val) {
  if (clientSuggestionsCache.has(key)) {
    clientSuggestionsCache.delete(key);
  } else if (clientSuggestionsCache.size >= CLIENT_CACHE_LIMIT) {
    const firstKey = clientSuggestionsCache.keys().next().value;
    clientSuggestionsCache.delete(firstKey);
  }
  clientSuggestionsCache.set(key, val);
}

export default function ChatComposer({
  onSend,
  onStop,
  disabled,
  typingSuggestionsEnabled = true,
  currentProgramme = null,
  conversationId = null,
  history = [],
  messages = [],
}) {
  const [text, setText] = useState("");
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [suggestionsOpen, setSuggestionsOpen] = useState(true);
  const [suggestions, setSuggestions] = useState([]);
  const textareaRef = useRef(null);
  const abortControllerRef = useRef(null);
  const lastTypedTimestampRef = useRef(0);
  const lastShownTipIdRef = useRef(null);
  const tipTimerRef = useRef(null);
  const [activeTip, setActiveTip] = useState(null);

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

  /* Contextual quiet tips under composer */
  const assistantCount = (messages.length > 0 ? messages : history).filter(
    (m) => m.role === "assistant" && !m.error && !m.isError
  ).length;

  useEffect(() => {
    if (disabled || assistantCount === 0) return;

    let showTipsPref = true;
    try {
      showTipsPref = localStorage.getItem("show_tips") !== "false";
    } catch {
      showTipsPref = true;
    }

    const isTouch = typeof window !== "undefined" && Boolean(window.matchMedia?.("(pointer: coarse)")?.matches);
    const isMac = typeof navigator !== "undefined" && /Mac|iPhone|iPod|iPad/i.test(navigator.platform || navigator.userAgent);
    const hasError = messages.some((m) => m.isError || m.error);

    const eligible = shouldShowTip({
      assistantCount,
      showTipsPreference: showTipsPref,
      lastTypedTimestamp: lastTypedTimestampRef.current,
      now: Date.now(),
      hasError,
    });

    if (eligible) {
      const tip = selectNextTip({
        lastTipId: lastShownTipIdRef.current,
        isTouch,
        isMac,
      });
      if (tip) {
        lastShownTipIdRef.current = tip.id;
        setActiveTip(tip);
        if (tipTimerRef.current) clearTimeout(tipTimerRef.current);
        tipTimerRef.current = setTimeout(() => {
          setActiveTip(null);
        }, 8000);
      }
    }
  }, [assistantCount, disabled, messages]);

  useEffect(() => {
    return () => {
      if (tipTimerRef.current) clearTimeout(tipTimerRef.current);
    };
  }, []);

  /* Auto-focus on mount and when re-enabled */
  useEffect(() => {
    const el = textareaRef.current;
    if (el && !disabled) {
      el.focus({ preventScroll: true });
    }
  }, [disabled]);

  /* As-you-type suggestions via POST /api/suggest (debounced 200ms) */
  useEffect(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    const trimmed = text.trim();
    if (
      !typingSuggestionsEnabled ||
      !suggestionsOpen ||
      disabled ||
      trimmed.length < 2 ||
      trimmed.length > 100
    ) {
      setSuggestions([]);
      return;
    }

    const cacheKey = `${currentProgramme || "all"}:${trimmed.toLowerCase()}`;
    const cached = getFromCache(cacheKey);
    if (cached) {
      setSuggestions(cached);
      return;
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    const timer = setTimeout(async () => {
      try {
        const payload = {
          text: trimmed,
          conversation_id: conversationId,
          history: (history || []).slice(-4),
          programme: currentProgramme,
        };
        const res = await apiFetch("/api/suggest", {
          method: "POST",
          body: JSON.stringify(payload),
          signal: controller.signal,
        });

        const items = res?.suggestions || [];
        const tokens = trimmed.split(/\s+/).filter(Boolean);
        const mapped = items.slice(0, 5).map((item, idx) => ({
          id: `sug-${idx}`,
          text: typeof item === "string" ? item : item.text,
          topic: typeof item === "object" ? item.topic : "General",
          matchedTokens: tokens,
        }));

        setInCache(cacheKey, mapped);
        setSuggestions(mapped);
      } catch (err) {
        if (err?.name !== "AbortError") {
          // Degraded mode: fail silently
          setSuggestions([]);
        }
      }
    }, 200);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [text, typingSuggestionsEnabled, suggestionsOpen, disabled, currentProgramme, conversationId, history]);

  /* Reset highlight index when suggestions change */
  useEffect(() => {
    setHighlightedIndex(-1);
  }, [suggestions]);

  const submit = useCallback(
    (overrideText) => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      const q = (typeof overrideText === "string" ? overrideText : text).trim();
      if (!q || disabled) return;
      onSend(q);
      setText("");
      setSuggestionsOpen(false);
      setSuggestions([]);
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
        if (abortControllerRef.current) {
          abortControllerRef.current.abort();
          abortControllerRef.current = null;
        }
        setSuggestionsOpen(false);
        setSuggestions([]);
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

        {/* Quiet Tip or Keyboard hint -- hidden while loading */}
        {activeTip ? (
          <p
            className="mt-1.5 text-center text-[11px] leading-tight transition-opacity duration-300"
            style={{ color: "var(--muted)" }}
            role="status"
            aria-live="polite"
          >
            {activeTip.text}
          </p>
        ) : (
          !disabled && (
            <p className="mt-1.5 text-center text-[10px]" style={{ color: "var(--muted)" }}>
              <kbd className="rounded border px-1 py-0.5 text-[9px]" style={{ borderColor: "var(--border)", background: "var(--surface-hover)" }}>Enter</kbd> to send
              {" "}&middot;{" "}
              <kbd className="rounded border px-1 py-0.5 text-[9px]" style={{ borderColor: "var(--border)", background: "var(--surface-hover)" }}>Shift + Enter</kbd> for new line
            </p>
          )
        )}
      </div>
    </div>
  );
}
