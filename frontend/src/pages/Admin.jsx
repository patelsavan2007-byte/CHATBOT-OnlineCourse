/**
 * Admin page — information-dense dashboard for admin users.
 * Connects to real backend /api/admin/stats endpoint.
 * Clear separation: admin is its own experience.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext.jsx";
import { apiFetch } from "../services/api.js";

function StatCard({ label, value, subtitle, accent }) {
  return (
    <div className={`rounded-2xl border p-6 ${accent ? "border-indigo-500/20 bg-indigo-500/8" : "border-white/8 bg-white/4"}`}>
      <p className="text-xs font-semibold uppercase tracking-widest text-slate-600">{label}</p>
      <p className={`mt-2 text-3xl font-semibold ${accent ? "text-indigo-300" : "text-white"}`}>
        {value ?? "—"}
      </p>
      {subtitle && <p className="mt-1 text-xs text-slate-600">{subtitle}</p>}
    </div>
  );
}

export default function Admin() {
  const { user } = useAuth();
  const [stats, setStats]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState("");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await apiFetch("/api/admin/stats");
        if (!cancelled) setStats(data);
      } catch (err) {
        if (!cancelled) setError(err.message || "Failed to load stats");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="min-h-dvh bg-slate-950">
      {/* Header */}
      <header className="border-b border-white/5 bg-slate-950/90 px-4 py-3.5 backdrop-blur-sm">
        <div className="mx-auto flex max-w-5xl items-center gap-3">
          <Link
            to="/chat"
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 transition hover:bg-white/8 hover:text-slate-300"
            aria-label="Back to chat"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <path d="M19 12H5M12 5l-7 7 7 7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-[15px] font-semibold text-white">Admin Dashboard</h1>
          </div>
          <span className="ml-2 rounded-full border border-amber-500/25 bg-amber-500/10 px-2.5 py-0.5 text-[11px] font-semibold text-amber-400">
            Admin
          </span>
          <div className="ml-auto flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-600/70 text-xs font-semibold text-white">
              {(user?.name?.[0] || "A").toUpperCase()}
            </div>
            <span className="text-xs text-slate-500">{user?.email}</span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        {loading ? (
          <div className="grid gap-4 sm:grid-cols-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-28 rounded-2xl skeleton" />
            ))}
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/8 p-8 text-center">
            <p className="text-sm text-rose-400">{error}</p>
          </div>
        ) : stats ? (
          <>
            {/* Stats grid */}
            <section aria-labelledby="stats-heading" className="mb-8">
              <h2 id="stats-heading" className="sr-only">System statistics</h2>
              <div className="grid gap-4 sm:grid-cols-3">
                <StatCard
                  label="Total Users"
                  value={stats.users}
                  subtitle="Registered accounts"
                />
                <StatCard
                  label="Conversations"
                  value={stats.conversations}
                  subtitle="All time"
                />
                <StatCard
                  label="RAG Pipeline"
                  value={stats.rag_ready ? "Active" : "Offline"}
                  subtitle={stats.rag_ready ? "Knowledge base indexed" : "Check backend logs"}
                  accent={stats.rag_ready}
                />
              </div>
            </section>

            {/* System info */}
            {stats.vector_store_documents != null && (
              <section aria-labelledby="system-heading" className="mb-8 rounded-2xl border border-white/8 bg-white/3 p-6">
                <h2 id="system-heading" className="mb-4 text-xs font-semibold uppercase tracking-widest text-slate-600">
                  System Status
                </h2>
                <dl className="grid gap-y-3 sm:grid-cols-2">
                  {[
                    { label: "Vector Store Documents", value: stats.vector_store_documents },
                    { label: "RAG Status",             value: stats.rag_ready ? "Ready" : "Not ready" },
                    { label: "MongoDB",                value: stats.mongodb_connected ? "Connected" : "Disconnected" },
                    { label: "LLM",                    value: stats.llm_provider || "Not configured" },
                  ].map(({ label, value }) => (
                    <div key={label} className="flex items-center justify-between gap-4 border-b border-white/5 pb-3 last:border-0">
                      <dt className="text-xs text-slate-500">{label}</dt>
                      <dd className="text-xs font-medium text-slate-300">{value ?? "—"}</dd>
                    </div>
                  ))}
                </dl>
              </section>
            )}

            {/* Future features placeholder */}
            <section className="rounded-2xl border border-dashed border-white/8 p-8 text-center">
              <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl border border-white/8 bg-white/5 text-slate-600 mb-3">
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
              <p className="text-sm font-medium text-slate-500">
                Document management, user management, and analytics
              </p>
              <p className="mt-1 text-xs text-slate-700">
                Will be connected when backend endpoints are available.
              </p>
            </section>
          </>
        ) : null}
      </main>
    </div>
  );
}
