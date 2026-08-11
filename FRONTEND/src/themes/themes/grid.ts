/**
 * Hallmark · Grid — Swiss Neo-Grotesque
 * 
 * Exposed 12-column hairline grid, Archivo 800 lowercase display.
 * Cool near-white paper, one signal ink (red default).
 * Zero cards, zero drop-shadows — hairlines do all the structure.
 * 
 * Axes:
 *   paper=light (cool ~255) · display=grotesk-heavy · accent=signal red (default)
 * 
 * Spec: .agents/skills/hallmark/references/themes/grid.md
 */

import type { ThemeConfig } from '../types';

export const gridTheme: ThemeConfig = {
  id: 'grid',
  className: 'theme-grid',
  displayName: 'Grid — İsviçre Tasarım Sistemi',
  description: 'Kurumsal İsviçre ekolü. Açık grid yapısı, tek sinyal rengi, sıfır kart gölgesi.',
  genre: 'editorial',
  paperBand: 'light',

  colors: {
    paper:       'oklch(99% 0.003 255)',   // cool near-white — never #fff
    paper2:      'oklch(97.2% 0.004 255)',
    ink:         'oklch(16% 0.010 255)',   // cool near-black
    ink2:        'oklch(30% 0.008 255)',
    muted:       'oklch(52% 0.006 255)',
    accent:      'oklch(55% 0.21 28)',     // signal red (default ink)
    accentDeep:  'oklch(44% 0.22 26)',     // hover
    accent2:     'oklch(45% 0.19 264)',    // ultramarine (alternative signal)
    glow:        'oklch(55% 0.21 28 / 0.10)',
    paperEmit:   'oklch(55% 0.21 28 / 0.04)',
    rule:        'oklch(16% 0.010 255 / 0.14)', // 1px hairline
    rule2:       'oklch(16% 0.010 255 / 0.06)',
    ruleBlueprint: 'oklch(16% 0.010 255 / 0.08)',
    focusRing:   'oklch(55% 0.21 28)',
  },

  typography: {
    // Archivo only — Swiss discipline from weight/scale/tracking, not second family
    fontDisplay: "'Archivo', 'Arial Black', ui-sans-serif, system-ui, sans-serif",
    fontBody:    "'Archivo', 'Arial', ui-sans-serif, sans-serif",
    fontMono:    "'Archivo', ui-sans-serif, sans-serif", // no mono — Archivo label voice used
  },

  radius: {
    sm:   '0px',  // zero radius — Grid theme rule
    md:   '0px',
    lg:   '0px',
    xl:   '0px',
    pill: '0px',   // no pills in Grid
  },

  motion: {
    durFast:   '150ms',
    durBase:   '220ms',
    durSlow:   '400ms',
    durReveal: '300ms',
    easeSoft:  'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
    easeOut:   'cubic-bezier(0.16, 1, 0.3, 1)',
    easeInOut: 'cubic-bezier(0.65, 0, 0.35, 1)',
    enabled:   true,
  },

  shadows: {
    card:  'none',  // zero shadows — hairlines do the work
    hover: 'none',
  },
};
