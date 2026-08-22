import { useEffect, useRef, useState } from "react";
import RichText from "./RichText.jsx";

const SUGGESTED = [
  "What online degree programmes does CHARUSAT offer?",
  "What is the total fee for the Online MBA?",
  "Am I eligible for the Online BCA after 12th?",
  "How do the online exams work?",
];

function TypingDots() {
  return (
    <div className="flex items-center gap-1 px-1 py-2" aria-label="Assistant is typing">
      <span className="typing-dot h-2 w-2 rounded-full bg-indigo-400" />
      <span className="typing-dot h-2 w-2 rounded-full bg-indigo-400" />
      <span className="typing-dot h-2 w-2 rounded-full bg-indigo-400" />
    </div>
  );
}

export default function ChatPanel({ messages, isSending, error, onSend }) {
  const [input, setInput] = useState("");
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, isSending]);

  const submit = (e) => {
    e.preventDefault();
    const q = input.trim();
    if (!q || isSending) return;
    setInput("");
    onSend(q);
    inputRef.current?.focus();
  };

  const empty = messages.length === 0;

  return (
    <div
      id="chat"
      className="flex h-[560px] flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl shadow-indigo-950/20 ring-1 ring-black/5"
    >
      {/* header */}
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3.5">
        <div className="flex items-center gap-3">
          <span className="relative flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-violet-600">
            <svg viewBox="0 0 24 24" className="h-4.5 w-4.5 fill-white">
              <path d="M12 3 1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
            </svg>
            <span className="absolute -right-0.5 -bottom-0.5 h-3 w-3 rounded-full border-2 border-white bg-emerald-500" />
          </span>
          <div>
            <p className="text-sm font-semibold text-slate-900">CHARUSAT Assistant</p>
            <p className="text-xs text-slate-500">Answers from official programme documents</p>
          </div>
        </div>
        <span className="hidden rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 sm:block">
          Online
        </span>
      </div>

      {/* messages */}
      <div ref={scrollRef} className="chat-scroll flex-1 space-y-4 overflow-y-auto bg-slate-50/60 px-4 py-5 sm:px-5">
        {empty && (
          <div className="animate-fade-up pt-6 pb-2 text-center">
            <h3 className="font-display text-xl font-semibold text-slate-900">
              Hi! How can I help you today?
            </h3>
            <p className="mx-auto mt-2 max-w-sm text-sm text-slate-500">
              Ask about fees, eligibility, curriculum, admissions or exams for CHARUSAT&apos;s online
              degree programmes.
            </p>
            <div className="mt-6 flex max-w-md flex-wrap justify-center gap-2">
              {SUGGESTED.map((q) => (
                <button
                  key={q}
                  onClick={() => onSend(q)}
                  disabled={isSending}
                  className="rounded-full border border-slate-200 bg-white px-3.5 py-2 text-left text-xs font-medium text-slate-600 shadow-sm transition hover:border-indigo-300 hover:text-indigo-700 hover:shadow disabled:opacity-50"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m) =>
          m.role === "user" ? (
            <div key={m.id} className="animate-fade-up flex justify-end">
              <div className="max-w-[85%] rounded-2xl rounded-br-md bg-gradient-to-br from-indigo-600 to-violet-600 px-4 py-2.5 text-[15px] leading-relaxed text-white shadow-md shadow-indigo-500/20">
                {m.text}
              </div>
            </div>
          ) : (
            <div key={m.id} className="animate-fade-up flex justify-start gap-2.5">
              <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white shadow-sm ring-1 ring-slate-200">
                <svg viewBox="0 0 24 24" className="h-4 w-4 fill-indigo-600">
                  <path d="M12 3 1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
                </svg>
              </span>
              <div
                className={`max-w-[85%] rounded-2xl rounded-tl-md border px-4 py-2.5 shadow-sm ${
                  m.error ? "border-rose-200 bg-rose-50 text-rose-800" : "border-slate-200 bg-white"
                }`}
              >
                {m.error ? (
                  <p className="text-sm">{m.text}</p>
                ) : (
                  <div className="text-slate-700">
                    <RichText text={m.text} />
                  </div>
                )}
              </div>
            </div>
          ),
        )}

        {isSending && (
          <div className="animate-fade-up flex justify-start gap-2.5">
            <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white shadow-sm ring-1 ring-slate-200">
              <svg viewBox="0 0 24 24" className="h-4 w-4 fill-indigo-600">
                <path d="M12 3 1 9l11 6 9-4.91V17h2V9L12 3zM5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" />
              </svg>
            </span>
            <div className="rounded-2xl rounded-tl-md border border-slate-200 bg-white px-3 py-1 shadow-sm">
              <TypingDots />
            </div>
          </div>
        )}
      </div>

      {/* error banner */}
      {error && (
        <div className="border-t border-rose-100 bg-rose-50 px-5 py-2 text-xs font-medium text-rose-700">
          {error} — check that the backend is running and try again.
        </div>
      )}

      {/* composer */}
      <form onSubmit={submit} className="border-t border-slate-100 bg-white px-4 py-3.5 sm:px-5">
        <div className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 py-1.5 pr-1.5 pl-4 transition focus-within:border-indigo-300 focus-within:bg-white focus-within:ring-4 focus-within:ring-indigo-500/10">
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about fees, eligibility, curriculum…"
            aria-label="Ask a question"
            className="h-10 min-w-0 flex-1 bg-transparent text-[15px] text-slate-800 placeholder:text-slate-400 focus:outline-none"
          />
          <button
            type="submit"
            disabled={!input.trim() || isSending}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-violet-600 text-white shadow-md shadow-indigo-500/25 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
            aria-label="Send message"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5 fill-current">
              <path d="M2.01 21 23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          </button>
        </div>
        <p className="mt-2 text-center text-[11px] text-slate-400">
          Informational only — always confirm details with official CHARUSAT sources.
        </p>
      </form>
    </div>
  );
}
