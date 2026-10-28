/**
 * Toast - lightweight accessible notifications.
 */
import { useEffect, useState } from "react";

export default function Toast({
  message,
  type = "info",
  duration = 4000,
  onClose,
}) {
  const [visible, setVisible] = useState(Boolean(message));

  useEffect(() => {
    if (!message) {
      setVisible(false);
      return;
    }
    setVisible(true);
    const timer = setTimeout(() => {
      setVisible(false);
      onClose?.();
    }, duration);
    return () => clearTimeout(timer);
  }, [message, duration, onClose]);

  if (!visible || !message) return null;

  const typeStyles = {
    info: {
      borderColor: "var(--border)",
      background: "var(--surface)",
      color: "var(--text)",
    },
    success: {
      borderColor: "var(--success-border)",
      background: "var(--surface)",
      color: "var(--success)",
    },
    danger: {
      borderColor: "var(--danger-border)",
      background: "var(--surface)",
      color: "var(--danger)",
    },
  }[type] || {
    borderColor: "var(--border)",
    background: "var(--surface)",
    color: "var(--text)",
  };

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed bottom-4 right-4 z-50 flex items-center gap-3 rounded-lg border px-4 py-2.5 text-xs font-medium shadow-md transition-opacity"
      style={typeStyles}
    >
      <span>{message}</span>
      <button
        onClick={() => {
          setVisible(false);
          onClose?.();
        }}
        className="text-xs opacity-70 hover:opacity-100 cursor-pointer"
        aria-label="Dismiss notification"
        type="button"
      >
        Dismiss
      </button>
    </div>
  );
}
