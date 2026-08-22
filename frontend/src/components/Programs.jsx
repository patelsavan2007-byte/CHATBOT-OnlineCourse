const PROGRAMS = [
  {
    code: "Online BBA",
    tag: "Undergraduate",
    desc: "Business administration fundamentals — management, marketing, finance and entrepreneurship.",
    ask: "What is the curriculum structure of the Online BBA programme?",
  },
  {
    code: "Online BCA",
    tag: "Undergraduate",
    desc: "Computer applications — programming, databases, web technologies and software skills.",
    ask: "What is the eligibility criteria for the Online BCA programme?",
  },
  {
    code: "Online MBA",
    tag: "Postgraduate",
    desc: "Advanced management education with specialisations, case studies and leadership focus.",
    ask: "What is the total fee for the Online MBA programme?",
  },
  {
    code: "Online MCA",
    tag: "Postgraduate",
    desc: "Master of Computer Applications — advanced computing, data and modern development.",
    ask: "How long is the Online MCA programme and how are exams conducted?",
  },
];

const TOPICS = [
  { icon: "M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6", label: "Fees & payment modes" },
  { icon: "M22 10v6M2 10l10-5 10 5-10 5zM6 12v5c3 3 9 3 12 0v-5", label: "Eligibility criteria" },
  { icon: "M4 19.5A2.5 2.5 0 0 1 6.5 17H20M4 19.5A2.5 2.5 0 0 0 6.5 22H20V2H6.5A2.5 2.5 0 0 0 4 4.5z", label: "Curriculum & syllabus" },
  { icon: "M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11", label: "Admission process" },
  { icon: "M12 8v4l3 3m6-3a9 9 0 1 1-18 0 9 9 0 0 1 18 0z", label: "Exams & duration" },
];

export default function Programs({ onQuickAsk }) {
  return (
    <section id="programs" className="mx-auto max-w-7xl scroll-mt-24 px-4 py-24 sm:px-6 lg:px-8">
      <div className="max-w-2xl">
        <p className="text-sm font-semibold tracking-wider text-indigo-600 uppercase">Programmes</p>
        <h2 className="font-display mt-2 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
          Every online degree, one assistant
        </h2>
        <p className="mt-4 text-lg text-slate-600">
          The assistant is trained on official programme regulations, fee documents and policies.
          Pick a programme to get started.
        </p>
      </div>

      <div className="mt-12 grid gap-6 sm:grid-cols-2 xl:grid-cols-4">
        {PROGRAMS.map((p) => (
          <article
            key={p.code}
            className="group flex flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:border-indigo-200 hover:shadow-xl hover:shadow-indigo-500/10"
          >
            <span className="inline-flex w-fit items-center rounded-full bg-indigo-50 px-2.5 py-1 text-[11px] font-semibold tracking-wide text-indigo-700 uppercase">
              {p.tag}
            </span>
            <h3 className="font-display mt-4 text-xl font-bold text-slate-900">{p.code}</h3>
            <p className="mt-2 flex-1 text-sm leading-relaxed text-slate-600">{p.desc}</p>
            <button
              onClick={() => onQuickAsk(p.ask)}
              className="mt-5 inline-flex items-center gap-1.5 text-sm font-semibold text-indigo-600 transition group-hover:gap-2.5 hover:text-indigo-500"
            >
              Ask about this
              <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current">
                <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z" />
              </svg>
            </button>
          </article>
        ))}
      </div>

      <div className="mt-10 flex flex-wrap justify-center gap-3">
        {TOPICS.map((t) => (
          <span
            key={t.label}
            className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-700"
          >
            <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-indigo-500 stroke-2 stroke-linecap-round stroke-linejoin-round">
              <path d={t.icon} />
            </svg>
            {t.label}
          </span>
        ))}
      </div>
    </section>
  );
}
