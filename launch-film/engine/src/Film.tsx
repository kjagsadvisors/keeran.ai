import React from 'react';
import { AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, staticFile, useVideoConfig, interpolate } from 'remotion';
import rawPlan from './plan.json';
import {
  C, inter, serif, useT, useU, k, lin, pal, Gradient, GridPattern, Grain, Whip, Cursor, Composer, UserBubble, ClaudeReply,
  TypingCaret, TrafficLights, Mark, Wave, PaletteName,
} from './ui';

// ── the plan (written by film.py plan) ─────────────────────────────────────────────────────────
type Word = { w: string; s: number; e: number };
type Media = { src: string; video?: boolean; w: number; h: number; rate?: number; from?: number };
type Row = { name: string; sub: string; bars: number[]; at: number; d: number; color?: string };
type Beat = {
  kind: 'screen' | 'type' | 'chips' | 'compare' | 'list' | 'chat' | 'end';
  at: number; end: number; inAt: number; outAt: number; hardIn?: boolean; hardOut?: boolean;
  words?: Word[]; bars?: number[]; levels?: number[]; dur?: number; palette?: string;
  media?: Media; mediaVertical?: Media; title?: string; click?: [number, number]; clickVertical?: [number, number]; clickAt?: number; size?: number;
  grey?: number;
  chips?: string[]; wave?: { before: number[]; after: number[]; labels: [string, string] };
  rows?: Row[];
  prefix?: string; items?: string[]; final?: string; onAt?: number;
  history?: { user?: string; claude?: string }[]; typed?: { w: string; at: number }[]; send?: number; reply?: number; watch?: number;
  replyText?: string; thinking?: string; result?: { src?: string; video?: boolean; label: string };
  keyword?: string; tagline?: string; cta?: boolean;
};
type Plan = {
  fps: number; total: number; cps: number;
  brand: { name: string; sub: string; accent: string; mark: string | null };
  opener: { tiles: number[]; labels: string[]; wordmark: number; next: number };
  claude: null | {
    prompt: string; skill: string | null; title: string; thinking: string; reply: string; model?: string;
    card: { title: string; sub: string; button: string };
    T: { claude: number; typeStart: number; typeEnd: number; send: number; think: number; reply: number; card: number; open: number };
  };
  beats: Beat[];
  audio: { src: string; at: number; from: number; dur: number; fadeIn?: number; fadeOut?: number }[];
  sfx: { src: string; at: number; db: number }[];
  music: null | { src: string; offset: number; db: number; lift: number };
  voice: [number, number][]; quiet: [number, number][];
};
const plan = rawPlan as unknown as Plan;
const dB = (db: number) => Math.pow(10, db / 20);
const B = plan.brand;

// ── 1. opener: a pause glyph, a dot, then gradient tiles cut on the music ──────────────────────
const Opener: React.FC = () => {
  const t = useT();
  const { u, W, H } = useU();
  const tiles = plan.opener.tiles;
  const idx = tiles.reduce((acc, x, i) => (t >= x ? i : acc), -1);
  const pz = tiles[0] * 0.45;
  const pals: PaletteName[] = ['plum', 'gold', 'blue', 'gold'];
  const sizes = [[300, 200], [330, 220], [420, 280], [560, 372]];
  const labels = plan.opener.labels;
  return (
    <AbsoluteFill style={{ background: C.cream }}>
      {idx < 0 && t < pz && (
        <div style={{ position: 'absolute', left: W / 2 - 9 * u, top: H / 2 - 12 * u, display: 'flex', gap: 6 * u, opacity: k(t, 0.02, pz * 0.6) }}>
          <div style={{ width: 6 * u, height: 24 * u, background: '#222', borderRadius: 2 }} />
          <div style={{ width: 6 * u, height: 24 * u, background: '#222', borderRadius: 2 }} />
        </div>
      )}
      {idx < 0 && t >= pz && (
        <>
          <div style={{ position: 'absolute', left: W / 2 - 7 * u, top: H / 2 - 7 * u, width: 14 * u, height: 14 * u, background: '#111', borderRadius: 2 * u, transform: `scale(${k(t, pz, pz + 0.12, 0.4, 1)})` }} />
          {[-1, 1].map((s) => (
            <div key={s} style={{ position: 'absolute', left: W / 2 + s * 260 * u * k(t, pz + 0.04, tiles[0], 0.3, 1) - 3 * u, top: H / 2 - 3 * u, width: 6 * u, height: 6 * u, borderRadius: '50%', background: '#222', opacity: k(t, pz + 0.04, pz + 0.15) }} />
          ))}
        </>
      )}
      {idx >= 0 && (() => {
        const [w, h] = sizes[Math.min(idx, 3)].map((x) => x * u);
        return (
          <>
            <div style={{ position: 'absolute', left: W / 2 - w / 2, top: H / 2 - h / 2, width: w, height: h, overflow: 'hidden' }}>
              <Gradient p={pals[idx % 4]} seed={idx * 3} />
            </div>
            {labels.slice(0, 4).map((lb, i) => {
              const x = i % 2 ? W / 2 + w / 2 + 70 * u : W / 2 - w / 2 - 70 * u;
              const y = i < 2 ? H / 2 - h / 2 + 18 * u : H / 2 + h / 2 - 30 * u;
              return <div key={i} style={{ position: 'absolute', left: x, top: y, transform: i % 2 ? undefined : 'translateX(-100%)', font: `500 ${13 * u}px ${inter}`, letterSpacing: '0.12em', textTransform: 'uppercase', color: C.muted, display: 'flex', alignItems: 'center', gap: 8 * u, whiteSpace: 'nowrap' }}><span style={{ width: 5 * u, height: 5 * u, borderRadius: '50%', background: '#555' }} />{lb}</div>;
            })}
          </>
        );
      })()}
    </AbsoluteFill>
  );
};

