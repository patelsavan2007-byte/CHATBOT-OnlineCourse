/**
 * Admin Dashboard — 5-tab operations portal:
 * 1. Overview (key metrics, query totals, health)
 * 2. Knowledge Gaps (unanswered queries, missing info, CSV export)
 * 3. Feedback (user ratings, thumbs up/down breakdown)
 * 4. Users (registered accounts, roles, activity)
 * 5. System (diagnostics, database, vector store, cache management)
 */
import { useEffect, useState, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext.jsx";
import { apiFetch, getAuthToken } from "../services/api.js";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "gaps", label: "Knowledge Gaps" },
  { id: "feedback", label: "Feedback" },
  { id: "users", label: "Users" },
  { id: "system", label: "System" },
];

function StatCard({ label, value, subtitle, accent }) {
  return (
    <div
      className={`rounded-2xl border p-5 transition ${
        accent
          ? "border-indigo-500/30 bg-indigo-500/10"
          : "border-white/8 bg-white/4"
      }`}
    >
      <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
        {label}
      </p>
      <p className={`mt-2 text-3xl font-bold ${accent ? "text-indigo-300" : "text-white"}`}>
        {value ?? "—"}
      </p>
      {subtitle && <p className="mt-1 text-xs text-slate-400">{subtitle}</p>}
    </div>
  );
}

