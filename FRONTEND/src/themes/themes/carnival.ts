/**
 * Hallmark · Carnival — Cold Snap (Default Drop)
 * 
 * Loud-maximalist editorial. Duo-tone: mustard + oxblood.
 * Warm pink-cream paper, Big Shoulders Display 800.
 * 
 * Axes:
 *   paper=light (tinted warm) · display=display-heavy · accent=warm/warm (duo-tone)
 * 
 * Spec: .agents/skills/hallmark/references/themes/carnival.md
 */

import type { ThemeConfig } from '../types';

export const carnivalTheme: ThemeConfig = {
  id: 'carnival',
  className: 'theme-carnival',
  displayName: 'Carnival — Editoryal Maksimalist',
  description: 'Cesur editoryal tema. Sıcak kremalı zemin, hardstop gölgeler, dekoratif süslemeler.',
  genre: 'editorial',
  paperBand: 'light',

  colors: {
    // Drop 01 — Cold Snap (default)
    paper:       'oklch(92% 0.045 50)',     // warm pink-cream
    paper2:      'oklch(88% 0.050 45)',
    ink:         'oklch(18% 0.080 20)',     // deep aubergine
    ink2:        'oklch(28% 0.060 25)',
    muted:       'oklch(45% 0.05 30)',
    accent:      'oklch(86% 0.18 95)',      // mustard (primary)
    accentDeep:  'oklch(78% 0.20 90)',      // mustard hover
    accent2:     'oklch(40% 0.21 25)',      // oxblood (secondary)
    glow:        'oklch(40% 0.21 25 / 0.15)',
    paperEmit:   'oklch(86% 0.18 95 / 0.08)',
    rule:        'oklch(40% 0.18 25)',      // oxblood rules (decorative)
    rule2:       'oklch(40% 0.18 25 / 0.40)',
    ruleBlueprint: 'oklch(18% 0.080 20 / 0.06)',
    focusRing:   'oklch(40% 0.21 25)',
  },

  typography: {
    fontDisplay: "'Big Shoulders Display', 'Impact', ui-sans-serif, system-ui, sans-serif",
    fontBody:    "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontMono:    "'JetBrains Mono', 'Fira Mono', ui-monospace, monospace",
  },

  radius: {
    sm:   '2px',
    md:   '4px',
    lg:   '6px',
    xl:   '8px',
    pill: '9999px',
  },

  motion: {
    durFast:   '120ms',
    durBase:   '200ms',
    durSlow:   '350ms',
    durReveal: '280ms',
    easeSoft:  'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
    easeOut:   'cubic-bezier(0.16, 1, 0.3, 1)',
    easeInOut: 'cubic-bezier(0.65, 0, 0.35, 1)',
    enabled:   true,
  },

  shadows: {
    card:  '4px 4px 0px 0px oklch(18% 0.080 20)',  // hard-offset shadow
    hover: '6px 6px 0px 0px oklch(18% 0.080 20)',
  },
};
