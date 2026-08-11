import React, { createContext, useContext, useEffect, useState, useMemo } from 'react';
import type { HallmarkThemeId, ThemeConfig } from './types';
import { resolveTheme, DEFAULT_THEME_ID } from './registry';

interface ThemeContextType {
  theme: ThemeConfig;
  themeId: HallmarkThemeId;
  setThemeId: (id: HallmarkThemeId) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

/**
 * ThemeConfig nesnesinden CSS değişkenlerini üretir ve belirtilen elemene uygular.
 */
export function applyThemeToElement(theme: ThemeConfig, element: HTMLElement = document.documentElement) {
  const { colors, typography, radius, motion, shadows } = theme;

  // Class override (eski theme-* class'ını kaldır, yenisini ekle)
  element.classList.forEach((cls) => {
    if (cls.startsWith('theme-')) element.classList.remove(cls);
  });
  element.classList.add(theme.className);

  // CSS variables injection
  const style = element.style;
  style.setProperty('--color-paper', colors.paper);
  style.setProperty('--color-paper-2', colors.paper2);
  style.setProperty('--color-ink', colors.ink);
  style.setProperty('--color-ink-2', colors.ink2);
  style.setProperty('--color-muted', colors.muted);
  style.setProperty('--color-accent', colors.accent);
  style.setProperty('--color-accent-deep', colors.accentDeep);
  style.setProperty('--color-accent-2', colors.accent2);
  style.setProperty('--color-glow', colors.glow);
  style.setProperty('--color-paper-emit', colors.paperEmit);
  style.setProperty('--color-rule', colors.rule);
  style.setProperty('--color-rule-2', colors.rule2);
  style.setProperty('--rule-blueprint', colors.ruleBlueprint);
  style.setProperty('--color-focus-ring', colors.focusRing);

  style.setProperty('--font-display', typography.fontDisplay);
  style.setProperty('--font-body', typography.fontBody);
  style.setProperty('--font-label', typography.fontMono);

  style.setProperty('--radius-sm', radius.sm);
  style.setProperty('--radius-md', radius.md);
  style.setProperty('--radius-lg', radius.lg);
  style.setProperty('--radius-xl', radius.xl);
  style.setProperty('--radius-pill', radius.pill);

  style.setProperty('--dur-fast', motion.durFast);
  style.setProperty('--dur-base', motion.durBase);
  style.setProperty('--dur-slow', motion.durSlow);
  style.setProperty('--dur-reveal', motion.durReveal);
  style.setProperty('--ease-soft', motion.easeSoft);
  style.setProperty('--ease-out', motion.easeOut);
  style.setProperty('--ease-in-out', motion.easeInOut);

  style.setProperty('--shadow-card', shadows.card);
  style.setProperty('--shadow-hover', shadows.hover);
}

interface ThemeProviderProps {
  initialThemeId?: HallmarkThemeId;
  children: React.ReactNode;
}

export function ThemeProvider({ initialThemeId = DEFAULT_THEME_ID, children }: ThemeProviderProps) {
  const [themeId, setThemeId] = useState<HallmarkThemeId>(initialThemeId);

  const theme = useMemo(() => resolveTheme(themeId), [themeId]);

  useEffect(() => {
    applyThemeToElement(theme);
  }, [theme]);

  const value = useMemo(
    () => ({
      theme,
      themeId,
      setThemeId,
    }),
    [theme, themeId]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextType {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme, bir ThemeProvider içerisinde kullanılmalıdır.');
  }
  return context;
}