// ── 2. the wordmark ───────────────────────────────────────────────────────────────────────────
const Wordmark: React.FC<{ at: number; size?: number }> = ({ at, size = 64 }) => {
  const t = useT();
  const { u } = useU();
  const s = size * u;
  const a = k(t, at, at + 0.35), b = k(t, at + 0.18, at + 0.6);
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: s * 0.28, font: `500 ${s}px ${inter}`, letterSpacing: '-0.035em', whiteSpace: 'nowrap' }}>
      <div style={{ opacity: a, transform: `scale(${0.8 + 0.2 * a})` }}><Mark size={s * 0.92} /></div>
      <span style={{ color: C.ink, opacity: a, filter: `blur(${(1 - a) * 8}px)` }}>{B.name}</span>
      {B.sub && <span style={{ color: C.soft, opacity: b, filter: `blur(${(1 - b) * 8}px)` }}>{B.sub}</span>}
    </div>
  );
};

const WordmarkScene: React.FC = () => {
  const { W } = useU();
  return (
    <AbsoluteFill style={{ background: C.cream, alignItems: 'center', justifyContent: 'center' }}>
      <GridPattern opacity={0.9} />
      <div style={{ transform: `scale(${W < 1200 ? 0.62 : 1})` }}><Wordmark at={plan.opener.wordmark} /></div>
    </AbsoluteFill>
  );
};

// ── 3. Claude: you type the ask, Claude hands back the product ───────────────────────────────
const useGeo = () => {
  const { u, W, H, vertical } = useU();
  const PW = vertical ? W * 0.9 : 1040 * u;
  const X0 = (W - PW) / 2;
  const cy = H / 2;
  const pad = vertical ? 18 * u : 56 * u;
  return { u, W, H, vertical, PW, X0, cy, pad };
};

const ProductCard: React.FC<{ u: number; width: number; at: number }> = ({ u, width, at }) => {
  const t = useT();
  const a = k(t, at, at + 0.3);
  const card = plan.claude!.card;
  return (
    <div style={{ width, marginTop: 18 * u, opacity: a, transform: `translateY(${(1 - a) * 14 * u}px)`, display: 'flex', alignItems: 'center', gap: 18 * u, padding: `${16 * u}px ${18 * u}px`, border: `${1.5 * u}px solid ${C.cBorder}`, borderRadius: 18 * u, background: '#fff', fontFamily: inter }}>
      <Mark size={58 * u} />
      <div style={{ flex: 1 }}>
        <div style={{ font: `600 ${24 * u}px ${inter}`, color: C.cInk }}>{card.title}</div>
        <div style={{ font: `400 ${19 * u}px ${inter}`, color: C.cMuted }}>{card.sub}</div>
      </div>
      <div style={{ padding: `${10 * u}px ${22 * u}px`, borderRadius: 12 * u, border: `${1.5 * u}px solid ${C.cBorder}`, font: `500 ${20 * u}px ${inter}`, color: C.cInk }}>{card.button}</div>
    </div>
  );
};

