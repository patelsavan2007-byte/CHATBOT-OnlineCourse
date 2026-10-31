/**
 * welcomeHelper.js
 * Logic for WelcomeScreen randomized greetings and topic-deduplicated starter questions.
 */

export function getGreetingOptions(name, date = new Date()) {
  if (name) {
    const hour = date.getHours();
    let timeGreeting = `Good afternoon, ${name}`;
    if (hour < 12) {
      timeGreeting = `Good morning, ${name}`;
    } else if (hour >= 17) {
      timeGreeting = `Good evening, ${name}`;
    }
    return [
      `Hey, ${name}`,
      `Welcome back, ${name}`,
      `Good to see you, ${name}`,
      `Hi ${name}, what would you like to know?`,
      timeGreeting,
    ];
  }
  return [
    "Hello",
    "Welcome",
    "What would you like to know?",
    "How can I help?",
  ];
}

export function pickGreeting(user, lastIdx = null, date = new Date()) {
  const name = user ? (user.display_name || user.name || (user.email ? user.email.split("@")[0] : "")).trim() : "";
  const firstName = name ? name.split(" ")[0] : "";
  const cleanFirst = firstName ? firstName.charAt(0).toUpperCase() + firstName.slice(1) : "";
  const options = getGreetingOptions(cleanFirst, date);

  let availableIndices = options.map((_, i) => i);
  if (lastIdx !== null && availableIndices.length > 1) {
    const numLast = typeof lastIdx === "number" ? lastIdx : parseInt(lastIdx, 10);
    if (!isNaN(numLast)) {
      availableIndices = availableIndices.filter((i) => i !== numLast);
    }
  }
  const chosenIdx = availableIndices[Math.floor(Math.random() * availableIndices.length)];
  return { greeting: options[chosenIdx], index: chosenIdx };
}

export function pickDiverseStarters(questionBank, validatedIds = [], recentIds = [], count = 4) {
  if (!questionBank || questionBank.length === 0) return [];

  const valSet = new Set(validatedIds && validatedIds.length > 0 ? validatedIds : []);
  const pool = valSet.size > 0
    ? questionBank.filter((q) => valSet.has(q.id))
    : questionBank;

  if (pool.length === 0) return [];

  // Filter out recent IDs if we have enough candidates
  const recentSet = new Set(recentIds || []);
  const fresh = pool.filter((q) => !recentSet.has(q.id));
  const candidatePool = fresh.length >= count ? fresh : pool;

  // Shuffle candidate pool
  const shuffled = [...candidatePool].sort(() => Math.random() - 0.5);

  const picked = [];
  const usedTopics = new Set();

  // Rule: at most one question per topic in the 4 starters
  for (const q of shuffled) {
    if (picked.length >= count) break;
    const topic = (q.topics && q.topics[0]) || q.topic || q.category || "general";
    if (!usedTopics.has(topic)) {
      usedTopics.add(topic);
      picked.push(q);
    }
  }

  // If we couldn't get count distinct topics, fill from remaining
  if (picked.length < count) {
    const pickedIds = new Set(picked.map((p) => p.id));
    for (const q of shuffled) {
      if (picked.length >= count) break;
      if (!pickedIds.has(q.id)) {
        pickedIds.add(q.id);
        picked.push(q);
      }
    }
  }

  return picked;
}
