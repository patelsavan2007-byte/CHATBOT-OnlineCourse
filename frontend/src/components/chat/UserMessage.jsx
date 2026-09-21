/**
 * UserMessage — renders a user's chat bubble.
 * Right-aligned, theme-aware, with a subtle timestamp.
 */
function formatTime(date) {
  try {
    return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(date);
  } catch {
    return "";
  }
}

export default function UserMessage({ content, timestamp }) {
  const time = timestamp || Date.now();

  return (
    <div className="flex flex-col items-end animate-fade-up">
      <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-[var(--user-bubble)] px-4 py-3 text-sm leading-relaxed text-[var(--user-bubble-text)] shadow-sm sm:max-w-[75%]">
        {content}
      </div>
      <span className="mt-1 pr-1 text-[10px] text-[var(--text-tertiary)]">{formatTime(time)}</span>
    </div>
  );
}