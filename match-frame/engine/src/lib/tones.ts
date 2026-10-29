import type { BrandConfig, Tone, Treatment } from '../config/types';

export interface Scheme {
  bg: string;
  fg: string;
  /** Faint line/detail colour on bg. */
  line: string;
  /** True when bg is dark, for lighting choices. */
  dark: boolean;
}

const withAlpha = (hex: string, a: number) => {
  const h = hex.replace('#', '');
  const n = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h, 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
};

export const alpha = withAlpha;

const rgb = (hex: string): [number, number, number] => {
  const h = hex.replace('#', '');
  const n = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
};

const luminance = (hex: string) => {
  const [r, g, b] = rgb(hex);
  return (0.3 * r + 0.59 * g + 0.11 * b) / 255;
};

/** Blend two hex colours: t=0 → a, t=1 → b. */
export const mix = (a: string, b: string, t: number) => {
  const [r1, g1, b1] = rgb(a);
  const [r2, g2, b2] = rgb(b);
  const m = (x: number, y: number) => Math.round(x + (y - x) * t);
  return `rgb(${m(r1, r2)}, ${m(g1, g2)}, ${m(b1, b2)})`;
};

export const scheme = (brand: BrandConfig, tone: Tone): Scheme => {
  const c = brand.colors;
  const [bg, fg] =
    tone === 'light' ? [c.paper, c.ink] : tone === 'dark' ? [c.ink, c.paper] : tone === 'brand' ? [c.primary, c.onPrimary] : [c.accent, c.onAccent];
  return { bg, fg, line: withAlpha(fg, 0.55), dark: luminance(bg) < 0.45 };
};

/** Default B tone: whichever of light/dark contrasts most with A's background. */
export const oppositeTone = (brand: BrandConfig, tone: Tone): Tone => (scheme(brand, tone).dark ? 'light' : 'dark');

export const toneFor = (brand: BrandConfig, shot: { tone?: Tone; toneB?: Tone }, variant: 'a' | 'b'): Tone => {
  const a = shot.tone ?? 'light';
  return variant === 'a' ? a : shot.toneB ?? oppositeTone(brand, a);
};

export const treatmentFilter = (t: Treatment): string | undefined =>
  ({
    mono: 'grayscale(1) contrast(1.08)',
    negative: 'grayscale(1) invert(1) contrast(1.05)',
    invert: 'invert(1) hue-rotate(180deg)',
    dim: 'grayscale(0.4) brightness(0.55)',
    none: undefined,
  })[t];
