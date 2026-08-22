const STEPS = [
  {
    n: "1",
    title: "Ask in plain language",
    desc: "Type any question about fees, eligibility, curriculum, admissions or exams — no keywords or menus needed.",
  },
  {
    n: "2",
    title: "We retrieve from official documents",
    desc: "The system searches the indexed CHARUSAT knowledge base and pulls the most relevant passages from programme regulations and policies.",
  },
  {
    n: "3",
    title: "Get a grounded answer",
    desc: "The assistant answers strictly from retrieved sources — and flags conflicts between documents instead of guessing.",
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="scroll-mt-24 bg-slate-50 py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl">
          <p className="text-sm font-semibold tracking-wider text-indigo-600 uppercase">
            How it works
          </p>
          <h2 className="font-display mt-2 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
            Grounded answers, not guesswork
          </h2>
        </div>

        <ol className="mt-12 grid gap-6 md:grid-cols-3">
          {STEPS.map((s) => (
            <li
              key={s.n}
              className="relative rounded-2xl border border-slate-200 bg-white p-7 shadow-sm"
            >
              <span className="font-display absolute -top-5 left-6 flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-violet-600 text-lg font-bold text-white shadow-lg shadow-indigo-500/25">
                {s.n}
              </span>
              <h3 className="mt-4 text-lg font-semibold text-slate-900">{s.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{s.desc}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
