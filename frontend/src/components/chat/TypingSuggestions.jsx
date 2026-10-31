/**
 * TypingSuggestions - dropdown list of matched question bank suggestions
 * rendered directly above the composer.
 *
 * Highlights matched query tokens in bold.
 * Plain background (no backdrop blur), standard design tokens.
 */
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
        <span key={idx} className="font-semibold" style={{ color: "var(--accent)" }}>
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
      className="absolute bottom-full left-0 right-0 z-30 mb-2 overflow-hidden rounded-lg border shadow-md"
      style={{
        borderColor: "var(--border)",
        background: "var(--surface)",
        color: "var(--text)",
      }}
    >
      <div
        className="flex items-center justify-between border-b px-3 py-1.5 text-[11px] font-medium"
        style={{
          borderColor: "var(--border)",
          background: "var(--surface-2)",
          color: "var(--muted)",
        }}
      >
        <span>Suggested questions</span>
        <span className="text-[10px]">Arrow keys to navigate, Enter to select, Esc to close</span>
      </div>

      <div className="max-h-64 overflow-y-auto divide-y p-1" style={{ borderColor: "var(--border)" }}>
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
                e.preventDefault();
                onSelect(item.text);
              }}
              className="flex items-center gap-2.5 rounded-md px-3 py-2 text-left text-xs transition cursor-pointer select-none"
              style={{
                background: isHighlighted ? "var(--surface-hover)" : "transparent",
                color: "var(--text)",
              }}
            >
              <svg
                className="h-3.5 w-3.5 shrink-0"
                style={{ color: isHighlighted ? "var(--accent)" : "var(--muted)" }}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                aria-hidden="true"
              >
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.3-4.3" />
              </svg>
              <span className="flex-1 truncate leading-snug">
                {highlightMatches(item.text, item.matchedTokens)}
              </span>
              {(item.topic || item.category) && (
                <span className="shrink-0 text-[10px]" style={{ color: "var(--muted)" }}>
                  {(item.topic || item.category).replace(" Questions", "")}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
