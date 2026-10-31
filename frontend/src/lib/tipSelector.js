/**
 * tipSelector.js - Logic for quiet contextual tips shown near the composer.
 */

export const AVAILABLE_TIPS = [
  {
    id: "toggle_sidebar",
    isKeyboardShortcut: true,
    getText: (isMac) => `Press ${isMac ? "Cmd+B" : "Ctrl+B"} to toggle the sidebar`,
  },
  {
    id: "topics_overview",
    isKeyboardShortcut: false,
    getText: () => "Ask about fees, syllabus, eligibility, or admissions",
  },
  {
    id: "programme_buttons",
    isKeyboardShortcut: false,
    getText: () => "Click any programme button to narrow the answer",
  },
  {
    id: "focus_slash",
    isKeyboardShortcut: true,
    getText: () => "Use / to focus the question box",
  },
  {
    id: "export_settings",
    isKeyboardShortcut: false,
    getText: () => "Export or clear chat history from Settings",
  },
];

export function shouldShowTip({
  assistantCount,
  showTipsPreference = true,
  lastTypedTimestamp = 0,
  now = Date.now(),
  hasError = false,
}) {
  if (!showTipsPreference) return false;
  if (hasError) return false;
  if (assistantCount < 3) return false;
  if ((assistantCount - 3) % 4 !== 0) return false;
  if (now - lastTypedTimestamp < 10000) return false;
  return true;
}

export function selectNextTip({
  lastTipId = null,
  isTouch = false,
  isMac = false,
}) {
  const eligible = AVAILABLE_TIPS.filter((t) => !(isTouch && t.isKeyboardShortcut));
  if (eligible.length === 0) return null;

  const pool = eligible.filter((t) => t.id !== lastTipId);
  const candidates = pool.length > 0 ? pool : eligible;

  let nextTip = candidates[0];
  if (lastTipId) {
    const lastIdx = eligible.findIndex((t) => t.id === lastTipId);
    if (lastIdx !== -1) {
      for (let i = 1; i <= eligible.length; i++) {
        const candidate = eligible[(lastIdx + i) % eligible.length];
        if (candidate.id !== lastTipId) {
          nextTip = candidate;
          break;
        }
      }
    }
  }

  return {
    id: nextTip.id,
    text: nextTip.getText(isMac),
  };
}
