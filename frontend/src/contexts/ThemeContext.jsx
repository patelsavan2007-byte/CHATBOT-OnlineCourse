/**
 * ThemeContext — light/dark/system theme provider.
 * Persists preference to localStorage and respects system preference.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

const ThemeContext = createContext(null);
const STORAGE_KEY = "charusat_theme";

function getSystemTheme() {
  if (typeof window === "undefined") return "dark";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function ThemeProvider({ children }) {
  const [mode, setMode] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) || "dark";
    } catch {
      return "dark";
    }
  });

  const resolvedTheme = mode === "system" ? getSystemTheme() : mode;

  // Apply theme class to <html>
  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", resolvedTheme === "dark");
    root.classList.toggle("light", resolvedTheme === "light");

    // Also set a data attribute for CSS selectors
    root.setAttribute("data-theme", resolvedTheme);
  }, [resolvedTheme]);

  // Listen for system preference changes
  useEffect(() => {
    if (mode !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => {
      const root = document.documentElement;
      const resolved = mq.matches ? "dark" : "light";
      root.classList.toggle("dark", resolved === "dark");
      root.classList.toggle("light", resolved === "light");
      root.setAttribute("data-theme", resolved);
    };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [mode]);

  const setTheme = useCallback((newMode) => {
    setMode(newMode);
    try {
      localStorage.setItem(STORAGE_KEY, newMode);
    } catch {/* ignore */}
  }, []);

  const cycleTheme = useCallback(() => {
    setTheme(mode === "dark" ? "light" : mode === "light" ? "system" : "dark");
  }, [mode, setTheme]);

  const value = useMemo(
    () => ({ theme: mode, resolvedTheme, setTheme, cycleTheme }),
    [mode, resolvedTheme, setTheme, cycleTheme],
  );

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within a ThemeProvider");
  return ctx;
}

export default ThemeContext;