const ClaudeScene: React.FC = () => {
  const t = useT();
  const { u, W, H, PW, X0, cy, pad } = useGeo();
  const cl = plan.claude!;
  const T = cl.T;
  const sent = t >= T.send + 0.05;
  const g = k(t, T.send + 0.05, T.send + 0.45); // composer grows into the chat window
  const compTop = interpolate(g, [0, 1], [cy - 88 * u, cy + 70 * u]);
  const win = { l: X0 - pad, t: cy - 380 * u, w: PW + 2 * pad, h: 690 * u };
  const typed = cl.prompt.slice(0, t >= T.typeStart ? Math.max(0, Math.floor((t - T.typeStart) * plan.cps) + 1) : 0);
  const sendX = X0 + PW - 49 * u, sendY = cy - 88 * u + 129 * u;
  const openX = X0 + PW - 66 * u, openY = cy - 66 * u;
  return (
    <AbsoluteFill>
      <Gradient p="blue" />
      <div style={{ position: 'absolute', left: interpolate(g, [0, 1], [X0, win.l]), top: interpolate(g, [0, 1], [cy - 88 * u, win.t]), width: interpolate(g, [0, 1], [PW, win.w]), height: interpolate(g, [0, 1], [176 * u, win.h]), background: C.cPaper, borderRadius: 30 * u, opacity: g, boxShadow: `0 ${30 * u}px ${80 * u}px rgba(20,20,40,.22)` }}>
        <TrafficLights u={u} style={{ position: 'absolute', left: 24 * u, top: 20 * u, opacity: k(t, T.send + 0.3, T.send + 0.5) }} />
        <div style={{ position: 'absolute', left: 0, right: 0, top: 16 * u, textAlign: 'center', font: `500 ${19 * u}px ${inter}`, color: C.cMuted, opacity: k(t, T.send + 0.3, T.send + 0.5) }}>{cl.title}</div>
      </div>
      {sent && (
        <div style={{ position: 'absolute', left: X0, width: PW, top: cy - 300 * u, display: 'flex', flexDirection: 'column', gap: 26 * u, opacity: k(t, T.send + 0.2, T.send + 0.45) }}>
          <UserBubble u={u}>{cl.skill && <span style={{ color: '#B4532F', marginRight: 8 * u }}>/{cl.skill}</span>}{cl.prompt}</UserBubble>
          <ClaudeReply u={u} at={T.reply} thinkingFrom={T.think} thinking={cl.thinking} perWord={0.025} text={cl.reply}>
            <ProductCard u={u} width={PW - 52 * u} at={T.card} />
          </ClaudeReply>
        </div>
      )}
      <div style={{ position: 'absolute', left: X0, top: compTop }}>
        <Composer u={u} width={PW} chip={!sent && cl.skill ? cl.skill : undefined} on={!sent && typed.length > 0}
          text={sent ? '' : typed ? <span>{typed}{t < T.send && <TypingCaret u={u} />}</span> : ''}
          placeholder={sent ? 'Reply to Claude…' : 'How can I help you today?'} />
      </div>
      <Cursor show={[T.typeEnd - 0.15, T.open + 0.25]} keys={[
        { t: T.typeEnd - 0.15, x: W * 0.78, y: H * 0.9 },
        { t: T.send - 0.04, x: sendX, y: sendY },
        { t: T.send, x: sendX, y: sendY, click: true },
        { t: T.card + 0.1, x: sendX - 40 * u, y: sendY + 30 * u },
        { t: T.open - 0.04, x: openX, y: openY },
        { t: T.open, x: openX, y: openY, click: true },
      ]} />
    </AbsoluteFill>
  );
};

