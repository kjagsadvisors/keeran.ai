import skillshift from './cuts/skillshift.json';
import identity from './identity.json';
import { rhythms } from './rhythms';
import type { MatchFrameConfig, PhotoShot, Shot } from './types';

/*
 * SHOT SHEET — "Northfold" (sample interiors studio)
 *
 * 13 pairs → 26 cuts: 9 photoreal Blender renders (`npm run shots`) and 4 flat
 * brand frames. Every A is dark and every B light, so adjacent cuts always flip
 * luminance (the strobe). The mark sits on the match point in every cut.
 *
 *  #  id        source     A → B                                story beat
 *  1  relief    blender    raised in charcoal / white plaster   the mark as an object (also the end hold)
 *  2  cards     blender    foil on black / ink on white         first application
 *  3  wallsign  blender    steel letters / black letters        in the space
 *  4  grid      flat       keyline grid                         how it was drawn
 *  5  totem     blender    brand totem / white totem            exhibition
 *  6  phone     blender    app on walnut / on marble            digital
 *  7  pattern   flat       brand → light                        the system
 *  8  billboard blender    street banner against the sky        out in the world
 *  9  boxes     blender    packaging on black / white sweep     product
 * 10  lockup    flat       name + tagline                       say the name
 * 11  notebook  blender    foil on green cloth / blind deboss   craft
 * 12  glass     blender    etched glass partition               architecture
 * 13  guides    flat       full-bleed rules                     back to the drawing → loops to relief
 */

/** A Blender scene's A/B renders from public/shots/. */
const render = (id: string): PhotoShot => ({ id, kind: 'photo', src: `shots/${id}_a.jpg`, srcB: `shots/${id}_b.jpg` });

const shots: Shot[] = [
  render('relief'),
  render('cards'),
  render('wallsign'),
  { id: 'grid', kind: 'grid', tone: 'dark' },
  render('totem'),
  render('phone'),
  { id: 'pattern', kind: 'pattern', tone: 'brand' },
  render('billboard'),
  render('boxes'),
  { id: 'lockup', kind: 'lockup', tone: 'brand' },
  render('notebook'),
  render('glass'),
  { id: 'guides', kind: 'grid', variant: 'guides', tone: 'dark', toneB: 'accent' },
  // Your own mockup photo (1080×1920) with the mark mapped onto a blank surface:
  // { id: 'tote', kind: 'photo', src: 'shots/tote.jpg', treatment: 'negative',
  //   logo: { quad: [[0.41, 0.44], [0.63, 0.42], [0.64, 0.48], [0.43, 0.51]], color: '#141414', blend: 'multiply' } },
];

const cuts = shots.reduce((n, s) => n + (s.pair === false ? 1 : 2), 0);

export const config: MatchFrameConfig = {
  fps: 30,
  width: 1080,
  height: 1920,
  // Brand and match point live in identity.json so the Blender scenes read the same values.
  brand: identity.brand,
  match: identity.match,
  shots,
  // 52 cuts × 3f + a 12f hold = 168 frames, the length of the track.
  rhythm: rhythms.steady({ cuts, frames: 3, passes: 2, hold: 12 }),
  audio: {
    // Soundtrack of the steady reference reel (gitignored; the reel renders silent without it).
    music: 'audio/ref-streak.m4a',
    startFrom: 0,
    volume: 1,
  },
};

/** The same shots cut to the ramp reference's track: its slowing ticks set every cut (`npm run cuts`). */
export const rampConfig: MatchFrameConfig = {
  ...config,
  rhythm: rhythms.fromTrack(skillshift),
  audio: { music: skillshift.track, startFrom: skillshift.startFrom, volume: 1 },
};

/** One composition per entry: `npx remotion render src/index.ts <id> out/<id>.mp4`. */
export const variants = { MatchFrame: config, MatchFrameRamp: rampConfig };
export type Variant = keyof typeof variants;
