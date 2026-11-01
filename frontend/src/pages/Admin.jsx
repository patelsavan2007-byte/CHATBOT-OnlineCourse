import RichText from "../components/RichText.jsx";
import ThemedLogo from "../components/ui/ThemedLogo.jsx";
/**
 * Admin Console - 5-tab operations portal for university staff.
 *
 * Tabs:
 * 1. Overview (metrics, single aggregation, custom SVG dual-series chart, accessible table)
 * 2. Needs attention (Unanswered questions with re-testing and "Answer this", Answers rated bad)
 * 3. Knowledge Base (Chroma vector index breakdown, official document status, sync status)
 * 4. Users (Role management, enable/disable toggle, last active, typed delete confirmation)
 * 5. System (Real MongoDB ping, vector chunk count, LLM statuses, cache controls, recent audit log)
 *
 * Strict standing rules:
 * - Zero emoji
 * - Zero em dashes
 * - No gradients, no purple/violet/indigo
 * - 6px buttons, 8px cards
 * - Accessible contrast across light and dark themes
 */
import { useEffect, useState, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext.jsx";
import { API_BASE, apiFetch } from "../services/api.js";
import Dialog from "../components/ui/Dialog.jsx";
import Toast from "../components/ui/Toast.jsx";
import ThemeToggle from "../components/ui/ThemeToggle.jsx";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "needs_attention", label: "Needs attention" },
  { id: "knowledge_base", label: "Knowledge Base" },
  { id: "users", label: "Users" },
  { id: "system", label: "System" },
];

const TAB_DESCRIPTIONS = {
  overview: "Overall question volume, unanswered rate, response times, and user satisfaction.",
  needs_attention: "Questions the assistant could not answer and answers rated unhelpful. Review and resolve them.",
  knowledge_base: "Official course catalogs, syllabi, and uploaded documents powering chatbot answers.",
  users: "Manage student and staff user accounts, role permissions, and access status.",
  system: "Infrastructure connectivity, vector store index status, cache management, and administrative audit logs.",
};

function StatCard({ label, value, subtitle, tooltip, accent = false }) {
  return (
    <div
      className="rounded-lg border p-4 transition-colors"
      style={{
        background: "var(--surface)",
        borderColor: accent ? "var(--border-focus)" : "var(--border)",
      }}
      title={tooltip}
    >
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium" style={{ color: "var(--muted)" }}>
          {label}
        </p>
        {tooltip && (
          <span
            className="text-[10px] font-mono cursor-help px-1 rounded border"
            style={{ borderColor: "var(--border)", color: "var(--muted)" }}
            aria-label={tooltip}
          >
            ?
          </span>
        )}
      </div>
      <p
        className="mt-2 text-2xl font-bold font-mono tracking-tight"
        style={{ color: accent ? "var(--accent)" : "var(--text)" }}
      >
        {value}
      </p>
      {subtitle && (
        <p className="mt-1 text-xs" style={{ color: "var(--text-2)" }}>
          {subtitle}
        </p>
      )}
    </div>
  );
}

