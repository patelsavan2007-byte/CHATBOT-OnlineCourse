import ChatPanel from "./ChatPanel.jsx";

const STATS = [
  { value: "4", label: "Online degrees covered" },
  { value: "408+", label: "Knowledge chunks indexed" },
  { value: "~24×7", label: "Instant answers" },
];

export default function Hero({ chatProps }) {
  return (
    <section id="top" className="relative overflow-hidden bg-slate-950 pt-16">
      {/* glow background */}
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="absolute -top-40 left-1/2 h-[480px] w-[720px] -translate-x-1/2 rounded-full bg-indigo-600/25 blur-[140px]" />
        <div className="absolute top-40 -left-32 h-72 w-72 rounded-full bg-violet-600/20 blur-[120px]" />
        <div className="absolute -right-24 bottom-0 h-72 w-72 rounded-full bg-sky-500/10 blur-[120px]" />
      </div>

      <div className="relative mx-auto grid max-w-7xl items-center gap-14 px-4 pt-16 pb-24 sm:px-6 lg:grid-cols-[1.05fr_1fr] lg:gap-10 lg:px-8 lg:pt-24 lg:pb-28">
        {/* copy */}
        <div className="animate-fade-up">
          <span className="inline-flex items-center gap-2 rounded-full border border-indigo-400/30 bg-indigo-500/10 px-3.5 py-1.5 text-xs font-semibold tracking-wide text-indigo-200">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            Powered by RAG · Official CHARUSAT sources
          </span>

          <h1 className="font-display mt-6 text-4xl leading-tight font-bold tracking-tight text-white sm:text-5xl xl:text-6xl">
            Ask anything about{" "}
            <span className="bg-gradient-to-r from-indigo-300 via-violet-300 to-sky-300 bg-clip-text text-transparent">
              CHARUSAT online degrees
            </span>
          </h1>

          <p className="mt-5 max-w-xl text-lg leading-relaxed text-slate-300">
            Get instant, source-backed answers about fees, eligibility, curriculum, admission
            process and exams for the Online BBA, BCA, MBA and MCA programmes — without digging
            through PDFs.
          </p>

          <dl className="mt-9 grid max-w-lg grid-cols-3 divide-x divide-white/10 rounded-2xl border border-white/10 bg-white/5 backdrop-blur">
            {STATS.map((s) => (
              <div key={s.label} className="px-4 py-4 text-center sm:px-6">
                <dt className="sr-only">{s.label}</dt>
                <dd className="font-display text-2xl font-bold text-white">{s.value}</dd>
                <dd className="mt-1 text-[11px] leading-snug font-medium tracking-wide text-slate-400 uppercase">
                  {s.label}
                </dd>
              </div>
            ))}
          </dl>
        </div>

        {/* chat card */}
        <div className="animate-fade-up lg:justify-self-end" style={{ animationDelay: "120ms" }}>
          <ChatPanel {...chatProps} />
        </div>
      </div>

      {/* wave divider */}
      <svg
        viewBox="0 0 1440 64"
        preserveAspectRatio="none"
        className="relative block h-10 w-full fill-white sm:h-14"
        aria-hidden
      >
        <path d="M0 64h1440V22c-180 28-360 42-540 42S360 36 180 8C120-1 60-1 0 8v56z" />
      </svg>
    </section>
  );
}
