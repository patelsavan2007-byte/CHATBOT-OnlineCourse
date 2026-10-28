/**
 * ChatLayout — full-screen chat application shell.
 * Desktop: sidebar 280px, collapsible; toggle button in header.
 * Mobile: sidebar as a slide-in drawer with plain overlay (no backdrop blur).
 * Skip-to-content link, keyboard shortcuts, accessible ARIA landmarks.
 */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ChatSidebar from "./Sidebar.jsx";
import ThemeToggle from "../ui/ThemeToggle.jsx";
import { useAuth } from "../../contexts/AuthContext.jsx";

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
  const { user } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(getInitialSidebarOpen);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const toggleSidebar = useCallback(() => {
    setSidebarOpen((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(SIDEBAR_STORAGE_KEY, String(next));
      } catch {
        /* ignore */
      }
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

  // Lock body scroll while mobile drawer is open
  useEffect(() => {
    document.body.style.overflow = drawerOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [drawerOpen]);

  // Escape key closes mobile drawer
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
    onToggleSidebar: toggleSidebar,
  };

  return (
    <div className="flex h-dvh overflow-hidden bg-[var(--page)] text-[var(--text)]">
      {/* Skip to main content link for keyboard & screen reader accessibility */}
      <a
        href="#main-chat-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:border focus:px-3 focus:py-2 focus:text-xs focus:font-medium focus:shadow-md"
        style={{
          borderColor: "var(--border)",
          background: "var(--surface)",
          color: "var(--text)",
        }}
      >
        Skip to main content
      </a>

      {/* ---- Desktop sidebar (280px) ---- */}
      <aside
        id="desktop-sidebar"
        aria-hidden={!sidebarOpen}
        className={`hidden md:flex shrink-0 flex-col transition-[width] duration-150 ease-in-out overflow-hidden ${
          sidebarOpen ? "w-[280px]" : "w-0"
        }`}
        style={{ minWidth: 0 }}
      >
        <ChatSidebar {...sidebarProps} />
      </aside>

      {/* ---- Mobile drawer overlay ---- */}
      {drawerOpen && (
        <>
          {/* Plain semi-transparent overlay */}
          <div
            className="fixed inset-0 z-40 bg-black/40 md:hidden"
            onClick={closeDrawer}
            aria-hidden="true"
          />
          <div
            id="mobile-sidebar-drawer"
            className="fixed inset-y-0 left-0 z-50 w-[280px] md:hidden shadow-lg"
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
        {/* Top bar -- plain solid background, no backdrop blur */}
        <header
          className="flex h-12 shrink-0 items-center justify-between border-b px-3 sm:px-4"
          style={{ borderColor: "var(--border)", background: "var(--surface)" }}
        >
          {/* Left: toggle sidebar (desktop) / open drawer (mobile) + Product wordmark */}
          <div className="flex items-center gap-2.5">
            <button
              id="desktop-sidebar-toggle"
              onClick={toggleSidebar}
              aria-expanded={sidebarOpen}
              aria-controls="desktop-sidebar"
              className="hidden md:flex h-7 w-7 items-center justify-center rounded-md border text-[var(--muted)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--text)] focus-visible:outline-2 cursor-pointer"
              style={{ borderColor: "var(--border)" }}
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
              className="flex md:hidden h-7 w-7 items-center justify-center rounded-md border text-[var(--muted)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--text)] focus-visible:outline-2 cursor-pointer"
              style={{ borderColor: "var(--border)" }}
              aria-label="Open menu"
              type="button"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="M3 12h18M3 6h18M3 18h18" />
              </svg>
            </button>

            <span className="text-xs font-semibold sm:text-sm" style={{ color: "var(--text)" }}>
              Online Programmes Assistant
            </span>
          </div>

          {/* Right: Theme + Account / Sign In */}
          <div className="flex items-center gap-2">
            <ThemeToggle />
            {user ? (
              <Link
                to="/settings"
                className="flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition hover:bg-[var(--surface-hover)]"
                style={{ borderColor: "var(--border)", color: "var(--text)" }}
                aria-label="Account settings"
              >
                <span className="hidden sm:inline truncate max-w-[120px]">{user.name || user.email}</span>
                <span className="sm:hidden">Account</span>
              </Link>
            ) : (
              <Link
                to="/login"
                className="rounded-md px-2.5 py-1 text-xs font-medium text-white transition hover:opacity-90"
                style={{ background: "var(--accent)" }}
              >
                Sign in
              </Link>
            )}
          </div>
        </header>

        {/* Content */}
        <main id="main-chat-content" className="flex min-h-0 flex-1 flex-col">
          {children}
        </main>
      </div>
    </div>
  );
}