import ThemedLogo from "../ui/ThemedLogo.jsx";
/**
 * Sidebar - left sidebar for the /chat application.
 * 280px width, client-side search, grouping (Today, Yesterday, This week, Older),
 * inline rename, delete with confirmation Dialog, keyboard shortcuts help,
 * pagination for 50+ conversations and footer links to Settings and About.
 */
import { useMemo, useState, useCallback, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext.jsx";
import Dialog from "../ui/Dialog.jsx";

const PAGE_SIZE = 50;

function ConversationItem({ conv, isActive, onSelect, onDeleteRequest, onRename }) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(conv.title || "Untitled");

  const commitRename = () => {
    setEditing(false);
    if (title.trim() && title.trim() !== conv.title) {
      onRename(conv.id, title.trim());
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      className={`group relative flex items-center gap-2 rounded-md px-2.5 py-2 text-xs transition cursor-pointer select-none ${
        isActive
          ? "font-medium"
          : "hover:bg-[var(--surface-hover)]"
      }`}
      style={{
        background: isActive ? "var(--sidebar-active)" : "transparent",
        color: isActive ? "var(--text)" : "var(--text-2)",
      }}
      onClick={() => !editing && onSelect(conv.id)}
      onKeyDown={(e) => {
        if (!editing && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          onSelect(conv.id);
        }
      }}
    >
      {editing ? (
        <input
          autoFocus
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={commitRename}
          onKeyDown={(e) => {
            if (e.key === "Enter") commitRename();
            if (e.key === "Escape") setEditing(false);
          }}
          className="flex-1 rounded border px-1.5 py-0.5 text-xs outline-none"
          style={{
            background: "var(--surface)",
            borderColor: "var(--border)",
            color: "var(--text)",
          }}
          onClick={(e) => e.stopPropagation()}
        />
      ) : (
        <span className="flex-1 truncate">{conv.title || "Untitled"}</span>
      )}

      {!editing && (
        <div className={`flex items-center gap-1 ${isActive ? "opacity-100" : "opacity-0 group-hover:opacity-100"} transition`}>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setEditing(true);
              setTitle(conv.title || "Untitled");
            }}
            className="rounded p-1 text-[var(--muted)] hover:text-[var(--text)] transition cursor-pointer"
            aria-label="Rename conversation"
            type="button"
          >
            <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDeleteRequest(conv);
            }}
            className="rounded p-1 text-[var(--muted)] hover:text-[var(--danger)] transition cursor-pointer"
            aria-label="Delete conversation"
            type="button"
          >
            <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}

function groupByDate(conversations) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const week = new Date(today.getTime() - 7 * 86400000);

  const groups = { Today: [], Yesterday: [], "This week": [], Older: [] };

  for (const conv of conversations) {
    const d = conv.updated_at ? new Date(conv.updated_at) : new Date(conv.created_at || 0);
    const day = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    if (day >= today) groups.Today.push(conv);
    else if (day >= yesterday) groups.Yesterday.push(conv);
    else if (day >= week) groups["This week"].push(conv);
    else groups.Older.push(conv);
  }

  return groups;
}