// ── screen: the real product, in a window, with a click ───────────────────────────────────────
const ScreenScene: React.FC<{ b: Beat }> = ({ b }) => {
  const t = useT();
  const { u, W, H, vertical } = useU();
  const { fps } = useVideoConfig();
  const m = (vertical && b.mediaVertical) || b.media!;
  const aspect = m.w / m.h;
  const bar = b.title ? 54 * u : 0;
  const sz = vertical ? 1 : b.size ?? 1;
  const maxW = (vertical ? W * 0.94 : 1560 * u) * sz, maxH = (vertical ? H * 0.62 : 820 * u) * sz - bar;
  const bw = Math.min(maxW, maxH * aspect), bh = bw / aspect;
  const left = (W - bw) / 2, top = (H - bh - bar) / 2;
  const push = k(t, b.inAt, b.outAt, 1, 1.05, lin);
  let keys = null as null | { t: number; x: number; y: number; click?: boolean }[];
  const click = vertical && b.mediaVertical ? b.clickVertical : b.click;
  if (click && b.clickAt !== undefined) {
    const s = 1 + 0.05 * Math.min(1, (b.clickAt - b.inAt) / (b.outAt - b.inAt));
    const tx = W / 2 + (left + click[0] * bw - W / 2) * s, ty = H / 2 + (top + bar + click[1] * bh - H / 2) * s;
    keys = [
      { t: b.at + (b.dur ?? 1) * 0.45, x: W * 0.72, y: H * 0.88 },
      { t: b.clickAt - 0.04, x: tx, y: ty },
      { t: b.clickAt, x: tx, y: ty, click: true },
      { t: b.outAt, x: tx + 20 * u, y: ty + 10 * u },
    ];
  }
  return (
    <AbsoluteFill style={{ background: '#e9e7e3' }}>
      <Gradient p={pal(b.palette, 'sky')} drift={0.6} />
      <div style={{ position: 'absolute', left, top, width: bw, height: bh + bar, borderRadius: 22 * u, overflow: 'hidden', background: '#fff', boxShadow: `0 ${40 * u}px ${100 * u}px rgba(30,30,40,.25)`, transform: `scale(${push})` }}>
        {b.title && (
          <div style={{ height: bar, display: 'flex', alignItems: 'center', padding: `0 ${20 * u}px`, borderBottom: '1px solid #e5e5e5', background: '#f6f6f6', position: 'relative' }}>
            <TrafficLights u={u} />
            <span style={{ position: 'absolute', left: 0, right: 0, textAlign: 'center', font: `600 ${19 * u}px ${inter}`, color: '#1d1d1f' }}>{b.title}</span>
          </div>
        )}
        <div style={{ position: 'relative', width: bw, height: bh }}>
          {m.video ? (
            <Sequence from={Math.round(b.inAt * fps)} layout="none">
              <OffthreadVideo src={staticFile(m.src)} muted playbackRate={m.rate ?? 1} trimBefore={Math.round((m.from ?? 0) * fps)} style={{ width: bw, height: bh, objectFit: 'cover' }} />
            </Sequence>
          ) : (
            <Img src={staticFile(m.src)} style={{ width: bw, height: bh, objectFit: 'cover' }} />
          )}
        </div>
      </div>
      {keys && <Cursor show={[keys[0].t, b.outAt]} keys={keys} />}
    </AbsoluteFill>
  );
};

// ── type: the line in big dark type, word by word as it's said ────────────────────────────────
const TypeScene: React.FC<{ b: Beat }> = ({ b }) => {
  const t = useT();
  const { u, vertical } = useU();
  const words = b.words!;
  const grey = b.grey ?? 1;
  return (
    <AbsoluteFill style={{ background: '#0d0d0f', alignItems: 'center', justifyContent: 'center' }}>
      <GridPattern dark />
      <AbsoluteFill style={{ background: 'radial-gradient(ellipse at center, rgba(13,13,15,0) 0%, rgba(13,13,15,.85) 75%)' }} />
      <div style={{ position: 'relative', font: `500 ${(vertical ? 74 : 84) * u}px ${inter}`, letterSpacing: '-0.04em', color: '#f2f2f2', textAlign: 'center', maxWidth: (vertical ? 900 : 1500) * u, lineHeight: 1.1 }}>
        {words.map((w, i) => {
          const a = k(t, b.at + w.s - 0.06, b.at + w.s + 0.16);
          return <span key={i} style={{ opacity: a, filter: `blur(${(1 - a) * 10}px)`, color: i >= words.length - grey ? '#6d6d72' : undefined }}>{w.w} </span>;
        })}
      </div>
      <Grain opacity={0.05} />
    </AbsoluteFill>
  );
};

