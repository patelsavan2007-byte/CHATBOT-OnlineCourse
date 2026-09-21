/**
 * ChatSidebar — left sidebar for the /chat application.
 * Search-filters history, groups by date, supports rename/delete,
 * and hosts theme + suggestion preferences in the footer.
 */
import { useMemo, useState, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext.jsx";
import ThemeToggle from "../ui/ThemeToggle.jsx";

/* ---- Icons ---- */
const Icon = ({ d, className = "h-4 w-4" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
    <path d={d} />
  </svg>
);

function ConversationItem({ conv, isActive, onSelect, onDelete, onRename }) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle]     = useState(conv.title || "Untitled");

  const commitRename = () => {
    setEditing(false);
    if (title.trim() && title.trim() !== conv.title) {
      onRename(conv.id, title.trim());
    }
  };

  return (
    <div
      className={`group relative flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm transition cursor-pointer select-none ${
        isActive
          ? "bg-[var(--sidebar-active)] text-[var(--text-primary)]"
          : "text-[var(--text-tertiary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-secondary)]"
      }`}
      onClick={() => !editing && onSelect(conv.id)}
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
          className="flex-1 rounded bg-[var(--surface-active)] px-2 py-0.5 text-sm text-[var(--text-primary)] outline-none"
          onClick={(e) => e.stopPropagation()}
        />
      ) : (
        <span className="flex-1 truncate text-[13px]">{conv.title || "Untitled"}</span>
      )}

      {/* Actions — only visible on hover/active */}
      {!editing && (
        <div className={`flex items-center gap-0.5 ${isActive ? "opacity-100" : "opacity-0 group-hover:opacity-100"} transition`}>
          <button
            onClick={(e) => { e.stopPropagation(); setEditing(true); setTitle(conv.title || "Untitled"); }}
            className="rounded p-1 text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition"
            aria-label="Rename conversation"
            type="button"
          >
            <Icon d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" className="h-3 w-3" />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(conv.id); }}
            className="rounded p-1 text-[var(--text-muted)] hover:text-[var(--error)] transition"
            aria-label="Delete conversation"
            type="button"
          >
            <Icon d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" className="h-3 w-3" />
          </button>
        </div>
      )}
    </div>
  );
}

