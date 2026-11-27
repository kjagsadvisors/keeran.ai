import React from 'react';
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig, staticFile, Img } from 'remotion';
import { loadFont as loadInter } from '@remotion/google-fonts/Inter';
import { loadFont as loadSerif } from '@remotion/google-fonts/InstrumentSerif';
import { loadFont as loadSourceSerif } from '@remotion/google-fonts/SourceSerif4';
import plan from './plan.json';

export const inter = loadInter('normal', { weights: ['400', '500', '600'] }).fontFamily;
export const serif = loadSerif().fontFamily;
export const bodySerif = loadSourceSerif('normal', { weights: ['400'] }).fontFamily;

export const C = {
  cream: '#f5f4f3', ink: '#0b0a0b', soft: '#9b9997', line: '#e4e2df', muted: '#8a8886',
  // the Claude app
  cPaper: '#FAF9F5', cInk: '#141413', cBorder: '#E1DFD6', cMuted: '#73726c', cChip: '#F0EEE6', cOrange: '#D97757',
  // the product
  accent: plan.brand.accent,
};

export const useT = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return frame / fps;
};

export const ease = Easing.bezier(0.22, 1, 0.36, 1);
export const k = (t: number, a: number, b: number, from = 0, to = 1, e = ease) =>
  interpolate(t, [a, b], [from, to], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: e });
export const lin = (x: number) => x;

/** Scale unit: 1 at 1080 px on the short side; a third bigger on 9:16 so the UI reads on a phone. */
export const useU = () => {
  const { width, height } = useVideoConfig();
  const vertical = height > width;
  return { u: (Math.min(width, height) / 1080) * (vertical ? 1.3 : 1), W: width, H: height, vertical };
};

// ── gradients: soft photographic blurs, the reference's backdrops ─────────────────────────────
type Palette = { base: string; blobs: [string, number, number, number, number][] }; // color, x%, y%, w%, h%
export const PALETTES: Record<string, Palette> = {
  blue: { base: '#b8c2ce', blobs: [['#6b78a2', 20, 70, 70, 60], ['#e3e8ec', 70, 25, 70, 55], ['#7c5670', 85, 90, 40, 35], ['#9fb0c4', 40, 20, 50, 40]] },
  plum: { base: '#c9a6b6', blobs: [['#3f1532', 30, 55, 55, 70], ['#9a4a72', 12, 30, 40, 45], ['#efdfe6', 78, 22, 60, 50], ['#b8748f', 70, 85, 50, 40]] },
  gold: { base: '#e7d7bf', blobs: [['#b88d5a', 25, 85, 70, 45], ['#f6efe3', 55, 40, 80, 45], ['#a9c1c9', 10, 10, 45, 40], ['#cfa978', 85, 75, 45, 40]] },
  sky: { base: '#cfd9dc', blobs: [['#93aeb9', 20, 20, 60, 50], ['#efe5d2', 60, 60, 80, 50], ['#c79f72', 85, 95, 50, 35], ['#e9eef0', 75, 15, 50, 40]] },
  violet: { base: '#9fa6cf', blobs: [['#3d4a9e', 30, 60, 60, 60], ['#d8dcf0', 75, 30, 60, 55], ['#6a3d72', 80, 85, 40, 35], ['#aab8e0', 15, 15, 45, 40]] },
  rose: { base: '#d8b4bd', blobs: [['#7a2e4c', 70, 60, 55, 60], ['#f3e4e6', 25, 35, 65, 55], ['#b77a8c', 15, 85, 45, 35], ['#e9c7c9', 85, 10, 45, 40]] },
  sage: { base: '#c6cfc2', blobs: [['#5f7a62', 25, 70, 60, 55], ['#eef0e6', 70, 25, 70, 55], ['#9a8a5c', 85, 90, 40, 35], ['#a9bba8', 40, 20, 50, 40]] },
  ember: { base: '#e2bfa8', blobs: [['#8a3b1f', 30, 65, 55, 60], ['#f6e6d8', 72, 25, 65, 55], ['#c46a3c', 15, 20, 40, 40], ['#e9a77c', 80, 85, 45, 40]] },
};
export type PaletteName = keyof typeof PALETTES;
export const pal = (p: string | undefined, fallback: PaletteName): PaletteName => (p && p in PALETTES ? (p as PaletteName) : fallback);

