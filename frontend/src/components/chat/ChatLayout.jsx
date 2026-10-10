/**
 * ChatLayout — full-screen chat application shell.
 * Desktop: sidebar collapses smoothly with transition; toggle button is ALWAYS visible in the header.
 * Mobile: sidebar as a slide-in drawer with overlay, scroll-locking and Escape-to-close.
 * State persisted in localStorage (charusat_sidebar_open) with full ARIA accessibility.
 */
import { useCallback, useEffect, useState } from "react";
import ChatSidebar from "./Sidebar.jsx";
import ThemeToggle from "../ui/ThemeToggle.jsx";

const SIDEBAR_STORAGE_KEY = "charusat_sidebar_open";

function getInitialSidebarOpen() {
  try {
    return localStorage.getItem(SIDEBAR_STORAGE_KEY) !== "false";
  } catch {
    return true;
  }
}

export default function ChatLayout({
  conversations,
  activeConversationId,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
  onRenameConversation,
  typingSuggestionsEnabled,
  onToggleTypingSuggestions,
  children,
}) {
  const [sidebarOpen, setSidebarOpen] = useState(getInitialSidebarOpen);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const toggleSidebar = useCallback(() => {
    setSidebarOpen((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(SIDEBAR_STORAGE_KEY, String(next));
      } catch {/* ignore */}
      return next;
    });
  }, []);

  const openDrawer = useCallback(() => setDrawerOpen(true), []);
  const closeDrawer = useCallback(() => setDrawerOpen(false), []);

  const handleSelect = useCallback(
    (id) => {
      onSelectConversation(id);
      setDrawerOpen(false);
    },
    [onSelectConversation]
  );

  const handleNew = useCallback(() => {
    onNewChat();
    setDrawerOpen(false);
  }, [onNewChat]);

  // Lock body scroll while the mobile drawer is open
  useEffect(() => {
    document.body.style.overflow = drawerOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [drawerOpen]);

  // Escape key closes the mobile drawer
  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (e) => {
      if (e.key === "Escape") closeDrawer();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawerOpen, closeDrawer]);

  const sidebarProps = {
    conversations,
    activeConversationId,
    onNewChat: handleNew,
    onSelectConversation: handleSelect,
    onDeleteConversation,
    onRenameConversation,
    typingSuggestionsEnabled,
    onToggleTypingSuggestions,
  };

  return (
    <div className="flex h-dvh overflow-hidden bg-[var(--surface-primary)] text-[var(--text-primary)]">
      {/* ---- Desktop sidebar ---- */}
      <aside
        id="desktop-sidebar"
        aria-hidden={!sidebarOpen}
        className={`hidden md:flex shrink-0 flex-col transition-[width] duration-200 ease-in-out overflow-hidden ${
          sidebarOpen ? "w-64" : "w-0"
        }`}
        style={{ minWidth: 0 }}
      >
        <ChatSidebar {...sidebarProps} />
      </aside>

      {/* ---- Mobile drawer overlay ---- */}
      {drawerOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
            onClick={closeDrawer}
            aria-hidden="true"
          />
          <div
            id="mobile-sidebar-drawer"
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
        <header className="flex h-11 shrink-0 items-center justify-between border-b border-[var(--border-primary)] bg-[var(--surface-primary)]/90 px-3 backdrop-blur-sm">
          {/* Left — toggle sidebar (desktop) / open drawer (mobile) */}
          <div className="flex items-center gap-1.5">
            <button
              id="desktop-sidebar-toggle"
              onClick={toggleSidebar}
              aria-expanded={sidebarOpen}
              aria-controls="desktop-sidebar"
              className="md:flex hidden h-7 w-7 items-center justify-center rounded-lg text-[var(--text-tertiary)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--text-secondary)] focus-visible:outline-2"
              aria-label={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
              title={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
              type="button"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                {sidebarOpen ? (
                  <path d="M9 3v18M3 5a2 2 0 012-2h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5z" />
                ) : (
                  <path d="M3 12h18M15 5h6M15 19h6M3 12v8a1 1 0 001 1h6V3H4a1 1 0 00-1 1v8z" />
                )}
              </svg>
            </button>
            <button
              id="mobile-drawer-toggle"
              onClick={openDrawer}
              aria-expanded={drawerOpen}
              aria-controls="mobile-sidebar-drawer"
              className="md:hidden flex h-7 w-7 items-center justify-center rounded-lg text-[var(--text-tertiary)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--text-secondary)] focus-visible:outline-2"
              aria-label="Open conversation history menu"
              type="button"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="M3 12h18M15 5h6M15 19h6M3 12v8a1 1 0 001 1h6V3H4a1 1 0 00-1 1v8z" />
              </svg>
            </button>
          </div>

          {/* Center — brand */}
          <div className="flex items-center gap-2">
            <svg viewBox="0 0 24 24" className="h-4 w-4 fill-[var(--accent-primary)]" aria-hidden="true">
              <path d="M12 3 1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
            </svg>
            <span className="text-[13px] font-medium text-[var(--text-tertiary)]">CHARUSAT Assistant</span>
          </div>

          {/* Right — theme toggle + new chat */}
          <div className="flex items-center gap-1">
            <ThemeToggle />
            <button
              onClick={handleNew}
              className="flex h-7 w-7 items-center justify-center rounded-lg text-[var(--text-tertiary)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--text-secondary)] focus-visible:outline-2"
              aria-label="New chat"
              title="New chat"
              type="button"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="M12 5v14M5 12h14" />
              </svg>
            </button>
          </div>
        </header>

        {/* Content */}
        <main className="flex min-h-0 flex-1 flex-col">
          {children}
        </main>
      </div>
    </div>
  );
}