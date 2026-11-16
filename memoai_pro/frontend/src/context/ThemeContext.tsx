import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';

const THEME_KEY = 'memoai_theme';
/** Couleur de la barre d'état (mobile / application installée) : celle de la barre latérale. */
const STATUS_BAR = { light: '#092f2c', dark: '#061a20' };

function initialDark(): boolean {
  try {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored !== null) return JSON.parse(stored) === true;
  } catch { /* ignore */ }
  return typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-color-scheme: dark)').matches;
}

const ThemeContext = createContext<{ isDark: boolean; toggle: () => void }>({ isDark: false, toggle: () => undefined });

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [isDark, setIsDark] = useState(initialDark);

  useEffect(() => {
    document.documentElement.classList.toggle('dark-theme', isDark);
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', isDark ? STATUS_BAR.dark : STATUS_BAR.light);
    try { localStorage.setItem(THEME_KEY, JSON.stringify(isDark)); } catch { /* ignore */ }
  }, [isDark]);

  const toggle = useCallback(() => {
    // Transition douce uniquement pendant le changement de thème.
    const root = document.documentElement;
    root.classList.add('theme-transition');
    window.setTimeout(() => root.classList.remove('theme-transition'), 350);
    setIsDark(d => !d);
  }, []);

  return <ThemeContext.Provider value={{ isDark, toggle }}>{children}</ThemeContext.Provider>;
}

export const useTheme = () => useContext(ThemeContext);