export const Gradient: React.FC<{ p: PaletteName; drift?: number; seed?: number }> = ({ p, drift = 1, seed = 0 }) => {
  const t = useT();
  const P = PALETTES[p];
  return (
    <AbsoluteFill style={{ background: P.base, overflow: 'hidden' }}>
      {P.blobs.map(([c, x, y, w, h], i) => {
        const dx = Math.sin(t * 0.35 * drift + i * 1.7 + seed) * 4;
        const dy = Math.cos(t * 0.3 * drift + i * 2.1 + seed) * 4;
        return (
          <div key={i} style={{
            position: 'absolute', left: `${x - w / 2 + dx}%`, top: `${y - h / 2 + dy}%`, width: `${w}%`, height: `${h}%`,
            background: `radial-gradient(ellipse at center, ${c} 0%, ${c}00 70%)`, filter: 'blur(60px)',
            transform: `rotate(${(i * 23 + t * 3 * drift) % 360}deg)`,
          }} />
        );
      })}
      <Grain opacity={0.07} />
    </AbsoluteFill>
  );
};

export const Grain: React.FC<{ opacity?: number }> = ({ opacity = 0.06 }) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ opacity, mixBlendMode: 'overlay', pointerEvents: 'none' }}>
      <svg width="100%" height="100%">
        <filter id={`g${frame % 4}`}>
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={frame % 4} />
        </filter>
        <rect width="100%" height="100%" filter={`url(#g${frame % 4})`} />
      </svg>
    </AbsoluteFill>
  );
};

/** Rounded-square grid: light on cream, faint on dark. */
export const GridPattern: React.FC<{ dark?: boolean; opacity?: number }> = ({ dark, opacity = 1 }) => {
  const { u } = useU();
  const s = 150 * u;
  const stroke = dark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.055)';
  return (
    <AbsoluteFill style={{ opacity }}>
      <svg width="100%" height="100%">
        <defs>
          <pattern id={`rg${dark ? 'd' : 'l'}`} width={s} height={s} patternUnits="userSpaceOnUse">
            <rect x={s * 0.06} y={s * 0.06} width={s * 0.88} height={s * 0.88} rx={s * 0.22} fill="none" stroke={stroke} strokeWidth={1.4} />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill={`url(#rg${dark ? 'd' : 'l'})`} />
      </svg>
    </AbsoluteFill>
  );
};

/** Whip / blur in and out, the main transition. Hard edges are straight cuts. */
export const Whip: React.FC<{ inAt: number; outAt?: number; dir?: 1 | -1; children: React.ReactNode; hardIn?: boolean; hardOut?: boolean }> =
  ({ inAt, outAt = 1e9, dir = 1, children, hardIn, hardOut }) => {
    const t = useT();
    if (t < inAt || t >= outAt) return null;
    const d = 0.24;
    const pin = hardIn ? 1 : k(t, inAt, inAt + d, 0, 1);
    const pout = hardOut ? 0 : k(t, outAt - d, outAt, 0, 1, Easing.in(Easing.cubic));
    const x = (1 - pin) * 7 * dir - pout * 7 * dir;
    const blur = (1 - pin) * 28 + pout * 28;
    const s = 1 + (1 - pin) * 0.04 + pout * 0.03;
    return (
      <AbsoluteFill style={{ transform: `translateX(${x}%) scale(${s})`, filter: blur > 0.3 ? `blur(${blur}px)` : undefined, opacity: Math.min(1, pin * 1.6) }}>
        {children}
      </AbsoluteFill>
    );
  };

