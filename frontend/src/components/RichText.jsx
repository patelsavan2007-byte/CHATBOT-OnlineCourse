/**
 * RichText — markdown renderer for assistant answers using react-markdown and remark-gfm.
 * Supports: tables (with responsive overflow wrapper), links (opening safely in new tabs),
 * headings, bold text, bullet/numbered/nested lists, inline code, and "Conflict Notice" callouts.
 * Theme-aware via index.css CSS custom properties.
 */
import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";

const markdownComponents = {
  table: ({ node, ...props }) => (
    <div className="my-3 overflow-x-auto rounded-lg border border-[var(--border-primary)]">
      <table className="min-w-full divide-y divide-[var(--border-primary)] text-left text-sm" {...props} />
    </div>
  ),
  thead: ({ node, ...props }) => (
    <thead className="bg-[var(--surface-tertiary)] text-[var(--text-primary)] font-semibold text-xs uppercase tracking-wider" {...props} />
  ),
  tbody: ({ node, ...props }) => (
    <tbody className="divide-y divide-[var(--border-secondary)] bg-[var(--surface-elevated)]" {...props} />
  ),
  tr: ({ node, ...props }) => (
    <tr className="transition hover:bg-[var(--surface-hover)]" {...props} />
  ),
  th: ({ node, ...props }) => (
    <th className="px-3.5 py-2.5 font-semibold text-[var(--text-primary)]" {...props} />
  ),
  td: ({ node, ...props }) => (
    <td className="px-3.5 py-2 text-[var(--text-secondary)] whitespace-normal" {...props} />
  ),
  a: ({ node, href, children, ...props }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="font-medium text-[var(--accent-primary)] underline hover:text-[var(--accent-primary-hover)]"
      {...props}
    >
      {children}
    </a>
  ),
  h1: ({ node, ...props }) => (
    <h1 className="mt-4 mb-2 text-lg font-bold text-[var(--text-primary)]" {...props} />
  ),
  h2: ({ node, ...props }) => (
    <h2 className="mt-3.5 mb-1.5 text-base font-semibold text-[var(--text-primary)]" {...props} />
  ),
  h3: ({ node, ...props }) => (
    <h3 className="mt-2.5 mb-1 text-[15px] font-semibold text-[var(--text-primary)]" {...props} />
  ),
  p: ({ node, ...props }) => (
    <p className="my-1.5 leading-relaxed text-[var(--text-primary)]" {...props} />
  ),
  ul: ({ node, ...props }) => (
    <ul className="my-2 list-disc space-y-1 pl-5 marker:text-[var(--accent-primary)] text-[var(--text-primary)]" {...props} />
  ),
  ol: ({ node, ...props }) => (
    <ol className="my-2 list-decimal space-y-1 pl-5 text-[var(--text-primary)]" {...props} />
  ),
  li: ({ node, ...props }) => (
    <li className="text-[var(--text-primary)] pl-0.5 leading-relaxed" {...props} />
  ),
  code: ({ node, inline, ...props }) => (
    <code className="rounded bg-[var(--surface-tertiary)] px-1.5 py-0.5 font-mono text-xs text-[var(--text-secondary)]" {...props} />
  ),
  strong: ({ node, ...props }) => (
    <strong className="font-semibold text-[var(--text-primary)]" {...props} />
  ),
};

export default function RichText({ text }) {
  if (!text) return null;

  // Replace <br> and <br/> with newline before rendering
  const cleanText = text.replace(/<br\s*\/?>/gi, "\n");
  const isConflict = /^\s*conflict notice/i.test(cleanText);

  if (isConflict) {
    return (
      <div
        className="notice-conflict my-2 rounded-xl border px-4 py-3 text-sm text-[var(--text-primary)]"
        style={{ borderColor: "var(--warning-border)", backgroundColor: "var(--warning-surface)" }}
      >
        <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} components={markdownComponents}>
          {cleanText}
        </ReactMarkdown>
      </div>
    );
  }

  return (
    <div className="text-[15px] prose-chat">
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} components={markdownComponents}>
        {cleanText}
      </ReactMarkdown>
    </div>
  );
}
