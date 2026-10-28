#!/usr/bin/env node
/**
 * check-rules.mjs
 * Enforces non-negotiable design rules before every build.
 * Run via: node scripts/check-rules.mjs
 * Wired into package.json "build" as a pre-step.
 *
 * Exit code 0 = clean.  Exit code 1 = violations found.
 */

import { readFileSync, readdirSync, statSync } from "fs";
import { join, resolve, relative, extname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const ROOT = resolve(__filename, "..", "..");
const SRC  = join(ROOT, "src");
const PUBLIC = join(ROOT, "public");

let violations = [];
let warnings   = [];

// ── Helpers ─────────────────────────────────────────────────────────────────

function walk(dir, exts, results = []) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      walk(full, exts, results);
    } else if (exts.includes(extname(full))) {
      results.push(full);
    }
  }
  return results;
}

function check(file, content, lineNum, line, pattern, message, severity = "error") {
  if (pattern.test(line)) {
    const relPath = relative(ROOT, file);
    const entry = `  ${relPath}:${lineNum}  ${message}\n    >> ${line.trim()}`;
    if (severity === "warn") warnings.push(entry);
    else violations.push(entry);
  }
}

function checkFile(filePath) {
  const content = readFileSync(filePath, "utf-8");
  const lines   = content.split("\n");

  lines.forEach((line, i) => {
    const n = i + 1;

    // allow-round on the same line OR the immediately preceding line is accepted
    const prevLine = i > 0 ? lines[i - 1] : "";
    const allowRound = /allow-round/i.test(line) || /allow-round/i.test(prevLine);

    // Named banned colors only -- hex heuristics produce too many false positives
    // for legitimate gray/beige tones. Hex enforcement is left to code review.
    const forbiddenColors = [
      /\bpurple\b/i,
      /\bviolet\b/i,
      /\bindigo\b/i,
    ];

    forbiddenColors.forEach((pat) => {
      // Don't flag CSS/JS comment lines or import strings
      if (line.trimStart().startsWith("//") || line.trimStart().startsWith("*") || line.trimStart().startsWith("/*")) return;
      if (pat.test(line)) {
        // Whitelist: allow-purple comment
        if (/allow-purple|allow-indigo|allow-violet/i.test(line)) return;
        check(filePath, content, n, line, pat, `Rule 1 -- forbidden color (purple/violet/indigo): ${pat}`);
      }
    });

    if (/linear-gradient|radial-gradient|conic-gradient/i.test(line)) {
      // Allow in comments, allow skeleton with allow-gradient tag
      if (!line.trimStart().startsWith("//") && !line.trimStart().startsWith("*") && !/allow-gradient/i.test(line)) {
        check(filePath, content, n, line, /gradient/, "Rule 1 -- no gradients allowed");
      }
    }

    // Rule 2: Border-radius <= 12px on interactive non-circle elements
    if (!allowRound) {
      if (/rounded-full/i.test(line)) {
        check(filePath, content, n, line, /rounded-full/, "Rule 2 -- rounded-full (9999px) on non-allowed element. Add // allow-round comment if this is a status dot, spinner, or avatar.");
      }
      if (/border-radius:\s*(100|9999|50%)/.test(line)) {
        check(filePath, content, n, line, /border-radius/, "Rule 2 -- border-radius too large (>12px) on non-allowed element");
      }
    }

    // Rule 3: No fake/unverified claims
    const fakePatterns = [
      [/NAAC\s+A\+/i, "Rule 3 -- NAAC A+ unverified claim (add inline cite or remove)"],
      [/NIRF\s+Top\s+\d+/i, "Rule 3 -- NIRF ranking unverified claim (add inline cite or remove)"],
      [/UGC\s+Recognised/i, "Rule 3 -- UGC Recognised unverified claim (add inline cite or remove)"],
      [/\d+\+?\s*(students|colleges|countries)/i, "Rule 3 -- marketing metric (unverified)"],
      [/\d+%\s*(placement|success|satisfaction)/i, "Rule 3 -- marketing percentage (unverified)"],
    ];

    fakePatterns.forEach(([pat, msg]) => {
      if (pat.test(line) && !/allow-claim/i.test(line)) {
        check(filePath, content, n, line, pat, msg);
      }
    });

    // Rule 4: No hero section, no scroll-triggered animation/parallax
    if (/parallax|IntersectionObserver.*animation|scrollY.*animation/i.test(line)) {
      check(filePath, content, n, line, /parallax/, "Rule 4 -- scroll-triggered animation or parallax");
    }

    // Rule 5: No emoji in JSX/JS source (UI text)
    // Allow in comments, allow in admin tables if explicitly approved
    if (/\.jsx$|\.js$/.test(filePath) && !/allow-emoji/i.test(line)) {
      // Emoji range check (simplified -- catches common ones used in this codebase)
      if (/[\u{1F600}-\u{1F9FF}]|\u{1F44D}|\u{1F44E}|\uD83D[\uDC4D\uDC4E]/u.test(line)) {
        if (!line.trimStart().startsWith("//") && !line.trimStart().startsWith("*")) {
          check(filePath, content, n, line, /emoji/, "Rule 5 -- emoji in UI source (use SVG icon instead)");
        }
      }
    }

    // Rule 6: No em dash in user-visible strings (use a hyphen or " - ")
    // Skip comment-only lines: // ... , /* ... , * ... , and JSX {/* ... */}
    if (/[\u2014]/.test(line) && !/allow-emdash/i.test(line)) {
      if (/\.(jsx?|html)$/.test(filePath)) {
        const trimmed = line.trimStart();
        const isComment =
          trimmed.startsWith("//") ||
          trimmed.startsWith("*") ||
          trimmed.startsWith("/*") ||
          /^\{?\/\*/.test(trimmed);  // JSX {/* ... */}
        if (!isComment) {
          check(filePath, content, n, line, /\u2014/, "Rule 6 -- em dash in UI text (use - or hyphen-minus instead)");
        }
      }
    }

    // Rule 7: Banned CSS/utility patterns
    const bannedPatterns = [
      [/backdrop-filter/i, "Rule 7 -- backdrop-filter / glassmorphism banned"],
      [/scroll-behavior\s*:\s*smooth/i, "Rule 7 -- scroll-behavior: smooth banned"],
      [/animate-float|@keyframes\s+float/i, "Rule 7 -- float animation banned"],
      [/animate-glow|@keyframes\s+glow/i, "Rule 7 -- glow animation banned"],
      [/noise-overlay|\.glass\b/i, "Rule 7 -- .glass / noise-overlay banned"],
    ];

    bannedPatterns.forEach(([pat, msg]) => {
      if (pat.test(line) && !/allow-effect/i.test(line)) {
        // Skip CSS comment lines
        if (line.trimStart().startsWith("/*") || line.trimStart().startsWith("*") || line.trimStart().startsWith("//")) return;
        check(filePath, content, n, line, pat, msg);
      }
    });

    // Rule 8: No cursor effects
    if (/cursor-blink|cursor-follow|cursor-glow/i.test(line)) {
      check(filePath, content, n, line, /cursor/, "Rule 8 -- cursor effect banned");
    }

    // Rule 9: No alert() or window.confirm()
    if (/\balert\(|window\.confirm\(/i.test(line)) {
      if (!/allow-alert/i.test(line)) {
        check(filePath, content, n, line, /alert/, "Rule 9 -- alert()/confirm() banned. Use in-app Dialog.");
      }
    }

    // Rule 10: No dead controls (onClick={() => {}} or onClick={() => undefined})
    if (/onClick=\{[^}]*=>\s*\{\s*\}[^}]*\}|onClick=\{[^}]*=>\s*undefined\s*\}/i.test(line)) {
      if (!/allow-noop/i.test(line)) {
        check(filePath, content, n, line, /onClick/, "Rule 10 -- dead control: empty onClick handler", "warn");
      }
    }

    // Rule 11: CONFIRM placeholders must not reach build
    if (/["'`]CONFIRM["'`]/.test(line) && !/allow-confirm/i.test(line)) {
      // Allow in site.js itself (the definition)
      if (!filePath.endsWith("site.js") && !filePath.endsWith("check-rules.mjs")) {
        check(filePath, content, n, line, /CONFIRM/, "Rule 11 -- CONFIRM placeholder not replaced", "warn");
      }
    }
  });
}

// ── Run ──────────────────────────────────────────────────────────────────────

const sourceFiles = walk(SRC, [".jsx", ".js", ".css", ".html"]);
const publicFiles = walk(PUBLIC, [".html", ".js"]);
const htmlFile    = [join(ROOT, "index.html")];

[...sourceFiles, ...publicFiles, ...htmlFile].forEach(checkFile);

// ── Report ───────────────────────────────────────────────────────────────────

const RESET = "\x1b[0m";
const RED   = "\x1b[31m";
const YELLOW = "\x1b[33m";
const GREEN  = "\x1b[32m";
const BOLD   = "\x1b[1m";

if (violations.length) {
  console.error(`\n${RED}${BOLD}Design rule violations:${RESET} (${violations.length} error${violations.length !== 1 ? "s" : ""})\n`);
  violations.forEach((v) => console.error(`${RED}${v}${RESET}\n`));
}

if (warnings.length) {
  console.warn(`\n${YELLOW}${BOLD}Warnings:${RESET} (${warnings.length})\n`);
  warnings.forEach((w) => console.warn(`${YELLOW}${w}${RESET}\n`));
}

if (!violations.length && !warnings.length) {
  console.log(`\n${GREEN}${BOLD}check-rules: all clean.${RESET}\n`);
}

if (violations.length) {
  process.exit(1);
}
