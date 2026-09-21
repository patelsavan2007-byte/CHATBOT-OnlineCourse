/**
 * RichText — lightweight markdown-like renderer for assistant answers.
 * Handles: **bold**, bullet lists (- / • / *), numbered lists, headers (##),
 * "Conflict Notice:" callout, and plain paragraphs.
 * Designed for use inside both the light landing (unused) and dark chat surfaces.
 */

function parseInline(text, keyPrefix) {
  const parts = [];
  const pattern = /\*\*(.+?)\*\*/g;
  let last = 0;
  let i = 0;
  let match;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) parts.push(text.slice(last, match.index));
    parts.push(
      <strong key={`${keyPrefix}-b${i++}`} className="font-semibold text-[var(--text-primary)]">
        {match[1]}
      </strong>
    );
    last = match.index + match[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

export default function RichText({ text }) {
  if (!text) return null;

  const isConflict = /^\s*conflict notice/i.test(text);
  const lines      = text.split("\n");
  const blocks     = [];
  let bullets      = [];
  let numberedItems = [];

  const flushBullets = (key) => {
    if (!bullets.length) return;
    blocks.push(
      <ul key={key} className="my-2 list-disc space-y-1 pl-5 marker:text-[var(--accent-primary)]">
        {bullets.map((b, idx) => (
          <li key={idx} className="text-[var(--text-primary)]">
            {parseInline(b, `${key}-${idx}`)}
          </li>
        ))}
      </ul>
    );
    bullets = [];
  };

  const flushNumbered = (key) => {
    if (!numberedItems.length) return;
    blocks.push(
      <ol key={key} className="my-2 list-decimal space-y-1 pl-5">
        {numberedItems.map((item, idx) => (
          <li key={idx} className="text-[var(--text-primary)]">
            {parseInline(item, `${key}-${idx}`)}
          </li>
        ))}
      </ol>
    );
    numberedItems = [];
  };

  lines.forEach((raw, idx) => {
    const line = raw.trimEnd();

    // Bullet list
    if (/^\s*[-•*]\s+/.test(line)) {
      flushNumbered(`ol-${idx}`);
      bullets.push(line.replace(/^\s*[-•*]\s+/, ""));
      return;
    }

    // Numbered list
    const numberedMatch = line.match(/^\s*\d+\.\s+(.*)/);
    if (numberedMatch) {
      flushBullets(`ul-${idx}`);
      numberedItems.push(numberedMatch[1]);
      return;
    }

    flushBullets(`ul-${idx}`);
    flushNumbered(`ol-${idx}`);

    if (line.trim() === "") return;

    // Headings (## / ###)
    const h2 = line.match(/^##\s+(.*)/);
    const h3 = line.match(/^###\s+(.*)/);
    if (h2) {
      blocks.push(
        <p key={`h2-${idx}`} className="mt-3 mb-1 font-semibold text-[var(--text-primary)] text-[15px]">
          {parseInline(h2[1], `h2-${idx}`)}
        </p>
      );
      return;
    }
    if (h3) {
      blocks.push(
        <p key={`h3-${idx}`} className="mt-2 mb-0.5 font-semibold text-[var(--text-primary)] text-[14px]">
          {parseInline(h3[1], `h3-${idx}`)}
        </p>
      );
      return;
    }

    // Plain paragraph
    blocks.push(
      <p key={`p-${idx}`} className="my-1.5 leading-relaxed text-[var(--text-primary)]">
        {parseInline(line, `p-${idx}`)}
      </p>
    );
  });

  // Flush any remaining
  flushBullets("ul-end");
  flushNumbered("ol-end");

  if (isConflict) {
    return (
      <div className="notice-conflict rounded-xl border px-4 py-3 text-sm"
        style={{ borderColor: "var(--warning-border)", backgroundColor: "var(--warning-surface)" }}>
        {blocks}
      </div>
    );
  }

  return <div className="text-[15px]">{blocks}</div>;
}