// ── chips: what it does, ticked off one by one (optionally a wave going from raw to clean) ────
const resample = (a: number[], n: number) => Array.from({ length: n }, (_, i) => a[Math.min(a.length - 1, Math.floor((i / n) * a.length))]);
const ChipsScene: React.FC<{ b: Beat }> = ({ b }) => {
  const t = useT();
  const { u, W, vertical } = useU();
  const chips = b.chips ?? [];
  const span = b.end - b.at;
  const n = 120;
  const WW = vertical ? W * 0.88 : 1360 * u;
  const bw = (WW - 3 * u * (n - 1)) / n;
  const wave = b.wave;
  const before = wave ? resample(wave.before, n) : [], after = wave ? resample(wave.after, n) : [];
  const sweep = k(t, b.at + 0.25, b.end - 0.05, 0, 1, lin);
  return (
    <AbsoluteFill style={{ background: C.cream, alignItems: 'center', justifyContent: 'center' }}>
      <GridPattern opacity={0.6} />
      <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 40 * u }}>
        <div style={{ display: 'flex', gap: (wave ? 12 : 16) * u, flexWrap: 'wrap', justifyContent: 'center', maxWidth: WW, flexDirection: !wave && vertical ? 'column' : 'row', alignItems: 'center' }}>
          {chips.map((c, i) => {
            const a = k(t, b.at + 0.2 + i * span * (0.8 / Math.max(1, chips.length)), b.at + 0.45 + i * span * (0.8 / Math.max(1, chips.length)));
            const size = wave ? 21 : 30;
            return <div key={i} style={{ opacity: a, transform: `translateY(${(1 - a) * 12 * u}px)`, display: 'flex', alignItems: 'center', gap: 10 * u, padding: `${(wave ? 11 : 16) * u}px ${(wave ? 20 : 28) * u}px`, borderRadius: 99, background: '#fff', border: `1px solid ${C.line}`, boxShadow: `0 ${6 * u}px ${18 * u}px rgba(0,0,0,.06)`, font: `500 ${size * u}px ${inter}`, color: C.ink, whiteSpace: 'nowrap' }}><span style={{ color: C.accent }}>✓</span>{c}</div>;
          })}
        </div>
        {wave && (
          <>
            <svg width={WW} height={230 * u}>
              {Array.from({ length: n }).map((_, i) => {
                const clean = i / n < sweep;
                const v = clean ? after[i] : before[i];
                const h = Math.max(3 * u, v * 220 * u * (clean ? 0.95 : 0.9));
                return <rect key={i} x={i * (bw + 3 * u)} y={(230 * u - h) / 2} width={bw} height={h} rx={bw / 2} fill={clean ? C.accent : '#b9b6b2'} />;
              })}
              {sweep > 0 && sweep < 1 && <rect x={sweep * WW - 1.5 * u} y={0} width={3 * u} height={230 * u} fill={C.ink} />}
            </svg>
            <div style={{ display: 'flex', justifyContent: 'space-between', width: WW, font: `500 ${14 * u}px ${inter}`, letterSpacing: '0.12em', color: C.muted, textTransform: 'uppercase' }}>
              <span>{wave.labels[0]}</span><span style={{ color: sweep > 0.98 ? C.accent : C.muted }}>{wave.labels[1]}</span>
            </div>
          </>
        )}
      </div>
    </AbsoluteFill>
  );
};

