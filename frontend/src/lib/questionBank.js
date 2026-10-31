/**
 * Question Bank client-side cache and typing suggestions matching engine.
 *
 * Provides:
 *  - loadQuestionBank(): fetches and caches /api/question-bank
 *  - getTypingSuggestions(query, currentProgramme, questionBank): fast client-side matcher
 *  - getRandomStarterQuestions(questionBank, count): diverse starter cards
 */

let cachedBank = null;
const CACHE_KEY = "charusat_qb_cache";

export async function loadQuestionBank() {
  if (cachedBank && cachedBank.length > 0) return cachedBank;

  // Try localStorage first for instant load
  try {
    const local = localStorage.getItem(CACHE_KEY);
    if (local) {
      cachedBank = JSON.parse(local);
    }
  } catch {/* ignore */}

  try {
    const res = await fetch("/api/question-bank");
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data) && data.length > 0) {
        cachedBank = data;
        try {
          localStorage.setItem(CACHE_KEY, JSON.stringify(data));
        } catch {/* ignore */}
        return cachedBank;
      }
    }
  } catch (err) {
    console.warn("Failed to fetch /api/question-bank, using fallback cache:", err);
  }

  return cachedBank || [];
}

// ---------------------------------------------------------------------------
// Synonym Lexicon
// ---------------------------------------------------------------------------
const SYNONYM_GROUPS = [
  ["fee", "fees", "cost", "price", "tuition", "payment", "pay", "charge"],
  ["eligibility", "eligible", "criteria", "qualification", "requirement"],
  ["syllabus", "subjects", "curriculum", "course", "subject"],
  ["duration", "years", "semesters", "semester", "credits", "credit", "time"],
  ["admission", "apply", "application", "process", "document", "documents", "enrol"],
  ["exam", "exams", "examination", "grading", "marks", "grade", "test", "evaluation", "pass"],
  ["lms", "portal", "login", "password", "technical", "access", "lecture", "recorded", "online"],
  ["placement", "career", "job", "jobs", "recruit", "recruiter", "package", "hiring"],
  ["refund", "cancel", "cancellation", "withdrawal", "withdraw"],
];

const SYNONYM_MAP = new Map();
for (const group of SYNONYM_GROUPS) {
  for (const word of group) {
    SYNONYM_MAP.set(word, group);
  }
}

function getSynonyms(word) {
  return SYNONYM_MAP.get(word) || [word];
}

function levenshteinDistance(s1, s2) {
  if (s1 === s2) return 0;
  if (s1.length === 0) return s2.length;
  if (s2.length === 0) return s1.length;
  if (Math.abs(s1.length - s2.length) > 1) return 2; // quick bail for distance > 1

  const row = [];
  for (let i = 0; i <= s2.length; i++) row[i] = i;

  for (let i = 1; i <= s1.length; i++) {
    let prev = i;
    for (let j = 1; j <= s2.length; j++) {
      let val;
      if (s1[i - 1] === s2[j - 1]) {
        val = row[j - 1];
      } else {
        val = Math.min(row[j - 1] + 1, prev + 1, row[j] + 1);
      }
      row[j - 1] = prev;
      prev = val;
    }
    row[s2.length] = prev;
  }
  return row[s2.length];
}

function tokenMatches(queryToken, targetToken) {
  if (queryToken === targetToken) return true;
  if (targetToken.startsWith(queryToken)) return true;

  // Synonyms check
  const syns = getSynonyms(queryToken);
  if (syns.includes(targetToken)) return true;
  for (const s of syns) {
    if (targetToken.startsWith(s)) return true;
  }

  // Edit distance 1 for tokens of 5+ letters
  if (queryToken.length >= 5) {
    if (levenshteinDistance(queryToken, targetToken) <= 1) return true;
    for (const s of syns) {
      if (s.length >= 5 && levenshteinDistance(s, targetToken) <= 1) return true;
    }
  }

  return false;
}

const PROGRAMMES = ["bba", "bca", "mba", "mca"];

const USER_QUESTIONS_KEY = "charusat_user_generated_questions";

