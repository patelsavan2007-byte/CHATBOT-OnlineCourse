/**
 * TypingSuggestions — dropdown list of matched question bank suggestions
 * rendered directly above the composer.
 *
 * Highlights matched query tokens in bold.
 * Accessible with ARIA listbox & option attributes.
 */
import { useMemo } from "react";

function highlightMatches(text, matchedTokens = []) {
  if (!matchedTokens || matchedTokens.length === 0) return text;

  // Build regex from matched tokens
  const escaped = matchedTokens
    .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .filter(Boolean)
    .sort((a, b) => b.length - a.length);

  if (escaped.length === 0) return text;

  const regex = new RegExp(`(\\b(?:${escaped.join("|")})\\w*)`, "gi");
  const parts = text.split(regex);

  return parts.map((part, idx) => {
    if (regex.test(part)) {
      return (
        <span key={idx} className="font-semibold text-[var(--text-primary)]">
          {part}
        </span>
      );
    }
    return <span key={idx}>{part}</span>;
  });
}

export default function TypingSuggestions({
  suggestions,
  highlightedIndex,
  onSelect,
  listId = "typing-suggestions-list",
}) {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div
      id={listId}
      role="listbox"
      aria-label="Question suggestions"
      className="absolute bottom-full left-0 right-0 z-30 mb-2 overflow-hidden rounded-xl border border-[var(--border-primary)] bg-[var(--surface-primary)] shadow-xl backdrop-blur-md animate-fade-up"
    >
      <div className="border-b border-[var(--border-primary)] bg-[var(--surface-hover)]/60 px-3 py-1.5 text-[11px] font-medium text-[var(--text-tertiary)] flex items-center justify-between">
        <span>Suggested questions</span>
        <span className="text-[10px] text-[var(--text-muted)]">↑↓ to navigate · ↵ to select · Esc to close</span>
      </div>

      <div className="max-h-64 overflow-y-auto divide-y divide-[var(--border-primary)]/40 p-1">
        {suggestions.map((item, idx) => {
          const isHighlighted = idx === highlightedIndex;
          const optionId = `${listId}-item-${idx}`;

          return (
            <div
              key={item.id || idx}
              id={optionId}
              role="option"
              aria-selected={isHighlighted}
              onMouseDown={(e) => {
                // Prevent textarea blur
                e.preventDefault();
                onSelect(item.text);
              }}
              className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-left text-[13px] transition cursor-pointer select-none ${
                isHighlighted
                  ? "bg-[var(--accent-primary)]/15 text-[var(--text-primary)] ring-1 ring-[var(--accent-primary)]/30"
                  : "text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)]"
              }`}
            >
              <svg
                className={`h-3.5 w-3.5 shrink-0 ${isHighlighted ? "text-[var(--accent-primary)]" : "text-[var(--text-tertiary)]"}`}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                aria-hidden
              >
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.3-4.3" />
              </svg>
              <span className="flex-1 truncate leading-snug">
                {highlightMatches(item.text, item.matchedTokens)}
              </span>
              {item.category && (
                <span className="shrink-0 text-[10px] text-[var(--text-muted)] opacity-70">
                  {item.category.replace(" Questions", "")}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