// ── cursor ──────────────────────────────────────────────────────────────────────────────────
export type CursorKey = { t: number; x: number; y: number; click?: boolean };
export const Cursor: React.FC<{ keys: CursorKey[]; show: [number, number] }> = ({ keys, show }) => {
  const t = useT();
  const { u } = useU();
  if (t < show[0] || t > show[1]) return null;
  let x = keys[0].x, y = keys[0].y;
  for (let i = 0; i < keys.length - 1; i++) {
    const a = keys[i], b = keys[i + 1];
    if (t >= a.t && t <= b.t) { x = k(t, a.t, b.t, a.x, b.x); y = k(t, a.t, b.t, a.y, b.y); }
    if (t > b.t) { x = b.x; y = b.y; }
  }
  const click = keys.find((c) => c.click && t >= c.t && t < c.t + 0.2);
  const s = click ? 0.84 : 1;
  const ring = keys.find((c) => c.click && t >= c.t && t < c.t + 0.4);
  const rp = ring ? (t - ring.t) / 0.4 : 0;
  const op = k(t, show[0], show[0] + 0.15);
  return (
    <div style={{ position: 'absolute', left: x, top: y, opacity: op, zIndex: 50 }}>
      {ring && <div style={{ position: 'absolute', left: -26 * u * rp, top: -26 * u * rp, width: 52 * u * rp, height: 52 * u * rp, borderRadius: '50%', border: `${2 * u}px solid rgba(0,0,0,${0.35 * (1 - rp)})` }} />}
      <svg width={34 * u} height={34 * u} viewBox="0 0 24 24" style={{ transform: `scale(${s})`, transformOrigin: '4px 2px', filter: 'drop-shadow(0 3px 6px rgba(0,0,0,.3))' }}>
        <path d="M4 2 L4 19 L8.5 15 L11.3 21.4 L14 20.2 L11.3 13.9 L17.2 13.9 Z" fill="#111" stroke="#fff" strokeWidth={1.4} strokeLinejoin="round" />
      </svg>
    </div>
  );
};

// ── the Claude app ──────────────────────────────────────────────────────────────────────────
export const Spark: React.FC<{ size: number; spin?: number }> = ({ size, spin = 0 }) => (
  <Img src={staticFile('img/claude-spark.svg')} style={{ width: size, height: size, transform: `rotate(${spin}deg)` }} />
);

export const SendButton: React.FC<{ on: boolean; size: number }> = ({ on, size }) => (
  <div style={{ width: size, height: size, borderRadius: size * 0.28, background: C.cOrange, opacity: on ? 1 : 0.45, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
    <svg width={size * 0.5} height={size * 0.5} viewBox="0 0 24 24"><path d="M12 19V5M5.5 11.5 12 5l6.5 6.5" stroke="#fff" strokeWidth={2.6} fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>
  </div>
);

export const TypingCaret: React.FC<{ u: number }> = ({ u }) => {
  const t = useT();
  return <span style={{ display: 'inline-block', width: 2.5 * u, height: 30 * u, background: C.cInk, marginLeft: 2 * u, verticalAlign: 'middle', opacity: Math.floor(t * 2.4) % 2 ? 0 : 1 }} />;
};

/** The skill pill Claude shows in the composer when a skill is invoked. */
export const SkillChip: React.FC<{ u: number; label: string }> = ({ u, label }) => (
  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 * u, padding: `${5 * u}px ${12 * u}px`, borderRadius: 10 * u, background: '#FBEDE7', color: '#B4532F', font: `500 ${21 * u}px ${inter}`, marginRight: 8 * u }}>
    <svg width={18 * u} height={18 * u} viewBox="0 0 24 24"><path d="M6 3h9l4 4v14H6z M15 3v4h4 M9 12h7 M9 16h5" stroke="#B4532F" strokeWidth={2} fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>
    {label}
  </span>
);

/** The box you type to Claude in. */
export const Composer: React.FC<{ u: number; width: number; text: React.ReactNode; on: boolean; placeholder?: string; chip?: string }> =
  ({ u, width, text, on, placeholder = 'How can I help you today?', chip }) => (
    <div style={{ width, background: '#fff', borderRadius: 26 * u, border: `${1.5 * u}px solid ${C.cBorder}`, boxShadow: `0 ${18 * u}px ${50 * u}px rgba(20,20,19,.16)`, padding: `${24 * u}px ${26 * u}px ${18 * u}px`, fontFamily: inter }}>
      <div style={{ minHeight: 64 * u, font: `400 ${27 * u}px ${inter}`, color: C.cInk, lineHeight: 1.35, display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
        {chip && <SkillChip u={u} label={chip} />}
        {text || <span style={{ color: '#a3a29c' }}>{placeholder}</span>}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 16 * u }}>
        <div style={{ display: 'flex', gap: 10 * u }}>
          {['+', '⌥'].map((g, i) => (
            <div key={i} style={{ width: 44 * u, height: 44 * u, borderRadius: 12 * u, border: `${1.5 * u}px solid ${C.cBorder}`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#3d3d3a', font: `400 ${28 * u}px ${inter}` }}>{i ? <svg width={20 * u} height={20 * u} viewBox="0 0 24 24"><path d="M4 7h10M18 7h2M4 17h4M12 17h8M14 4v6M8 14v6" stroke="#3d3d3a" strokeWidth={2} strokeLinecap="round" /></svg> : g}</div>
          ))}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 * u }}>
          <span style={{ font: `500 ${20 * u}px ${inter}`, color: C.cMuted }}>{plan.claude?.model ?? 'Opus 5.5'} ⌄</span>
          <SendButton on={on} size={46 * u} />
        </div>
      </div>
    </div>
  );

