import type { MatchFrameConfig, Segment, Shot } from '../config/types';

/** One shot variant as it appears on screen. */
export interface Cut {
  shot: Shot;
  variant: 'a' | 'b';
}

/** A cut placed on the timeline. */
export interface TimedCut extends Cut {
  from: number;
  frames: number;
}

/** Shots expanded into their A/B cut order. */
export const expandShots = (shots: Shot[]): Cut[] =>
  shots.flatMap((shot) =>
    shot.pair === false
      ? [{ shot, variant: 'a' as const }]
      : [
          { shot, variant: 'a' as const },
          { shot, variant: 'b' as const },
        ],
  );

/** Frames per cut for a tempo. 150 BPM at 16ths (4 cuts/beat) and 30fps = 3 frames. */
export const beatFrames = (bpm: number, cutsPerBeat: number, fps: number) => (fps * 60) / (bpm * cutsPerBeat);

const findCut = (cuts: Cut[], ref: string | undefined): Cut => {
  if (!ref) return cuts[0];
  const [id, variant = 'a'] = ref.split(':');
  const hit = cuts.find((c) => c.shot.id === id && c.variant === variant);
  if (!hit) throw new Error(`hold.cut "${ref}" matches no shot`);
  return hit;
};

/** Cut lengths for one segment, rounded cumulatively so fractional lengths don't drift. */
const segmentLengths = (seg: Exclude<Segment, { kind: 'hold' }>): number[] => {
  if (seg.kind === 'lengths') return seg.frames;
  const raw: number[] = [];
  for (let i = 0; i < seg.cuts; i++) {
    if (seg.kind === 'steady') {
      raw.push(seg.frames);
    } else {
      const t = seg.cuts === 1 ? 1 : i / (seg.cuts - 1);
      const e = seg.ease === 'linear' ? t : t * t;
      raw.push(seg.from + (seg.to - seg.from) * e);
    }
  }
  const out: number[] = [];
  let acc = 0;
  let placed = 0;
  for (const r of raw) {
    acc += r;
    const len = Math.max(1, Math.round(acc) - placed);
    out.push(len);
    placed += len;
  }
  return out;
};

export const buildTimeline = (config: MatchFrameConfig): TimedCut[] => {
  const cuts = expandShots(config.shots);
  if (cuts.length === 0) throw new Error('No shots in config');
  const out: TimedCut[] = [];
  let frame = 0;
  let next = 0;
  for (const seg of config.rhythm) {
    if (seg.kind === 'hold') {
      out.push({ ...findCut(cuts, seg.cut), from: frame, frames: seg.frames });
      frame += seg.frames;
      continue;
    }
    for (const len of segmentLengths(seg)) {
      out.push({ ...cuts[next % cuts.length], from: frame, frames: len });
      next++;
      frame += len;
    }
  }
  return out;
};

export const timelineDuration = (timeline: TimedCut[]) =>
  timeline.reduce((sum, c) => sum + c.frames, 0);

export const cutAt = (timeline: TimedCut[], frame: number): TimedCut => {
  for (let i = timeline.length - 1; i >= 0; i--) {
    if (frame >= timeline[i].from) return timeline[i];
  }
  return timeline[0];
};
