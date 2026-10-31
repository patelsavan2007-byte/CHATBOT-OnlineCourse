import test from "node:test";
import assert from "node:assert/strict";
import { getGreetingOptions, pickGreeting, pickDiverseStarters } from "../../src/lib/welcomeHelper.js";

test("guest greeting options have no exclamation marks or emoji", () => {
  const options = getGreetingOptions("");
  assert.equal(options.length, 4);
  for (const opt of options) {
    assert.ok(!opt.includes("!"), `Greeting "${opt}" should not contain exclamation marks`);
    assert.ok(!/[\u{1F300}-\u{1F6FF}]/u.test(opt), `Greeting "${opt}" should not contain emoji`);
  }
});

test("authenticated greeting options include user first name and time-of-day variant", () => {
  const morning = new Date("2026-10-31T09:00:00");
  const options = getGreetingOptions("Rahul", morning);
  assert.equal(options.length, 5);
  assert.ok(options.includes("Hey, Rahul"));
  assert.ok(options.includes("Good morning, Rahul"));
  for (const opt of options) {
    assert.ok(!opt.includes("!"), `Greeting "${opt}" should not contain exclamation marks`);
  }

  const evening = new Date("2026-10-31T19:00:00");
  const eveningOptions = getGreetingOptions("Rahul", evening);
  assert.ok(eveningOptions.includes("Good evening, Rahul"));
});

test("pickGreeting non-repeating across sessions", () => {
  const user = { name: "Ananya Sharma" };
  const first = pickGreeting(user, null);
  assert.ok(first.greeting.includes("Ananya"));
  assert.ok(typeof first.index === "number");

  // Running 20 times with lastIdx set to first.index should never return first.index
  for (let i = 0; i < 20; i++) {
    const next = pickGreeting(user, first.index);
    assert.notEqual(next.index, first.index, "Should not return last shown index");
  }
});

test("pickDiverseStarters enforces max one question per topic and respects validatedIds", () => {
  const mockBank = [
    { id: "Q01", text: "Fee for BCA?", topics: ["fees"] },
    { id: "Q02", text: "Fee for MCA?", topics: ["fees"] },
    { id: "Q03", text: "Eligibility for BBA?", topics: ["eligibility"] },
    { id: "Q04", text: "Eligibility for MCA?", topics: ["eligibility"] },
    { id: "Q05", text: "How to apply?", topics: ["admission"] },
    { id: "Q06", text: "Exam schedule?", topics: ["exam"] },
    { id: "Q07", text: "Placement recruiters?", topics: ["placement"] },
    { id: "Q08", text: "Unvalidated question", topics: ["general"] },
  ];

  const validatedIds = ["Q01", "Q02", "Q03", "Q04", "Q05", "Q06", "Q07"];

  const starters = pickDiverseStarters(mockBank, validatedIds, [], 4);
  assert.equal(starters.length, 4);

  // Check that all picked are in validatedIds
  for (const s of starters) {
    assert.ok(validatedIds.includes(s.id));
    assert.notEqual(s.id, "Q08");
  }

  // Check unique topics
  const topics = starters.map((s) => s.topics[0]);
  const uniqueTopics = new Set(topics);
  assert.equal(uniqueTopics.size, starters.length, "Each starter must have a unique topic");
});

test("pickDiverseStarters avoids recently shown starter IDs when possible", () => {
  const mockBank = [
    { id: "Q01", text: "Fee for BCA?", topics: ["fees"] },
    { id: "Q02", text: "Fee for MCA?", topics: ["fees"] },
    { id: "Q03", text: "Eligibility for BBA?", topics: ["eligibility"] },
    { id: "Q04", text: "Eligibility for MCA?", topics: ["eligibility_2"] },
    { id: "Q05", text: "How to apply?", topics: ["admission"] },
    { id: "Q06", text: "Exam schedule?", topics: ["exam"] },
  ];

  const recentIds = ["Q01", "Q03", "Q05", "Q06"];
  const starters = pickDiverseStarters(mockBank, [], recentIds, 2);

  // Since Q02 and Q04 are fresh, they should be picked
  const pickedIds = starters.map((s) => s.id);
  assert.ok(pickedIds.includes("Q02"));
  assert.ok(pickedIds.includes("Q04"));
});
