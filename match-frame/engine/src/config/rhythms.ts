import type { Segment } from './types';

/**
 * Rhythm presets measured from reference reels (30fps). Pass the number of cuts
 * in your expanded shot list (pairs × 2) so passes line up with the list.
 */
export const rhythms = {
  /**
   * Constant strobe: every cut holds `frames` (3 = 10 cuts/s), the list plays `passes`
   * times, then a short hold on the opening cut. Reference: a 5.7s identity reel
   * (34 cuts × 3 frames, 1.7 passes, ~8-frame end hold).
   */
  steady: ({ cuts, frames = 3, passes = 2, hold = 8 }: { cuts: number; frames?: number; passes?: number; hold?: number }): Segment[] => [
    { kind: 'steady', cuts: Math.round(cuts * passes), frames },
    { kind: 'hold', frames: hold },
  ],

  /**
   * Fast open that brakes into the end card: 2-frame cuts, then 3-frame, then cut lengths
   * ease from 3 up to 16 frames and land on a long hold. Reference: an 8.1s academy
   * identity reel (15×2f, 10×3f, ~22 cuts easing 3→16f, 24f hold).
   */
  rampDown: ({ fast = 15, mid = 10, ramp = 22, to = 16, hold = 24 } = {}): Segment[] => [
    { kind: 'steady', cuts: fast, frames: 2 },
    { kind: 'steady', cuts: mid, frames: 3 },
    { kind: 'ramp', cuts: ramp, from: 3, to, ease: 'in' },
    { kind: 'hold', frames: hold },
  ],

  /**
   * Every cut on a hit of the music: `lengths` from `npm run cuts -- <track> --out <json>`.
   * The last length is the end hold, running to the track's final hit so the loop restarts on it.
   */
  fromTrack: ({ lengths }: { lengths: number[] }): Segment[] => [
    { kind: 'lengths', frames: lengths.slice(0, -1) },
    { kind: 'hold', frames: lengths[lengths.length - 1] },
  ],
};
