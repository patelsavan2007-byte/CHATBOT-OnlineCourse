/**
 * ChatLayout — full-screen chat application shell.
 * Desktop: sidebar + main. Mobile: sidebar as a slide-in drawer
 * with overlay, scroll-locking and Escape-to-close.
 */
import { useCallback, useEffect, useState } from "react";
import ChatSidebar from "./Sidebar.jsx";
import ThemeToggle from "../ui/ThemeToggle.jsx";

export default function ChatLayout({
  conversations,
  activeConversationId,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
  onRenameConversation,
  onToggleSuggestions,
  suggestionsEnabled,
  children,
}) {
  const [sidebarOpen, setSidebarOpen]     = useState(true);
  const [drawerOpen,  setDrawerOpen]      = useState(false);

  const toggleSidebar = useCallback(() => setSidebarOpen((v) => !v), []);
  const openDrawer    = useCallback(() => setDrawerOpen(true), []);
  const closeDrawer   = useCallback(() => setDrawerOpen(false), []);

  const handleSelect = useCallback((id) => { onSelectConversation(id); setDrawerOpen(false); }, [onSelectConversation]);
  const handleNew    = useCallback(() => { onNewChat(); setDrawerOpen(false); }, [onNewChat]);

  // Lock body scroll while the mobile drawer is open
  useEffect(() => {
    document.body.style.overflow = drawerOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [drawerOpen]);

  // Escape closes the drawer
  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (e) => { if (e.key === "Escape") closeDrawer(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawerOpen, closeDrawer]);

  const sidebarProps = {
    conversations,
    activeConversationId,
    onNewChat:            handleNew,
    onSelectConversation: handleSelect,
    onDeleteConversation,
    onRenameConversation,
    onToggleSuggestions,
    suggestionsEnabled,
  };

  return (
    <div className="flex h-dvh overflow-hidden bg-[var(--surface-primary)] text-[var(--text-primary)]">
      {/* ---- Desktop sidebar ---- */}
      <div
        className={`hidden md:flex shrink-0 flex-col transition-all duration-250 ease-in-out overflow-hidden ${
          sidebarOpen ? "w-64" : "w-0"
        }`}
        style={{ minWidth: 0 }}
      >
        <ChatSidebar {...sidebarProps} />
      </div>

      {/* ---- Mobile drawer overlay ---- */}
      {drawerOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
            onClick={closeDrawer}
            aria-hidden
          />
          <div
            className="fixed inset-y-0 left-0 z-50 w-72 md:hidden animate-slide-in"
            role="dialog"
            aria-modal="true"
            aria-label="Conversation history"
          >
            <ChatSidebar {...sidebarProps} onClose={closeDrawer} />
          </div>
        </>
      )}

      {/* ---- Main area ---- */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top bar */}
        <div className="flex h-11 shrink-0 items-center justify-between border-b border-[var(--border-primary)] bg-[var(--surface-primary)]/90 px-3 backdrop-blur-sm">
          {/* Left — toggle sidebar / open drawer */}
          <button
            onClick={sidebarOpen ? toggleSidebar : openDrawer}
            className="md:flex hidden h-7 w-7 items-center justify-center rounded-lg text-[var(--text-tertiary)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--text-secondary)]"
            aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
            title={sidebarOpen ? "Close sidebar" : "Open sidebar"}
            type="button"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              {sidebarOpen ? (
                <path d="M9 3v18M3 5a2 2 0 012-2h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5z" />
              ) : (
                <path d="M3 12h18M15 5h6M15 19h6M3 12v8a1 1 0 001 1h6V3H4a1 1 0 00-1 1v8z" />
              )}
            </svg>
          </button>
          <button
            onClick={openDrawer}
            className="md:hidden flex h-7 w-7 items-center justify-center rounded-lg text-[var(--text-tertiary)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--text-secondary)]"
            aria-label="Open sidebar"
            type="button"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <path d="M3 12h18M15 5h6M15 19h6M3 12v8a1 1 0 001 1h6V3H4a1 1 0 00-1 1v8z" />
            </svg>
          </button>

          {/* Center — brand */}
          <div className="flex items-center gap-2">
            <svg viewBox="0 0 24 24" className="h-4 w-4 fill-[var(--accent-primary)]" aria-hidden>
              <path d="M12 3 1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
            </svg>
            <span className="text-[13px] font-medium text-[var(--text-tertiary)]">CHARUSAT Assistant</span>
          </div>

          {/* Right — suggestions toggle + theme toggle + new chat */}
          <div className="flex items-center gap-1">
            <button
              onClick={onToggleSuggestions}
              className={`flex h-7 items-center gap-1.5 rounded-lg px-2 text-[11px] font-medium transition ${
                suggestionsEnabled
                  ? "text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)]"
                  : "text-[var(--text-muted)] line-through hover:bg-[var(--surface-hover)]"
              }`}
              aria-pressed={suggestionsEnabled}
              title={suggestionsEnabled ? "Suggested questions are on — click to hide" : "Suggested questions are off — click to show"}
              type="button"
            >
              <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                <path d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01" />
              </svg>
              <span className="hidden sm:inline">Suggestions</span>
            </button>
            <ThemeToggle />
            <button
              onClick={handleNew}
              className="flex h-7 w-7 items-center justify-center rounded-lg text-[var(--text-tertiary)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--text-secondary)]"
              aria-label="New chat"
              title="New chat"
              type="button"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                <path d="M12 5v14M5 12h14" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex min-h-0 flex-1 flex-col">
          {children}
        </div>
      </div>
    </div>
  );
}