export default function Admin() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("overview");

  // State per tab
  const [stats, setStats] = useState(null);
  const [gaps, setGaps] = useState([]);
  const [feedbackData, setFeedbackData] = useState(null);
  const [usersList, setUsersList] = useState([]);
  const [systemInfo, setSystemInfo] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [gapSearch, setGapSearch] = useState("");

  const loadTabData = useCallback(async (tabId) => {
    setLoading(true);
    setError("");
    try {
      if (tabId === "overview") {
        const data = await apiFetch("/api/admin/stats");
        setStats(data);
      } else if (tabId === "gaps") {
        const data = await apiFetch("/api/admin/knowledge-gaps");
        setGaps(data.gaps || []);
      } else if (tabId === "feedback") {
        const data = await apiFetch("/api/admin/feedback");
        setFeedbackData(data);
      } else if (tabId === "users") {
        const data = await apiFetch("/api/admin/users");
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
  }, []);

  useEffect(() => {
    loadTabData(activeTab);
  }, [activeTab, loadTabData]);

  const handleExportCsv = async () => {
    try {
      const token = getAuthToken();
      const res = await fetch("/api/admin/knowledge-gaps/csv", {
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
    } catch (err) {
      alert(`Export failed: ${err.message}`);
    }
  };

  const handleClearCache = async () => {
    if (!window.confirm("Are you sure you want to clear the entire RAG question cache?")) return;
    try {
      await apiFetch("/api/admin/cache", { method: "DELETE" });
      alert("Cache cleared successfully.");
      loadTabData("system");
    } catch (err) {
      alert(`Clear cache failed: ${err.message}`);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate("/", { replace: true });
  };

  const filteredGaps = gaps.filter((g) =>
    (g.question || "").toLowerCase().includes(gapSearch.toLowerCase()) ||
    (g.topic || "").toLowerCase().includes(gapSearch.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Bar */}
      <header className="border-b border-white/8 bg-slate-900/80 px-4 py-3 backdrop-blur-md sticky top-0 z-30">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              to="/chat"
              className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition hover:bg-white/8 hover:text-white"
              aria-label="Back to chat"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                <path d="M19 12H5M12 5l-7 7 7 7" />
              </svg>
            </Link>
            <div>
              <h1 className="text-sm font-semibold text-white tracking-tight">CHARUSAT Admin Console</h1>
            </div>
            <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-0.5 text-[10px] font-bold text-amber-400">
              Admin
            </span>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 text-xs text-slate-400">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              <span>{user?.email}</span>
            </div>
            <button
              onClick={handleLogout}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:bg-rose-500/20 hover:text-rose-300 hover:border-rose-500/30"
              type="button"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="border-b border-white/8 bg-slate-900/40 px-4">
        <div className="mx-auto flex max-w-6xl gap-1 overflow-x-auto py-2">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`rounded-xl px-4 py-2 text-xs font-medium transition whitespace-nowrap ${
                activeTab === tab.id
                  ? "bg-indigo-600 text-white shadow"
                  : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
              }`}
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <main className="mx-auto max-w-6xl flex-1 px-4 py-8 sm:px-6 w-full">
        {loading ? (
          <div className="grid gap-4 sm:grid-cols-3 animate-pulse">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-28 rounded-2xl bg-white/5" />
            ))}
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 p-8 text-center">
            <p className="text-sm text-rose-400">{error}</p>
            <button
              onClick={() => loadTabData(activeTab)}
              className="mt-4 rounded-xl bg-white/10 px-4 py-2 text-xs font-medium text-white hover:bg-white/20"
              type="button"
            >
              Retry
            </button>
          </div>
        ) : (
          <>
            {/* 1. OVERVIEW TAB */}
            {activeTab === "overview" && stats && (
              <div className="space-y-6">
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <StatCard
                    label="Total Registered Users"
                    value={stats.users}
                    subtitle="Student and faculty accounts"
                  />
                  <StatCard
                    label="Conversations Created"
                    value={stats.conversations}
                    subtitle="Multi-turn chat threads"
                  />
                  <StatCard
                    label="Total Queries Processed"
                    value={stats.total_queries}
                    subtitle="Logged in chat_events"
                  />
                  <StatCard
                    label="Knowledge Gaps Detected"
                    value={stats.knowledge_gaps}
                    subtitle="Unanswered / missing in docs"
                    accent={stats.knowledge_gaps > 0}
                  />
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="rounded-2xl border border-white/8 bg-white/4 p-6">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-4">
                      RAG Pipeline Status
                    </h3>
                    <div className="flex items-center gap-3">
                      <span className={`h-3 w-3 rounded-full ${stats.rag_ready ? "bg-emerald-500" : "bg-rose-500"}`} />
                      <span className="text-lg font-medium text-white">
                        {stats.rag_ready ? "Operational & Ready" : "Pipeline Offline"}
                      </span>
                    </div>
                    <p className="mt-2 text-xs text-slate-400">
                      Vector database: {stats.vector_store_documents ? `${stats.vector_store_documents} chunks indexed` : "Initialized"}
                    </p>
                  </div>

                  <div className="rounded-2xl border border-white/8 bg-white/4 p-6">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-4">
                      User Satisfaction
                    </h3>
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-bold text-white">
                        {stats.feedback?.feedback_rate != null ? `${Math.round(stats.feedback.feedback_rate * 100)}%` : "0%"}
                      </span>
                      <span className="text-xs text-slate-400">rating engagement</span>
                    </div>
                    <div className="mt-3 flex gap-4 text-xs text-slate-400">
                      <span>👍 Thumbs up: {stats.feedback?.thumbs_up || 0}</span>
                      <span>👎 Thumbs down: {stats.feedback?.thumbs_down || 0}</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 2. KNOWLEDGE GAPS TAB */}
            {activeTab === "gaps" && (
              <div className="space-y-4">
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                  <input
                    type="search"
                    placeholder="Search queries or topics..."
                    value={gapSearch}
                    onChange={(e) => setGapSearch(e.target.value)}
                    className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 sm:w-72"
                  />
                  <button
                    onClick={handleExportCsv}
                    className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-medium text-white shadow transition hover:bg-indigo-500"
                    type="button"
                  >
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" />
                    </svg>
                    Export CSV
                  </button>
                </div>

                {filteredGaps.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-white/10 p-12 text-center text-slate-400">
                    <p className="text-sm">No knowledge gaps currently recorded.</p>
                    <p className="mt-1 text-xs text-slate-600">
                      Queries that cannot be answered from official documents will appear here automatically.
                    </p>
                  </div>
                ) : (
                  <div className="overflow-x-auto rounded-2xl border border-white/10 bg-white/4">
                    <table className="w-full text-left text-xs">
                      <thead className="border-b border-white/10 bg-white/5 text-slate-400 uppercase text-[10px]">
                        <tr>
                          <th className="px-4 py-3">Unanswered Query</th>
                          <th className="px-4 py-3">Topic</th>
                          <th className="px-4 py-3">Programme</th>
                          <th className="px-4 py-3">Status</th>
                          <th className="px-4 py-3">Date</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5 text-slate-300">
                        {filteredGaps.map((g) => (
                          <tr key={g.id} className="hover:bg-white/5 transition">
                            <td className="px-4 py-3 font-medium text-white max-w-xs truncate">{g.question}</td>
                            <td className="px-4 py-3">
                              <span className="rounded-md bg-white/10 px-2 py-0.5 text-[10px] text-slate-300">
                                {g.topic}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-slate-400">{g.programmes?.join(", ") || "All"}</td>
                            <td className="px-4 py-3 text-amber-400 text-[11px]">{g.status}</td>
                            <td className="px-4 py-3 text-slate-500 whitespace-nowrap">
                              {g.timestamp ? new Date(g.timestamp).toLocaleDateString() : "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* 3. FEEDBACK TAB */}
            {activeTab === "feedback" && (
              <div className="space-y-6">
                <div className="grid gap-4 sm:grid-cols-3">
                  <StatCard
                    label="Thumbs Up"
                    value={feedbackData?.stats?.thumbs_up ?? 0}
                    subtitle="Positive interactions"
                    accent
                  />
                  <StatCard
                    label="Thumbs Down"
                    value={feedbackData?.stats?.thumbs_down ?? 0}
                    subtitle="Responses needing review"
                  />
                  <StatCard
                    label="Total Feedback Items"
                    value={feedbackData?.feedback_items?.length ?? 0}
                    subtitle="Collected across sessions"
                  />
                </div>

                <div className="overflow-x-auto rounded-2xl border border-white/10 bg-white/4">
                  <table className="w-full text-left text-xs">
                    <thead className="border-b border-white/10 bg-white/5 text-slate-400 uppercase text-[10px]">
                      <tr>
                        <th className="px-4 py-3">Rating</th>
                        <th className="px-4 py-3">Response Preview</th>
                        <th className="px-4 py-3">Date</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 text-slate-300">
                      {feedbackData?.feedback_items?.length ? (
                        feedbackData.feedback_items.map((item) => (
                          <tr key={item.id} className="hover:bg-white/5 transition">
                            <td className="px-4 py-3 font-medium">
                              {item.feedback === "thumbs_up" ? (
                                <span className="inline-flex items-center gap-1 rounded-md bg-emerald-500/10 px-2 py-0.5 text-emerald-400 text-[11px]">
                                  👍 Positive
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 rounded-md bg-rose-500/10 px-2 py-0.5 text-rose-400 text-[11px]">
                                  👎 Negative
                                </span>
                              )}
                            </td>
                            <td className="px-4 py-3 max-w-md text-slate-300 truncate">{item.preview}</td>
                            <td className="px-4 py-3 text-slate-500 whitespace-nowrap">
                              {item.timestamp ? new Date(item.timestamp).toLocaleString() : "—"}
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan="3" className="px-4 py-8 text-center text-slate-500">
                            No feedback items recorded yet.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* 4. USERS TAB */}
            {activeTab === "users" && (
              <div className="overflow-x-auto rounded-2xl border border-white/10 bg-white/4">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-white/10 bg-white/5 text-slate-400 uppercase text-[10px]">
                    <tr>
                      <th className="px-4 py-3">Name</th>
                      <th className="px-4 py-3">Email</th>
                      <th className="px-4 py-3">Role</th>
                      <th className="px-4 py-3">Auth Provider</th>
                      <th className="px-4 py-3">Conversations</th>
                      <th className="px-4 py-3">Registered</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 text-slate-300">
                    {usersList.map((u) => (
                      <tr key={u.id} className="hover:bg-white/5 transition">
                        <td className="px-4 py-3 font-medium text-white">{u.name}</td>
                        <td className="px-4 py-3 text-slate-400">{u.email}</td>
                        <td className="px-4 py-3">
                          <span
                            className={`rounded-md px-2 py-0.5 text-[10px] font-semibold uppercase ${
                              u.role === "admin"
                                ? "bg-amber-500/20 text-amber-400"
                                : "bg-white/10 text-slate-300"
                            }`}
                          >
                            {u.role}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-400">{u.auth_provider}</td>
                        <td className="px-4 py-3 text-slate-300">{u.conversations_count}</td>
                        <td className="px-4 py-3 text-slate-500 whitespace-nowrap">
                          {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* 5. SYSTEM TAB */}
            {activeTab === "system" && systemInfo && (
              <div className="space-y-6">
                <div className="rounded-2xl border border-white/10 bg-white/4 p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      System Architecture & Health
                    </h3>
                    <button
                      onClick={handleClearCache}
                      className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-xs font-medium text-rose-300 transition hover:bg-rose-500/20"
                      type="button"
                    >
                      Clear RAG Cache
                    </button>
                  </div>

                  <dl className="grid gap-4 sm:grid-cols-2">
                    <div className="border-b border-white/5 pb-3">
                      <dt className="text-xs text-slate-500">Python Version</dt>
                      <dd className="mt-1 text-sm font-medium text-white">{systemInfo.python_version}</dd>
                    </div>
                    <div className="border-b border-white/5 pb-3">
                      <dt className="text-xs text-slate-500">Platform OS</dt>
                      <dd className="mt-1 text-sm font-medium text-white">{systemInfo.os_platform}</dd>
                    </div>
                    <div className="border-b border-white/5 pb-3">
                      <dt className="text-xs text-slate-500">MongoDB Database</dt>
                      <dd className="mt-1 text-sm font-medium text-emerald-400">
                        {systemInfo.database_connected ? `${systemInfo.database_name} (Connected)` : "Disconnected"}
                      </dd>
                    </div>
                    <div className="border-b border-white/5 pb-3">
                      <dt className="text-xs text-slate-500">Vector Store Documents</dt>
                      <dd className="mt-1 text-sm font-medium text-white">
                        {systemInfo.vector_store_documents ?? "345 chunks indexed"}
                      </dd>
                    </div>
                    <div className="border-b border-white/5 pb-3">
                      <dt className="text-xs text-slate-500">Preferred LLM Models</dt>
                      <dd className="mt-1 text-xs text-slate-300">
                        {systemInfo.llm_preferred_models?.join(", ") || "Gemini"}
                      </dd>
                    </div>
                    <div className="border-b border-white/5 pb-3">
                      <dt className="text-xs text-slate-500">Groq Failover Tier</dt>
                      <dd className="mt-1 text-xs text-slate-300">{systemInfo.groq_failover_model}</dd>
                    </div>
                  </dl>
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}

