function inline(text, keyPrefix) {
  const parts = [];
  let rest = text;
  let i = 0;
  const pattern = /\*\*(.+?)\*\*/g;
  let match;
  let last = 0;

  while ((match = pattern.exec(rest)) !== null) {
    if (match.index > last) parts.push(rest.slice(last, match.index));
    parts.push(
      <strong key={`${keyPrefix}-b${i++}`} className="font-semibold text-slate-900">
        {match[1]}
      </strong>,
    );
    last = match.index + match[0].length;
  }
  if (last < rest.length) parts.push(rest.slice(last));
  return parts;
}

/**
 * Lightweight renderer for assistant answers:
 * - groups consecutive "- " lines into bullet lists
 * - renders **bold** inline
 * - renders "Conflict Notice:" answers inside a highlighted callout
 */
export default function RichText({ text }) {
  const isConflict = /^\s*conflict notice/i.test(text);
  const lines = text.split("\n");
  const blocks = [];
  let bullets = [];

  const flushBullets = (key) => {
    if (bullets.length === 0) return;
    blocks.push(
      <ul key={key} className="my-1.5 list-disc space-y-1 pl-5 marker:text-indigo-400">
        {bullets.map((b, idx) => (
          <li key={idx}>{inline(b, `${key}-${idx}`)}</li>
        ))}
      </ul>,
    );
    bullets = [];
  };

  lines.forEach((raw, idx) => {
    const line = raw.trimEnd();
    if (/^\s*[-•*]\s+/.test(line)) {
      bullets.push(line.replace(/^\s*[-•*]\s+/, ""));
      return;
    }
    flushBullets(`ul-${idx}`);
    if (line.trim() === "") return;
    blocks.push(
      <p key={`p-${idx}`} className="my-1.5 leading-relaxed">
        {inline(line, `p-${idx}`)}
      </p>,
    );
  });
  flushBullets("ul-end");

  if (isConflict) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900 [&_p]:my-1 [&_strong]:text-amber-950">
        {blocks}
      </div>
    );
  }
  return <div className="text-[15px]">{blocks}</div>;
}
