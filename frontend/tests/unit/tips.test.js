import test from "node:test";
import assert from "node:assert/strict";
import { shouldShowTip, selectNextTip, AVAILABLE_TIPS } from "../../src/lib/tipSelector.js";

test("shouldShowTip enforces answer frequency (3rd answer, then every 4th answer)", () => {
  const base = {
    showTipsPreference: true,
    lastTypedTimestamp: 0,
    now: 100000,
    hasError: false,
  };

  // 1st and 2nd answers: false
  assert.equal(shouldShowTip({ ...base, assistantCount: 1 }), false);
  assert.equal(shouldShowTip({ ...base, assistantCount: 2 }), false);

  // 3rd answer: true
  assert.equal(shouldShowTip({ ...base, assistantCount: 3 }), true);

  // 4th, 5th, 6th answers: false
  assert.equal(shouldShowTip({ ...base, assistantCount: 4 }), false);
  assert.equal(shouldShowTip({ ...base, assistantCount: 5 }), false);
  assert.equal(shouldShowTip({ ...base, assistantCount: 6 }), false);

  // 7th answer: true (3 + 4)
  assert.equal(shouldShowTip({ ...base, assistantCount: 7 }), true);

  // 11th answer: true (7 + 4)
  assert.equal(shouldShowTip({ ...base, assistantCount: 11 }), true);
});

test("shouldShowTip respects user preference toggle and error states", () => {
  const base = {
    assistantCount: 3,
    lastTypedTimestamp: 0,
    now: 100000,
  };

  // Disabled in settings: false
  assert.equal(shouldShowTip({ ...base, showTipsPreference: false, hasError: false }), false);

  // During error: false
  assert.equal(shouldShowTip({ ...base, showTipsPreference: true, hasError: true }), false);
});

test("shouldShowTip suppresses tip if user typed in the last 10 seconds", () => {
  const now = 50000;
  // User typed 5 seconds ago (<10s): false
  assert.equal(
    shouldShowTip({
      assistantCount: 3,
      showTipsPreference: true,
      lastTypedTimestamp: now - 5000,
      now,
      hasError: false,
    }),
    false
  );

  // User typed 15 seconds ago (>=10s): true
  assert.equal(
    shouldShowTip({
      assistantCount: 3,
      showTipsPreference: true,
      lastTypedTimestamp: now - 15000,
      now,
      hasError: false,
    }),
    true
  );
});

test("selectNextTip rotates and never shows the same tip twice in a row", () => {
  let lastTipId = null;
  const history = [];

  for (let i = 0; i < 10; i++) {
    const tip = selectNextTip({ lastTipId, isTouch: false, isMac: false });
    assert.ok(tip);
    assert.notEqual(tip.id, lastTipId, "Tip should never equal previous tip");
    lastTipId = tip.id;
    history.push(tip.id);
  }

  // Ensure diversity in history
  const uniqueInHistory = new Set(history);
  assert.ok(uniqueInHistory.size >= 3, "Tips should rotate across multiple options");
});

test("selectNextTip skips keyboard shortcuts on touch devices", () => {
  const seenIds = new Set();
  let lastTipId = null;

  for (let i = 0; i < 20; i++) {
    const tip = selectNextTip({ lastTipId, isTouch: true, isMac: false });
    assert.ok(tip);
    assert.notEqual(tip.id, "toggle_sidebar");
    assert.notEqual(tip.id, "focus_slash");
    lastTipId = tip.id;
    seenIds.add(tip.id);
  }

  // All seen tips must not be keyboard shortcuts
  for (const id of seenIds) {
    const original = AVAILABLE_TIPS.find((t) => t.id === id);
    assert.equal(original.isKeyboardShortcut, false);
  }
});

test("selectNextTip uses Cmd+B on macOS and Ctrl+B on other platforms", () => {
  const macTip = selectNextTip({ lastTipId: "topics_overview", isTouch: false, isMac: true });
  if (macTip.id === "toggle_sidebar") {
    assert.ok(macTip.text.includes("Cmd+B"));
  }

  const winTip = selectNextTip({ lastTipId: "topics_overview", isTouch: false, isMac: false });
  if (winTip.id === "toggle_sidebar") {
    assert.ok(winTip.text.includes("Ctrl+B"));
  }
});
