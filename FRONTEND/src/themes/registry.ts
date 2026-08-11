/**
 * LawAgent — Hallmark Theme Registry
 *
 * Tüm 5 implement edilmiş tema buradan export edilir.
 * resolveTheme() fonksiyonu client config'den gelen ID'yi ThemeConfig'e çevirir.
 */

import type { HallmarkThemeId, ImplementedThemeId, ThemeConfig } from './types';
export type { HallmarkThemeId, ImplementedThemeId, ThemeConfig };
export { DEFAULT_THEME_ID, THEME_DISPLAY_NAMES } from './types';

import { lumenTheme }   from './themes/lumen';
import { carnivalTheme } from './themes/carnival';
import { cobaltTheme }  from './themes/cobalt';
import { humTheme }     from './themes/hum';
import { gridTheme }    from './themes/grid';

/**
 * Implement edilmiş 5 Hallmark temasının registry'si.
 */
export const THEME_REGISTRY: Record<ImplementedThemeId, ThemeConfig> = {
  lumen:    lumenTheme,
  carnival: carnivalTheme,
  cobalt:   cobaltTheme,
  hum:      humTheme,
  grid:     gridTheme,
};

/**
 * HallmarkThemeId → ThemeConfig resolver.
 * Bilinmeyen veya henüz implement edilmemiş tema ID'si gelirse Lumen'e fallback yapılır.
 */
export function resolveTheme(themeId: HallmarkThemeId | string | undefined): ThemeConfig {
  if (!themeId) return lumenTheme;
  const theme = THEME_REGISTRY[themeId as ImplementedThemeId];
  if (!theme) {
    console.warn(`[ThemeRegistry] "${themeId}" teması henüz implement edilmedi. Lumen'e fallback yapılıyor.`);
    return lumenTheme;
  }
  return theme;
}

export function isImplemented(themeId: string): themeId is ImplementedThemeId {
  return themeId in THEME_REGISTRY;
}

export const IMPLEMENTED_THEMES = Object.values(THEME_REGISTRY);
