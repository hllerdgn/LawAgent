/**
 * Hallmark · Cobalt — Modern-Minimal Dev Tool
 * 
 * Cool engineered paper, one electric cobalt signal accent, code-as-hero.
 * Space Grotesk 500/600, hairline borders, zero drop-shadows.
 * 
 * Axes:
 *   paper=light (cool ~250) · display=grotesk-sans · accent=cool (electric cobalt H256)
 * 
 * Spec: .agents/skills/hallmark/references/themes/cobalt.md
 */

import type { ThemeConfig } from '../types';

export const cobaltTheme: ThemeConfig = {
  id: 'cobalt',
  className: 'theme-cobalt',
  displayName: 'Cobalt — Kurumsal / Geliştirici',
  description: 'Profesyonel kurumsal tema. Serin beyaz zemin, tek elektrik mavisi vurgu, hairline yapısı.',
  genre: 'modern-minimal',
  paperBand: 'light',

  colors: {
    paper:       'oklch(98.5% 0.004 250)', // engineered near-white — never #fff
    paper2:      'oklch(96% 0.006 252)',
    ink:         'oklch(24% 0.02 258)',    // cool charcoal
    ink2:        'oklch(34% 0.018 257)',   // body text
    muted:       'oklch(54% 0.014 255)',
    accent:      'oklch(58% 0.20 256)',    // electric cobalt — THE signal
    accentDeep:  'oklch(48% 0.22 256)',   // hover state
    accent2:     'oklch(72% 0.10 256)',   // soft cobalt tint (links)
    glow:        'oklch(58% 0.20 256 / 0.12)',
    paperEmit:   'oklch(58% 0.20 256 / 0.04)',
    rule:        'oklch(88% 0.006 252)',   // hairline border — very light
    rule2:       'oklch(93% 0.004 250)',   // even lighter hairline
    ruleBlueprint: 'oklch(88% 0.006 252 / 0.50)',
    focusRing:   'oklch(58% 0.20 256)',
  },

  typography: {
    fontDisplay: "'Space Grotesk', 'Inter', ui-sans-serif, system-ui, sans-serif",
    fontBody:    "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontMono:    "'JetBrains Mono', 'Fira Mono', ui-monospace, monospace",
  },

  radius: {
    sm:   '4px',
    md:   '6px',      // "drawn with a ruler"
    lg:   '10px',     // code cards
    xl:   '12px',
    pill: '9999px',
  },

  motion: {
    durFast:   '150ms',
    durBase:   '220ms',
    durSlow:   '400ms',
    durReveal: '320ms',
    easeSoft:  'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
    easeOut:   'cubic-bezier(0.16, 1, 0.3, 1)',
    easeInOut: 'cubic-bezier(0.65, 0, 0.35, 1)',
    enabled:   true,
  },

  shadows: {
    card:  '0 1px 2px oklch(0% 0 0 / 0.06)',   // barely-there lift
    hover: '0 2px 8px oklch(0% 0 0 / 0.08)',
  },
};
