export default function Footer({ onAskClick }) {
  return (
    <footer className="bg-slate-950 text-slate-400">
      <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
        <div className="flex flex-col items-start justify-between gap-10 md:flex-row md:items-center">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600">
                <svg viewBox="0 0 24 24" className="h-5 w-5 fill-white">
                  <path d="M12 3 1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
                </svg>
              </span>
              <span className="text-sm font-bold tracking-wide text-white">CHARUSAT Assistant</span>
            </div>
            <p className="mt-3 max-w-md text-sm leading-relaxed">
              An AI-powered Q&amp;A assistant for CHARUSAT&apos;s online degree programmes, built on
              retrieval-augmented generation over official documents.
            </p>
          </div>

          <nav className="flex flex-wrap gap-x-8 gap-y-3 text-sm">
            <a href="#programs" className="transition hover:text-white">
              Programs
            </a>
            <a href="#how-it-works" className="transition hover:text-white">
              How it works
            </a>
            <a href="#faq" className="transition hover:text-white">
              FAQ
            </a>
            <button onClick={onAskClick} className="font-medium text-indigo-300 hover:text-indigo-200">
              Ask a question
            </button>
          </nav>
        </div>

        <div className="mt-12 border-t border-white/10 pt-6 text-xs">
          <p>© {new Date().getFullYear()} CHARUSAT Online Programs Assistant. Informational only.</p>
        </div>
      </div>
    </footer>
  );
}