// ── compare: hear the before, then the after ──────────────────────────────────────────────────
const CompareScene: React.FC<{ b: Beat }> = ({ b }) => {
  const t = useT();
  const { u, W, vertical } = useU();
  const WW = vertical ? W * 0.9 : 1360 * u;
  return (
    <AbsoluteFill style={{ background: C.cream, alignItems: 'center', justifyContent: 'center' }}>
      <GridPattern opacity={0.6} />
      <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', gap: 34 * u, width: WW }}>
        {b.rows!.map((r, i) => {
          const active = t >= r.at - 0.15 && t < r.at + r.d + 0.05;
          const pr = k(t, r.at, r.at + r.d, 0, 1, lin);
          const appear = k(t, b.inAt + i * 0.12, b.inAt + 0.3 + i * 0.12);
          const col = r.color ?? (i ? C.accent : '#55524f');
          return (
            <div key={i} style={{ opacity: appear * (active ? 1 : 0.38), transform: `translateY(${(1 - appear) * 16 * u}px) scale(${active ? 1 : 0.98})`, background: '#fff', border: `1px solid ${C.line}`, borderRadius: 22 * u, padding: `${24 * u}px ${30 * u}px`, display: 'flex', alignItems: vertical ? 'stretch' : 'center', flexDirection: vertical ? 'column' : 'row', gap: 28 * u, boxShadow: active ? `0 ${16 * u}px ${44 * u}px rgba(0,0,0,.08)` : 'none' }}>
              <div style={{ width: vertical ? undefined : 270 * u, fontFamily: inter }}>
                <div style={{ font: `500 ${44 * u}px ${inter}`, letterSpacing: '-0.035em', color: C.ink }}>{r.name}</div>
                <div style={{ font: `400 ${20 * u}px ${inter}`, color: C.muted, marginTop: 2 * u }}>{r.sub}</div>
              </div>
              <Wave bars={r.bars} width={vertical ? WW - 60 * u : WW - 360 * u} height={120 * u} progress={pr} lit={col} dim="#c9c6c2" gap={3 * u} dimOpacity={1} />
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ── list: "<prefix> — A / B / C / anything", one gradient per word, the last on its word ──────
const ListScene: React.FC<{ b: Beat }> = ({ b }) => {
  const t = useT();
  const { u, vertical } = useU();
  const list = b.items ?? [];
  const s0 = b.at - 0.1;
  const onAt = b.onAt ?? b.end;
  const step = (onAt - s0) / Math.max(1, list.length);
  const idx = t >= onAt ? list.length : Math.max(0, Math.floor((t - s0) / step));
  const word = idx >= list.length ? b.final ?? '' : list[idx];
  const pals: PaletteName[] = ['gold', 'sky', 'plum', 'violet', 'rose', 'sage', 'ember'];
  return (
    <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center' }}>
      <Gradient p={pals[idx % pals.length]} seed={idx * 2} />
      <AbsoluteFill style={{ background: 'radial-gradient(ellipse at center, rgba(40,30,30,.2) 0%, rgba(40,30,30,.05) 70%)' }} />
      <div style={{ position: 'relative', display: 'flex', flexDirection: vertical ? 'column' : 'row', alignItems: 'center', gap: 22 * u, font: `400 ${(vertical ? 66 : 70) * u}px ${inter}`, letterSpacing: '-0.035em', color: '#fff', textShadow: '0 2px 24px rgba(0,0,0,.28)', textAlign: 'center' }}>
        {b.prefix && <span style={{ opacity: 0.92 }}>{b.prefix}</span>}
        {b.prefix && <span style={{ width: 60 * u, height: 2 * u, background: 'rgba(255,255,255,.85)', boxShadow: '0 1px 8px rgba(0,0,0,.2)' }} />}
        <span style={{ fontWeight: 500 }}>{word}</span>
      </div>
    </AbsoluteFill>
  );
};

// ── chat: back in Claude, the ask typed as it's said, the result opens full frame ─────────────
const ResultThumb: React.FC<{ r: NonNullable<Beat['result']> }> = ({ r }) => (
  r.src ? (r.video ? <OffthreadVideo src={staticFile(r.src)} muted style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : <Img src={staticFile(r.src)} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />)
    : <Gradient p="violet" />
);

const ChatScene: React.FC<{ b: Beat }> = ({ b }) => {
  const t = useT();
  const { u, W, H, PW, X0, cy, pad } = useGeo();
  const cl = plan.claude;
  const typedWords = (b.typed ?? []).filter((w) => t >= w.at).map((w) => w.w.replace(/[.,]$/, '')).join(' ');
  const text = typedWords.charAt(0).toUpperCase() + typedWords.slice(1);
  const send = b.send!, reply = b.reply!, watch = b.watch!;
  const sent = t >= send + 0.05;
  const up = k(t, send + 0.05, send + 0.45);
  const win = { l: X0 - pad, t: cy - 380 * u, w: PW + 2 * pad, h: 690 * u };
  const sendX = X0 + PW - 49 * u, sendY = cy + 70 * u + 129 * u;
  const vidX = X0 + 52 * u + 200 * u, vidY = cy - 90 * u;
  const zoom = k(t, watch + 0.05, b.outAt, 0, 1);
  const r = b.result ?? { label: '' };
  return (
    <AbsoluteFill>
      <Gradient p={pal(b.palette, 'gold')} />
      <div style={{ position: 'absolute', left: win.l, top: win.t, width: win.w, height: win.h, background: C.cPaper, borderRadius: 30 * u, boxShadow: `0 ${30 * u}px ${80 * u}px rgba(60,40,10,.2)`, overflow: 'hidden' }}>
        <TrafficLights u={u} style={{ position: 'absolute', left: 24 * u, top: 20 * u }} />
        <div style={{ position: 'absolute', left: 0, right: 0, top: 16 * u, textAlign: 'center', font: `500 ${19 * u}px ${inter}`, color: C.cMuted }}>{cl?.title ?? B.name}</div>
        <div style={{ position: 'absolute', left: 0, right: 0, top: 58 * u, bottom: 250 * u, overflow: 'hidden', WebkitMaskImage: 'linear-gradient(to bottom, transparent 0, #000 40px)' }}>
          <div style={{ position: 'absolute', left: pad, width: PW, bottom: 20 * u, transform: `translateY(${sent ? (1 - up) * 80 * u : 0}px)`, display: 'flex', flexDirection: 'column', gap: 26 * u }}>
            {cl && (
              <ClaudeReply u={u} at={-1} text={cl.reply}>
                <ProductCard u={u} width={PW - 52 * u} at={-1} />
              </ClaudeReply>
            )}
            {(b.history ?? []).map((h, i) => h.user ? <UserBubble key={i} u={u}>{h.user}</UserBubble> : <ClaudeReply key={i} u={u} at={-1} text={h.claude ?? ''} />)}
            {sent && <UserBubble u={u}>{text}</UserBubble>}
            {sent && (
              <ClaudeReply u={u} at={reply} thinkingFrom={send + 0.15} thinking={b.thinking ?? 'Working on it…'} text={b.replyText ?? 'Done.'}>
                <div style={{ marginTop: 14 * u, width: 400 * u, height: 225 * u, borderRadius: 16 * u, overflow: 'hidden', position: 'relative', opacity: k(t, reply + 0.15, reply + 0.4), border: `1px solid ${C.cBorder}` }}>
                  <ResultThumb r={r} />
                  <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center' }}>
                    <div style={{ width: 70 * u, height: 70 * u, borderRadius: '50%', background: 'rgba(255,255,255,.92)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <svg width={30 * u} height={30 * u} viewBox="0 0 24 24"><path d="M8 5.5v13l10-6.5Z" fill={C.cInk} /></svg>
                    </div>
                  </AbsoluteFill>
                  {r.label && <div style={{ position: 'absolute', left: 14 * u, bottom: 10 * u, font: `500 ${16 * u}px ${inter}`, color: '#fff', textShadow: '0 1px 6px rgba(0,0,0,.4)' }}>{r.label}</div>}
                </div>
              </ClaudeReply>
            )}
          </div>
        </div>
        <div style={{ position: 'absolute', left: pad, bottom: 30 * u }}>
          <Composer u={u} width={PW} on={!sent && text.length > 0}
            text={!sent && text ? <span>{text}<TypingCaret u={u} /></span> : ''} placeholder="Reply to Claude…" />
        </div>
      </div>
      {zoom > 0 && (
        <div style={{ position: 'absolute', left: interpolate(zoom, [0, 1], [vidX - 200 * u, 0]), top: interpolate(zoom, [0, 1], [vidY - 112 * u, 0]), width: interpolate(zoom, [0, 1], [400 * u, W]), height: interpolate(zoom, [0, 1], [225 * u, H]), borderRadius: (1 - zoom) * 16 * u, overflow: 'hidden' }}>
          <ResultThumb r={r} />
        </div>
      )}
      <Cursor show={[b.at + 0.4, watch + 0.2]} keys={[
        { t: b.at + 0.4, x: W * 0.8, y: H * 0.92 },
        { t: send - 0.04, x: sendX, y: sendY },
        { t: send, x: sendX, y: sendY, click: true },
        { t: watch - 0.04, x: vidX, y: vidY },
        { t: watch, x: vidX, y: vidY, click: true },
      ]} />
    </AbsoluteFill>
  );
};

// ── end card: the orb, the wordmark, then the comment word ────────────────────────────────────
const CommentLine: React.FC<{ b: Beat }> = ({ b }) => {
  const t = useT();
  const { u, W, vertical } = useU();
  const words = b.words!;
  const key = (b.keyword ?? '').toLowerCase();
  const vi = key ? words.findIndex((w) => w.w.toLowerCase().replace(/[^a-z0-9]/g, '').startsWith(key)) : -1;
  const size = (vertical ? 50 : 56) * u;
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', alignItems: 'center', columnGap: size * 0.26, rowGap: size * 0.18, maxWidth: vertical ? W * 0.88 : 1800 * u, font: `500 ${size}px ${inter}`, letterSpacing: '-0.035em', lineHeight: 1.15 }}>
      {words.map((w, i) => {
        const a = k(t, b.at + w.s - 0.06, b.at + w.s + 0.16);
        const pill = i === vi;
        return (
          <span key={i} style={{ opacity: a, filter: `blur(${(1 - a) * 10}px)`, transform: `translateY(${(1 - a) * 8 * u}px)`, color: pill ? '#fff' : i > vi && vi >= 0 ? C.soft : C.ink, background: pill ? C.ink : undefined, borderRadius: pill ? 99 : undefined, padding: pill ? `${size * 0.1}px ${size * 0.38}px ${size * 0.13}px` : undefined, letterSpacing: pill ? '0.01em' : undefined }}>
            {pill ? (b.keyword ?? '').toUpperCase() : w.w}
          </span>
        );
      })}
    </div>
  );
};

const EndScene: React.FC<{ b: Beat }> = ({ b }) => {
  const t = useT();
  const { u, W, H, vertical } = useU();
  const e = b.inAt;
  const orb = t < e + 0.7 ? Math.sin(Math.PI * k(t, e, e + 0.7, 0, 1, lin)) : 0;
  return (
    <AbsoluteFill style={{ background: C.cream, alignItems: 'center', justifyContent: 'center' }}>
      <GridPattern opacity={k(t, e + 0.4, e + 0.9)} />
      {orb > 0.01 && (
        <div style={{ position: 'absolute', left: W / 2 - 170 * u * orb, top: H / 2 - 170 * u * orb, width: 340 * u * orb, height: 340 * u * orb, borderRadius: '50%', overflow: 'hidden', filter: 'blur(1px)' }}>
          <Gradient p="violet" drift={3} />
        </div>
      )}
      <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 46 * u }}>
        <div style={{ transform: `scale(${vertical ? 0.62 : 1})` }}><Wordmark at={e + 0.4} /></div>
        {b.cta ? <CommentLine b={b} /> : (
          <div style={{ display: 'flex', alignItems: 'center', gap: 18 * u, opacity: k(t, e + 1.3, e + 1.6), transform: `translateY(${(1 - k(t, e + 1.3, e + 1.6)) * 10 * u}px)` }}>
            {b.tagline && <span style={{ font: `400 ${26 * u}px ${inter}`, color: C.muted }}>{b.tagline}</span>}
            {b.keyword && <span style={{ padding: `${12 * u}px ${26 * u}px`, borderRadius: 99, background: C.ink, color: '#fff', font: `500 ${26 * u}px ${inter}`, letterSpacing: '-0.01em' }}>Comment {b.keyword.toUpperCase()}</span>}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};

// ── sound: voice on top, SFX on the actions, music up only where nobody's talking ─────────────
const Sound: React.FC = () => {
  const { fps } = useVideoConfig();
  const f = (s: number) => Math.round(s * fps);
  const m = plan.music;
  const total = plan.total;
  const cl = { extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const };
  const musicVol = (sec: number) => {
    if (!m) return 0;
    let voice = 0;
    for (const [a, b] of plan.voice) voice = Math.max(voice, interpolate(sec, [a - 0.5, a, b + 0.3, b + 0.8], [0, 1, 1, 0], cl));
    let quiet = 0; // a raw "before" clip plays at its real level: get the music out of its way
    for (const [a, b] of plan.quiet) quiet = Math.max(quiet, interpolate(sec, [a - 0.1, a + 0.2, b - 0.25, b + 0.05], [0, 1, 1, 0], cl));
    const out = interpolate(sec, [total - 1.6, total], [1, 0], cl);
    return dB(m.db + (1 - voice) * m.lift - quiet * 12) * out;
  };
  return (
    <>
      {m && (
        <Sequence from={0} durationInFrames={f(total)}>
          <Audio src={staticFile(m.src)} trimBefore={f(m.offset)} volume={(fr) => musicVol(fr / fps)} />
        </Sequence>
      )}
      {plan.audio.map((a, i) => (
        <Sequence key={`a${i}`} from={f(a.at)} durationInFrames={Math.max(1, f(a.dur))}>
          <Audio src={staticFile(a.src)} trimBefore={f(a.from)}
            volume={(fr) => {
              const s = fr / fps;
              const fi = a.fadeIn ? Math.min(1, s / a.fadeIn) : 1;
              const fo = a.fadeOut ? Math.min(1, Math.max(0, (a.dur - s) / a.fadeOut)) : 1;
              return fi * fo;
            }} />
        </Sequence>
      ))}
      {plan.sfx.map((s, i) => (
        <Sequence key={`s${i}`} from={f(s.at)} durationInFrames={f(1.5)}>
          <Audio src={staticFile(s.src)} volume={dB(s.db)} />
        </Sequence>
      ))}
    </>
  );
};

const SCENES: Record<Beat['kind'], React.FC<{ b: Beat }>> = {
  screen: ScreenScene, type: TypeScene, chips: ChipsScene, compare: CompareScene, list: ListScene, chat: ChatScene, end: EndScene,
};

export const Film: React.FC = () => {
  const o = plan.opener;
  const first = plan.beats[0];
  return (
    <AbsoluteFill style={{ background: C.cream }}>
      <Whip inAt={0} outAt={o.wordmark} hardIn hardOut><Opener /></Whip>
      <Whip inAt={o.wordmark} outAt={o.next} hardIn hardOut={!plan.claude && first?.hardIn}><WordmarkScene /></Whip>
      {plan.claude && <Whip inAt={plan.claude.T.claude - 0.08} outAt={first ? first.inAt + (first.hardIn ? 0 : 0.05) : plan.total}><ClaudeScene /></Whip>}
      {plan.beats.map((b, i) => {
        const S = SCENES[b.kind];
        return <Whip key={i} inAt={b.inAt} outAt={b.outAt} hardIn={b.hardIn} hardOut={b.hardOut}><S b={b} /></Whip>;
      })}
      <Sound />
    </AbsoluteFill>
  );
};

export { serif };
