/**
 * Settings page - account, appearance, chat preferences, and data management.
 * Dense, plain, accessible, and strictly follows design system tokens.
 */
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext.jsx";
import { useTheme } from "../contexts/ThemeContext.jsx";
import { apiFetch, clearAuth } from "../services/api.js";
import { updateProfile } from "../services/auth.js";
import Dialog from "../components/ui/Dialog.jsx";
import Toast from "../components/ui/Toast.jsx";

export default function Settings() {
  const { user, setUser, logout } = useAuth();
  const navigate = useNavigate();
  const { theme, setTheme } = useTheme();

  // Profile customisation state
  const [displayName, setDisplayName] = useState(() => user?.display_name || user?.name || "");
  const [avatarType, setAvatarType] = useState(() => user?.avatar_type || (user?.photo_url || user?.avatar ? "photo" : "initials"));
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileStatus, setProfileStatus] = useState(null);

  // Sync profile state when user changes
  useEffect(() => {
    if (user) {
      setDisplayName(user.display_name || user.name || "");
      setAvatarType(user.avatar_type || (user.photo_url || user.avatar ? "photo" : "initials"));
    }
  }, [user]);

  // Typing suggestions preference
  const [typingSuggestions, setTypingSuggestions] = useState(() => {
    try {
      return localStorage.getItem("typing_suggestions") !== "false";
    } catch {
      return true;
    }
  });

  // Tips preference
  const [showTips, setShowTips] = useState(() => {
    try {
      return localStorage.getItem("show_tips") !== "false";
    } catch {
      return true;
    }
  });

  // UI state
  const [toastMessage, setToastMessage] = useState("");
  const [toastType, setToastType] = useState("info");
  const [confirmSignout, setConfirmSignout] = useState(false);
  const [confirmDeleteConvs, setConfirmDeleteConvs] = useState(false);
  const [confirmDeleteAccount, setConfirmDeleteAccount] = useState(false);
  const [deleteAccountInput, setDeleteAccountInput] = useState("");
  const [exporting, setExporting] = useState(false);

  const showToast = (msg, type = "info") => {
    setToastMessage(msg);
    setToastType(type);
  };

  const handleToggleSuggestions = () => {
    const next = !typingSuggestions;
    setTypingSuggestions(next);
    try {
      localStorage.setItem("typing_suggestions", String(next));
      showToast(next ? "Typing suggestions enabled" : "Typing suggestions disabled", "success");
    } catch {
      /* ignore */
    }
  };

  const handleToggleTips = () => {
    const next = !showTips;
    setShowTips(next);
    try {
      localStorage.setItem("show_tips", String(next));
      showToast(next ? "Tips enabled" : "Tips disabled", "success");
    } catch {
      /* ignore */
    }
  };

  const hasPhotoUrl = Boolean(user?.photo_url || user?.avatar);
  const trimmedName = displayName.trim();
  let nameError = "";
  if (!trimmedName) {
    nameError = "Display name cannot be empty";
  } else if (trimmedName.length > 40) {
    nameError = "Display name cannot exceed 40 characters";
  } else if (/<|>/.test(trimmedName)) {
    nameError = "Display name cannot contain HTML tags";
  } else if (/https?:\/\/|www\./i.test(trimmedName)) {
    nameError = "Display name cannot contain URLs";
  }

  const isProfileDirty = user && (
    trimmedName !== (user.display_name || user.name || "").trim() ||
    avatarType !== (user.avatar_type || (hasPhotoUrl ? "photo" : "initials"))
  );
  const isProfileValid = !nameError && (avatarType === "initials" || (avatarType === "photo" && hasPhotoUrl));

  const handleSaveProfile = async (e) => {
    e?.preventDefault();
    if (!isProfileValid || !isProfileDirty || profileSaving) return;
    setProfileSaving(true);
    setProfileStatus(null);
    try {
      const updated = await updateProfile({
        display_name: trimmedName,
        avatar_type: avatarType,
      });
      setUser((prev) => ({
        ...prev,
        ...updated,
        name: updated.display_name || updated.name || prev?.name,
        display_name: updated.display_name,
        avatar_type: updated.avatar_type,
      }));
      setProfileStatus({ type: "success", message: "Profile updated successfully" });
      showToast("Profile updated successfully", "success");
    } catch (err) {
      const msg = err.message || "Failed to update profile";
      setProfileStatus({ type: "error", message: msg });
      showToast(msg, "danger");
    } finally {
      setProfileSaving(false);
    }
  };

  const handleExportData = async () => {
    setExporting(true);
    try {
      const data = await apiFetch("/api/auth/me/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `charusat_conversations_${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      showToast("Conversation data exported as JSON", "success");
    } catch (err) {
      showToast(err.message || "Failed to export conversations", "danger");
    } finally {
      setExporting(false);
    }
  };

  const handleDeleteAllConversations = async () => {
    try {
      await apiFetch("/api/conversations", { method: "DELETE" });
      setConfirmDeleteConvs(false);
      showToast("All conversations deleted successfully", "success");
    } catch (err) {
      showToast(err.message || "Failed to delete conversations", "danger");
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteAccountInput !== "DELETE") {
      showToast("Type DELETE to confirm account deletion", "danger");
      return;
    }
    try {
      await apiFetch("/api/auth/me", { method: "DELETE" });
      setConfirmDeleteAccount(false);
      clearAuth();
      navigate("/login", { replace: true });
    } catch (err) {
      showToast(err.message || "Failed to delete account", "danger");
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate("/", { replace: true });
  };

  const handleBack = () => {
    if (window.history.state?.idx > 0) navigate(-1);
    else navigate("/");
  };

  return (
    <div className="min-h-dvh flex flex-col font-sans" style={{ background: "var(--page)", color: "var(--text)" }}>
      <Toast
        message={toastMessage}
        type={toastType}
        onClose={() => setToastMessage("")}
      />

      {/* Header */}
      <header
        className="sticky top-0 z-30 border-b px-4 py-3"
        style={{ borderColor: "var(--border)", background: "var(--surface)" }}
      >
        <div className="mx-auto flex max-w-2xl items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={handleBack}
              className="flex h-8 w-8 items-center justify-center rounded-md border text-xs font-medium transition hover:border-[var(--border-focus)]"
              style={{
                borderColor: "var(--border)",
                background: "var(--surface-2)",
                color: "var(--text)",
              }}
              aria-label="Back to chat"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="M19 12H5M12 5l-7 7 7 7" />
              </svg>
            </button>
            <h1 className="text-sm font-semibold tracking-tight" style={{ color: "var(--text)" }}>
              Settings
            </h1>
          </div>
          <Link
            to="/chat"
            className="rounded-md border px-3 py-1.5 text-xs font-medium transition hover:border-[var(--border-focus)]"
            style={{
              borderColor: "var(--border)",
              background: "var(--surface)",
              color: "var(--text)",
            }}
          >
            Done
          </Link>
        </div>
      </header>

      {/* Main Settings List */}
      <main className="mx-auto max-w-2xl flex-1 px-4 py-6 sm:px-6 w-full space-y-6">
        {user ? (
          <>
            {/* Account Card */}
            <section
              className="rounded-lg border p-5"
              style={{ background: "var(--surface)", borderColor: "var(--border)" }}
            >
              <div className="flex items-center gap-4 mb-4">
                <div
                  className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-base font-semibold font-mono text-white" /* allow-round: avatar */
                  style={{ background: "var(--accent)" }}
                >
                  {(user.name?.[0] || user.email?.[0] || "U").toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold truncate" style={{ color: "var(--text)" }}>
                    {user.name || "User"}
                  </p>
                  <p className="text-xs font-mono truncate" style={{ color: "var(--muted)" }}>
                    {user.email}
                  </p>
                </div>
                <span
                  className="rounded-md border px-2 py-0.5 text-[11px] font-mono font-medium uppercase shrink-0"
                  style={{
                    borderColor: "var(--border)",
                    background: "var(--surface-2)",
                    color: "var(--text-2)",
                  }}
                >
                  {user.role}
                </span>
              </div>

              <div className="border-t pt-3 text-xs divide-y" style={{ borderColor: "var(--border)" }}>
                <div className="flex items-center justify-between py-2">
                  <span style={{ color: "var(--muted)" }}>Sign-in method</span>
                  <span className="font-medium" style={{ color: "var(--text)" }}>
                    {user.google_id ? "Google OAuth" : "Email and password"}
                  </span>
                </div>
                {user.role === "admin" && (
                  <div className="flex items-center justify-between py-2">
                    <span style={{ color: "var(--muted)" }}>Staff Administration</span>
                    <Link
                      to="/admin"
                      className="rounded-md border px-2.5 py-1 text-xs font-medium transition hover:border-[var(--accent)]"
                      style={{
                        background: "var(--accent-surface)",
                        borderColor: "var(--border)",
                        color: "var(--accent)",
                      }}
                    >
                      Admin Console
                    </Link>
                  </div>
                )}
              </div>
            </section>

            {/* Profile Section */}
            <section
              className="rounded-lg border p-5 space-y-4"
              style={{ background: "var(--surface)", borderColor: "var(--border)" }}
            >
              <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
                Profile
              </h2>

              {/* Display Name Input */}
              <div className="space-y-1.5">
                <label htmlFor="display-name-input" className="block text-xs font-medium" style={{ color: "var(--text)" }}>
                  Display Name
                </label>
                <input
                  id="display-name-input"
                  type="text"
                  value={displayName}
                  onChange={(e) => {
                    setDisplayName(e.target.value);
                    if (profileStatus) setProfileStatus(null);
                  }}
                  maxLength={50}
                  className="w-full rounded-md border px-3 py-2 text-xs transition outline-none focus:border-[var(--accent)]"
                  style={{
                    borderColor: nameError && displayName ? "var(--danger)" : "var(--border)",
                    background: "var(--surface-2)",
                    color: "var(--text)",
                    borderRadius: "6px",
                  }}
                  placeholder="Your display name"
                />
                {nameError && displayName && (
                  <p className="text-[11px]" style={{ color: "var(--danger)" }}>
                    {nameError}
                  </p>
                )}
                <p className="text-[11px]" style={{ color: "var(--muted)" }}>
                  1 to 40 characters. Visible in greetings and assistant interactions.
                </p>
              </div>

              {/* Avatar Choice */}
              <div className="space-y-2">
                <span className="block text-xs font-medium" style={{ color: "var(--text)" }}>
                  Avatar Choice
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {/* Google Photo */}
                  <button
                    type="button"
                    disabled={!hasPhotoUrl}
                    onClick={() => {
                      if (hasPhotoUrl) {
                        setAvatarType("photo");
                        if (profileStatus) setProfileStatus(null);
                      }
                    }}
                    className="flex items-center gap-3 rounded-lg border p-3 text-left transition cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                    style={{
                      borderColor: avatarType === "photo" && hasPhotoUrl ? "var(--accent)" : "var(--border)",
                      background: avatarType === "photo" && hasPhotoUrl ? "var(--accent-surface)" : "var(--surface-2)",
                      borderRadius: "8px",
                    }}
                  >
                    {hasPhotoUrl ? (
                      <img
                        src={user?.photo_url || user?.avatar}
                        alt="Google avatar"
                        className="h-8 w-8 rounded-full object-cover shrink-0" /* allow-round: avatar */
                      />
                    ) : (
                      <div
                        className="h-8 w-8 rounded-full flex items-center justify-center shrink-0 text-xs font-mono" /* allow-round: avatar */
                        style={{ background: "var(--border)", color: "var(--muted)" }}
                      >
                        ?
                      </div>
                    )}
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-semibold" style={{ color: "var(--text)" }}>
                        Google photo
                      </p>
                      <p className="text-[11px] truncate" style={{ color: "var(--muted)" }}>
                        {hasPhotoUrl ? "Connected Google account photo" : "Unavailable (no photo linked)"}
                      </p>
                    </div>
                  </button>

                  {/* Initials */}
                  <button
                    type="button"
                    onClick={() => {
                      setAvatarType("initials");
                      if (profileStatus) setProfileStatus(null);
                    }}
                    className="flex items-center gap-3 rounded-lg border p-3 text-left transition cursor-pointer"
                    style={{
                      borderColor: avatarType === "initials" ? "var(--accent)" : "var(--border)",
                      background: avatarType === "initials" ? "var(--accent-surface)" : "var(--surface-2)",
                      borderRadius: "8px",
                    }}
                  >
                    <div
                      className="h-8 w-8 rounded-full flex items-center justify-center shrink-0 text-xs font-semibold font-mono text-white" /* allow-round: avatar */
                      style={{ background: "var(--accent)" }}
                    >
                      {((trimmedName || user?.email || "U")[0] || "U").toUpperCase()}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-semibold" style={{ color: "var(--text)" }}>
                        Initials
                      </p>
                      <p className="text-[11px] truncate" style={{ color: "var(--muted)" }}>
                        Two-letter initials preview
                      </p>
                    </div>
                  </button>
                </div>
              </div>

              {/* Save Button */}
              <div className="flex items-center gap-3 pt-2">
                <button
                  type="button"
                  disabled={!isProfileDirty || !isProfileValid || profileSaving}
                  onClick={handleSaveProfile}
                  className="rounded-md px-4 py-2 text-xs font-medium text-white transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                  style={{
                    background: "var(--accent)",
                    borderRadius: "6px",
                  }}
                >
                  {profileSaving ? "Saving..." : "Save profile"}
                </button>
                {profileStatus && (
                  <span
                    className="text-xs font-medium"
                    style={{ color: profileStatus.type === "success" ? "var(--accent)" : "var(--danger)" }}
                  >
                    {profileStatus.message}
                  </span>
                )}
              </div>
            </section>

            {/* Appearance */}
            <section
              className="rounded-lg border p-5 space-y-3"
              style={{ background: "var(--surface)", borderColor: "var(--border)" }}
            >
              <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
                Appearance
              </h2>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { id: "system", label: "System" },
                  { id: "light", label: "Light" },
                  { id: "dark", label: "Dark" },
                ].map((item) => {
                  const isSelected = theme === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => setTheme(item.id)}
                      className="rounded-md border px-3 py-2 text-xs font-medium transition"
                      style={{
                        background: isSelected ? "var(--accent)" : "var(--surface-2)",
                        borderColor: isSelected ? "var(--accent)" : "var(--border)",
                        color: isSelected ? "#FFFFFF" : "var(--text)",
                      }}
                      type="button"
                    >
                      {item.label}
                    </button>
                  );
                })}
              </div>
            </section>

            {/* Chat Preferences */}
            <section
              className="rounded-lg border p-5 space-y-3"
              style={{ background: "var(--surface)", borderColor: "var(--border)" }}
            >
              <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
                Chat Preferences
              </h2>
              <div className="flex items-center justify-between py-1">
                <div>
                  <p className="text-xs font-semibold" style={{ color: "var(--text)" }}>
                    Typing Suggestions
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
                    Display recommended questions from official bank as you type
                  </p>
                </div>
                <button
                  onClick={handleToggleSuggestions}
                  className="rounded-md border px-3 py-1.5 text-xs font-medium transition"
                  style={{
                    background: typingSuggestions ? "var(--accent-surface)" : "var(--surface-2)",
                    borderColor: typingSuggestions ? "var(--accent)" : "var(--border)",
                    color: typingSuggestions ? "var(--accent)" : "var(--muted)",
                  }}
                  type="button"
                >
                  {typingSuggestions ? "Enabled" : "Disabled"}
                </button>
                {/* Tips toggle */}
                <div className="flex items-center justify-between py-1 border-t pt-3" style={{ borderColor: "var(--border)" }}>
                  <div>
                    <p className="text-xs font-semibold" style={{ color: "var(--text)" }}>
                      Show Tips
                    </p>
                    <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
                      Show helpful keyboard shortcuts and discovery tips near the composer
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleToggleTips}
                    className="relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full transition-colors" /* allow-round: toggle switch */
                    style={{
                      background: showTips ? "var(--accent)" : "var(--surface-3)",
                    }}
                    role="switch"
                    aria-checked={showTips}
                  >
                    <span
                      className="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform" /* allow-round: toggle dot */
                      style={{
                        transform: showTips ? "translateX(18px)" : "translateX(2px)",
                      }}
                    />
                  </button>
                </div>
              </div>
            </section>

            {/* Data Management */}
            <section
              className="rounded-lg border p-5 space-y-3"
              style={{ background: "var(--surface)", borderColor: "var(--border)" }}
            >
              <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
                Data and Privacy
              </h2>
              <div className="space-y-3">
                <div className="flex items-center justify-between py-1 border-b pb-3" style={{ borderColor: "var(--border)" }}>
                  <div>
                    <p className="text-xs font-semibold" style={{ color: "var(--text)" }}>
                      Export Conversations
                    </p>
                    <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
                      Download all your chat history and messages in JSON format
                    </p>
                  </div>
                  <button
                    onClick={handleExportData}
                    disabled={exporting}
                    className="rounded-md border px-3 py-1.5 text-xs font-medium transition hover:border-[var(--border-focus)] disabled:opacity-50"
                    style={{
                      background: "var(--surface)",
                      borderColor: "var(--border)",
                      color: "var(--text)",
                    }}
                    type="button"
                  >
                    {exporting ? "Exporting..." : "Export JSON"}
                  </button>
                </div>

                <div className="flex items-center justify-between py-1">
                  <div>
                    <p className="text-xs font-semibold" style={{ color: "var(--text)" }}>
                      Clear Conversation History
                    </p>
                    <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
                      Delete all chat threads while keeping your user account active
                    </p>
                  </div>
                  <button
                    onClick={() => setConfirmDeleteConvs(true)}
                    className="rounded-md border px-3 py-1.5 text-xs font-medium transition hover:border-[var(--danger)]"
                    style={{
                      background: "var(--surface)",
                      borderColor: "var(--border)",
                      color: "var(--danger)",
                    }}
                    type="button"
                  >
                    Clear history
                  </button>
                </div>
              </div>
            </section>

            {/* About */}
            <section
              className="rounded-lg border p-5 space-y-3"
              style={{ background: "var(--surface)", borderColor: "var(--border)" }}
            >
              <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
                About
              </h2>
              <div>
                <Link
                  to="/about"
                  className="rounded-md border p-2.5 text-center text-xs font-medium transition hover:border-[var(--border-focus)]"
                  style={{
                    background: "var(--surface-2)",
                    borderColor: "var(--border)",
                    color: "var(--text-2)",
                  }}
                >
                  About Assistant
                </Link>
              </div>
            </section>

            {/* Sign Out and Danger Zone */}
            <section
              className="rounded-lg border p-5 space-y-4"
              style={{
                background: "var(--surface)",
                borderColor: "var(--border)",
              }}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold" style={{ color: "var(--text)" }}>
                    Sign Out
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
                    End your current session on this device
                  </p>
                </div>
                <button
                  onClick={() => setConfirmSignout(true)}
                  className="rounded-md border px-3 py-1.5 text-xs font-medium transition hover:border-[var(--border-focus)]"
                  style={{
                    background: "var(--surface)",
                    borderColor: "var(--border)",
                    color: "var(--text)",
                  }}
                  type="button"
                >
                  Sign out
                </button>
              </div>

              <div className="border-t pt-4 flex items-center justify-between" style={{ borderColor: "var(--border)" }}>
                <div>
                  <p className="text-xs font-semibold" style={{ color: "var(--danger)" }}>
                    Delete Account
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
                    Permanently delete your profile and all conversation data
                  </p>
                </div>
                <button
                  onClick={() => setConfirmDeleteAccount(true)}
                  className="rounded-md border px-3 py-1.5 text-xs font-medium transition hover:border-[var(--danger)]"
                  style={{
                    background: "var(--surface)",
                    borderColor: "var(--border)",
                    color: "var(--danger)",
                  }}
                  type="button"
                >
                  Delete account
                </button>
              </div>
            </section>
          </>
        ) : (
          <div
            className="rounded-lg border p-8 text-center space-y-3"
            style={{ background: "var(--surface)", borderColor: "var(--border)", borderRadius: "8px" }}
          >
            <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>
              Sign in to customize your profile name and avatar
            </p>
            <p className="text-xs max-w-md mx-auto" style={{ color: "var(--muted)" }}>
              Guest mode uses a temporary session. Sign in to customize your display name, choose your avatar, and access persistent chat history.
            </p>
            <div className="pt-2 flex items-center justify-center gap-3">
              <Link
                to="/login"
                className="rounded-md px-4 py-2 text-xs font-medium text-white transition hover:opacity-90"
                style={{ background: "var(--accent)", borderRadius: "6px" }}
              >
                Sign in
              </Link>
              <Link
                to="/signup"
                className="rounded-md border px-4 py-2 text-xs font-medium transition hover:border-[var(--border-focus)]"
                style={{
                  borderColor: "var(--border)",
                  background: "var(--surface)",
                  color: "var(--text)",
                  borderRadius: "6px",
                }}
              >
                Create account
              </Link>
            </div>
          </div>
        )}
      </main>

      {/* Confirm Sign Out Modal */}
      <Dialog
        open={confirmSignout}
        onClose={() => setConfirmSignout(false)}
        title="Sign Out"
        confirmLabel="Sign Out"
        onConfirm={handleLogout}
      >
        <p className="text-xs leading-relaxed" style={{ color: "var(--text-2)" }}>
          Are you sure you want to sign out of your account? Your saved conversations remain safely stored on the server.
        </p>
      </Dialog>

      {/* Confirm Delete Conversations Modal */}
      <Dialog
        open={confirmDeleteConvs}
        onClose={() => setConfirmDeleteConvs(false)}
        title="Delete All Conversations"
        confirmLabel="Delete All"
        danger
        onConfirm={handleDeleteAllConversations}
      >
        <p className="text-xs leading-relaxed" style={{ color: "var(--text-2)" }}>
          Are you sure you want to delete all your conversations? This action cannot be undone.
        </p>
      </Dialog>

      {/* Confirm Delete Account Modal */}
      <Dialog
        open={confirmDeleteAccount}
        onClose={() => {
          setConfirmDeleteAccount(false);
          setDeleteAccountInput("");
        }}
        title="Delete Account and Data"
        confirmLabel="Permanently Delete"
        danger
        onConfirm={handleDeleteAccount}
      >
        <div className="space-y-3">
          <p className="text-xs leading-relaxed" style={{ color: "var(--text-2)" }}>
            This will permanently delete your account, saved conversations, and associated settings.
          </p>
          <p className="text-xs font-semibold" style={{ color: "var(--danger)" }}>
            Type DELETE below to confirm:
          </p>
          <input
            type="text"
            value={deleteAccountInput}
            onChange={(e) => setDeleteAccountInput(e.target.value)}
            placeholder="DELETE"
            className="w-full rounded-md border p-2 text-xs font-mono uppercase focus:outline-none"
            style={{
              background: "var(--surface)",
              borderColor: "var(--border)",
              color: "var(--text)",
            }}
          />
        </div>
      </Dialog>
    </div>
  );
}