function groupByDate(conversations) {
  const now = new Date();
  const today     = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const week      = new Date(today.getTime() - 7 * 86400000);

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
  conversations,
  activeConversationId,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
  onRenameConversation,
  onToggleSuggestions,
  suggestionsEnabled,
  onClose,
}) {
  const { user, isGuest, logout } = useAuth();
  const navigate   = useNavigate();
  const [query, setQuery] = useState("");

  const handleLogout = useCallback(async () => {
    await logout();
    navigate("/", { replace: true });
  }, [logout, navigate]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return conversations;
    return conversations.filter((c) => (c.title || "").toLowerCase().includes(q));
  }, [conversations, query]);

  const groups = groupByDate(filtered);

  return (
    <div className="flex h-full w-full flex-col bg-[var(--sidebar-bg)] border-r border-[var(--border-primary)] backdrop-blur-xl">
      {/* Top — logo + actions */}
      <div className="flex items-center justify-between px-3 pt-3 pb-2">
        <Link
          to="/"
          className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-[var(--text-tertiary)] transition hover:text-[var(--text-primary)]"
          aria-label="Go to home"
        >
          <svg viewBox="0 0 24 24" className="h-4 w-4 fill-[var(--accent-primary)] shrink-0" aria-hidden>
            <path d="M12 3 1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
          </svg>
          <span className="text-[12px] font-medium text-[var(--text-muted)]">CHARUSAT</span>
        </Link>

        <div className="flex items-center gap-1">
          {/* New chat button */}
          <button
            onClick={onNewChat}
            className="flex h-7 w-7 items-center justify-center rounded-lg text-[var(--text-tertiary)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)]"
            aria-label="New chat"
            title="New chat"
            type="button"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <path d="M12 5v14M5 12h14" />
            </svg>
          </button>

          {/* Close (mobile only) */}
          {onClose && (
            <button
              onClick={onClose}
              className="flex h-7 w-7 items-center justify-center rounded-lg text-[var(--text-tertiary)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)] md:hidden"
              aria-label="Close sidebar"
              type="button"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* New chat — large button */}
      <div className="px-3 pb-2">
        <button
          onClick={onNewChat}
          className="flex w-full items-center gap-2.5 rounded-lg border border-[var(--border-primary)] px-3 py-2 text-[13px] font-medium text-[var(--text-tertiary)] transition hover:border-[var(--border-hover)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-secondary)]"
          type="button"
        >
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
            <path d="M12 5v14M5 12h14" />
          </svg>
          New chat
        </button>
      </div>

      {/* Search */}
      {!isGuest && filtered.length > 0 && (
        <div className="px-3 pb-2">
          <div className="flex items-center gap-2 rounded-lg border border-[var(--border-primary)] bg-[var(--surface-hover)] px-2.5 py-1.5 transition focus-within:border-[var(--border-hover)]">
            <svg className="h-3.5 w-3.5 shrink-0 text-[var(--text-muted)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <circle cx="11" cy="11" r="8" />
              <path d="M21 21l-4.35-4.35" />
            </svg>
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search conversations…"
              className="w-full bg-transparent text-[12px] text-[var(--text-secondary)] placeholder:text-[var(--text-muted)] outline-none"
              aria-label="Search conversations"
            />
            {query && (
              <button
                onClick={() => setQuery("")}
                className="text-[var(--text-muted)] transition hover:text-[var(--text-tertiary)]"
                aria-label="Clear search"
                type="button"
              >
                <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                  <path d="M18 6 6 18M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto chat-scroll px-2 pb-2 min-h-0">
        {isGuest ? (
          <div className="px-3 py-10 text-center">
            <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl border border-[var(--border-primary)] bg-[var(--surface-hover)] text-[var(--text-muted)] mb-3">
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
            </div>
            <p className="text-xs text-[var(--text-tertiary)] leading-relaxed">
              Sign in to save your conversations
            </p>
            <Link
              to="/login"
              className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-[var(--border-primary)] bg-[var(--surface-hover)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] transition hover:bg-[var(--surface-active)]"
            >
              Sign in
            </Link>
          </div>
        ) : filtered.length === 0 ? (
          <div className="px-3 py-10 text-center">
            <p className="text-xs text-[var(--text-tertiary)]">
              {query ? "No conversations match" : "No conversations yet"}
            </p>
            <p className="mt-1 text-[11px] text-[var(--text-muted)]">
              {query ? "Try a different search" : "Start a new chat above"}
            </p>
          </div>
        ) : (
          <>
            {Object.entries(groups).map(([label, convs]) =>
              convs.length === 0 ? null : (
                <div key={label} className="mb-4">
                  <p className="mb-1 px-2.5 text-[10px] font-semibold uppercase tracking-widest text-[var(--text-muted)]">
                    {label}
                  </p>
                  {convs.map((conv) => (
                    <ConversationItem
                      key={conv.id}
                      conv={conv}
                      isActive={conv.id === activeConversationId}
                      onSelect={onSelectConversation}
                      onDelete={onDeleteConversation}
                      onRename={onRenameConversation}
                    />
                  ))}
                </div>
              )
            )}
          </>
        )}
      </div>

      {/* Footer — preferences + user profile */}
      <div className="border-t border-[var(--border-primary)] px-3 py-3">
        {/* Preferences row */}
        <div className="mb-2 flex items-center justify-between rounded-lg bg-[var(--surface-hover)] px-2.5 py-1.5">
          <span className="flex items-center gap-2 text-[11px] font-medium text-[var(--text-tertiary)]">
            <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <path d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01" />
            </svg>
            Suggested questions
          </span>
          <button
            role="switch"
            aria-checked={suggestionsEnabled}
            aria-label="Toggle suggested questions"
            onClick={onToggleSuggestions}
            className={`relative h-4.5 w-8 rounded-full transition ${
              suggestionsEnabled ? "bg-[var(--accent-primary)]" : "bg-[var(--surface-active)]"
            }`}
            type="button"
          >
            <span
              className={`absolute top-0.5 h-3.5 w-3.5 rounded-full bg-white shadow transition-all ${
                suggestionsEnabled ? "left-4" : "left-0.5"
              }`}
            />
          </button>
        </div>

        <div className="flex items-center justify-between pl-2.5 pr-1">
          <span className="text-[11px] font-medium text-[var(--text-tertiary)]">Theme</span>
          <ThemeToggle />
        </div>

        {/* User profile */}
        <div className="mt-2 border-t border-[var(--border-primary)] pt-2">
          {user ? (
            <div className="flex items-center gap-2.5">
              {/* Avatar */}
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--accent-primary)] text-xs font-semibold text-white">
                {(user.name?.[0] || user.email?.[0] || "U").toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[12px] font-medium text-[var(--text-secondary)]">{user.name || "User"}</p>
                <p className="truncate text-[10px] text-[var(--text-muted)]">{user.email}</p>
              </div>
              <div className="flex items-center gap-0.5">
                {/* Settings link */}
                <Link
                  to="/settings"
                  className="flex h-6 w-6 items-center justify-center rounded text-[var(--text-muted)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--text-secondary)]"
                  aria-label="Settings"
                  title="Settings"
                >
                  <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
                    <circle cx="12" cy="12" r="3" />
                    <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" />
                  </svg>
                </Link>
                {/* Logout */}
                <button
                  onClick={handleLogout}
                  className="flex h-6 w-6 items-center justify-center rounded text-[var(--text-muted)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--error)]"
                  aria-label="Sign out"
                  title="Sign out"
                  type="button"
                >
                  <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
                    <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" />
                  </svg>
                </button>
              </div>
            </div>
          ) : (
            <Link
              to="/login"
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-[var(--border-primary)] bg-[var(--surface-hover)] px-3 py-2 text-[13px] font-medium text-[var(--text-secondary)] transition hover:bg-[var(--surface-active)] hover:text-[var(--text-primary)]"
            >
              Sign in
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}