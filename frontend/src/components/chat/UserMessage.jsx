/**
 * UserMessage - renders a user's chat message.
 * Right-aligned block on surface-2, 8px radius, normal text color (no accent bubble).
 */
function formatTime(date) {
  try {
    return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(new Date(date));
  } catch {
    return "";
  }
}

export default function UserMessage({ content, timestamp }) {
  const time = timestamp || Date.now();

  return (
    <div className="flex flex-col items-end">
      <div
        className="max-w-[85%] rounded-lg px-4 py-3 text-sm leading-relaxed sm:max-w-[75%]"
        style={{
          background: "var(--user-bg)",
          color: "var(--user-text)",
          border: "1px solid var(--border)",
        }}
      >
        <p className="whitespace-pre-wrap break-words">{content}</p>
      </div>
      <span className="mt-1 pr-1 text-[10px]" style={{ color: "var(--muted)" }}>
        {formatTime(time)}
      </span>
    </div>
  );
}