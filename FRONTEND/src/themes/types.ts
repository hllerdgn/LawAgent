/**
 * LawAgent — Hallmark Theme System
 * 
 * ThemeConfig: Type-safe theme definition.
 * Mevcut tokens.css / lumen.css yapısıyla birebir örtüşür.
 */

export interface ThemeColors {
  /** Ana arka plan rengi (paper) */
  paper: string;
  /** İkincil yüzey (input, card bg) */
  paper2: string;
  /** Birincil metin rengi */
  ink: string;
  /** İkincil metin rengi */
  ink2: string;
  /** Soluk/muted metin */
  muted: string;
  /** Birincil vurgu rengi */
  accent: string;
  /** Vurgu hover state */
  accentDeep: string;
  /** İkincil vurgu (verb landmark) */
  accent2: string;
  /** Glow efekti */
  glow: string;
  /** Canvas wash */
  paperEmit: string;
  /** Hairline / border */
  rule: string;
  /** Çok hafif border */
  rule2: string;
  /** Blueprint grid hairline */
  ruleBlueprint: string;
  /** Focus ring */
  focusRing: string;
}

export interface ThemeTypography {
  /** Display/Heading font (serif, display vb.) */
  fontDisplay: string;
  /** Body font */
  fontBody: string;
  /** Monospace / label font */
  fontMono: string;
}

export interface ThemeRadius {
  sm: string;
  md: string;
  lg: string;
  xl: string;
  pill: string;
}

export interface ThemeMotion {
  durFast: string;
  durBase: string;
  durSlow: string;
  durReveal: string;
  easeSoft: string;
  easeOut: string;
  easeInOut: string;
  /** Animasyonlar aktif mi? */
  enabled: boolean;
}

export interface ThemeShadows {
  card: string;
  hover: string;
}

export interface ThemeConfig {
  /** Unique tema kimliği — HallmarkThemeId ile eşleşmeli */
  id: HallmarkThemeId;

  /**
   * CSS class name that is added to the root element.
   * lumen → "theme-lumen", cobalt → "theme-cobalt" vb.
   * CSS'deki .theme-* kurallarıyla eşleşir.
   */
  className: string;

  /** İnsan-okunabilir tema adı (admin panel dropdown'da görünür) */
  displayName: string;

  /** Kısa açıklama (admin panel tooltip'i) */
  description: string;

  /** Hangi Hallmark genre'ına ait */
  genre: 'editorial' | 'atmospheric' | 'modern-minimal' | 'playful';

  /** Paper band: light/mid/dark (tema çakışma tespiti için) */
  paperBand: 'light' | 'mid' | 'dark';

  colors: ThemeColors;
  typography: ThemeTypography;
  radius: ThemeRadius;
  motion: ThemeMotion;
  shadows: ThemeShadows;
}

// ─── Hallmark Theme IDs ──────────────────────────────────────────────────────
// Spec dosyası olan 5 tema (tam implementasyon)
export type ImplementedThemeId =
  | 'lumen'
  | 'carnival'
  | 'cobalt'
  | 'hum'
  | 'grid';

// Spec dosyası olmayan 16 tema (tip sisteme ekli, henüz token yok)
export type PlannedThemeId =
  | 'specimen'
  | 'atelier'
  | 'brutal'
  | 'newsprint'
  | 'studio'
  | 'manifesto'
  | 'terminal'
  | 'midnight'
  | 'almanac'
  | 'garden'
  | 'riso'
  | 'sport'
  | 'bloom'
  | 'coral'
  | 'aurora'
  | 'editorial';

export type HallmarkThemeId = ImplementedThemeId | PlannedThemeId;

/** Tema adlarını client admin panelinde göstermek için */
export const THEME_DISPLAY_NAMES: Record<ImplementedThemeId, string> = {
  lumen:    'Lumen — AI Araç Teması (Gece/Gündüz)',
  carnival: 'Carnival — Editoryal Maksimalist',
  cobalt:   'Cobalt — Kurumsal / Geliştirici',
  hum:      'Hum — Canlı ve Oyunsu',
  grid:     'Grid — İsviçre Tasarım Sistemi',
};

export const DEFAULT_THEME_ID: HallmarkThemeId = 'lumen';