export default function ChatSidebar({
  conversations = [],
  activeConversationId,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
  onRenameConversation,
  onToggleSidebar,
  onClose,
}) {
  const { user, isGuest, logout } = useAuth();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);

  const handleLogout = useCallback(async () => {
    await logout();
    navigate("/", { replace: true });
  }, [logout, navigate]);

  // Global keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Don't trigger when typing in inputs/textareas
      const tag = e.target.tagName;
      const isInput = tag === "INPUT" || tag === "TEXTAREA" || e.target.isContentEditable;

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onNewChat();
        return;
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "b") {
        e.preventDefault();
        onToggleSidebar?.();
        return;
      }
      if (e.key === "/" && !isInput) {
        e.preventDefault();
        const input = document.getElementById("chat-input");
        input?.focus();
        return;
      }
      if (e.key === "?" && !isInput) {
        e.preventDefault();
        setShortcutsOpen((prev) => !prev);
        return;
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onNewChat, onToggleSidebar]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return conversations;
    return conversations.filter((c) => (c.title || "").toLowerCase().includes(q));
  }, [conversations, query]);

  const pagedList = useMemo(() => {
    return filtered.slice(0, visibleCount);
  }, [filtered, visibleCount]);

  const groups = useMemo(() => groupByDate(pagedList), [pagedList]);

  const confirmDelete = () => {
    if (deleteTarget) {
      onDeleteConversation(deleteTarget.id);
      setDeleteTarget(null);
    }
  };

  return (
    <div
      className="flex h-full w-full flex-col border-r"
      style={{
        background: "var(--sidebar-bg)",
        borderColor: "var(--border)",
      }}
    >
      {/* Top Header: Brand Wordmark + Actions */}
      <div className="flex items-center justify-between px-3 pt-3 pb-2 border-b" style={{ borderColor: "var(--border)" }}>
        <Link
          to="/"
          className="flex items-center gap-2 rounded-md px-1 py-0.5 transition hover:opacity-80"
          aria-label="CCOE, CHARUSAT"
        >
          <ThemedLogo variant="ccoe" height={32} />
        </Link>

        <div className="flex items-center gap-1">
          <button
            onClick={() => setShortcutsOpen(true)}
            className="flex h-7 w-7 items-center justify-center rounded-md text-[var(--muted)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--text)] cursor-pointer"
            aria-label="Keyboard shortcuts"
            title="Shortcuts (?)"
            type="button"
          >
            <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </button>

          {onClose && (
            <button
              onClick={onClose}
              className="flex md:hidden h-7 w-7 items-center justify-center rounded-md text-[var(--muted)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--text)] cursor-pointer"
              aria-label="Close sidebar"
              type="button"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* New chat button */}
      <div className="px-3 pt-3 pb-2">
        <button
          onClick={onNewChat}
          className="flex w-full items-center justify-between rounded-md px-3 py-2 text-xs font-medium text-white transition hover:opacity-90 cursor-pointer shadow-xs"
          style={{ background: "var(--accent)" }}
          type="button"
        >
          <span className="flex items-center gap-2">
            <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
              <path d="M12 5v14M5 12h14" />
            </svg>
            New chat
          </span>
          <kbd className="text-[10px] opacity-75 font-mono">Ctrl+K</kbd>
        </button>
      </div>

      {/* Instant Search */}
      {!isGuest && conversations.length > 0 && (
        <div className="px-3 pb-2">
          <div
            className="flex items-center gap-2 rounded-md border px-2.5 py-1.5 transition"
            style={{
              borderColor: "var(--border)",
              background: "var(--surface)",
            }}
          >
            <svg className="h-3.5 w-3.5 shrink-0" style={{ color: "var(--muted)" }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <circle cx="11" cy="11" r="8" />
              <path d="M21 21l-4.35-4.35" />
            </svg>
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search chats..."
              className="w-full bg-transparent text-xs outline-none"
              style={{ color: "var(--text)" }}
              aria-label="Search chats"
            />
            {query && (
              <button
                onClick={() => setQuery("")}
                className="text-xs transition hover:opacity-100 cursor-pointer"
                style={{ color: "var(--muted)" }}
                aria-label="Clear search"
                type="button"
              >
                &times;
              </button>
            )}
          </div>
        </div>
      )}

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto chat-scroll px-2 pb-2 min-h-0">
        {isGuest ? (
          <div className="px-3 py-8 text-center">
            <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
              Guest chats are not saved. Sign in to keep your history across sessions.
            </p>
            <Link
              to="/login"
              className="mt-3 inline-flex items-center justify-center rounded-md border px-3 py-1.5 text-xs font-medium transition hover:bg-[var(--surface-hover)]"
              style={{ borderColor: "var(--border)", color: "var(--text)" }}
            >
              Sign in
            </Link>
          </div>
        ) : filtered.length === 0 ? (
          <div className="px-3 py-8 text-center text-xs" style={{ color: "var(--muted)" }}>
            {query ? "No chats match your search." : "No saved chats yet."}
          </div>
        ) : (
          <>
            {Object.entries(groups).map(([label, convs]) =>
              convs.length === 0 ? null : (
                <div key={label} className="mb-3">
                  <p className="mb-1 px-2.5 text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
                    {label}
                  </p>
                  <div className="space-y-0.5">
                    {convs.map((conv) => (
                      <ConversationItem
                        key={conv.id}
                        conv={conv}
                        isActive={conv.id === activeConversationId}
                        onSelect={onSelectConversation}
                        onDeleteRequest={(c) => setDeleteTarget(c)}
                        onRename={onRenameConversation}
                      />
                    ))}
                  </div>
                </div>
              )
            )}

            {filtered.length > visibleCount && (
              <div className="pt-2 text-center">
                <button
                  type="button"
                  onClick={() => setVisibleCount((prev) => prev + PAGE_SIZE)}
                  className="rounded-md border px-3 py-1 text-xs font-medium transition hover:bg-[var(--surface-hover)] cursor-pointer"
                  style={{ borderColor: "var(--border)", color: "var(--text-2)" }}
                >
                  Load older ({filtered.length - visibleCount} remaining)
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Footer Navigation & User State */}
      <div className="border-t px-3 py-2.5 text-xs" style={{ borderColor: "var(--border)" }}>
        {/* Links row */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 pb-2 text-[11px]" style={{ color: "var(--muted)" }}>
          <Link to="/about" className="hover:underline">About</Link>
          <Link to="/settings" className="hover:underline">Settings</Link>
        </div>

        {/* User bar */}
        {user ? (
          <div className="flex items-center justify-between border-t pt-2" style={{ borderColor: "var(--border)" }}>
            <div className="flex items-center gap-2 min-w-0">
              {/* allow-round: user avatar circle */}
              <div
                className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-semibold text-white" /* allow-round: avatar circle */
                style={{ background: "var(--accent)" }}
              >
                {(user.name?.[0] || user.email?.[0] || "U").toUpperCase()}
              </div>
              <span className="truncate text-xs font-medium" style={{ color: "var(--text)" }}>
                {user.name || user.email}
              </span>
            </div>
            <button
              onClick={handleLogout}
              className="text-[11px] hover:underline cursor-pointer"
              style={{ color: "var(--danger)" }}
              type="button"
            >
              Sign out
            </button>
          </div>
        ) : (
          <div className="border-t pt-2" style={{ borderColor: "var(--border)" }}>
            <Link
              to="/login"
              className="block w-full text-center rounded-md border py-1.5 text-xs font-medium transition hover:bg-[var(--surface-hover)]"
              style={{ borderColor: "var(--border)", color: "var(--text)" }}
            >
              Sign in to save history
            </Link>
          </div>
        )}
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        title="Delete conversation?"
        description={`"${deleteTarget?.title || "This chat"}" will be permanently removed. This cannot be undone.`}
        confirmLabel="Delete"
        cancelLabel="Cancel"
        danger={true}
        onConfirm={confirmDelete}
      />

      {/* Keyboard Shortcuts Help Dialog */}
      <Dialog
        open={shortcutsOpen}
        onClose={() => setShortcutsOpen(false)}
        title="Keyboard shortcuts"
        confirmLabel="Done"
        onConfirm={() => setShortcutsOpen(false)}
      >
        <div className="space-y-2 text-xs" style={{ color: "var(--text-2)" }}>
          <div className="flex justify-between py-1 border-b" style={{ borderColor: "var(--border)" }}>
            <span>New chat</span>
            <kbd className="rounded border px-1.5 py-0.5 font-mono text-[11px]" style={{ borderColor: "var(--border)", background: "var(--surface-hover)" }}>Ctrl + K</kbd>
          </div>
          <div className="flex justify-between py-1 border-b" style={{ borderColor: "var(--border)" }}>
            <span>Focus message input</span>
            <kbd className="rounded border px-1.5 py-0.5 font-mono text-[11px]" style={{ borderColor: "var(--border)", background: "var(--surface-hover)" }}>/</kbd>
          </div>
          <div className="flex justify-between py-1 border-b" style={{ borderColor: "var(--border)" }}>
            <span>Toggle sidebar</span>
            <kbd className="rounded border px-1.5 py-0.5 font-mono text-[11px]" style={{ borderColor: "var(--border)", background: "var(--surface-hover)" }}>Ctrl + B</kbd>
          </div>
          <div className="flex justify-between py-1">
            <span>Show keyboard shortcuts</span>
            <kbd className="rounded border px-1.5 py-0.5 font-mono text-[11px]" style={{ borderColor: "var(--border)", background: "var(--surface-hover)" }}>?</kbd>
          </div>
        </div>
      </Dialog>
    </div>
  );
}
