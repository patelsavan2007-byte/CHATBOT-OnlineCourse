import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test("About page content is calm, under 250 words, has 4 sections and no banned terms", () => {
  const aboutPath = path.resolve(__dirname, "../../src/pages/About.jsx");
  const content = fs.readFileSync(aboutPath, "utf-8");

  // 1. Check required four sections
  const requiredSections = [
    "What this assistant is",
    "What it can answer",
    "Document sources and disclaimer",
    "Official contact",
  ];

  for (const sec of requiredSections) {
    assert.ok(
      content.includes(sec),
      `About page must contain section: "${sec}"`
    );
  }

  // 2. Check no Privacy or Terms links
  assert.ok(!content.includes("/privacy"), "About page must not contain /privacy link");
  assert.ok(!content.includes("/terms"), "About page must not contain /terms link");
  assert.ok(!content.toLowerCase().includes("privacy policy"), "About page must not reference Privacy Policy");
  assert.ok(!content.toLowerCase().includes("terms and conditions"), "About page must not reference Terms and Conditions");

  // 3. Check official verified contact details
  assert.ok(content.includes("7434055553"), "About page must list verified admissions contact");
  assert.ok(content.includes("7600257365"), "About page must list verified admissions contact");
  assert.ok(content.includes("9408033391"), "About page must list verified student support contact");
  assert.ok(content.includes("charusat.online"), "About page must list official website");

  // 4. Check banned words
  const bannedWords = [
    "supercharge",
    "unlock",
    "seamless",
    "elevate",
    "revolutionize",
    "empower",
    "cutting-edge",
    "next-generation",
    "leverage",
    "delve",
    "journey",
    "tailored",
    "game-changer",
    "your trusted",
  ];
  for (const banned of bannedWords) {
    assert.ok(!content.toLowerCase().includes(banned), `About page must not contain banned word: "${banned}"`);
  }

  // 5. Strip JSX tags, import/export boilerplate to compute word count of user-facing text
  // Extract text within JSX strings and paragraphs
  const textMatches = content.match(/>([^<]+)</g) || [];
  const textOnly = textMatches
    .map((m) => m.slice(1, -1).trim())
    .filter((t) => t.length > 0 && !t.startsWith("{") && !t.includes("new Date()"))
    .join(" ");

  const words = textOnly.split(/\s+/).filter((w) => w.length > 0);
  assert.ok(
    words.length < 250,
    `About page text must be under 250 words (currently ${words.length} words)`
  );
  assert.ok(
    words.length > 50,
    `About page text should have sufficient content (currently ${words.length} words)`
  );
});
