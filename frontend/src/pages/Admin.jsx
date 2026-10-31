import ThemedLogo from "../components/ui/ThemedLogo.jsx";
/**
 * Admin Console - 8-tab operations portal for university staff.
 *
 * Dense tables (13px text), sticky headers, tabular numerals,
 * browser timezone labeled with absolute ISO time on hover.
 * Zero emojis, zero gradients, zero pill shapes, full theme support.
 */
import { useEffect, useState, useCallback, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext.jsx";
import { API_BASE, apiFetch, getAuthToken } from "../services/api.js";
import Dialog from "../components/ui/Dialog.jsx";
import Toast from "../components/ui/Toast.jsx";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "gaps", label: "Knowledge Gaps" },
  { id: "conversations", label: "Conversations" },
  { id: "feedback", label: "Feedback" },
  { id: "users", label: "Users" },
  { id: "knowledge_base", label: "Knowledge Base" },
  { id: "audit_log", label: "Audit Log" },
  { id: "system", label: "System" },
];

function StatCard({ label, value, subtitle, accent = false }) {
  return (
    <div
      className="rounded-lg border p-4 transition-colors"
      style={{
        background: accent ? "var(--accent-surface)" : "var(--surface)",
        borderColor: accent ? "var(--border-focus)" : "var(--border)",
      }}
    >
      <p className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
        {label}
      </p>
      <p
        className="mt-2 text-2xl font-bold font-mono tracking-tight"
        style={{ color: accent ? "var(--accent)" : "var(--text)" }}
      >
        {value ?? "No data yet"}
      </p>
      {subtitle && (
        <p className="mt-1 text-xs" style={{ color: "var(--muted)" }}>
          {subtitle}
        </p>
      )}
    </div>
  );
}

