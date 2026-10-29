/**
 * Field reference for match-frame configs.
 *
 * A reel is a list of SHOTS (scenes) played through a RHYTHM (cut lengths).
 * Each shot becomes a pair of cuts by default: variant A, then variant B
 * (light/dark swap for procedural shots, mono/negative treatment for photos).
 */

/** Background/foreground scheme for procedural shots. */
export type Tone = 'light' | 'dark' | 'brand' | 'accent';

/** How variant B of a photo shot differs from A (ignored when `srcB` is set). */
export type Treatment = 'mono' | 'negative' | 'invert' | 'dim' | 'none';

/** Procedural surface materials. */
export type Material = 'flat' | 'concrete' | 'paper' | 'plaster' | 'metal' | 'gradient';

/** How the logo sits on a textured surface. */
export type Finish = 'flat' | 'emboss' | 'deboss';

export interface BrandConfig {
  name: string;
  tagline?: string;
  /** Single-colour SVG in public/. Its fills are overridden per shot. */
  logo: string;
  colors: {
    /** Near-black used for dark tones and ink. */
    ink: string;
    /** Near-white used for light tones. */
    paper: string;
    /** Main brand colour (the "brand" tone background). */
    primary: string;
    /** Logo/text colour on top of `primary`. */
    onPrimary: string;
    /** Second brand colour (the "accent" tone background). */
    accent: string;
    /** Logo/text colour on top of `accent`. */
    onAccent: string;
  };
  /** Key from src/lib/fonts.ts. */
  font: string;
}

/** The match point: where the mark sits in every cut. Fractions of the frame. */
export interface MatchPoint {
  x: number;
  y: number;
  /** Logo width as a fraction of frame width. */
  width: number;
}

interface ShotBase {
  id: string;
  /** Emit a B variant after A. Default true. */
  pair?: boolean;
  /** Logo size multiplier relative to the match-point width. Default 1. */
  logoScale?: number;
}

interface ToneShot extends ShotBase {
  /** Tone of variant A. Default 'light'. */
  tone?: Tone;
  /** Tone of variant B. Default: light or dark, whichever contrasts with A. */
  toneB?: Tone;
  /** Make B a filtered copy of A (e.g. 'mono') instead of a tone swap. */
  treatment?: Treatment;
  /** Mockups only: tone of the object (card, tile, badge, sign). Default 'brand', or 'dark' on a brand background. */
  objectTone?: Tone;
}

/** Logo on a material: concrete wall, paper, brushed metal, flat colour, soft gradient. */
export interface SurfaceShot extends ToneShot {
  kind: 'surface';
  material?: Material;
  finish?: Finish;
  /** Diagonal window-light shadow across the surface. */
  shadow?: boolean;
  /** Hide the logo (pure texture beat). */
  noLogo?: boolean;
}

/** Logo construction drawing. 'keyline' = icon grid; 'guides' = full-bleed rules + dots. */
export interface GridShot extends ToneShot {
  kind: 'grid';
  variant?: 'keyline' | 'guides';
}

/** The mark tiled as a signature pattern. */
export interface PatternShot extends ToneShot {
  kind: 'pattern';
  /** Tile width as a fraction of frame width. Default 0.16. */
  tile?: number;
  /** Field rotation in degrees. Default -18. */
  rotate?: number;
}

/** Logo + name + tagline. */
export interface LockupShot extends ToneShot {
  kind: 'lockup';
  layout?: 'stacked' | 'inline';
}

/** Business cards lying on a surface. */
export interface CardShot extends ToneShot {
  kind: 'card';
  material?: Material;
}

/** App icon tile. */
export interface AppIconShot extends ToneShot {
  kind: 'app-icon';
}

/** ID badge hanging from a lanyard. */
export interface BadgeShot extends ToneShot {
  kind: 'badge';
  person?: string;
  role?: string;
}

/** Free-standing signage totem in a studio space. */
export interface SignShot extends ToneShot {
  kind: 'sign';
}

/** Interface chips / buttons in brand colours. */
export interface UiShot extends ToneShot {
  kind: 'ui';
  labels?: string[];
}

/** A 9:16 photo (mockup render, inspiration image, product shot). */
export interface PhotoShot extends ShotBase {
  kind: 'photo';
  /** Path in public/. Prepare it at 1080x1920 so quads line up. */
  src: string;
  /** Explicit B image (e.g. the dark render of the same mockup). */
  srcB?: string;
  treatment?: Treatment;
  /** Film grain over the image, 0 = off. Default 1. Clean CG renders read as photos with it. */
  grain?: number;
  /** Composite the logo onto the photo. */
  logo?: {
    /** Corners TL, TR, BR, BL as frame fractions. Omit to sit on the match point. */
    quad?: [[number, number], [number, number], [number, number], [number, number]];
    color?: string;
    blend?: 'normal' | 'multiply' | 'screen' | 'overlay';
    opacity?: number;
  };
}

export type Shot =
  | SurfaceShot
  | GridShot
  | PatternShot
  | LockupShot
  | CardShot
  | AppIconShot
  | BadgeShot
  | SignShot
  | UiShot
  | PhotoShot;

/** Rhythm segments, played in order. Cuts walk through the expanded shot list, wrapping. */
export type Segment =
  /** `cuts` cuts of `frames` each. Fractional frames are spread by cumulative rounding (BPM sync). */
  | { kind: 'steady'; cuts: number; frames: number }
  /** Cut length eases from `from` to `to` frames: the slow-down into the end card. */
  | { kind: 'ramp'; cuts: number; from: number; to: number; ease?: 'in' | 'linear' }
  /** Explicit cut lengths, e.g. a music track's hits from `npm run cuts`. */
  | { kind: 'lengths'; frames: number[] }
  /** One long cut. `cut` = "<shotId>" or "<shotId>:b". Default: the very first cut, so the loop is seamless. */
  | { kind: 'hold'; frames: number; cut?: string };

export interface MatchFrameConfig {
  fps: number;
  width: number;
  height: number;
  brand: BrandConfig;
  match: MatchPoint;
  shots: Shot[];
  rhythm: Segment[];
  audio?: {
    music?: string;
    /** Seconds into the music file where the reel starts (put the drop on frame 0). */
    startFrom?: number;
    volume?: number;
  };
}