function OverviewChart({ dailyCounts }) {
  if (!dailyCounts || dailyCounts.length === 0) {
    return (
      <div className="rounded-lg border p-8 text-center" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
        <p className="text-xs" style={{ color: "var(--muted)" }}>No query activity recorded in this period.</p>
      </div>
    );
  }

  const maxTotal = Math.max(...dailyCounts.map((d) => d.total), 5);
  const chartHeight = 160;
  const chartWidth = 720;
  const paddingX = 40;
  const paddingY = 25;
  const innerWidth = chartWidth - paddingX * 2;
  const innerHeight = chartHeight - paddingY * 2;

  const pointsTotal = dailyCounts.map((d, i) => {
    const x = paddingX + (i / Math.max(1, dailyCounts.length - 1)) * innerWidth;
    const y = paddingY + innerHeight - (d.total / maxTotal) * innerHeight;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");

  const pointsGaps = dailyCounts.map((d, i) => {
    const x = paddingX + (i / Math.max(1, dailyCounts.length - 1)) * innerWidth;
    const y = paddingY + innerHeight - (d.gaps / maxTotal) * innerHeight;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");

  return (
    <div className="rounded-lg border p-4" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
            Daily Query Volume and Knowledge Gaps
          </h3>
          <p className="text-[11px]" style={{ color: "var(--text-2)" }}>
            Blue: Total queries. Amber: Unanswered questions.
          </p>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono">
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: "var(--accent)" }} />
            Total queries
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: "var(--warning)" }} />
            Unanswered (gaps)
          </span>
        </div>
      </div>

      <div className="w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          className="w-full h-auto min-w-[500px]"
          aria-label="Daily query trend chart"
          role="img"
        >
          {/* Gridlines */}
          {[0, 0.5, 1].map((pct) => {
            const y = paddingY + innerHeight * pct;
            const val = Math.round(maxTotal * (1 - pct));
            return (
              <g key={pct}>
                <line
                  x1={paddingX}
                  y1={y}
                  x2={chartWidth - paddingX}
                  y2={y}
                  stroke="var(--border)"
                  strokeDasharray="3 3"
                  strokeWidth="1"
                />
                <text
                  x={paddingX - 6}
                  y={y + 3}
                  fontSize="10"
                  textAnchor="end"
                  fill="var(--muted)"
                  fontFamily="monospace"
                >
                  {val}
                </text>
              </g>
            );
          })}

          {/* Lines */}
          <polyline
            fill="none"
            stroke="var(--accent)"
            strokeWidth="2.2"
            points={pointsTotal}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <polyline
            fill="none"
            stroke="var(--warning)"
            strokeWidth="2"
            strokeDasharray="4 2"
            points={pointsGaps}
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Dots on points */}
          {dailyCounts.map((d, i) => {
            const x = paddingX + (i / Math.max(1, dailyCounts.length - 1)) * innerWidth;
            const yTot = paddingY + innerHeight - (d.total / maxTotal) * innerHeight;
            const yGap = paddingY + innerHeight - (d.gaps / maxTotal) * innerHeight;
            return (
              <g key={d.date}>
                <circle cx={x} cy={yTot} r="3" fill="var(--accent)" />
                {d.gaps > 0 && <circle cx={x} cy={yGap} r="3" fill="var(--warning)" />}
              </g>
            );
          })}

          {/* Date labels on X axis */}
          {dailyCounts.map((d, i) => {
            if (dailyCounts.length > 10 && i % Math.ceil(dailyCounts.length / 7) !== 0 && i !== dailyCounts.length - 1) {
              return null;
            }
            const x = paddingX + (i / Math.max(1, dailyCounts.length - 1)) * innerWidth;
            const label = d.date.slice(5); // MM-DD
            return (
              <text
                key={d.date}
                x={x}
                y={chartHeight - 4}
                fontSize="10"
                textAnchor="middle"
                fill="var(--muted)"
                fontFamily="monospace"
              >
                {label}
              </text>
            );
          })}
        </svg>
      </div>

      {/* Accessible data table */}
      <details className="mt-3 text-xs" style={{ color: "var(--text-2)" }}>
        <summary className="cursor-pointer font-medium hover:underline">
          View tabular data for screen readers
        </summary>
        <div className="mt-2 max-h-48 overflow-y-auto rounded border" style={{ borderColor: "var(--border)" }}>
          <table className="w-full text-left font-mono text-[11px]">
            <thead style={{ background: "var(--surface-2)" }}>
              <tr>
                <th className="px-3 py-1.5 border-b" style={{ borderColor: "var(--border)" }}>Date</th>
                <th className="px-3 py-1.5 border-b text-right" style={{ borderColor: "var(--border)" }}>Total</th>
                <th className="px-3 py-1.5 border-b text-right" style={{ borderColor: "var(--border)" }}>Answered</th>
                <th className="px-3 py-1.5 border-b text-right" style={{ borderColor: "var(--border)" }}>Gaps</th>
              </tr>
            </thead>
            <tbody>
              {dailyCounts.map((d) => (
                <tr key={d.date} className="border-b" style={{ borderColor: "var(--border)" }}>
                  <td className="px-3 py-1">{d.date}</td>
                  <td className="px-3 py-1 text-right">{d.total}</td>
                  <td className="px-3 py-1 text-right">{d.answered}</td>
                  <td className="px-3 py-1 text-right">{d.gaps}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}

export default function Admin() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("overview");

  // Global loading / error / toast state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [toastMessage, setToastMessage] = useState("");
  const [toastType, setToastType] = useState("info");
  const [showSignoutDialog, setShowSignoutDialog] = useState(false);

  const showToast = (msg, type = "info") => {
    setToastMessage(msg);
    setToastType(type);
  };

  // Tab 1: Overview
  const [overviewDays, setOverviewDays] = useState(30);
  const [overviewData, setOverviewData] = useState(null);

  // Tab 2: Needs attention
  const [attentionSubtab, setAttentionSubtab] = useState("unanswered"); // "unanswered" | "feedback"
  const [gaps, setGaps] = useState([]);
  const [gapSearch, setGapSearch] = useState("");
  const [gapProgrammeFilter, setGapProgrammeFilter] = useState("");
  const [gapTopicFilter, setGapTopicFilter] = useState("");
  const [gapStatusFilter, setGapStatusFilter] = useState("");
  const [retestingGaps, setRetestingGaps] = useState(false);
  const [editingGapNote, setEditingGapNote] = useState(null); // { question, notes }
  const [feedbackItems, setFeedbackItems] = useState([]);

  // "Answer this" state for Part 4
  const [answeringGap, setAnsweringGap] = useState(null);
  const [answerDraft, setAnswerDraft] = useState("");
  const [answerSource, setAnswerSource] = useState("");
  const [answerProgramme, setAnswerProgramme] = useState("GENERAL");
  const [savingAnswer, setSavingAnswer] = useState(false);

  // Tab 3: Knowledge Base
  const [kbData, setKbData] = useState(null);
  const [kbStatus, setKbStatus] = useState(null);
  const [kbUploading, setKbUploading] = useState(false);
  const [kbSyncing, setKbSyncing] = useState(false);
  const [activeDraft, setActiveDraft] = useState(null);
  const [showPublishConfirm, setShowPublishConfirm] = useState(false);
  const [publishingDraft, setPublishingDraft] = useState(false);
  const [viewingDoc, setViewingDoc] = useState(null);
  const [viewingDocContent, setViewingDocContent] = useState("");
  const [loadingDocContent, setLoadingDocContent] = useState(false);
  const [deletingDoc, setDeletingDoc] = useState(null);
  const [deleteDocConfirmInput, setDeleteDocConfirmInput] = useState("");
  const [testQuestionInput, setTestQuestionInput] = useState("");
  const [testQuestionResult, setTestQuestionResult] = useState(null);
  const [testingQuestion, setTestingQuestion] = useState(false);

  // Tab 4: Users
  const [usersList, setUsersList] = useState([]);
  const [userSearch, setUserSearch] = useState("");
  const [userRoleFilter, setUserRoleFilter] = useState("");
  const [userToDelete, setUserToDelete] = useState(null);
  const [deleteConfirmInput, setDeleteConfirmInput] = useState("");

  // Tab 5: System
  const [systemInfo, setSystemInfo] = useState(null);
  const [confirmClearCache, setConfirmClearCache] = useState(false);

  // Data loader
  const loadTabData = useCallback(
    async (tabId) => {
      setLoading(true);
      setError("");
      try {
        if (tabId === "overview") {
          const data = await apiFetch(`/api/admin/overview?days=${overviewDays}`);
          setOverviewData(data);
        } else if (tabId === "needs_attention") {
          const params = new URLSearchParams();
          if (gapProgrammeFilter) params.append("programme", gapProgrammeFilter);
          if (gapTopicFilter) params.append("topic", gapTopicFilter);
          if (gapStatusFilter) params.append("review_status", gapStatusFilter);
          if (gapSearch) params.append("q", gapSearch);
          const [gapsRes, fbRes] = await Promise.all([
            apiFetch(`/api/admin/knowledge-gaps?${params.toString()}`),
            apiFetch("/api/admin/feedback"),
          ]);
          setGaps(gapsRes.gaps || []);
          setFeedbackItems(fbRes.feedback_items || fbRes.feedback || []);
        } else if (tabId === "knowledge_base") {
          const [data, statusData] = await Promise.all([
            apiFetch("/api/admin/knowledge-base").catch(() => null),
            apiFetch("/api/admin/kb/status").catch(() => null),
          ]);
          setKbData(data);
          setKbStatus(statusData);
        } else if (tabId === "users") {
          const params = new URLSearchParams();
          if (userSearch) params.append("q", userSearch);
          if (userRoleFilter) params.append("role", userRoleFilter);
          const data = await apiFetch(`/api/admin/users?${params.toString()}`);
          setUsersList(data.users || []);
        } else if (tabId === "system") {
          const data = await apiFetch("/api/admin/system");
          setSystemInfo(data);
        }
      } catch (err) {
        setError(err.message || "Failed to load tab data");
      } finally {
        setLoading(false);
      }
    },
    [overviewDays, gapProgrammeFilter, gapTopicFilter, gapStatusFilter, gapSearch, userSearch, userRoleFilter]
  );

  useEffect(() => {
    loadTabData(activeTab);
  }, [activeTab, loadTabData]);

  // Handlers for Part 3 & 4: Knowledge Base Manager & Answer This
  const handleUploadFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      showToast("File exceeds 10 MB limit", "danger");
      return;
    }
    setKbUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const token = localStorage.getItem("auth_token");
      const res = await fetch(`${API_BASE}/api/admin/kb/convert`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Conversion failed (${res.status})`);
      }
      const draft = await res.json();
      setActiveDraft(draft);
      showToast("Document converted. Review draft before publishing.", "success");
    } catch (err) {
      showToast(err.message || "Upload conversion failed", "danger");
    } finally {
      setKbUploading(false);
      e.target.value = "";
    }
  };

  const handlePublishDraft = async () => {
    if (!activeDraft) return;
    setPublishingDraft(true);
    try {
      const token = localStorage.getItem("auth_token");
      const res = await apiFetch(`/api/admin/kb/drafts/${activeDraft.draft_id}/publish`, {
        method: "POST",
        body: JSON.stringify({
          title: activeDraft.title,
          programme: activeDraft.programme,
          source_note: activeDraft.source_note,
        }),
      });
      showToast(res.message || "Document published successfully.", "success");
      setActiveDraft(null);
      setShowPublishConfirm(false);
      loadTabData("knowledge_base");
    } catch (err) {
      showToast(err.message || "Failed to publish document", "danger");
    } finally {
      setPublishingDraft(false);
    }
  };

  const handleDeleteDoc = async () => {
    if (!deletingDoc) return;
    try {
      await apiFetch(`/api/admin/kb/documents/${deletingDoc.slug}`, {
        method: "DELETE",
      });
      showToast(`Document ${deletingDoc.filename} removed successfully`, "success");
      setDeletingDoc(null);
      setDeleteDocConfirmInput("");
      loadTabData("knowledge_base");
    } catch (err) {
      showToast(err.message || "Failed to remove document", "danger");
    }
  };

  const handleRunSync = async (forceRebuild = false) => {
    setKbSyncing(true);
    try {
      await apiFetch(`/api/admin/kb/sync?force_rebuild=${forceRebuild}`, {
        method: "POST",
      });
      showToast("Sync workflow dispatched on GitHub Actions", "success");
      loadTabData("knowledge_base");
    } catch (err) {
      showToast(err.message || "Failed to run sync workflow", "danger");
    } finally {
      setKbSyncing(false);
    }
  };

  const handleTestQuestion = async (e) => {
    e?.preventDefault();
    if (!testQuestionInput.trim()) return;
    setTestingQuestion(true);
    try {
      const res = await apiFetch("/api/admin/kb/test-question", {
        method: "POST",
        body: JSON.stringify({ question: testQuestionInput.trim() }),
      });
      setTestQuestionResult(res);
    } catch (err) {
      showToast(err.message || "Test question failed", "danger");
    } finally {
      setTestingQuestion(false);
    }
  };

  const handleDownloadMarkdown = (filename, mdContent) => {
    const blob = new Blob([mdContent], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filename.replace(/\.[^/.]+$/, "")}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleSubmitFaq = async (e) => {
    e?.preventDefault();
    if (!answeringGap) return;
    if (answerDraft.trim().length < 20) {
      showToast("Answer must be at least 20 characters long", "danger");
      return;
    }
    if (!answerSource.trim()) {
      showToast("Official source is required", "danger");
      return;
    }
    setSavingAnswer(true);
    try {
      const qText = answeringGap.question || answeringGap.normalized_question;
      const res = await apiFetch("/api/admin/kb/faq", {
        method: "POST",
        body: JSON.stringify({
          question: qText,
          answer: answerDraft.trim(),
          source: answerSource.trim(),
          programme: answerProgramme,
          gap_id: answeringGap.id || null,
        }),
      });
      showToast("FAQ document saved and knowledge gap resolved.", "success");
      // Update gap status in local state
      setGaps((prev) =>
        prev.map((item) =>
          (item.id === answeringGap.id || item.normalized_question === answeringGap.normalized_question)
            ? { ...item, review_status: "resolved", note: `Answered via ${res.rel_path}` }
            : item
        )
      );
      setAnsweringGap(null);
      setAnswerDraft("");
      setAnswerSource("");
    } catch (err) {
      showToast(err.message || "Failed to save FAQ answer", "danger");
    } finally {
      setSavingAnswer(false);
    }
  };

  // Poll knowledge base status every 15s if rebuilding
  useEffect(() => {
    if (activeTab !== "knowledge_base") return;
    const hasRebuilding = (kbStatus?.documents || []).some((d) => d.status === "Rebuilding") ||
      kbStatus?.automation?.status === "in_progress" ||
      kbStatus?.automation?.status === "queued";
    if (!hasRebuilding) return;

    const timer = setInterval(() => {
      apiFetch("/api/admin/kb/status")
        .then((data) => setKbStatus(data))
        .catch(() => {});
    }, 15000);
    return () => clearInterval(timer);
  }, [activeTab, kbStatus]);

  // Handlers for Needs Attention: Knowledge Gaps
  const handleUpdateGapStatus = async (gapId, newStatus, currentNotes) => {
    try {
      await apiFetch(`/api/admin/knowledge-gaps/${gapId}`, {
        method: "PATCH",
        body: JSON.stringify({
          review_status: newStatus,
          note: currentNotes,
        }),
      });
      showToast("Knowledge gap status updated", "success");
      loadTabData("needs_attention");
    } catch (err) {
      showToast(err.message || "Failed to update gap status", "danger");
    }
  };

  const handleRetestGaps = async () => {
    setRetestingGaps(true);
    try {
      const res = await apiFetch("/api/admin/knowledge-gaps/retest", { method: "POST" });
      showToast(`Retested ${res.retested} questions: ${res.answerable_now} probably answerable now.`, "success");
      loadTabData("needs_attention");
    } catch (err) {
      showToast(err.message || "Retest failed", "danger");
    } finally {
      setRetestingGaps(false);
    }
  };

  const handleBulkResolveAnswerable = async () => {
    try {
      const res = await apiFetch("/api/admin/knowledge-gaps/bulk-resolve", {
        method: "POST",
        body: JSON.stringify({ only_answerable: true }),
      });
      showToast(`Marked ${res.resolved_count} answerable questions as resolved.`, "success");
      loadTabData("needs_attention");
    } catch (err) {
      showToast(err.message || "Bulk resolve failed", "danger");
    }
  };

  const handleExportCsv = () => {
    const params = new URLSearchParams();
    if (gapProgrammeFilter) params.append("programme", gapProgrammeFilter);
    if (gapTopicFilter) params.append("topic", gapTopicFilter);
    const url = `${API_BASE}/api/admin/knowledge-gaps/csv?${params.toString()}`;
    window.open(url, "_blank");
  };

  // Handlers for Needs Attention: Bad Feedback
  const handleMarkFeedbackReviewed = async (messageId) => {
    try {
      await apiFetch(`/api/admin/feedback/${messageId}`, {
        method: "PATCH",
        body: JSON.stringify({ review_status: "reviewed" }),
      });
      showToast("Feedback marked as reviewed", "success");
      loadTabData("needs_attention");
    } catch (err) {
      showToast(err.message || "Failed to update feedback status", "danger");
    }
  };

  // Handlers for Users
  const handleToggleUserRole = async (targetUser) => {
    if (targetUser.id === user?.id) {
      showToast("You cannot change your own admin role", "danger");
      return;
    }
    const newRole = targetUser.role === "admin" ? "user" : "admin";
    try {
      await apiFetch(`/api/admin/users/${targetUser.id}`, {
        method: "PATCH",
        body: JSON.stringify({ role: newRole }),
      });
      showToast(`User role updated to ${newRole}`, "success");
      loadTabData("users");
    } catch (err) {
      showToast(err.message || "Failed to change user role", "danger");
    }
  };

  const handleToggleDisable = async (targetUser) => {
    if (targetUser.id === user?.id) {
      showToast("You cannot disable your own account", "danger");
      return;
    }
    const targetState = !targetUser.is_disabled;
    try {
      await apiFetch(`/api/admin/users/${targetUser.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_disabled: targetState }),
      });
      showToast(targetState ? "User account disabled" : "User account enabled", "success");
      loadTabData("users");
    } catch (err) {
      showToast(err.message || "Failed to update account status", "danger");
    }
  };

  const handleDeleteUser = async () => {
    if (!userToDelete) return;
    if (deleteConfirmInput !== "DELETE") {
      showToast("Please type DELETE to confirm deletion", "danger");
      return;
    }
    try {
      await apiFetch(`/api/admin/users/${userToDelete.id}`, { method: "DELETE" });
      showToast("User and conversation history deleted", "success");
      setUserToDelete(null);
      setDeleteConfirmInput("");
      loadTabData("users");
    } catch (err) {
      showToast(err.message || "Failed to delete user", "danger");
    }
  };

  // Handlers for System Cache
  const handleExecuteClearCache = async () => {
    try {
      await apiFetch("/api/admin/cache", { method: "DELETE" });
      showToast("Question cache cleared successfully", "success");
      setConfirmClearCache(false);
      loadTabData("system");
    } catch (err) {
      showToast(err.message || "Failed to clear cache", "danger");
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
    <div
      className="min-h-screen flex flex-col font-sans"
      style={{ background: "var(--page)", color: "var(--text)" }}
    >
      <Toast
        message={toastMessage}
        type={toastType}
        onClose={() => setToastMessage("")}
      />

      {/* Header Bar */}
      <header
        className="sticky top-0 z-30 border-b px-4 py-3"
        style={{ background: "var(--surface)", borderColor: "var(--border)" }}
      >
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={handleBack}
              className="flex h-8 w-8 items-center justify-center rounded-md border text-xs font-medium transition hover:border-[var(--border-focus)] cursor-pointer"
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
            <ThemedLogo variant="ccoe" height={28} />
            <div>
              <h1 className="text-sm font-semibold tracking-tight" style={{ color: "var(--text)" }}>
                CCOE CHARUSAT Admin Console
              </h1>
            </div>
            <span
              className="rounded-md border px-2 py-0.5 text-[10px] font-semibold"
              style={{
                background: "var(--accent-surface)",
                borderColor: "var(--border)",
                color: "var(--accent)",
              }}
            >
              Staff Portal
            </span>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 text-xs" style={{ color: "var(--muted)" }}>
              <span
                className="h-2 w-2 rounded-full" /* allow-round: status dot */
                style={{ background: "var(--success)" }}
              />
              <span className="font-mono">{user?.email}</span>
            </div>
            <ThemeToggle />
            <button
              onClick={() => setShowSignoutDialog(true)}
              className="rounded-md border px-3 py-1.5 text-xs font-medium transition hover:border-[var(--danger)] cursor-pointer"
              style={{
                borderColor: "var(--border)",
                background: "var(--surface)",
                color: "var(--text-2)",
              }}
              type="button"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      {/* 5-Tab Navigation Bar */}
      <div
        className="border-b px-4"
        style={{ background: "var(--surface)", borderColor: "var(--border)" }}
      >
        <div className="mx-auto flex max-w-6xl gap-1 overflow-x-auto py-2">
          {TABS.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className="rounded-md px-3.5 py-1.5 text-xs font-medium transition whitespace-nowrap cursor-pointer"
                style={{
                  background: isActive ? "var(--accent)" : "transparent",
                  color: isActive ? "#FFFFFF" : "var(--text-2)",
                }}
                type="button"
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Tab Workspace */}
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
        {/* Plain-language one sentence explanation */}
        <div className="mb-6">
          <p className="text-xs" style={{ color: "var(--text-2)" }}>
            {TAB_DESCRIPTIONS[activeTab]}
          </p>
        </div>

        {error && (
          <div
            className="mb-4 rounded-lg border p-3 text-xs"
            style={{
              background: "var(--danger-surface)",
              borderColor: "var(--danger)",
              color: "var(--danger)",
            }}
          >
            {error}
          </div>
        )}

        {/* 1. OVERVIEW TAB */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
                Selected Time Window
              </span>
              <div className="flex items-center gap-1 rounded-md border p-0.5" style={{ borderColor: "var(--border)", background: "var(--surface)" }}>
                {[7, 30, 90].map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setOverviewDays(d)}
                    className="rounded px-2.5 py-1 text-xs font-mono transition cursor-pointer"
                    style={{
                      background: overviewDays === d ? "var(--accent)" : "transparent",
                      color: overviewDays === d ? "#FFFFFF" : "var(--text-2)",
                    }}
                  >
                    {d}d
                  </button>
                ))}
              </div>
            </div>

            {/* 5 Primary Metrics */}
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              <StatCard
                label="Questions"
                value={overviewData?.total_queries ?? 0}
                subtitle={`${overviewData?.answered_queries ?? 0} answered`}
                tooltip="Total student queries submitted in this window."
                accent
              />
              <StatCard
                label="Unanswered Rate"
                value={`${Math.round((overviewData?.gap_rate ?? 0) * 100)}%`}
                subtitle={`${overviewData?.gap_queries ?? 0} unanswered questions`}
                tooltip="Percentage of questions where the bot could not find a confident answer."
              />
              <StatCard
                label="Median Response Time"
                value={`${overviewData?.median_latency_s ?? 0}s`}
                subtitle="Measured end-to-end"
                tooltip="Middle latency for assistant responses in seconds."
              />
              <StatCard
                label="Positive Feedback"
                value={
                  overviewData?.feedback?.enough_ratings
                    ? `${Math.round((overviewData?.feedback?.positive_share ?? 0) * 100)}%`
                    : "Not enough ratings yet"
                }
                subtitle={`${overviewData?.feedback?.thumbs_up ?? 0} helpful, ${overviewData?.feedback?.thumbs_down ?? 0} unhelpful`}
                tooltip="Student ratings breakdown. Shows percentage once 20 or more ratings are received."
              />
              <StatCard
                label="Active Users"
                value={overviewData?.active_users ?? 0}
                subtitle={`${overviewData?.total_users ?? 0} total registered`}
                tooltip="Count of distinct registered accounts asking questions in this period."
              />
            </div>

            {/* Chart: Total queries & Unanswered */}
            <OverviewChart dailyCounts={overviewData?.queries_per_day} />
          </div>
        )}

        {/* 2. NEEDS ATTENTION TAB */}
        {activeTab === "needs_attention" && (
          <div className="space-y-4">
            {/* Segmented Control */}
            <div className="flex border-b" style={{ borderColor: "var(--border)" }}>
              <button
                type="button"
                onClick={() => setAttentionSubtab("unanswered")}
                className="px-4 py-2 text-xs font-semibold border-b-2 transition cursor-pointer"
                style={{
                  borderColor: attentionSubtab === "unanswered" ? "var(--accent)" : "transparent",
                  color: attentionSubtab === "unanswered" ? "var(--accent)" : "var(--text-2)",
                }}
              >
                Unanswered questions ({gaps.length})
              </button>
              <button
                type="button"
                onClick={() => setAttentionSubtab("feedback")}
                className="px-4 py-2 text-xs font-semibold border-b-2 transition cursor-pointer"
                style={{
                  borderColor: attentionSubtab === "feedback" ? "var(--accent)" : "transparent",
                  color: attentionSubtab === "feedback" ? "var(--accent)" : "var(--text-2)",
                }}
              >
                Answers rated bad ({feedbackItems.length})
              </button>
            </div>

            {attentionSubtab === "unanswered" && (
              <div className="space-y-4">
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2 flex-1">
                    <input
                      type="search"
                      placeholder="Search question..."
                      value={gapSearch}
                      onChange={(e) => setGapSearch(e.target.value)}
                      className="rounded-md border px-3 py-1.5 text-xs focus:outline-none w-48 sm:w-60"
                      style={{
                        background: "var(--surface)",
                        borderColor: "var(--border)",
                        color: "var(--text)",
                      }}
                    />
                    <select
                      value={gapProgrammeFilter}
                      onChange={(e) => setGapProgrammeFilter(e.target.value)}
                      className="rounded-md border px-2.5 py-1.5 text-xs focus:outline-none"
                      style={{
                        background: "var(--surface)",
                        borderColor: "var(--border)",
                        color: "var(--text)",
                      }}
                    >
                      <option value="">All Programmes</option>
                      <option value="bba">BBA</option>
                      <option value="bca">BCA</option>
                      <option value="mba">MBA</option>
                      <option value="mca">MCA</option>
                    </select>
                    <select
                      value={gapStatusFilter}
                      onChange={(e) => setGapStatusFilter(e.target.value)}
                      className="rounded-md border px-2.5 py-1.5 text-xs focus:outline-none"
                      style={{
                        background: "var(--surface)",
                        borderColor: "var(--border)",
                        color: "var(--text)",
                      }}
                    >
                      <option value="">All Statuses</option>
                      <option value="open">Open</option>
                      <option value="in_progress">In Progress</option>
                      <option value="resolved">Resolved</option>
                      <option value="ignored">Ignored</option>
                    </select>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      onClick={handleRetestGaps}
                      disabled={retestingGaps}
                      className="rounded-md border px-3 py-1.5 text-xs font-medium transition hover:border-[var(--border-focus)] cursor-pointer"
                      style={{
                        background: "var(--surface)",
                        borderColor: "var(--border)",
                        color: "var(--text)",
                      }}
                      type="button"
                    >
                      {retestingGaps ? "Checking index..." : "Re-test open questions"}
                    </button>
                    <button
                      onClick={handleBulkResolveAnswerable}
                      className="rounded-md border px-3 py-1.5 text-xs font-medium transition hover:border-[var(--success)] cursor-pointer"
                      style={{
                        background: "var(--surface)",
                        borderColor: "var(--border)",
                        color: "var(--text)",
                      }}
                      type="button"
                    >
                      Resolve answerable
                    </button>
                    <button
                      onClick={handleExportCsv}
                      className="rounded-md border px-3 py-1.5 text-xs font-medium transition hover:border-[var(--border-focus)] cursor-pointer"
                      style={{
                        background: "var(--surface)",
                        borderColor: "var(--border)",
                        color: "var(--text)",
                      }}
                      type="button"
                    >
                      Export CSV
                    </button>
                  </div>
                </div>

                {gaps.length === 0 ? (
                  <div className="rounded-lg border p-10 text-center" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
                    <p className="text-xs font-medium" style={{ color: "var(--muted)" }}>
                      No knowledge gaps recorded matching these criteria.
                    </p>
                  </div>
                ) : (
                  <div className="overflow-x-auto rounded-lg border" style={{ borderColor: "var(--border)", background: "var(--surface)" }}>
                    <table className="w-full text-left text-[13px] border-collapse font-sans">
                      <thead
                        className="sticky top-0 z-10 border-b text-[11px] font-semibold uppercase tracking-wider"
                        style={{ background: "var(--surface-2)", borderColor: "var(--border)", color: "var(--muted)" }}
                      >
                        <tr>
                          <th className="px-3.5 py-2.5">Question</th>
                          <th className="px-3 py-2.5 text-center">Freq</th>
                          <th className="px-3 py-2.5">Topic / Prog</th>
                          <th className="px-3 py-2.5">Last Seen</th>
                          <th className="px-3 py-2.5">Status</th>
                          <th className="px-3 py-2.5">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y" style={{ borderColor: "var(--border)" }}>
                        {gaps.map((g) => {
                          const isAnswerableNow = g.retest_status === "Probably answerable now";
                          return (
                            <tr key={g.id || g.normalized_question} className="transition-colors hover:bg-[var(--surface-2)]">
                              <td className="px-3.5 py-2.5 max-w-xs font-medium">
                                <div className="truncate" title={g.question || g.normalized_question}>
                                  {g.question || g.normalized_question}
                                </div>
                                {isAnswerableNow && (
                                  <span
                                    className="mt-1 inline-block rounded border px-1.5 py-0.5 text-[10px] font-medium"
                                    style={{ borderColor: "var(--success)", color: "var(--success)" }}
                                  >
                                    Probably answerable now
                                  </span>
                                )}
                              </td>
                              <td className="px-3 py-2.5 text-center font-mono font-semibold">
                                {g.frequency ?? g.count ?? 1}
                              </td>
                              <td className="px-3 py-2.5 whitespace-nowrap">
                                <div className="flex flex-wrap gap-1">
                                  <span
                                    className="rounded border px-1.5 py-0.5 text-[10px] font-mono uppercase"
                                    style={{ background: "var(--surface-2)", borderColor: "var(--border)", color: "var(--text-2)" }}
                                  >
                                    {g.topic || "general"}
                                  </span>
                                  <span
                                    className="rounded border px-1.5 py-0.5 text-[10px] font-mono uppercase"
                                    style={{ background: "var(--surface-2)", borderColor: "var(--border)", color: "var(--text-2)" }}
                                  >
                                    {g.programme || (g.programmes && g.programmes[0]) || "general"}
                                  </span>
                                </div>
                              </td>
                              <td className="px-3 py-2.5 font-mono text-xs whitespace-nowrap" style={{ color: "var(--muted)" }}>
                                {g.last_seen ? new Date(g.last_seen).toLocaleDateString() : "Recent"}
                              </td>
                              <td className="px-3 py-2.5">
                                <select
                                  value={g.review_status || "open"}
                                  onChange={(e) => handleUpdateGapStatus(g.id, e.target.value, g.note || g.notes)}
                                  className="rounded border px-2 py-1 text-xs focus:outline-none"
                                  style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--text)" }}
                                >
                                  <option value="open">Open</option>
                                  <option value="in_progress">In Progress</option>
                                  <option value="resolved">Resolved</option>
                                  <option value="ignored">Ignored</option>
                                </select>
                              </td>
                              <td className="px-3 py-2.5 whitespace-nowrap">
                                <button
                                  type="button"
                                  onClick={() => {
                                    setAnsweringGap(g);
                                    setAnswerDraft("");
                                    setAnswerSource("");
                                    setAnswerProgramme((g.programme || "GENERAL").toUpperCase());
                                  }}
                                  className="rounded border px-2.5 py-1 text-xs font-medium transition hover:border-[var(--accent)] cursor-pointer"
                                  style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--accent)" }}
                                >
                                  Answer this
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {attentionSubtab === "feedback" && (
              <div className="space-y-4">
                {feedbackItems.length === 0 ? (
                  <div className="rounded-lg border p-10 text-center" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
                    <p className="text-xs font-medium" style={{ color: "var(--muted)" }}>
                      No negative feedback items logged.
                    </p>
                  </div>
                ) : (
                  <div className="overflow-x-auto rounded-lg border" style={{ borderColor: "var(--border)", background: "var(--surface)" }}>
                    <table className="w-full text-left text-[13px] border-collapse font-sans">
                      <thead
                        className="sticky top-0 z-10 border-b text-[11px] font-semibold uppercase tracking-wider"
                        style={{ background: "var(--surface-2)", borderColor: "var(--border)", color: "var(--muted)" }}
                      >
                        <tr>
                          <th className="px-3.5 py-2.5">Question asked</th>
                          <th className="px-3.5 py-2.5">Answer given</th>
                          <th className="px-3 py-2.5">Reason</th>
                          <th className="px-3 py-2.5">Date</th>
                          <th className="px-3 py-2.5">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y" style={{ borderColor: "var(--border)" }}>
                        {feedbackItems.map((fb) => (
                          <tr key={fb.id} className="transition-colors hover:bg-[var(--surface-2)]">
                            <td className="px-3.5 py-2.5 max-w-xs font-medium">
                              <div className="truncate" title={fb.question}>
                                {fb.question || "Unknown question"}
                              </div>
                            </td>
                            <td className="px-3.5 py-2.5 max-w-sm text-xs truncate" style={{ color: "var(--text-2)" }} title={fb.answer}>
                              {fb.answer}
                            </td>
                            <td className="px-3 py-2.5 text-xs">
                              {fb.reason || "Unhelpful"}
                            </td>
                            <td className="px-3 py-2.5 font-mono text-xs whitespace-nowrap" style={{ color: "var(--muted)" }}>
                              {fb.timestamp ? new Date(fb.timestamp).toLocaleDateString() : "Recent"}
                            </td>
                            <td className="px-3 py-2.5">
                              {fb.review_status === "reviewed" ? (
                                <span className="text-xs font-mono" style={{ color: "var(--success)" }}>Reviewed</span>
                              ) : (
                                <button
                                  type="button"
                                  onClick={() => handleMarkFeedbackReviewed(fb.id)}
                                  className="rounded border px-2 py-1 text-xs font-medium transition hover:border-[var(--border-focus)] cursor-pointer"
                                  style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--text)" }}
                                >
                                  Mark reviewed
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* 3. KNOWLEDGE BASE TAB */}
        {activeTab === "knowledge_base" && (
          <div className="space-y-6">
            {/* Automation & Index Card */}
            <div className="rounded-lg border p-4 space-y-3" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
                      Automation
                    </span>
                    <span
                      className="inline-flex items-center rounded border px-2 py-0.5 text-[11px] font-mono font-medium"
                      style={{
                        borderColor: kbStatus?.automation?.status === "in_progress" || kbStatus?.automation?.status === "queued"
                          ? "var(--accent)"
                          : kbStatus?.automation?.result === "failure"
                          ? "var(--danger)"
                          : "var(--success)",
                        color: kbStatus?.automation?.status === "in_progress" || kbStatus?.automation?.status === "queued"
                          ? "var(--accent)"
                          : kbStatus?.automation?.result === "failure"
                          ? "var(--danger)"
                          : "var(--success)",
                      }}
                    >
                      {kbStatus?.automation?.status === "in_progress" || kbStatus?.automation?.status === "queued"
                        ? "Rebuilding"
                        : kbStatus?.automation?.result === "failure"
                        ? "Failed"
                        : "OK"}
                    </span>
                  </div>
                  <p className="mt-1 text-xs" style={{ color: "var(--text-2)" }}>
                    Last sync: {kbStatus?.automation?.last_run ? new Date(kbStatus.automation.last_run).toLocaleString() : "01 Nov 07:00 IST"}
                    {kbStatus?.automation?.trigger && ` (${kbStatus.automation.trigger})`}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={kbSyncing || !kbStatus?.automation?.configured}
                    onClick={() => handleRunSync(false)}
                    className="rounded-md border px-3 py-1.5 text-xs font-medium transition cursor-pointer disabled:opacity-50"
                    style={{
                      background: "var(--surface-2)",
                      borderColor: "var(--border)",
                      color: "var(--text)",
                    }}
                    title={!kbStatus?.automation?.configured ? "Configure GITHUB_REPO and GITHUB_TOKEN in backend environment to enable" : "Trigger website scrape and sync workflow"}
                  >
                    {kbSyncing ? "Triggering..." : "Run sync now"}
                  </button>
                  <button
                    type="button"
                    disabled={kbSyncing || !kbStatus?.automation?.configured}
                    onClick={() => handleRunSync(true)}
                    className="rounded-md border px-3 py-1.5 text-xs font-medium transition cursor-pointer disabled:opacity-50"
                    style={{
                      background: "var(--surface-2)",
                      borderColor: "var(--border)",
                      color: "var(--text-2)",
                    }}
                    title="Force rebuild vector database chunks"
                  >
                    Force rebuild
                  </button>
                </div>
              </div>

              <div className="pt-2 border-t flex flex-wrap items-center justify-between gap-2 text-xs" style={{ borderColor: "var(--border)" }}>
                <p style={{ color: "var(--text-2)" }}>
                  <strong>Index:</strong> {kbStatus?.index?.total_chunks ?? kbData?.total_chunks ?? 301} chunks, {kbStatus?.index?.total_documents ?? kbData?.total_documents ?? 23} documents
                </p>
                {!kbStatus?.automation?.configured && (
                  <p className="text-[11px] font-mono" style={{ color: "var(--muted)" }}>
                    GitHub sync not configured (local storage active)
                  </p>
                )}
              </div>
            </div>

            {/* Upload Document Strip */}
            <div className="rounded-lg border p-4 flex flex-col sm:flex-row items-center justify-between gap-3" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
              <div>
                <h3 className="text-sm font-semibold" style={{ color: "var(--text)" }}>Upload Document</h3>
                <p className="text-xs" style={{ color: "var(--muted)" }}>PDF, DOCX, MD or TXT, up to 10 MB</p>
              </div>
              <label
                className="rounded-md border px-4 py-2 text-xs font-semibold cursor-pointer transition inline-flex items-center"
                style={{
                  background: "var(--accent)",
                  borderColor: "var(--accent)",
                  color: "var(--text-inverse, #fff)",
                }}
              >
                {kbUploading ? "Converting..." : "Upload document"}
                <input
                  type="file"
                  accept=".pdf,.docx,.md,.txt"
                  disabled={kbUploading}
                  onChange={handleUploadFile}
                  className="hidden"
                />
              </label>
            </div>

            {/* Documents Inventory Table */}
            <div className="overflow-x-auto rounded-lg border" style={{ borderColor: "var(--border)", background: "var(--surface)" }}>
              <div className="p-3 border-b flex items-center justify-between" style={{ borderColor: "var(--border)", background: "var(--surface-2)" }}>
                <p className="text-xs font-medium" style={{ color: "var(--text-2)" }}>
                  Knowledge base inventory powering the CHARUSAT chatbot answers
                </p>
                <span className="text-[11px] font-mono" style={{ color: "var(--muted)" }}>
                  {(kbStatus?.documents || []).length} items
                </span>
              </div>
              <table className="w-full text-left text-[13px] border-collapse font-sans">
                <thead
                  className="sticky top-0 z-10 border-b text-[11px] font-semibold uppercase tracking-wider"
                  style={{ background: "var(--surface-2)", borderColor: "var(--border)", color: "var(--muted)" }}
                >
                  <tr>
                    <th className="px-3.5 py-2.5">Document</th>
                    <th className="px-3 py-2.5">Source</th>
                    <th className="px-3 py-2.5">Programme</th>
                    <th className="px-3 py-2.5 text-center">Chunks</th>
                    <th className="px-3 py-2.5">Status</th>
                    <th className="px-3 py-2.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y" style={{ borderColor: "var(--border)" }}>
                  {(kbStatus?.documents || []).map((doc) => {
                    const isLive = doc.status === "Live";
                    const isRebuilding = doc.status === "Rebuilding";
                    const isFailed = doc.status === "Failed";
                    return (
                      <tr key={doc.rel_path} className="transition-colors hover:bg-[var(--surface-2)]">
                        <td className="px-3.5 py-2.5 font-medium max-w-xs truncate" title={doc.title}>
                          <div>{doc.title}</div>
                          <div className="font-mono text-[10px]" style={{ color: "var(--muted)" }}>{doc.rel_path}</div>
                        </td>
                        <td className="px-3 py-2.5">
                          <span
                            className="rounded border px-1.5 py-0.5 text-[10px] font-mono uppercase"
                            style={{ background: "var(--surface-2)", borderColor: "var(--border)", color: "var(--text-2)" }}
                          >
                            {doc.source_type}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 uppercase font-mono text-xs">{doc.programme}</td>
                        <td className="px-3 py-2.5 text-center font-mono font-semibold">{doc.chunks}</td>
                        <td className="px-3 py-2.5 whitespace-nowrap">
                          <span
                            className="inline-block rounded border px-2 py-0.5 text-[10px] font-mono font-medium"
                            style={{
                              borderColor: isLive ? "var(--success)" : isRebuilding ? "var(--accent)" : isFailed ? "var(--danger)" : "var(--border)",
                              color: isLive ? "var(--success)" : isRebuilding ? "var(--accent)" : isFailed ? "var(--danger)" : "var(--muted)",
                            }}
                          >
                            {doc.status}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 text-right space-x-2 whitespace-nowrap">
                          <button
                            type="button"
                            onClick={() => {
                              setViewingDoc(doc);
                              setViewingDocContent(doc.markdown || `# ${doc.title}\n\nSource: ${doc.rel_path}`);
                            }}
                            className="rounded border px-2 py-1 text-xs font-medium transition cursor-pointer hover:border-[var(--border-focus)]"
                            style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--text-2)" }}
                          >
                            View
                          </button>
                          {doc.can_delete && (
                            <button
                              type="button"
                              onClick={() => {
                                setDeletingDoc(doc);
                                setDeleteDocConfirmInput("");
                              }}
                              className="rounded border px-2 py-1 text-xs font-medium transition cursor-pointer hover:border-[var(--danger)]"
                              style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--danger)" }}
                            >
                              Remove
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Test a Question Panel */}
            <div className="rounded-lg border p-4 space-y-3" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
              <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
                Test a question against index
              </h3>
              <form onSubmit={handleTestQuestion} className="flex gap-2">
                <input
                  type="text"
                  placeholder="Type a test question (e.g. What is the fee refund policy?)..."
                  value={testQuestionInput}
                  onChange={(e) => setTestQuestionInput(e.target.value)}
                  className="flex-1 rounded-md border px-3 py-2 text-xs focus:outline-none font-sans"
                  style={{
                    background: "var(--surface)",
                    borderColor: "var(--border)",
                    color: "var(--text)",
                  }}
                />
                <button
                  type="submit"
                  disabled={testingQuestion || !testQuestionInput.trim()}
                  className="rounded-md border px-4 py-2 text-xs font-semibold transition cursor-pointer disabled:opacity-50"
                  style={{
                    background: "var(--accent)",
                    borderColor: "var(--accent)",
                    color: "var(--text-inverse, #fff)",
                  }}
                >
                  {testingQuestion ? "Testing..." : "Ask"}
                </button>
              </form>

              {testQuestionResult && (
                <div className="mt-3 pt-3 border-t space-y-2 text-xs" style={{ borderColor: "var(--border)" }}>
                  <div className="flex items-center justify-between">
                    <span className="font-medium" style={{ color: "var(--text)" }}>
                      Relevance score: <strong className="font-mono">{testQuestionResult.relevance_score}</strong>
                    </span>
                    <span
                      className="rounded border px-2 py-0.5 text-[10px] font-mono font-medium"
                      style={{
                        borderColor: testQuestionResult.answerable ? "var(--success)" : "var(--danger)",
                        color: testQuestionResult.answerable ? "var(--success)" : "var(--danger)",
                      }}
                    >
                      {testQuestionResult.answerable ? "Probably answerable now" : "Low relevance (unanswered)"}
                    </span>
                  </div>
                  <div className="space-y-2 mt-2">
                    {(testQuestionResult.chunks || []).map((ch, idx) => (
                      <div key={idx} className="rounded border p-2 text-xs" style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}>
                        <div className="flex items-center justify-between font-mono text-[10px]" style={{ color: "var(--muted)" }}>
                          <span>{ch.source} ({ch.programme})</span>
                          <span>score: {ch.score}</span>
                        </div>
                        <p className="mt-1 line-clamp-2" style={{ color: "var(--text-2)" }}>{ch.content_snippet}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 4. USERS TAB */}
        {activeTab === "users" && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2 flex-1">
                <input
                  type="search"
                  placeholder="Search by email..."
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  className="rounded-md border px-3 py-1.5 text-xs focus:outline-none w-48 sm:w-60"
                  style={{
                    background: "var(--surface)",
                    borderColor: "var(--border)",
                    color: "var(--text)",
                  }}
                />
                <select
                  value={userRoleFilter}
                  onChange={(e) => setUserRoleFilter(e.target.value)}
                  className="rounded-md border px-2.5 py-1.5 text-xs focus:outline-none"
                  style={{
                    background: "var(--surface)",
                    borderColor: "var(--border)",
                    color: "var(--text)",
                  }}
                >
                  <option value="">All Roles</option>
                  <option value="admin">Admin</option>
                  <option value="user">Student / User</option>
                </select>
              </div>
            </div>

            <div className="overflow-x-auto rounded-lg border" style={{ borderColor: "var(--border)", background: "var(--surface)" }}>
              <table className="w-full text-left text-[13px] border-collapse font-sans">
                <thead
                  className="sticky top-0 z-10 border-b text-[11px] font-semibold uppercase tracking-wider"
                  style={{ background: "var(--surface-2)", borderColor: "var(--border)", color: "var(--muted)" }}
                >
                  <tr>
                    <th className="px-3.5 py-2.5">Email</th>
                    <th className="px-3 py-2.5">Role</th>
                    <th className="px-3 py-2.5">Registered</th>
                    <th className="px-3 py-2.5">Last Active</th>
                    <th className="px-3 py-2.5">Status</th>
                    <th className="px-3 py-2.5">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y" style={{ borderColor: "var(--border)" }}>
                  {usersList.map((u) => {
                    const isSelf = u.id === user?.id;
                    const isDisabled = u.is_disabled || u.disabled;
                    return (
                      <tr key={u.id} className="transition-colors hover:bg-[var(--surface-2)]">
                        <td className="px-3.5 py-2.5 font-mono text-xs">
                          {u.email}
                          {isSelf && (
                            <span className="ml-2 rounded px-1.5 py-0.5 text-[10px] font-semibold" style={{ background: "var(--accent-surface)", color: "var(--accent)" }}>
                              You
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2.5">
                          <span
                            className="rounded border px-2 py-0.5 text-[11px] font-mono uppercase"
                            style={{
                              background: u.role === "admin" ? "var(--accent-surface)" : "var(--surface-2)",
                              borderColor: u.role === "admin" ? "var(--border-focus)" : "var(--border)",
                              color: u.role === "admin" ? "var(--accent)" : "var(--text-2)",
                            }}
                          >
                            {u.role}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 font-mono text-xs whitespace-nowrap" style={{ color: "var(--muted)" }}>
                          {u.created_at ? new Date(u.created_at).toLocaleDateString() : "Historical"}
                        </td>
                        <td className="px-3 py-2.5 font-mono text-xs whitespace-nowrap" style={{ color: "var(--text-2)" }}>
                          {u.last_active ? new Date(u.last_active).toLocaleString() : "Never"}
                        </td>
                        <td className="px-3 py-2.5">
                          <span
                            className="inline-flex items-center gap-1.5 text-xs font-medium"
                            style={{ color: isDisabled ? "var(--danger)" : "var(--success)" }}
                          >
                            <span
                              className="h-2 w-2 rounded-full" /* allow-round: status dot */
                              style={{ background: isDisabled ? "var(--danger)" : "var(--success)" }}
                            />
                            {isDisabled ? "Disabled" : "Active"}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              disabled={isSelf}
                              onClick={() => handleToggleDisable(u)}
                              className="rounded border px-2 py-1 text-xs font-medium transition disabled:opacity-30 cursor-pointer"
                              style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--text)" }}
                            >
                              {isDisabled ? "Enable" : "Disable"}
                            </button>
                            <button
                              type="button"
                              disabled={isSelf}
                              onClick={() => handleToggleUserRole(u)}
                              className="rounded border px-2 py-1 text-xs font-medium transition disabled:opacity-30 cursor-pointer"
                              style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--text)" }}
                            >
                              {u.role === "admin" ? "Demote" : "Make Admin"}
                            </button>
                            <button
                              type="button"
                              disabled={isSelf}
                              onClick={() => {
                                setUserToDelete(u);
                                setDeleteConfirmInput("");
                              }}
                              className="rounded border px-2 py-1 text-xs font-medium transition hover:border-[var(--danger)] disabled:opacity-30 cursor-pointer"
                              style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--danger)" }}
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 5. SYSTEM TAB */}
        {activeTab === "system" && systemInfo && (
          <div className="space-y-6">
            <div className="rounded-lg border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
              <h3 className="text-xs font-semibold uppercase tracking-wider mb-4" style={{ color: "var(--muted)" }}>
                Core Service Infrastructure
              </h3>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-md border p-3" style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}>
                  <div className="flex items-center gap-2">
                    <span
                      className="h-2 w-2 rounded-full" /* allow-round: status dot */
                      style={{ background: (systemInfo.database?.connected || systemInfo.database_connected) ? "var(--success)" : "var(--danger)" }}
                    />
                    <span className="text-xs font-semibold">MongoDB</span>
                  </div>
                  <p className="mt-2 text-xs font-mono" style={{ color: "var(--muted)" }}>
                    Database: {systemInfo.database?.name || systemInfo.database_name || "charusat_assistant"}
                  </p>
                </div>

                <div className="rounded-md border p-3" style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}>
                  <div className="flex items-center gap-2">
                    <span
                      className="h-2 w-2 rounded-full" /* allow-round: status dot */
                      style={{ background: (systemInfo.vector_store?.ready || systemInfo.vector_store_documents > 0) ? "var(--success)" : "var(--danger)" }}
                    />
                    <span className="text-xs font-semibold">Chroma Vector Store</span>
                  </div>
                  <p className="mt-2 text-xs font-mono" style={{ color: "var(--muted)" }}>
                    {systemInfo.vector_store?.chunks ?? systemInfo.vector_store_documents ?? 301} indexed chunks
                  </p>
                </div>

                <div className="rounded-md border p-3" style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}>
                  <div className="flex items-center gap-2">
                    <span
                      className="h-2 w-2 rounded-full" /* allow-round: status dot */
                      style={{ background: "var(--success)" }}
                    />
                    <span className="text-xs font-semibold">Primary LLM</span>
                  </div>
                  <p className="mt-2 text-xs font-mono" style={{ color: "var(--muted)" }}>
                    Gemini 2.5 Flash (Configured)
                  </p>
                </div>

                <div className="rounded-md border p-3" style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}>
                  <div className="flex items-center gap-2">
                    <span
                      className="h-2 w-2 rounded-full" /* allow-round: status dot */
                      style={{ background: "var(--success)" }}
                    />
                    <span className="text-xs font-semibold">Failover LLM</span>
                  </div>
                  <p className="mt-2 text-xs font-mono" style={{ color: "var(--muted)" }}>
                    Groq gpt-oss-120b (Configured)
                  </p>
                </div>
              </div>
            </div>

            {/* Cache Stats and Clear Cache */}
            <div className="rounded-lg border p-5" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
              <div className="flex flex-wrap items-center justify-between gap-4 mb-3">
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
                    In-Memory Question Cache
                  </h3>
                  <p className="text-xs mt-1" style={{ color: "var(--text-2)" }}>
                    Caches grounded answers for recurring learner questions with 1-hour TTL.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setConfirmClearCache(true)}
                  className="rounded-md border px-3 py-1.5 text-xs font-medium transition hover:border-[var(--danger)] cursor-pointer"
                  style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--danger)" }}
                >
                  Clear question cache
                </button>
              </div>

              <div className="grid grid-cols-3 gap-3 font-mono text-center">
                <div className="rounded-md border p-2" style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}>
                  <p className="text-[10px] uppercase" style={{ color: "var(--muted)" }}>Hits</p>
                  <p className="text-base font-bold">{systemInfo.cache?.hits ?? 0}</p>
                </div>
                <div className="rounded-md border p-2" style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}>
                  <p className="text-[10px] uppercase" style={{ color: "var(--muted)" }}>Misses</p>
                  <p className="text-base font-bold">{systemInfo.cache?.misses ?? 0}</p>
                </div>
                <div className="rounded-md border p-2" style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}>
                  <p className="text-[10px] uppercase" style={{ color: "var(--muted)" }}>Hit Rate</p>
                  <p className="text-base font-bold">
                    {systemInfo.cache?.hit_rate ? `${Math.round(systemInfo.cache.hit_rate * 100)}%` : "0%"}
                  </p>
                </div>
              </div>
            </div>

            {/* Recent Administrative Activity (Audit Log) */}
            <div className="rounded-lg border" style={{ borderColor: "var(--border)", background: "var(--surface)" }}>
              <div className="p-4 border-b flex items-center justify-between" style={{ borderColor: "var(--border)" }}>
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
                    Recent Admin Activity (Audit Log)
                  </h3>
                  <p className="text-[11px]" style={{ color: "var(--text-2)" }}>
                    Append-only audit events for staff authentication, user role changes, and index updates.
                  </p>
                </div>
                <span className="text-xs font-mono" style={{ color: "var(--muted)" }}>
                  Last 50 entries
                </span>
              </div>

              <div className="overflow-x-auto max-h-96">
                <table className="w-full text-left text-[12px] border-collapse font-sans">
                  <thead className="sticky top-0 z-10 border-b text-[11px] font-semibold uppercase tracking-wider" style={{ background: "var(--surface-2)", borderColor: "var(--border)", color: "var(--muted)" }}>
                    <tr>
                      <th className="px-3.5 py-2">Timestamp</th>
                      <th className="px-3 py-2">Admin User</th>
                      <th className="px-3 py-2">Action</th>
                      <th className="px-3 py-2">Target</th>
                      <th className="px-3 py-2">Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y" style={{ borderColor: "var(--border)" }}>
                    {(systemInfo.recent_logs || []).map((log) => (
                      <tr key={log.id} className="transition-colors hover:bg-[var(--surface-2)]">
                        <td className="px-3.5 py-2 font-mono text-xs whitespace-nowrap" style={{ color: "var(--muted)" }}>
                          {log.timestamp ? new Date(log.timestamp).toLocaleString() : "Recent"}
                        </td>
                        <td className="px-3 py-2 font-mono text-xs">{log.admin_email}</td>
                        <td className="px-3 py-2 font-semibold">{log.action}</td>
                        <td className="px-3 py-2 font-mono text-xs">{log.target_type}</td>
                        <td className="px-3 py-2 text-xs font-mono truncate max-w-xs" style={{ color: "var(--text-2)" }}>
                          {JSON.stringify(log.details || {})}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Answer This FAQ Modal (Part 4) */}
      <Dialog
        open={Boolean(answeringGap)}
        onClose={() => {
          setAnsweringGap(null);
          setAnswerDraft("");
          setAnswerSource("");
        }}
        title="Answer Unanswered Question"
        confirmLabel={savingAnswer ? "Publishing FAQ..." : "Publish FAQ"}
        onConfirm={handleSubmitFaq}
        disabled={savingAnswer || answerDraft.trim().length < 20 || !answerSource.trim()}
      >
        <div className="space-y-3">
          <div>
            <label className="text-xs font-semibold block mb-1" style={{ color: "var(--muted)" }}>
              Question
            </label>
            <p className="rounded border p-2 text-xs font-medium" style={{ background: "var(--surface-2)", borderColor: "var(--border)", color: "var(--text)" }}>
              {answeringGap?.question || answeringGap?.normalized_question}
            </p>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-semibold" style={{ color: "var(--muted)" }}>
                Official Answer (min 20 characters)
              </label>
              <span className="text-[11px] font-mono" style={{ color: answerDraft.trim().length >= 20 ? "var(--success)" : "var(--muted)" }}>
                {answerDraft.trim().length} chars
              </span>
            </div>
            <textarea
              rows={5}
              value={answerDraft}
              onChange={(e) => setAnswerDraft(e.target.value)}
              placeholder="Write the clear, accurate answer based on official university information..."
              className="w-full rounded-md border p-2 text-xs focus:outline-none"
              style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--text)" }}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold block mb-1" style={{ color: "var(--muted)" }}>
                Programme
              </label>
              <select
                value={answerProgramme}
                onChange={(e) => setAnswerProgramme(e.target.value)}
                className="w-full rounded-md border p-2 text-xs focus:outline-none"
                style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--text)" }}
              >
                <option value="GENERAL">GENERAL</option>
                <option value="BBA">BBA</option>
                <option value="BCA">BCA</option>
                <option value="MBA">MBA</option>
                <option value="MCA">MCA</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold block mb-1" style={{ color: "var(--muted)" }}>
                Official Source (URL or document)
              </label>
              <input
                type="text"
                value={answerSource}
                onChange={(e) => setAnswerSource(e.target.value)}
                placeholder="https://charusat.online/... or Syllabus"
                className="w-full rounded-md border p-2 text-xs focus:outline-none"
                style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--text)" }}
              />
            </div>
          </div>
        </div>
      </Dialog>

      {/* Document Review Modal (Part 3) */}
      <Dialog
        open={Boolean(activeDraft)}
        onClose={() => setActiveDraft(null)}
        title={`Review Document Draft - ${activeDraft?.filename || ""}`}
        confirmLabel="Publish to Knowledge Base"
        cancelLabel="Close"
        disabled={!activeDraft?.can_publish}
        onConfirm={() => setShowPublishConfirm(true)}
      >
        {activeDraft && (
          <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
            {activeDraft.warnings?.length > 0 && (
              <div className="rounded-md border p-3 text-xs" style={{ borderColor: "var(--danger)", background: "var(--surface-2)", color: "var(--danger)" }}>
                {activeDraft.warnings.map((w, idx) => (
                  <p key={idx}>Warning: {w}</p>
                ))}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="sm:col-span-2">
                <label className="text-xs font-semibold block mb-1" style={{ color: "var(--muted)" }}>Document Title</label>
                <input
                  type="text"
                  value={activeDraft.title}
                  onChange={(e) => setActiveDraft({ ...activeDraft, title: e.target.value })}
                  className="w-full rounded-md border p-2 text-xs focus:outline-none"
                  style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--text)" }}
                />
              </div>
              <div>
                <label className="text-xs font-semibold block mb-1" style={{ color: "var(--muted)" }}>Programme</label>
                <select
                  value={activeDraft.programme}
                  onChange={(e) => setActiveDraft({ ...activeDraft, programme: e.target.value })}
                  className="w-full rounded-md border p-2 text-xs focus:outline-none"
                  style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--text)" }}
                >
                  <option value="GENERAL">GENERAL</option>
                  <option value="BBA">BBA</option>
                  <option value="BCA">BCA</option>
                  <option value="MBA">MBA</option>
                  <option value="MCA">MCA</option>
                </select>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs" style={{ color: "var(--muted)" }}>
              <span>Pages: <strong>{activeDraft.page_count}</strong> | Estimated Chunks: <strong>{activeDraft.chunk_estimate}</strong></span>
              <button
                type="button"
                onClick={() => handleDownloadMarkdown(activeDraft.filename, activeDraft.markdown)}
                className="underline hover:text-[var(--accent)] cursor-pointer"
              >
                Download Markdown (.md)
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold block mb-1" style={{ color: "var(--muted)" }}>Editable Markdown</label>
                <textarea
                  rows={14}
                  value={activeDraft.markdown}
                  onChange={(e) => setActiveDraft({ ...activeDraft, markdown: e.target.value })}
                  className="w-full rounded-md border p-2 text-xs font-mono focus:outline-none"
                  style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--text)" }}
                />
              </div>
              <div>
                <label className="text-xs font-semibold block mb-1" style={{ color: "var(--muted)" }}>Rendered Preview</label>
                <div
                  className="w-full rounded-md border p-3 text-xs overflow-y-auto max-h-[280px]"
                  style={{ background: "var(--surface-2)", borderColor: "var(--border)", color: "var(--text)" }}
                >
                  <RichText content={activeDraft.markdown} />
                </div>
              </div>
            </div>
          </div>
        )}
      </Dialog>

      {/* Publish Confirm Dialog */}
      <Dialog
        open={showPublishConfirm}
        onClose={() => setShowPublishConfirm(false)}
        title="Publish Document to Knowledge Base?"
        description="This document will be committed to the repository and a vector database rebuild will be dispatched on GitHub Actions. Continue?"
        confirmLabel={publishingDraft ? "Publishing..." : "Confirm Publish"}
        disabled={publishingDraft}
        onConfirm={handlePublishDraft}
      />

      {/* View Document Modal */}
      <Dialog
        open={Boolean(viewingDoc)}
        onClose={() => setViewingDoc(null)}
        title={viewingDoc?.title || "Document Preview"}
        cancelLabel="Close"
      >
        <div className="max-h-[60vh] overflow-y-auto p-2 rounded border" style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}>
          <RichText content={viewingDocContent} />
        </div>
      </Dialog>

      {/* Delete Document Confirmation Modal */}
      <Dialog
        open={Boolean(deletingDoc)}
        onClose={() => {
          setDeletingDoc(null);
          setDeleteDocConfirmInput("");
        }}
        title="Delete Uploaded Document"
        confirmLabel="Delete Document"
        danger
        disabled={deleteDocConfirmInput.trim().toUpperCase() !== "DELETE"}
        onConfirm={handleDeleteDoc}
      >
        <div className="space-y-3">
          <p className="text-xs leading-relaxed" style={{ color: "var(--text-2)" }}>
            Are you sure you want to permanently delete <strong className="font-mono text-[var(--text)]">{deletingDoc?.filename}</strong>? This will remove the document and dispatch an index update.
          </p>
          <p className="text-xs font-semibold" style={{ color: "var(--danger)" }}>
            Type DELETE below to confirm:
          </p>
          <input
            type="text"
            value={deleteDocConfirmInput}
            onChange={(e) => setDeleteDocConfirmInput(e.target.value)}
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

      {/* Delete User Confirmation Modal */}
      <Dialog
        open={Boolean(userToDelete)}
        onClose={() => {
          setUserToDelete(null);
          setDeleteConfirmInput("");
        }}
        title="Delete User Account"
        confirmLabel="Delete User"
        danger
        onConfirm={handleDeleteUser}
      >
        <div className="space-y-3">
          <p className="text-xs leading-relaxed" style={{ color: "var(--text-2)" }}>
            This action will permanently delete user <strong className="font-mono text-[var(--text)]">{userToDelete?.email}</strong> and their saved conversations. This cannot be undone.
          </p>
          <p className="text-xs font-semibold" style={{ color: "var(--danger)" }}>
            Type DELETE below to confirm:
          </p>
          <input
            type="text"
            value={deleteConfirmInput}
            onChange={(e) => setDeleteConfirmInput(e.target.value)}
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

      {/* Confirm Clear Cache Modal */}
      <Dialog
        open={confirmClearCache}
        onClose={() => setConfirmClearCache(false)}
        title="Clear Question Cache"
        confirmLabel="Clear Cache"
        danger
        onConfirm={handleExecuteClearCache}
      >
        <p className="text-xs leading-relaxed" style={{ color: "var(--text-2)" }}>
          Are you sure you want to clear the question cache? Future queries will bypass the cache and run live vector search until the cache repopulates.
        </p>
      </Dialog>

      {/* Sign out confirmation dialog */}
      <Dialog
        open={showSignoutDialog}
        onClose={() => setShowSignoutDialog(false)}
        title="Sign out?"
        description="You will need to sign in again to use the admin console."
        confirmLabel="Sign out"
        cancelLabel="Cancel"
        danger
        onConfirm={async () => {
          setShowSignoutDialog(false);
          await handleLogout();
        }}
      />
    </div>
  );
}