export function getUserQuestions() {
  try {
    const raw = typeof localStorage !== "undefined" ? localStorage.getItem(USER_QUESTIONS_KEY) : null;
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function addUserQuestion(text, programme = null) {
  if (!text || typeof text !== "string") return;
  const clean = text.trim();
  if (clean.length < 4 || clean.length > 200) return;
  try {
    const existing = getUserQuestions();
    const cleanLower = clean.toLowerCase();
    if (existing.some((q) => q.text.toLowerCase() === cleanLower)) return;
    const newItem = {
      id: `usr-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      text: clean,
      category: "Recent Questions",
      programme: programme || null,
      variants: {},
    };
    const updated = [newItem, ...existing].slice(0, 50);
    localStorage.setItem(USER_QUESTIONS_KEY, JSON.stringify(updated));
  } catch {
    // Ignore storage quota or disabled localStorage errors
  }
}

export function getTypingSuggestions(query, currentProgramme, questionBank) {
  if (!query || typeof query !== "string") return [];
  const clean = query.trim().toLowerCase();
  if (clean.length < 2) return [];

  const rawTokens = clean.split(/[^a-z0-9]+/).filter(Boolean);
  if (rawTokens.length === 0) return [];

  // Detect programme in query
  let typedProgramme = null;
  for (const p of PROGRAMMES) {
    if (rawTokens.includes(p) || clean.includes(`online ${p}`)) {
      typedProgramme = p;
      break;
    }
  }

  const effectiveProgramme = typedProgramme || currentProgramme || null;
  const userBank = typeof window !== "undefined" ? getUserQuestions() : [];
  const baseBank = (questionBank && questionBank.length > 0) ? questionBank : (cachedBank || []);
  const bank = [...baseBank, ...userBank];
  const matches = [];

  for (const q of bank) {
    // Resolve variant text if applicable
    let displayText = q.text;
    if (effectiveProgramme && q.variants && q.variants[effectiveProgramme]) {
      displayText = q.variants[effectiveProgramme];
    }

    const qLower = displayText.toLowerCase();
    const qTokens = qLower.split(/[^a-z0-9]+/).filter(Boolean);

    let matchCount = 0;
    const matchedTokens = new Set();

    for (const qt of rawTokens) {
      let tokenMatched = false;
      for (const tt of qTokens) {
        if (tokenMatches(qt, tt)) {
          tokenMatched = true;
          matchedTokens.add(tt);
        }
      }
      if (tokenMatched) matchCount++;
    }

    if (matchCount > 0) {
      // Score based on matched fraction and exact prefix
      const matchScore = (matchCount / rawTokens.length) * 10 + (matchCount / qTokens.length);
      const isFullTokenMatch = matchCount === rawTokens.length;

      // Filter: if multiple tokens typed, require at least 2 token matches or full match
      if (rawTokens.length > 1 && matchCount < 2 && !isFullTokenMatch) {
        continue;
      }

      matches.push({
        id: q.id,
        text: displayText,
        score: matchScore,
        matchedTokens: Array.from(matchedTokens),
        category: q.category,
      });
    }
  }

  // Sort descending by match score, limit to 5
  matches.sort((a, b) => b.score - a.score);
  return matches.slice(0, 5);
}

/**
 * Returns 4 randomised starter questions across distinct categories.
 * Ensures the set is different from the previous visit's set using localStorage.
 */
const STARTER_STORAGE_KEY = "charusat_last_starter_ids";

export function getRandomStarterQuestions(questionBank) {
  const bank = (questionBank && questionBank.length > 0) ? questionBank : (cachedBank || []);
  if (!bank || bank.length === 0) return [];

  let lastIds = [];
  try {
    const raw = localStorage.getItem(STARTER_STORAGE_KEY);
    if (raw) lastIds = JSON.parse(raw);
  } catch {/* ignore */}

  // Group questions by category
  const byCategory = new Map();
  for (const q of bank) {
    const cat = q.category || "General Questions";
    if (!byCategory.has(cat)) byCategory.set(cat, []);
    byCategory.get(cat).push(q);
  }

  const categories = Array.from(byCategory.keys()).sort(() => Math.random() - 0.5);
  const picked = [];
  const pickedIds = new Set();

  // Pick one question from distinct categories, avoiding recently used ids
  for (const cat of categories) {
    if (picked.length >= 4) break;
    const items = byCategory.get(cat) || [];
    const candidates = items.filter((item) => !lastIds.includes(item.id));
    const pool = candidates.length > 0 ? candidates : items;
    if (pool.length > 0) {
      const chosen = pool[Math.floor(Math.random() * pool.length)];
      if (!pickedIds.has(chosen.id)) {
        picked.push(chosen);
        pickedIds.add(chosen.id);
      }
    }
  }

  // Save chosen ids
  try {
    localStorage.setItem(STARTER_STORAGE_KEY, JSON.stringify(Array.from(pickedIds)));
  } catch {/* ignore */}

  return picked;
}
