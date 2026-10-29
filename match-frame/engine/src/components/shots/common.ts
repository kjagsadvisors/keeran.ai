import type { MatchFrameConfig, Tone } from '../../config/types';
import { scheme } from '../../lib/tones';

export interface ShotProps<T> {
  shot: T;
  config: MatchFrameConfig;
  /** Resolved tone for this variant. */
  tone: Tone;
}

/** Match-point geometry in frame px. */
export const matchPx = (config: MatchFrameConfig, logoScale = 1) => ({
  x: config.match.x * config.width,
  y: config.match.y * config.height,
  w: config.match.width * config.width * logoScale,
});

/** Mockup object colours: brand by default, dark when the background is already the brand colour. */
export const objectScheme = (config: MatchFrameConfig, tone: Tone, objectTone?: Tone) =>
  scheme(config.brand, objectTone ?? (tone === 'brand' ? 'dark' : 'brand'));
