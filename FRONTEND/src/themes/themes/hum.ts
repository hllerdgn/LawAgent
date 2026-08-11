/**
 * Hallmark · Hum — Playful Vibrant
 * 
 * Cream paper, multi-accent (pear-yellow + sky-cyan + coral-red).
 * Plus Jakarta Sans, rounded surfaces, lifting shadows.
 * 
 * Axes:
 *   paper=light (warm cream ~95°) · display=rounded-sans · accent=multi
 * 
 * Spec: .agents/skills/hallmark/references/themes/hum.md
 */

import type { ThemeConfig } from '../types';

export const humTheme: ThemeConfig = {
  id: 'hum',
  className: 'theme-hum',
  displayName: 'Hum — Canlı ve Oyunsu',
  description: 'Sıcak ve canlı tema. Krem zemin, çoklu vurgu renkleri, yuvarlatılmış yüzeyler.',
  genre: 'playful',
  paperBand: 'light',

  colors: {
    paper:       'oklch(97% 0.012 95)',    // cream, pear-yellow pull
    paper2:      'oklch(94% 0.016 95)',    // tinted band
    ink:         'oklch(20% 0.012 250)',   // near-black with cool tilt
    ink2:        'oklch(36% 0.010 250)',
    muted:       'oklch(56% 0.008 250)',
    accent:      'oklch(86% 0.18 95)',     // pear-yellow (primary CTA)
    accentDeep:  'oklch(78% 0.20 90)',     // pear hover
    accent2:     'oklch(66% 0.18 235)',    // sky-cyan (secondary — links, hover)
    glow:        'oklch(86% 0.18 95 / 0.20)',
    paperEmit:   'oklch(86% 0.18 95 / 0.10)',
    rule:        'oklch(88% 0.010 95)',
    rule2:       'oklch(92% 0.008 95)',
    ruleBlueprint: 'oklch(88% 0.010 95 / 0.40)',
    focusRing:   'oklch(66% 0.18 235)',    // cyan focus ring
  },

  typography: {
    fontDisplay: "'Plus Jakarta Sans', 'Open Runde', 'Geist', ui-sans-serif, system-ui, sans-serif",
    fontBody:    "'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    fontMono:    "'JetBrains Mono', 'Fira Mono', ui-monospace, monospace",
  },

  radius: {
    sm:   '8px',
    md:   '12px',
    lg:   '20px',    // generous radii — Hum signature
    xl:   '28px',
    pill: '9999px',
  },

  motion: {
    durFast:   '130ms',
    durBase:   '220ms',
    durSlow:   '380ms',
    durReveal: '300ms',
    easeSoft:  'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
    easeOut:   'cubic-bezier(0.16, 1, 0.3, 1)',
    easeInOut: 'cubic-bezier(0.65, 0, 0.35, 1)',
    enabled:   true,
  },

  shadows: {
    card:  '0 4px 24px -4px oklch(20% 0.012 250 / 0.10)', // soft lifting shadow
    hover: '0 8px 32px -4px oklch(20% 0.012 250 / 0.14)',
  },
};
