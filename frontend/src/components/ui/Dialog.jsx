/**
 * Dialog - accessible, plain modal dialog for confirmations, alerts, and help.
 * No backdrop-filter, no smooth animation hijacking. 150ms transition.
 */
import { useEffect, useRef } from "react";

export default function Dialog({
  open,
  onClose,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  onConfirm,
  danger = false,
  children,
}) {
  const dialogRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose?.();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="presentation"
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose?.();
      }}
    >
      {/* Plain backdrop overlay */}
      <div
        className="fixed inset-0 bg-black/40 transition-opacity"
        aria-hidden="true"
      />

      {/* Modal card */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? "dialog-title" : undefined}
        aria-describedby={description ? "dialog-description" : undefined}
        className="relative z-10 w-full max-w-md rounded-lg border p-5 shadow-md"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border)",
          color: "var(--text)",
        }}
      >
        {title && (
          <h2 id="dialog-title" className="text-base font-semibold leading-6">
            {title}
          </h2>
        )}

        {description && (
          <p id="dialog-description" className="mt-2 text-sm leading-relaxed" style={{ color: "var(--text-2)" }}>
            {description}
          </p>
        )}

        {children && <div className="mt-3">{children}</div>}

        {(onConfirm || onClose) && (
          <div className="mt-5 flex justify-end gap-2.5">
            {onClose && cancelLabel && (
              <button
                type="button"
                onClick={onClose}
                className="rounded-md border px-3.5 py-1.5 text-xs font-medium transition hover:opacity-80 cursor-pointer"
                style={{
                  borderColor: "var(--border)",
                  background: "var(--surface)",
                  color: "var(--text)",
                }}
              >
                {cancelLabel}
              </button>
            )}
            {onConfirm && (
              <button
                type="button"
                onClick={onConfirm}
                className="rounded-md px-3.5 py-1.5 text-xs font-medium text-white transition hover:opacity-90 cursor-pointer"
                style={{
                  background: danger ? "var(--danger)" : "var(--accent)",
                }}
              >
                {confirmLabel}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