export const UserBubble: React.FC<{ u: number; children: React.ReactNode }> = ({ u, children }) => (
  <div style={{ alignSelf: 'flex-end', maxWidth: '78%', background: C.cChip, borderRadius: 18 * u, padding: `${14 * u}px ${20 * u}px`, font: `400 ${25 * u}px ${inter}`, color: C.cInk, display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
    {children}
  </div>
);

/** Claude's reply: the spark spins while it thinks, then the words stream in. */
export const ClaudeReply: React.FC<{ u: number; text: string; at: number; thinkingFrom?: number; thinking?: string; perWord?: number; children?: React.ReactNode }> =
  ({ u, text, at, thinkingFrom, thinking = 'Thinking…', perWord = 0.045, children }) => {
    const t = useT();
    if (thinkingFrom !== undefined && t < thinkingFrom) return null;
    const words = text.split(' ');
    const spin = t < at ? t * 260 : 0;
    return (
      <div style={{ display: 'flex', gap: 18 * u, alignItems: 'flex-start' }}>
        <div style={{ paddingTop: 4 * u }}><Spark size={34 * u} spin={spin} /></div>
        <div style={{ flex: 1, font: `400 ${27 * u}px ${bodySerif}`, color: C.cInk, lineHeight: 1.45 }}>
          {t < at ? (
            <span style={{ font: `400 ${24 * u}px ${inter}`, color: C.cMuted, opacity: 0.6 + 0.4 * Math.sin(t * 9) }}>{thinking}</span>
          ) : (
            <>
              {words.map((w, i) => (
                <span key={i} style={{ opacity: k(t, at + i * perWord, at + i * perWord + 0.12) }}>{w} </span>
              ))}
              {children}
            </>
          )}
        </div>
      </div>
    );
  };

export const TrafficLights: React.FC<{ u: number; style?: React.CSSProperties }> = ({ u, style }) => (
  <div style={{ display: 'flex', gap: 9 * u, ...style }}>
    {['#ff5f57', '#febc2e', '#28c840'].map((c) => <div key={c} style={{ width: 13 * u, height: 13 * u, borderRadius: '50%', background: c }} />)}
  </div>
);

// ── the product ─────────────────────────────────────────────────────────────────────────────
/** The product's mark: its logo file, or its first letter on the accent colour. */
export const Mark: React.FC<{ size: number }> = ({ size }) => {
  const b = plan.brand;
  if (b.mark) return <Img src={staticFile(b.mark)} style={{ width: size, height: size, borderRadius: size * 0.22, objectFit: 'contain' }} />;
  const letter = (b.name.replace(/[^A-Za-z0-9]/g, '')[0] || '•').toUpperCase();
  return (
    <div style={{ width: size, height: size, borderRadius: size * 0.26, background: C.accent, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', font: `600 ${size * 0.52}px ${inter}` }}>{letter}</div>
  );
};

/** Waveform bars; bars up to `progress` are lit. */
export const Wave: React.FC<{ bars: number[]; width: number; height: number; progress: number; lit: string; dim: string; gap?: number; dimOpacity?: number }> =
  ({ bars, width, height, progress, lit, dim, gap = 3, dimOpacity = 0.55 }) => {
    const bw = Math.max(1.5, (width - gap * (bars.length - 1)) / bars.length);
    return (
      <svg width={width} height={height}>
        {bars.map((v, i) => {
          const h = Math.max(3, v * height * 0.9);
          const on = i / bars.length <= progress;
          return <rect key={i} x={i * (bw + gap)} y={(height - h) / 2} width={bw} height={h} rx={bw / 2} fill={on ? lit : dim} opacity={on ? 1 : dimOpacity} />;
        })}
      </svg>
    );
  };