// Hand-written SVG Bar Chart for Daily Volume
function DailyVolumeChart({ data = [] }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-44 items-center justify-center text-xs" style={{ color: "var(--muted)" }}>
        No query activity in this period.
      </div>
    );
  }

  const maxVal = Math.max(...data.map((d) => d.count || 0), 1);
  const chartHeight = 130;
  const chartWidth = 560;
  const barWidth = Math.max(Math.floor((chartWidth - data.length * 6) / data.length), 6);

  return (
    <div className="w-full overflow-x-auto">
      <svg
        viewBox={`0 0 ${chartWidth} 170`}
        className="w-full text-xs"
        style={{ minWidth: "480px", maxHeight: "170px" }}
        role="img"
        aria-label="Daily query volume bar chart"
      >
        {/* Baseline grid */}
        <line
          x1="0"
          y1={chartHeight}
          x2={chartWidth}
          y2={chartHeight}
          stroke="var(--border)"
          strokeWidth="1"
        />
        {/* Halfway grid */}
        <line
          x1="0"
          y1={chartHeight / 2}
          x2={chartWidth}
          y2={chartHeight / 2}
          stroke="var(--border)"
          strokeWidth="1"
          strokeDasharray="4 4"
        />
        <text x="4" y={chartHeight / 2 - 4} fill="var(--muted)" fontSize="9" fontFamily="monospace">
          {Math.round(maxVal / 2)}
        </text>
        <text x="4" y="12" fill="var(--muted)" fontSize="9" fontFamily="monospace">
          {maxVal}
        </text>

        {data.map((d, i) => {
          const count = d.count || 0;
          const h = (count / maxVal) * chartHeight;
          const x = i * (chartWidth / data.length) + 4;
          const y = chartHeight - h;
          const dateStr = d.date ? d.date.slice(5) : "";

          return (
            <g key={d.date || i}>
              <title>{`${d.date}: ${count} queries`}</title>
              <rect
                x={x}
                y={y}
                width={barWidth}
                height={Math.max(h, 2)}
                fill="var(--accent)"
                rx="2"
              />
              {/* Date label on every 2nd or 3rd bar if dense */}
              {(data.length <= 14 || i % 3 === 0) && (
                <text
                  x={x + barWidth / 2}
                  y={chartHeight + 16}
                  textAnchor="middle"
                  fill="var(--muted)"
                  fontSize="9"
                  fontFamily="monospace"
                >
                  {dateStr}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// Hand-written SVG Line Chart for Latency p50 and p95
function LatencyLineChart({ data = [] }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-44 items-center justify-center text-xs" style={{ color: "var(--muted)" }}>
        No latency data in this period.
      </div>
    );
  }

  const chartHeight = 130;
  const chartWidth = 560;
  const maxVal = Math.max(
    ...data.flatMap((d) => [d.p95 || 0, d.p50 || 0]),
    1.0
  );

  const getPoints = (key) =>
    data
      .map((d, i) => {
        const val = d[key] || 0;
        const x = (i / Math.max(data.length - 1, 1)) * (chartWidth - 20) + 10;
        const y = chartHeight - (val / maxVal) * chartHeight;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");

  const p50Points = getPoints("p50");
  const p95Points = getPoints("p95");

  return (
    <div className="w-full overflow-x-auto">
      <svg
        viewBox={`0 0 ${chartWidth} 170`}
        className="w-full text-xs"
        style={{ minWidth: "480px", maxHeight: "170px" }}
        role="img"
        aria-label="Response latency p50 and p95 line chart"
      >
        <line
          x1="0"
          y1={chartHeight}
          x2={chartWidth}
          y2={chartHeight}
          stroke="var(--border)"
          strokeWidth="1"
        />
        <line
          x1="0"
          y1={chartHeight / 2}
          x2={chartWidth}
          y2={chartHeight / 2}
          stroke="var(--border)"
          strokeWidth="1"
          strokeDasharray="4 4"
        />
        <text x="4" y={chartHeight / 2 - 4} fill="var(--muted)" fontSize="9" fontFamily="monospace">
          {(maxVal / 2).toFixed(1)}s
        </text>
        <text x="4" y="12" fill="var(--muted)" fontSize="9" fontFamily="monospace">
          {maxVal.toFixed(1)}s
        </text>

        {/* p95 line */}
        <polyline
          fill="none"
          stroke="var(--warning)"
          strokeWidth="2"
          strokeDasharray="4 3"
          points={p95Points}
        />
        {/* p50 line */}
        <polyline
          fill="none"
          stroke="var(--accent)"
          strokeWidth="2"
          points={p50Points}
        />

        {/* Data points */}
        {data.map((d, i) => {
          const x = (i / Math.max(data.length - 1, 1)) * (chartWidth - 20) + 10;
          const y50 = chartHeight - ((d.p50 || 0) / maxVal) * chartHeight;
          const y95 = chartHeight - ((d.p95 || 0) / maxVal) * chartHeight;
          const dateStr = d.date ? d.date.slice(5) : "";

          return (
            <g key={d.date || i}>
              <title>{`${d.date} - p50: ${d.p50}s, p95: ${d.p95}s`}</title>
              <circle
                cx={x}
                cy={y50}
                r="3"
                fill="var(--accent)"
                /* allow-round: chart point */
              />
              <circle
                cx={x}
                cy={y95}
                r="3"
                fill="var(--warning)"
                /* allow-round: chart point */
              />
              {(data.length <= 14 || i % 3 === 0) && (
                <text
                  x={x}
                  y={chartHeight + 16}
                  textAnchor="middle"
                  fill="var(--muted)"
                  fontSize="9"
                  fontFamily="monospace"
                >
                  {dateStr}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      <div className="mt-2 flex items-center justify-end gap-5 text-[11px]" style={{ color: "var(--muted)" }}>
        <div className="flex items-center gap-1.5">
          <span className="h-0.5 w-4" style={{ background: "var(--accent)" }} />
          <span>p50 Median</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-0.5 w-4 border-b border-dashed" style={{ borderColor: "var(--warning)" }} />
          <span>p95 Tail Latency</span>
        </div>
      </div>
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

  const showToast = (msg, type = "info") => {
    setToastMessage(msg);
    setToastType(type);
  };

  // Tab 1: Overview
  const [overviewDays, setOverviewDays] = useState(30);
  const [overviewData, setOverviewData] = useState(null);

  // Tab 2: Knowledge Gaps
  const [gaps, setGaps] = useState([]);
  const [gapSearch, setGapSearch] = useState("");
  const [gapProgrammeFilter, setGapProgrammeFilter] = useState("");
  const [gapTopicFilter, setGapTopicFilter] = useState("");
  const [gapStatusFilter, setGapStatusFilter] = useState("");
  const [editingGapNote, setEditingGapNote] = useState(null); // { question, notes }

  // Tab 3: Conversations
  const [conversations, setConversations] = useState([]);
  const [convSearch, setConvSearch] = useState("");
  const [revealedEmails, setRevealedEmails] = useState({}); // conv_id -> full_email
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [transcriptData, setTranscriptData] = useState(null);
  const [loadingTranscript, setLoadingTranscript] = useState(false);

  // Tab 4: Feedback
  const [feedbackItems, setFeedbackItems] = useState([]);
  const [feedbackFilter, setFeedbackFilter] = useState("all"); // 'all' | 'unreviewed' | 'negative'

  // Tab 5: Users
  const [usersList, setUsersList] = useState([]);
  const [userSearch, setUserSearch] = useState("");
  const [userRoleFilter, setUserRoleFilter] = useState("");
  const [userToDelete, setUserToDelete] = useState(null);
  const [deleteConfirmInput, setDeleteConfirmInput] = useState("");
  const [roleChangeTarget, setRoleChangeTarget] = useState(null); // { user, newRole }

  // Tab 6: Knowledge Base
  const [kbData, setKbData] = useState(null);

  // Tab 7: Audit Log
  const [auditLogs, setAuditLogs] = useState([]);

  // Tab 8: System
  const [systemInfo, setSystemInfo] = useState(null);
  const [confirmClearCache, setConfirmClearCache] = useState(false);

  // Load data for active tab
  const loadTabData = useCallback(
    async (tabId) => {
      setLoading(true);
      setError("");
      try {
        if (tabId === "overview") {
          const data = await apiFetch(`/api/admin/overview?days=${overviewDays}`);
          setOverviewData(data);
        } else if (tabId === "gaps") {
          const params = new URLSearchParams();
          if (gapProgrammeFilter) params.append("programme", gapProgrammeFilter);
          if (gapTopicFilter) params.append("topic", gapTopicFilter);
          if (gapStatusFilter) params.append("review_status", gapStatusFilter);
          if (gapSearch) params.append("search", gapSearch);
          const data = await apiFetch(`/api/admin/knowledge-gaps?${params.toString()}`);
          setGaps(data.gaps || []);
        } else if (tabId === "conversations") {
          const params = new URLSearchParams();
          if (convSearch) params.append("search", convSearch);
          const data = await apiFetch(`/api/admin/conversations?${params.toString()}`);
          setConversations(data.conversations || []);
        } else if (tabId === "feedback") {
          const data = await apiFetch("/api/admin/feedback");
          setFeedbackItems(data.feedback || []);
        } else if (tabId === "users") {
          const params = new URLSearchParams();
          if (userSearch) params.append("search", userSearch);
          if (userRoleFilter) params.append("role", userRoleFilter);
          const data = await apiFetch(`/api/admin/users?${params.toString()}`);
          setUsersList(data.users || []);
        } else if (tabId === "knowledge_base") {
          const data = await apiFetch("/api/admin/knowledge-base");
          setKbData(data);
        } else if (tabId === "audit_log") {
          const data = await apiFetch("/api/admin/audit-log");
          setAuditLogs(data.logs || []);
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
    [overviewDays, gapProgrammeFilter, gapTopicFilter, gapStatusFilter, gapSearch, convSearch, userSearch, userRoleFilter]
  );

  useEffect(() => {
    loadTabData(activeTab);
  }, [activeTab, loadTabData]);

  // Tab 2 Handlers
  const handleUpdateGapStatus = async (normalized_question, newStatus, currentNotes) => {
    try {
      await apiFetch("/api/admin/knowledge-gaps/review-status", {
        method: "PATCH",
        body: JSON.stringify({
          normalized_question,
          review_status: newStatus,
          notes: currentNotes,
        }),
      });
      showToast("Knowledge gap status updated", "success");
      loadTabData("gaps");
    } catch (err) {
      showToast(err.message || "Failed to update gap status", "danger");
    }
  };

  const handleSaveGapNote = async () => {
    if (!editingGapNote) return;
    try {
      await apiFetch("/api/admin/knowledge-gaps/review-status", {
        method: "PATCH",
        body: JSON.stringify({
          normalized_question: editingGapNote.question,
          review_status: editingGapNote.status || "open",
          notes: editingGapNote.notes,
        }),
      });
      showToast("Note saved successfully", "success");
      setEditingGapNote(null);
      loadTabData("gaps");
    } catch (err) {
      showToast(err.message || "Failed to save note", "danger");
    }
  };

  const handleExportCsv = async () => {
    try {
      const token = getAuthToken();
      const res = await fetch(`${API_BASE}/api/admin/knowledge-gaps/csv`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error("Failed to download CSV");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `charusat_knowledge_gaps_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      showToast("Knowledge gaps CSV exported", "success");
    } catch (err) {
      showToast(err.message || "CSV export failed", "danger");
    }
  };

  // Tab 3 Handlers
  const handleRevealEmail = async (convId) => {
    try {
      const data = await apiFetch(`/api/admin/conversations/${convId}/reveal`, { method: "POST" });
      if (data?.user_email) {
        setRevealedEmails((prev) => ({ ...prev, [convId]: data.user_email }));
        showToast("Email revealed and logged to audit trail", "info");
      }
    } catch (err) {
      showToast(err.message || "Failed to reveal email", "danger");
    }
  };

  const handleOpenTranscript = async (conv) => {
    setSelectedConversation(conv);
    setLoadingTranscript(true);
    setTranscriptData(null);
    try {
      const data = await apiFetch(`/api/admin/conversations/${conv.id}/transcript`);
      setTranscriptData(data);
    } catch (err) {
      showToast(err.message || "Failed to load conversation transcript", "danger");
    } finally {
      setLoadingTranscript(false);
    }
  };

  // Tab 4 Handlers
  const handleMarkReviewed = async (item) => {
    try {
      const targetState = !item.reviewed;
      await apiFetch(`/api/admin/feedback/${item.id}/reviewed`, {
        method: "PATCH",
        body: JSON.stringify({ reviewed: targetState }),
      });
      showToast(targetState ? "Feedback marked as reviewed" : "Feedback marked unreviewed", "success");
      loadTabData("feedback");
    } catch (err) {
      showToast(err.message || "Failed to update review status", "danger");
    }
  };

  // Tab 5 Handlers
  const handleChangeRole = async () => {
    if (!roleChangeTarget) return;
    try {
      await apiFetch(`/api/admin/users/${roleChangeTarget.user.id}/role`, {
        method: "PATCH",
        body: JSON.stringify({ role: roleChangeTarget.newRole }),
      });
      showToast(`User role updated to ${roleChangeTarget.newRole}`, "success");
      setRoleChangeTarget(null);
      loadTabData("users");
    } catch (err) {
      showToast(err.message || "Failed to change user role", "danger");
    }
  };

  const handleToggleDisable = async (targetUser) => {
    try {
      const targetState = !targetUser.is_disabled;
      await apiFetch(`/api/admin/users/${targetUser.id}/disable`, {
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

  // Tab 8 Handlers
  const handleExecuteClearCache = async () => {
    try {
      await apiFetch("/api/admin/cache", { method: "DELETE" });
      showToast("RAG question cache cleared successfully", "success");
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
            <button
              onClick={handleLogout}
              className="rounded-md border px-3 py-1.5 text-xs font-medium transition hover:border-[var(--danger)]"
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

      {/* Tab Navigation */}
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
                className="rounded-md px-3.5 py-1.5 text-xs font-medium transition whitespace-nowrap"
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

      {/* Main Content Area */}
      <main className="mx-auto max-w-6xl flex-1 px-4 py-6 sm:px-6 w-full">
        {loading && !selectedConversation ? (
          <div className="grid gap-4 sm:grid-cols-4 animate-pulse">
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="h-24 rounded-lg border"
                style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}
              />
            ))}
          </div>
        ) : error ? (
          <div
            className="rounded-lg border p-6 text-center"
            style={{
              background: "var(--surface)",
              borderColor: "var(--danger)",
              color: "var(--danger)",
            }}
          >
            <p className="text-sm font-medium">{error}</p>
            <button
              onClick={() => loadTabData(activeTab)}
              className="mt-3 rounded-md px-3 py-1.5 text-xs font-medium text-white"
              style={{ background: "var(--accent)" }}
              type="button"
            >
              Retry
            </button>
          </div>
        ) : (
          <>
            {/* 1. OVERVIEW TAB */}
            {activeTab === "overview" && overviewData && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                    Performance and Usage Metrics
                  </h2>
                  <div className="flex items-center gap-1">
                    {[7, 30, 90].map((d) => (
                      <button
                        key={d}
                        onClick={() => setOverviewDays(d)}
                        className="rounded-md border px-2.5 py-1 text-xs font-medium transition"
                        style={{
                          background: overviewDays === d ? "var(--accent)" : "var(--surface)",
                          borderColor: overviewDays === d ? "var(--accent)" : "var(--border)",
                          color: overviewDays === d ? "#FFFFFF" : "var(--text-2)",
                        }}
                        type="button"
                      >
                        Last {d}d
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                  <StatCard
                    label="Total Queries"
                    value={overviewData.total_queries ?? "No data yet"}
                    subtitle={`Logged over last ${overviewDays} days`}
                  />
                  <StatCard
                    label="Unique Users"
                    value={overviewData.unique_users ?? "No data yet"}
                    subtitle="Registered and guest sessions"
                  />
                  <StatCard
                    label="Knowledge Gap Rate"
                    value={
                      overviewData.knowledge_gap_rate != null
                        ? `${(overviewData.knowledge_gap_rate * 100).toFixed(1)}%`
                        : "No data yet"
                    }
                    subtitle="Unanswered queries"
                    accent={Boolean(overviewData.knowledge_gap_rate && overviewData.knowledge_gap_rate > 0.1)}
                  />
                  <StatCard
                    label="Feedback Rate"
                    value={
                      overviewData.feedback_rate != null
                        ? `${(overviewData.feedback_rate * 100).toFixed(1)}%`
                        : "No data yet"
                    }
                    subtitle="Ratings per query"
                  />
                  <StatCard
                    label="Positive Feedback Share"
                    value={
                      (overviewData.total_ratings || 0) < 20
                        ? "Not enough ratings yet"
                        : overviewData.positive_feedback_share != null
                        ? `${(overviewData.positive_feedback_share * 100).toFixed(1)}%`
                        : "No data yet"
                    }
                    subtitle={
                      (overviewData.total_ratings || 0) < 20
                        ? `${overviewData.total_ratings || 0} of 20 ratings recorded`
                        : `${overviewData.total_ratings} total ratings`
                    }
                  />
                </div>

                <div className="grid gap-4 lg:grid-cols-2">
                  {/* Daily Query Volume Chart */}
                  <div
                    className="rounded-lg border p-4"
                    style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                  >
                    <div className="mb-3 flex items-center justify-between">
                      <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
                        Daily Query Volume
                      </h3>
                      <span className="text-xs font-mono" style={{ color: "var(--muted)" }}>
                        {overviewData.daily_volume?.reduce((acc, d) => acc + (d.count || 0), 0) || 0} total
                      </span>
                    </div>
                    <DailyVolumeChart data={overviewData.daily_volume} />
                  </div>

                  {/* Latency Percentiles Chart */}
                  <div
                    className="rounded-lg border p-4"
                    style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                  >
                    <div className="mb-3 flex items-center justify-between">
                      <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
                        Response Latency (Seconds)
                      </h3>
                      <span className="text-xs font-mono" style={{ color: "var(--muted)" }}>
                        Target: &lt; 2.5s p50
                      </span>
                    </div>
                    <LatencyLineChart data={overviewData.daily_latency} />
                  </div>
                </div>
              </div>
            )}

            {/* 2. KNOWLEDGE GAPS TAB */}
            {activeTab === "gaps" && (
              <div className="space-y-4">
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2 flex-1">
                    <input
                      type="search"
                      placeholder="Search query or topic..."
                      value={gapSearch}
                      onChange={(e) => setGapSearch(e.target.value)}
                      className="rounded-lg border px-3 py-1.5 text-xs focus:outline-none w-48 sm:w-60"
                      style={{
                        background: "var(--surface)",
                        borderColor: "var(--border)",
                        color: "var(--text)",
                      }}
                    />
                    <select
                      value={gapProgrammeFilter}
                      onChange={(e) => setGapProgrammeFilter(e.target.value)}
                      className="rounded-lg border px-2.5 py-1.5 text-xs focus:outline-none"
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
                      className="rounded-lg border px-2.5 py-1.5 text-xs focus:outline-none"
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
                  <button
                    onClick={handleExportCsv}
                    className="inline-flex items-center justify-center gap-2 rounded-md border px-3 py-1.5 text-xs font-medium transition hover:border-[var(--border-focus)]"
                    style={{
                      background: "var(--surface)",
                      borderColor: "var(--border)",
                      color: "var(--text)",
                    }}
                    type="button"
                  >
                    <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" />
                    </svg>
                    Export CSV (UTF-8)
                  </button>
                </div>

                {gaps.length === 0 ? (
                  <div
                    className="rounded-lg border p-10 text-center"
                    style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                  >
                    <p className="text-xs font-medium" style={{ color: "var(--muted)" }}>
                      No knowledge gaps recorded matching these criteria.
                    </p>
                  </div>
                ) : (
                  <div
                    className="overflow-x-auto rounded-lg border"
                    style={{ borderColor: "var(--border)", background: "var(--surface)" }}
                  >
                    <table className="w-full text-left text-[13px] border-collapse font-sans">
                      <thead
                        className="sticky top-0 z-10 border-b text-[11px] font-semibold uppercase tracking-wider"
                        style={{
                          background: "var(--surface-2)",
                          borderColor: "var(--border)",
                          color: "var(--muted)",
                        }}
                      >
                        <tr>
                          <th className="px-3.5 py-2.5">Normalized Question</th>
                          <th className="px-3 py-2.5 text-center">Freq</th>
                          <th className="px-3 py-2.5">Topic / Prog</th>
                          <th className="px-3 py-2.5">First / Last Seen</th>
                          <th className="px-3 py-2.5">Workflow Status</th>
                          <th className="px-3 py-2.5">Notes</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y" style={{ borderColor: "var(--border)" }}>
                        {gaps.map((g) => {
                          return (
                            <tr
                              key={g.normalized_question}
                              className="transition-colors hover:bg-[var(--surface-2)]"
                            >
                              <td className="px-3.5 py-2.5 max-w-xs font-medium">
                                <div className="truncate" title={g.sample_question || g.normalized_question}>
                                  {g.sample_question || g.normalized_question}
                                </div>
                              </td>
                              <td className="px-3 py-2.5 text-center font-mono font-semibold">
                                {g.frequency}
                              </td>
                              <td className="px-3 py-2.5 whitespace-nowrap">
                                <div className="flex flex-wrap gap-1">
                                  {g.topics?.slice(0, 2).map((t) => (
                                    <span
                                      key={t}
                                      className="rounded border px-1.5 py-0.5 text-[10px] font-mono uppercase"
                                      style={{
                                        background: "var(--surface-2)",
                                        borderColor: "var(--border)",
                                        color: "var(--text-2)",
                                      }}
                                    >
                                      {t}
                                    </span>
                                  ))}
                                  {g.programmes?.map((p) => (
                                    <span
                                      key={p}
                                      className="rounded border px-1.5 py-0.5 text-[10px] font-mono uppercase"
                                      style={{
                                        background: "var(--accent-surface)",
                                        borderColor: "var(--border)",
                                        color: "var(--accent)",
                                      }}
                                    >
                                      {p}
                                    </span>
                                  ))}
                                </div>
                              </td>
                              <td className="px-3 py-2.5 text-xs font-mono whitespace-nowrap" style={{ color: "var(--muted)" }}>
                                <span title={g.last_seen || ""}>
                                  {g.last_seen ? new Date(g.last_seen).toLocaleDateString() : "None"}
                                </span>
                              </td>
                              <td className="px-3 py-2.5 whitespace-nowrap">
                                <select
                                  value={g.review_status || "open"}
                                  onChange={(e) =>
                                    handleUpdateGapStatus(g.normalized_question, e.target.value, g.notes)
                                  }
                                  className="rounded border px-2 py-1 text-xs focus:outline-none"
                                  style={{
                                    background: "var(--surface)",
                                    borderColor: "var(--border)",
                                    color: "var(--text)",
                                  }}
                                >
                                  <option value="open">Open</option>
                                  <option value="in_progress">In Progress</option>
                                  <option value="resolved">Resolved</option>
                                  <option value="ignored">Ignored</option>
                                </select>
                              </td>
                              <td className="px-3 py-2.5 text-xs max-w-xs">
                                <div className="flex items-center justify-between gap-2">
                                  <span className="truncate italic" style={{ color: g.notes ? "var(--text)" : "var(--muted)" }}>
                                    {g.notes || "None"}
                                  </span>
                                  <button
                                    onClick={() =>
                                      setEditingGapNote({
                                        question: g.normalized_question,
                                        status: g.review_status,
                                        notes: g.notes || "",
                                      })
                                    }
                                    className="rounded border px-2 py-0.5 text-[11px] font-medium transition hover:border-[var(--border-focus)] shrink-0"
                                    style={{
                                      borderColor: "var(--border)",
                                      background: "var(--surface)",
                                      color: "var(--text-2)",
                                    }}
                                    type="button"
                                  >
                                    Edit
                                  </button>
                                </div>
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

            {/* 3. CONVERSATIONS TAB */}
            {activeTab === "conversations" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between gap-3">
                  <input
                    type="search"
                    placeholder="Search conversations by email or query preview..."
                    value={convSearch}
                    onChange={(e) => setConvSearch(e.target.value)}
                    className="rounded-lg border px-3 py-1.5 text-xs focus:outline-none w-72"
                    style={{
                      background: "var(--surface)",
                      borderColor: "var(--border)",
                      color: "var(--text)",
                    }}
                  />
                  <span className="text-xs font-mono" style={{ color: "var(--muted)" }}>
                    {conversations.length} threads
                  </span>
                </div>

                {conversations.length === 0 ? (
                  <div
                    className="rounded-lg border p-10 text-center"
                    style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                  >
                    <p className="text-xs font-medium" style={{ color: "var(--muted)" }}>
                      No conversations found.
                    </p>
                  </div>
                ) : (
                  <div
                    className="overflow-x-auto rounded-lg border"
                    style={{ borderColor: "var(--border)", background: "var(--surface)" }}
                  >
                    <table className="w-full text-left text-[13px] border-collapse font-sans">
                      <thead
                        className="sticky top-0 z-10 border-b text-[11px] font-semibold uppercase tracking-wider"
                        style={{
                          background: "var(--surface-2)",
                          borderColor: "var(--border)",
                          color: "var(--muted)",
                        }}
                      >
                        <tr>
                          <th className="px-3.5 py-2.5">User Email</th>
                          <th className="px-3 py-2.5">Preview</th>
                          <th className="px-3 py-2.5 text-center">Messages</th>
                          <th className="px-3 py-2.5">Updated</th>
                          <th className="px-3 py-2.5 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y" style={{ borderColor: "var(--border)" }}>
                        {conversations.map((c) => {
                          const revealed = revealedEmails[c.id];
                          const displayEmail = revealed || c.user_email_masked || "Guest Session";

                          return (
                            <tr
                              key={c.id}
                              className="transition-colors hover:bg-[var(--surface-2)]"
                            >
                              <td className="px-3.5 py-2.5 whitespace-nowrap">
                                <div className="flex items-center gap-2 font-mono text-xs">
                                  <span>{displayEmail}</span>
                                  {!revealed && c.user_email_masked && c.user_email_masked !== "Guest Session" && (
                                    <button
                                      onClick={() => handleRevealEmail(c.id)}
                                      className="rounded border px-1.5 py-0.5 text-[10px] font-sans font-medium transition hover:border-[var(--border-focus)]"
                                      style={{
                                        borderColor: "var(--border)",
                                        background: "var(--surface)",
                                        color: "var(--accent)",
                                      }}
                                      title="Reveal full email (audited)"
                                      type="button"
                                    >
                                      Reveal
                                    </button>
                                  )}
                                </div>
                              </td>
                              <td className="px-3 py-2.5 max-w-sm truncate" style={{ color: "var(--text-2)" }}>
                                {c.preview || "No preview"}
                              </td>
                              <td className="px-3 py-2.5 text-center font-mono font-semibold">
                                {c.message_count || 0}
                              </td>
                              <td
                                className="px-3 py-2.5 text-xs font-mono whitespace-nowrap"
                                style={{ color: "var(--muted)" }}
                                title={c.updated_at || ""}
                              >
                                {c.updated_at ? new Date(c.updated_at).toLocaleDateString() : "None"}
                              </td>
                              <td className="px-3 py-2.5 text-right whitespace-nowrap">
                                <button
                                  onClick={() => handleOpenTranscript(c)}
                                  className="rounded border px-2.5 py-1 text-xs font-medium transition hover:border-[var(--border-focus)]"
                                  style={{
                                    borderColor: "var(--border)",
                                    background: "var(--surface-2)",
                                    color: "var(--text)",
                                  }}
                                  type="button"
                                >
                                  Transcript
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

            {/* 4. FEEDBACK TAB */}
            {activeTab === "feedback" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setFeedbackFilter("all")}
                      className="rounded-md border px-2.5 py-1 text-xs font-medium transition"
                      style={{
                        background: feedbackFilter === "all" ? "var(--accent)" : "var(--surface)",
                        borderColor: feedbackFilter === "all" ? "var(--accent)" : "var(--border)",
                        color: feedbackFilter === "all" ? "#FFFFFF" : "var(--text-2)",
                      }}
                      type="button"
                    >
                      All Feedback
                    </button>
                    <button
                      onClick={() => setFeedbackFilter("unreviewed")}
                      className="rounded-md border px-2.5 py-1 text-xs font-medium transition"
                      style={{
                        background: feedbackFilter === "unreviewed" ? "var(--accent)" : "var(--surface)",
                        borderColor: feedbackFilter === "unreviewed" ? "var(--accent)" : "var(--border)",
                        color: feedbackFilter === "unreviewed" ? "#FFFFFF" : "var(--text-2)",
                      }}
                      type="button"
                    >
                      Unreviewed Only
                    </button>
                    <button
                      onClick={() => setFeedbackFilter("negative")}
                      className="rounded-md border px-2.5 py-1 text-xs font-medium transition"
                      style={{
                        background: feedbackFilter === "negative" ? "var(--accent)" : "var(--surface)",
                        borderColor: feedbackFilter === "negative" ? "var(--accent)" : "var(--border)",
                        color: feedbackFilter === "negative" ? "#FFFFFF" : "var(--text-2)",
                      }}
                      type="button"
                    >
                      Thumbs Down Only
                    </button>
                  </div>
                  <span className="text-xs font-mono" style={{ color: "var(--muted)" }}>
                    {feedbackItems.length} records
                  </span>
                </div>

                {feedbackItems.length === 0 ? (
                  <div
                    className="rounded-lg border p-10 text-center"
                    style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                  >
                    <p className="text-xs font-medium" style={{ color: "var(--muted)" }}>
                      No feedback submissions recorded yet.
                    </p>
                  </div>
                ) : (
                  <div
                    className="overflow-x-auto rounded-lg border"
                    style={{ borderColor: "var(--border)", background: "var(--surface)" }}
                  >
                    <table className="w-full text-left text-[13px] border-collapse font-sans">
                      <thead
                        className="sticky top-0 z-10 border-b text-[11px] font-semibold uppercase tracking-wider"
                        style={{
                          background: "var(--surface-2)",
                          borderColor: "var(--border)",
                          color: "var(--muted)",
                        }}
                      >
                        <tr>
                          <th className="px-3.5 py-2.5">Rating</th>
                          <th className="px-3 py-2.5">User Question</th>
                          <th className="px-3 py-2.5">Assistant Answer</th>
                          <th className="px-3 py-2.5">User Reason</th>
                          <th className="px-3 py-2.5">Date</th>
                          <th className="px-3 py-2.5 text-right">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y" style={{ borderColor: "var(--border)" }}>
                        {feedbackItems
                          .filter((fb) => {
                            if (feedbackFilter === "unreviewed") return !fb.reviewed;
                            if (feedbackFilter === "negative") return fb.rating === -1;
                            return true;
                          })
                          .map((fb) => (
                            <tr
                              key={fb.id}
                              className="transition-colors hover:bg-[var(--surface-2)]"
                            >
                              <td className="px-3.5 py-2.5 whitespace-nowrap">
                                {fb.rating === 1 ? (
                                  <span
                                    className="inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[11px] font-medium"
                                    style={{
                                      borderColor: "var(--border)",
                                      background: "var(--surface-2)",
                                      color: "var(--success)",
                                    }}
                                  >
                                    <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                                      <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
                                    </svg>
                                    Helpful
                                  </span>
                                ) : (
                                  <span
                                    className="inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[11px] font-medium"
                                    style={{
                                      borderColor: "var(--border)",
                                      background: "var(--surface-2)",
                                      color: "var(--danger)",
                                    }}
                                  >
                                    <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                                      <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3" />
                                    </svg>
                                    Unhelpful
                                  </span>
                                )}
                              </td>
                              <td className="px-3 py-2.5 font-medium max-w-xs truncate" title={fb.user_question}>
                                {fb.user_question || "None"}
                              </td>
                              <td className="px-3 py-2.5 max-w-sm truncate text-xs" style={{ color: "var(--text-2)" }} title={fb.assistant_answer}>
                                {fb.assistant_answer || "None"}
                              </td>
                              <td className="px-3 py-2.5 text-xs italic max-w-xs truncate" style={{ color: fb.reason ? "var(--warning)" : "var(--muted)" }} title={fb.reason}>
                                {fb.reason || "None"}
                              </td>
                              <td
                                className="px-3 py-2.5 text-xs font-mono whitespace-nowrap"
                                style={{ color: "var(--muted)" }}
                                title={fb.timestamp || ""}
                              >
                                {fb.timestamp ? new Date(fb.timestamp).toLocaleDateString() : "None"}
                              </td>
                              <td className="px-3 py-2.5 text-right whitespace-nowrap">
                                <button
                                  onClick={() => handleMarkReviewed(fb)}
                                  className="rounded border px-2 py-1 text-xs font-medium transition hover:border-[var(--border-focus)]"
                                  style={{
                                    borderColor: "var(--border)",
                                    background: fb.reviewed ? "var(--surface-2)" : "var(--accent)",
                                    color: fb.reviewed ? "var(--text-2)" : "#FFFFFF",
                                  }}
                                  type="button"
                                >
                                  {fb.reviewed ? "Reviewed" : "Mark reviewed"}
                                </button>
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* 5. USERS TAB */}
            {activeTab === "users" && (
              <div className="space-y-4">
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <input
                      type="search"
                      placeholder="Search users by email..."
                      value={userSearch}
                      onChange={(e) => setUserSearch(e.target.value)}
                      className="rounded-lg border px-3 py-1.5 text-xs focus:outline-none w-56"
                      style={{
                        background: "var(--surface)",
                        borderColor: "var(--border)",
                        color: "var(--text)",
                      }}
                    />
                    <select
                      value={userRoleFilter}
                      onChange={(e) => setUserRoleFilter(e.target.value)}
                      className="rounded-lg border px-2.5 py-1.5 text-xs focus:outline-none"
                      style={{
                        background: "var(--surface)",
                        borderColor: "var(--border)",
                        color: "var(--text)",
                      }}
                    >
                      <option value="">All Roles</option>
                      <option value="admin">Admin</option>
                      <option value="user">User</option>
                    </select>
                  </div>
                  <span className="text-xs font-mono" style={{ color: "var(--muted)" }}>
                    {usersList.length} registered
                  </span>
                </div>

                <div
                  className="overflow-x-auto rounded-lg border"
                  style={{ borderColor: "var(--border)", background: "var(--surface)" }}
                >
                  <table className="w-full text-left text-[13px] border-collapse font-sans">
                    <thead
                      className="sticky top-0 z-10 border-b text-[11px] font-semibold uppercase tracking-wider"
                      style={{
                        background: "var(--surface-2)",
                        borderColor: "var(--border)",
                        color: "var(--muted)",
                      }}
                    >
                      <tr>
                        <th className="px-3.5 py-2.5">User Email</th>
                        <th className="px-3 py-2.5">Role</th>
                        <th className="px-3 py-2.5">Account Status</th>
                        <th className="px-3 py-2.5">Registered</th>
                        <th className="px-3 py-2.5">Last Active</th>
                        <th className="px-3 py-2.5 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y" style={{ borderColor: "var(--border)" }}>
                      {usersList.map((u) => {
                        const isSelf = user?.email && u.email === user.email;
                        return (
                          <tr
                            key={u.id}
                            className="transition-colors hover:bg-[var(--surface-2)]"
                          >
                            <td className="px-3.5 py-2.5 font-mono text-xs font-medium">
                              {u.email}
                              {isSelf && (
                                <span className="ml-2 rounded border px-1.5 py-0.2 text-[10px] font-sans" style={{ borderColor: "var(--border)", color: "var(--accent)" }}>
                                  You
                                </span>
                              )}
                            </td>
                            <td className="px-3 py-2.5 whitespace-nowrap">
                              <select
                                value={u.role}
                                onChange={(e) => {
                                  if (isSelf && e.target.value !== "admin") {
                                    setRoleChangeTarget({ user: u, newRole: e.target.value });
                                  } else {
                                    setRoleChangeTarget({ user: u, newRole: e.target.value });
                                  }
                                }}
                                className="rounded border px-2 py-1 text-xs focus:outline-none"
                                style={{
                                  background: "var(--surface)",
                                  borderColor: "var(--border)",
                                  color: "var(--text)",
                                }}
                              >
                                <option value="user">User</option>
                                <option value="admin">Admin</option>
                              </select>
                            </td>
                            <td className="px-3 py-2.5 whitespace-nowrap">
                              <button
                                onClick={() => handleToggleDisable(u)}
                                disabled={isSelf}
                                className="rounded border px-2 py-0.5 text-xs font-medium transition disabled:opacity-40"
                                style={{
                                  borderColor: "var(--border)",
                                  background: u.is_disabled ? "var(--surface-2)" : "var(--surface)",
                                  color: u.is_disabled ? "var(--danger)" : "var(--success)",
                                }}
                                type="button"
                              >
                                {u.is_disabled ? "Disabled" : "Active"}
                              </button>
                            </td>
                            <td
                              className="px-3 py-2.5 text-xs font-mono whitespace-nowrap"
                              style={{ color: "var(--muted)" }}
                              title={u.created_at || ""}
                            >
                              {u.created_at ? new Date(u.created_at).toLocaleDateString() : "None"}
                            </td>
                            <td
                              className="px-3 py-2.5 text-xs font-mono whitespace-nowrap"
                              style={{ color: "var(--muted)" }}
                              title={u.last_active || ""}
                            >
                              {u.last_active ? new Date(u.last_active).toLocaleDateString() : "None"}
                            </td>
                            <td className="px-3 py-2.5 text-right whitespace-nowrap">
                              <button
                                onClick={() => setUserToDelete(u)}
                                disabled={isSelf}
                                className="rounded border px-2.5 py-1 text-xs font-medium transition hover:border-[var(--danger)] disabled:opacity-30"
                                style={{
                                  borderColor: "var(--border)",
                                  background: "var(--surface)",
                                  color: "var(--danger)",
                                }}
                                title={isSelf ? "Cannot delete own account while logged in" : "Delete user account and all data"}
                                type="button"
                              >
                                Delete
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* 6. KNOWLEDGE BASE TAB */}
            {activeTab === "knowledge_base" && kbData && (
              <div className="space-y-6">
                <div className="grid gap-3 sm:grid-cols-3">
                  <StatCard
                    label="Total Chunks Indexed"
                    value={kbData.total_chunks ?? 0}
                    subtitle="Stored in Chroma vector database"
                  />
                  <StatCard
                    label="Source Documents"
                    value={kbData.total_documents ?? 0}
                    subtitle="Official PDFs and syllabi"
                  />
                  <StatCard
                    label="Last Ingestion Date"
                    value={kbData.last_modified ? new Date(kbData.last_modified).toLocaleDateString() : "Active"}
                    subtitle="Server filesystem timestamp"
                  />
                </div>

                <div
                  className="rounded-lg border p-4"
                  style={{
                    background: "var(--surface)",
                    borderColor: "var(--border)",
                  }}
                >
                  <h3 className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--muted)" }}>
                    Chunks per Programme
                  </h3>
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 font-mono text-center">
                    {Object.entries(kbData.chunks_per_programme || {}).map(([prog, count]) => (
                      <div
                        key={prog}
                        className="rounded-md border p-2"
                        style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}
                      >
                        <p className="text-[11px] uppercase" style={{ color: "var(--muted)" }}>{prog}</p>
                        <p className="text-lg font-bold" style={{ color: "var(--accent)" }}>{count}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div
                  className="rounded-lg border p-4 text-xs"
                  style={{
                    background: "var(--surface-2)",
                    borderColor: "var(--border)",
                    color: "var(--text-2)",
                  }}
                >
                  <p className="font-semibold mb-1" style={{ color: "var(--text)" }}>
                    Document Ingestion Workflow
                  </p>
                  <p>
                    {kbData.rebuild_instructions ||
                      "To add or update documents, place them in backend/knowledge_base/ and run python scripts/rebuild_knowledge_base.py from the server."}
                  </p>
                </div>

                <div
                  className="overflow-x-auto rounded-lg border"
                  style={{ borderColor: "var(--border)", background: "var(--surface)" }}
                >
                  <table className="w-full text-left text-[13px] border-collapse font-sans">
                    <thead
                      className="sticky top-0 z-10 border-b text-[11px] font-semibold uppercase tracking-wider"
                      style={{
                        background: "var(--surface-2)",
                        borderColor: "var(--border)",
                        color: "var(--muted)",
                      }}
                    >
                      <tr>
                        <th className="px-3.5 py-2.5">Document File</th>
                        <th className="px-3 py-2.5">Programme</th>
                        <th className="px-3 py-2.5 text-center">Chunk Count</th>
                        <th className="px-3 py-2.5">Source Path</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y" style={{ borderColor: "var(--border)" }}>
                      {(kbData.documents || []).map((doc) => (
                        <tr key={doc.source} className="transition-colors hover:bg-[var(--surface-2)]">
                          <td className="px-3.5 py-2.5 font-medium">{doc.name}</td>
                          <td className="px-3 py-2.5 uppercase font-mono text-xs">{doc.program}</td>
                          <td className="px-3 py-2.5 text-center font-mono font-semibold">{doc.chunk_count}</td>
                          <td className="px-3 py-2.5 font-mono text-xs truncate max-w-xs" style={{ color: "var(--muted)" }}>
                            {doc.source}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* 7. AUDIT LOG TAB */}
            {activeTab === "audit_log" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                    Append-Only Administrative Audit Log
                  </h2>
                  <span className="text-xs font-mono" style={{ color: "var(--muted)" }}>
                    {auditLogs.length} events logged
                  </span>
                </div>

                {auditLogs.length === 0 ? (
                  <div
                    className="rounded-lg border p-10 text-center"
                    style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                  >
                    <p className="text-xs font-medium" style={{ color: "var(--muted)" }}>
                      No audit events recorded yet.
                    </p>
                  </div>
                ) : (
                  <div
                    className="overflow-x-auto rounded-lg border"
                    style={{ borderColor: "var(--border)", background: "var(--surface)" }}
                  >
                    <table className="w-full text-left text-[13px] border-collapse font-sans">
                      <thead
                        className="sticky top-0 z-10 border-b text-[11px] font-semibold uppercase tracking-wider"
                        style={{
                          background: "var(--surface-2)",
                          borderColor: "var(--border)",
                          color: "var(--muted)",
                        }}
                      >
                        <tr>
                          <th className="px-3.5 py-2.5">Timestamp</th>
                          <th className="px-3 py-2.5">Admin User</th>
                          <th className="px-3 py-2.5">Action</th>
                          <th className="px-3 py-2.5">Target</th>
                          <th className="px-3 py-2.5">Details</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y" style={{ borderColor: "var(--border)" }}>
                        {auditLogs.map((log) => (
                          <tr key={log.id} className="transition-colors hover:bg-[var(--surface-2)]">
                            <td
                              className="px-3.5 py-2.5 font-mono text-xs whitespace-nowrap"
                              style={{ color: "var(--muted)" }}
                              title={log.timestamp || ""}
                            >
                              {log.timestamp ? new Date(log.timestamp).toLocaleString() : "None"}
                            </td>
                            <td className="px-3 py-2.5 font-mono text-xs">{log.admin_email}</td>
                            <td className="px-3 py-2.5">
                              <span
                                className="rounded border px-1.5 py-0.5 text-[11px] font-mono"
                                style={{
                                  background: "var(--surface-2)",
                                  borderColor: "var(--border)",
                                  color: "var(--accent)",
                                }}
                              >
                                {log.action}
                              </span>
                            </td>
                            <td className="px-3 py-2.5 font-mono text-xs truncate max-w-xs">{log.target || "None"}</td>
                            <td className="px-3 py-2.5 font-mono text-xs text-slate-500 max-w-sm truncate" style={{ color: "var(--muted)" }}>
                              {log.details ? JSON.stringify(log.details) : "None"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* 8. SYSTEM TAB */}
            {activeTab === "system" && systemInfo && (
              <div className="space-y-6">
                <div
                  className="rounded-lg border p-5"
                  style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                >
                  <h3 className="text-xs font-semibold uppercase tracking-wider mb-4" style={{ color: "var(--muted)" }}>
                    Core Service Infrastructure
                  </h3>
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    <div className="rounded-md border p-3" style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}>
                      <div className="flex items-center gap-2">
                        <span
                          className="h-2 w-2 rounded-full" /* allow-round: status dot */
                          style={{ background: systemInfo.database?.connected ? "var(--success)" : "var(--danger)" }}
                        />
                        <span className="text-xs font-semibold">MongoDB</span>
                      </div>
                      <p className="mt-2 text-xs font-mono" style={{ color: "var(--muted)" }}>
                        Database: {systemInfo.database?.name || "Connected"}
                      </p>
                    </div>

                    <div className="rounded-md border p-3" style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}>
                      <div className="flex items-center gap-2">
                        <span
                          className="h-2 w-2 rounded-full" /* allow-round: status dot */
                          style={{ background: systemInfo.vector_store?.ready ? "var(--success)" : "var(--danger)" }}
                        />
                        <span className="text-xs font-semibold">Chroma Vector Store</span>
                      </div>
                      <p className="mt-2 text-xs font-mono" style={{ color: "var(--muted)" }}>
                        {systemInfo.vector_store?.chunks ?? 0} indexed chunks
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
                        {systemInfo.models?.primary || "Gemini 2.5 Flash"}
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
                        {systemInfo.models?.failover || "Groq (openai/gpt-oss-120b)"}
                      </p>
                    </div>
                  </div>
                </div>

                <div
                  className="rounded-lg border p-5"
                  style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                >
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
                        Question Cache Performance
                      </h3>
                      <p className="mt-1 text-xs" style={{ color: "var(--muted)" }}>
                        In-memory LRU query cache for instant responses to identical questions
                      </p>
                    </div>
                    <button
                      onClick={() => setConfirmClearCache(true)}
                      className="rounded-md border px-3 py-1.5 text-xs font-medium transition hover:border-[var(--danger)]"
                      style={{
                        borderColor: "var(--border)",
                        background: "var(--surface)",
                        color: "var(--danger)",
                      }}
                      type="button"
                    >
                      Clear cache
                    </button>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-4 font-mono">
                    <div className="rounded-md border p-3" style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}>
                      <p className="text-[11px] uppercase" style={{ color: "var(--muted)" }}>Cached Questions</p>
                      <p className="mt-1 text-xl font-bold" style={{ color: "var(--text)" }}>{systemInfo.cache?.entries ?? 0}</p>
                    </div>
                    <div className="rounded-md border p-3" style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}>
                      <p className="text-[11px] uppercase" style={{ color: "var(--muted)" }}>Cache Hits</p>
                      <p className="mt-1 text-xl font-bold" style={{ color: "var(--success)" }}>{systemInfo.cache?.hits ?? 0}</p>
                    </div>
                    <div className="rounded-md border p-3" style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}>
                      <p className="text-[11px] uppercase" style={{ color: "var(--muted)" }}>Cache Misses</p>
                      <p className="mt-1 text-xl font-bold" style={{ color: "var(--text-2)" }}>{systemInfo.cache?.misses ?? 0}</p>
                    </div>
                    <div className="rounded-md border p-3" style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}>
                      <p className="text-[11px] uppercase" style={{ color: "var(--muted)" }}>Hit Rate</p>
                      <p className="mt-1 text-xl font-bold" style={{ color: "var(--accent)" }}>
                        {systemInfo.cache?.hit_rate != null ? `${(systemInfo.cache.hit_rate * 100).toFixed(1)}%` : "0.0%"}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </main>

      {/* Transcript Slide-Over Drawer */}
      {selectedConversation && (
        <div
          role="presentation"
          className="fixed inset-0 z-50 flex justify-end"
          onClick={(e) => {
            if (e.target === e.currentTarget) setSelectedConversation(null);
          }}
        >
          <div className="fixed inset-0 bg-black/40 transition-opacity" aria-hidden="true" />
          <div
            className="relative z-10 w-full max-w-xl h-full flex flex-col border-l shadow-xl"
            style={{
              background: "var(--surface)",
              borderColor: "var(--border)",
              color: "var(--text)",
            }}
          >
            {/* Drawer Header */}
            <div
              className="flex items-center justify-between border-b px-4 py-3"
              style={{ borderColor: "var(--border)", background: "var(--surface-2)" }}
            >
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
                  Conversation Transcript
                </h3>
                <p className="text-xs font-mono mt-0.5" style={{ color: "var(--text)" }}>
                  {revealedEmails[selectedConversation.id] ||
                    selectedConversation.user_email_masked ||
                    "Guest Session"}
                </p>
              </div>
              <button
                onClick={() => setSelectedConversation(null)}
                className="flex h-7 w-7 items-center justify-center rounded-md border text-xs"
                style={{ borderColor: "var(--border)", color: "var(--muted)" }}
                aria-label="Close transcript"
                type="button"
              >
                ✕
              </button>
            </div>

            {/* Drawer Messages Feed */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {loadingTranscript ? (
                <div className="flex h-40 items-center justify-center text-xs" style={{ color: "var(--muted)" }}>
                  Loading transcript...
                </div>
              ) : !transcriptData?.messages?.length ? (
                <div className="text-center text-xs py-8" style={{ color: "var(--muted)" }}>
                  No messages recorded in this conversation.
                </div>
              ) : (
                transcriptData.messages.map((m) => {
                  const isUser = m.role === "user";
                  return (
                    <div
                      key={m.id}
                      className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}
                    >
                      <div className="text-[10px] font-mono mb-1" style={{ color: "var(--muted)" }}>
                        {isUser ? "User" : "Assistant"} {m.timestamp ? ` - ${new Date(m.timestamp).toLocaleTimeString()}` : ""}
                      </div>
                      <div
                        className="rounded-lg p-3 text-xs leading-relaxed max-w-[85%]"
                        style={{
                          background: isUser ? "var(--surface-2)" : "transparent",
                          border: isUser ? "1px solid var(--border)" : "none",
                          color: "var(--text)",
                        }}
                      >
                        <p className="whitespace-pre-wrap">{m.content}</p>

                        {!isUser && m.sources?.length > 0 && (
                          <div className="mt-2 pt-2 border-t border-[var(--border)] text-[11px]" style={{ color: "var(--muted)" }}>
                            <p className="font-semibold mb-1">Sources Cited ({m.sources.length}):</p>
                            <ul className="list-disc pl-4 space-y-0.5">
                              {m.sources.map((s, idx) => (
                                <li key={idx}>
                                  {s.source_name || s.document_name || "Document"}{" "}
                                  {s.page ? `(Page ${s.page})` : ""}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {!isUser && (m.feedback || m.latency_s) && (
                          <div className="mt-2 flex items-center gap-3 text-[10px] font-mono" style={{ color: "var(--muted)" }}>
                            {m.latency_s != null && <span>Latency: {m.latency_s}s</span>}
                            {m.feedback === 1 && <span style={{ color: "var(--success)" }}>Feedback: Helpful</span>}
                            {m.feedback === -1 && <span style={{ color: "var(--danger)" }}>Feedback: Unhelpful</span>}
                          </div>
                        )}

                        {!isUser && m.reason && (
                          <p className="mt-1 text-[11px] italic" style={{ color: "var(--warning)" }}>
                            Reason: {m.reason}
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}

      {/* Note Editing Modal */}
      <Dialog
        open={Boolean(editingGapNote)}
        onClose={() => setEditingGapNote(null)}
        title="Edit Knowledge Gap Note"
        confirmLabel="Save Note"
        onConfirm={handleSaveGapNote}
      >
        <div className="space-y-3">
          <p className="text-xs" style={{ color: "var(--muted)" }}>
            Document what information needs to be added to which course document to answer this query.
          </p>
          <p className="text-xs font-semibold" style={{ color: "var(--text)" }}>
            {editingGapNote?.question}
          </p>
          <textarea
            value={editingGapNote?.notes || ""}
            onChange={(e) =>
              setEditingGapNote((prev) => ({ ...prev, notes: e.target.value }))
            }
            rows={4}
            className="w-full rounded-md border p-2 text-xs focus:outline-none"
            style={{
              background: "var(--surface)",
              borderColor: "var(--border)",
              color: "var(--text)",
            }}
            placeholder="e.g. Add revised semester 3 fee structure to BBA 2026 handbook page 12."
          />
        </div>
      </Dialog>

      {/* Confirm User Role Change Modal */}
      <Dialog
        open={Boolean(roleChangeTarget)}
        onClose={() => setRoleChangeTarget(null)}
        title="Confirm Role Change"
        confirmLabel="Update Role"
        onConfirm={handleChangeRole}
      >
        <p className="text-xs leading-relaxed" style={{ color: "var(--text-2)" }}>
          Are you sure you want to change the role of{" "}
          <strong className="font-mono text-[var(--text)]">{roleChangeTarget?.user.email}</strong> to{" "}
          <strong className="uppercase text-[var(--accent)]">{roleChangeTarget?.newRole}</strong>?
          {roleChangeTarget?.user.email === user?.email && roleChangeTarget?.newRole !== "admin" && (
            <span className="block mt-2 font-semibold text-[var(--danger)]">
              Warning: You are demoting your own account. You will lose access to the admin console immediately.
            </span>
          )}
        </p>
      </Dialog>

      {/* Confirm Delete User Modal */}
      <Dialog
        open={Boolean(userToDelete)}
        onClose={() => {
          setUserToDelete(null);
          setDeleteConfirmInput("");
        }}
        title="Delete User and All Data"
        confirmLabel="Permanently Delete"
        danger
        onConfirm={handleDeleteUser}
      >
        <div className="space-y-3">
          <p className="text-xs leading-relaxed" style={{ color: "var(--text-2)" }}>
            This action will permanently delete user{" "}
            <strong className="font-mono text-[var(--text)]">{userToDelete?.email}</strong> and cascade delete all their conversations, messages, and feedback records. This cannot be undone.
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
        title="Clear RAG Question Cache"
        confirmLabel="Clear Cache"
        danger
        onConfirm={handleExecuteClearCache}
      >
        <p className="text-xs leading-relaxed" style={{ color: "var(--text-2)" }}>
          Are you sure you want to clear the entire RAG question cache? Future queries will bypass cache and recompute full vector search and LLM calls until the cache repopulates.
        </p>
      </Dialog>
    </div>
  );
}
