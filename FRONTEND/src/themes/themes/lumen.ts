/**
 * Hallmark · Lumen — Day Foundry (Default Drop)
 * 
 * tokens.css değerleriyle birebir aynı.
 * Day Foundry: Cool-bone canvas, deep violet-indigo accent, refraction physics.
 * 
 * Axes:
 *   paper=light · display=classical-serif-lowercase · accent=cool (H268)
 */

import type { ThemeConfig } from '../types';

export const lumenTheme: ThemeConfig = {
  id: 'lumen',
  className: 'theme-lumen',
  displayName: 'Lumen — AI Araç Teması',
  description: 'Premium AI araç teması. Serin kemik zemin, derin indigo vurgu, lowercase klasik serif.',
  genre: 'atmospheric',
  paperBand: 'light',

  colors: {
    // ── tokens.css ile birebir eşleşme ─────────────────────────────────────
    paper:       'oklch(97% 0.008 265)',    // --color-paper
    paper2:      'oklch(94% 0.010 265)',    // --color-paper-2
    ink:         'oklch(18% 0.014 265)',    // --color-ink
    ink2:        'oklch(38% 0.012 265)',    // --color-ink-2
    muted:       'oklch(55% 0.010 265)',    // --color-muted
    accent:      'oklch(46% 0.24 268)',     // --color-accent
    accentDeep:  'oklch(36% 0.22 268)',     // --color-accent-deep
    accent2:     'oklch(68% 0.16 18)',      // --color-accent-2 (coral)
    glow:        'oklch(58% 0.22 268 / 0.28)', // --color-glow
    paperEmit:   'oklch(46% 0.24 268 / 0.03)', // --color-paper-emit
    rule:        'oklch(18% 0.014 265 / 0.12)', // --color-rule
    rule2:       'oklch(18% 0.014 265 / 0.06)', // --color-rule-2
    ruleBlueprint: 'oklch(18% 0.014 265 / 0.05)', // --rule-blueprint
    focusRing:   'oklch(46% 0.24 268)',    // --color-focus-ring
  },

  typography: {
    fontDisplay: "'Instrument Serif', 'Tiempos Headline', ui-serif, Georgia, serif",
    fontBody:    "'Geist', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontMono:    "'JetBrains Mono', 'Fira Mono', ui-monospace, 'Courier New', monospace",
  },

  radius: {
    sm:   '4px',
    md:   '8px',
    lg:   '12px',
    xl:   '16px',
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
    card:  '0 24px 60px -28px oklch(0% 0 0 / 0.10)',
    hover: '0 28px 64px -24px oklch(0% 0 0 / 0.14)',
  },
};
