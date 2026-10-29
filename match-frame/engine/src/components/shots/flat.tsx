import React, { useId } from 'react';
import { AbsoluteFill } from 'remotion';
import type { GridShot, LockupShot, PatternShot, SurfaceShot, UiShot } from '../../config/types';
import { brandFont } from '../../lib/fonts';
import { alpha, mix, scheme } from '../../lib/tones';
import { Mark, PinnedMark, useLogo } from '../Logo';
import { Material } from '../Material';
import { matchPx, type ShotProps } from './common';

/** Logo on a material. With emboss/deboss the mark is cut from the surface colour itself. */
export const Surface: React.FC<ShotProps<SurfaceShot>> = ({ shot, config, tone }) => {
  const s = scheme(config.brand, tone);
  const finish = shot.finish ?? 'flat';
  const { x, y, w } = matchPx(config, shot.logoScale);
  const color = finish === 'flat' ? s.fg : mix(s.bg, s.fg, s.dark ? 0.3 : 0.22);
  return (
    <AbsoluteFill>
      <Material kind={shot.material ?? 'flat'} scheme={s} shadow={shot.shadow} />
      {!shot.noLogo && <PinnedMark x={x} y={y} width={w} color={color} finish={finish} dark={s.dark} />}
    </AbsoluteFill>
  );
};

/** Construction drawing: icon keyline grid around the mark on the match point, or full-bleed guides. */
export const Grid: React.FC<ShotProps<GridShot>> = ({ shot, config, tone }) => {
  const s = scheme(config.brand, tone);
  const { width: W, height: H } = config;
  const variant = shot.variant ?? 'keyline';
  const { x, y, w } = matchPx(config, shot.logoScale ?? (variant === 'guides' ? 0.45 : 1));
  const S = w * 1.75;
  const ext = S * 0.62;
  const stroke = { stroke: s.line, strokeWidth: 2, fill: 'none' };
  return (
    <AbsoluteFill style={{ background: s.bg }}>
      <svg width={W} height={H} style={{ position: 'absolute', inset: 0 }}>
        {variant === 'keyline' ? (
          <g {...stroke}>
            <rect x={x - S / 2} y={y - S / 2} width={S} height={S} rx={S * 0.22} />
            <circle cx={x} cy={y} r={S * 0.5} />
            <circle cx={x} cy={y} r={S * 0.34} />
            <circle cx={x} cy={y} r={S * 0.17} />
            {[-0.5, -1 / 6, 1 / 6, 0.5].map((k) => (
              <React.Fragment key={k}>
                <line x1={x + k * S} y1={y - ext} x2={x + k * S} y2={y + ext} />
                <line x1={x - ext} y1={y + k * S} x2={x + ext} y2={y + k * S} />
              </React.Fragment>
            ))}
            <line x1={x - ext} y1={y - ext} x2={x + ext} y2={y + ext} />
            <line x1={x + ext} y1={y - ext} x2={x - ext} y2={y + ext} />
          </g>
        ) : (
          <g {...stroke}>
            {[0.25, 0.5, 0.75].map((k) => (
              <line key={k} x1={W * k} y1={0} x2={W * k} y2={H} />
            ))}
            <line x1={W * 0.08} y1={H * 0.92} x2={W * 0.92} y2={H * 0.08} strokeDasharray="10 14" />
            {[0.25, 0.5, 0.75].map((k) => {
              const t = (k - 0.08) / 0.84;
              return <circle key={k} cx={W * k} cy={H * (0.92 - 0.84 * t)} r={9} fill={s.fg} stroke="none" />;
            })}
          </g>
        )}
      </svg>
      <PinnedMark x={x} y={y} width={w} color={s.fg} />
    </AbsoluteFill>
  );
};

/** The mark tiled as a signature pattern, rows offset by half a step. */
export const Pattern: React.FC<ShotProps<PatternShot>> = ({ shot, config, tone }) => {
  const s = scheme(config.brand, tone);
  const logo = useLogo();
  const id = `p${useId().replace(/:/g, '')}`;
  const { width: W, height: H } = config;
  const tw = (shot.tile ?? 0.16) * W;
  const th = tw / logo.aspect;
  const sx = tw * 1.55;
  const sy = th * 1.9;
  const mark = (px: number, py: number) => (
    <svg x={px} y={py} width={tw} height={th} viewBox={logo.viewBox}>
      <g fill={s.fg} dangerouslySetInnerHTML={{ __html: logo.inner }} />
    </svg>
  );
  return (
    <AbsoluteFill style={{ background: s.bg }}>
      <svg width={W} height={H}>
        <defs>
          <pattern
            id={id}
            width={sx}
            height={sy * 2}
            patternUnits="userSpaceOnUse"
            patternTransform={`translate(${W / 2} ${H / 2}) rotate(${shot.rotate ?? -18})`}
          >
            {mark(0, 0)}
            {mark(sx / 2, sy)}
            {mark(sx / 2 - sx, sy)}
          </pattern>
        </defs>
        <rect width={W} height={H} fill={`url(#${id})`} />
      </svg>
    </AbsoluteFill>
  );
};

/** Mark + name + tagline. */
export const Lockup: React.FC<ShotProps<LockupShot>> = ({ shot, config, tone }) => {
  const s = scheme(config.brand, tone);
  const logo = useLogo();
  const font = brandFont(config.brand.font);
  const { x, y, w } = matchPx(config, shot.logoScale);
  const { name, tagline } = config.brand;
  const markH = w / logo.aspect;
  const nameSize = w * 0.38;
  if ((shot.layout ?? 'stacked') === 'inline') {
    return (
      <AbsoluteFill style={{ background: s.bg }}>
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: y - markH * 0.35,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            gap: w * 0.18,
          }}
        >
          <Mark width={w * 0.7} color={s.fg} />
          <div style={{ fontFamily: font, fontWeight: 700, fontSize: nameSize, color: s.fg, letterSpacing: '-0.02em' }}>
            {name}
          </div>
        </div>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{ background: s.bg }}>
      <PinnedMark x={x} y={y} width={w} color={s.fg} />
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: y + markH / 2 + w * 0.22,
          textAlign: 'center',
          fontFamily: font,
          color: s.fg,
        }}
      >
        <div style={{ fontWeight: 700, fontSize: nameSize, letterSpacing: '-0.02em', lineHeight: 1 }}>{name}</div>
        {tagline && (
          <div style={{ fontWeight: 400, fontSize: nameSize * 0.32, marginTop: nameSize * 0.35, opacity: 0.7 }}>{tagline}</div>
        )}
      </div>
    </AbsoluteFill>
  );
};

/** Brand buttons staggered across the frame, some bleeding off the edges. */
export const Ui: React.FC<ShotProps<UiShot>> = ({ shot, config, tone }) => {
  const s = scheme(config.brand, tone);
  const c = config.brand.colors;
  const font = brandFont(config.brand.font);
  const { width: W, height: H } = config;
  const labels = shot.labels ?? ['Get started', 'Book a call', 'See the work', 'About the studio', 'Say hello'];
  const offsets = [-0.14, 0.2, -0.04, 0.28, 0.02];
  const styles = [
    { background: c.primary, color: c.onPrimary, border: 'none' },
    { background: 'transparent', color: s.fg, border: `4px solid ${s.fg}` },
    { background: c.accent, color: c.onAccent, border: 'none' },
    { background: alpha(s.fg, 0.1), color: s.fg, border: 'none' },
    { background: s.fg, color: s.bg, border: 'none' },
  ];
  const pillH = H * 0.078;
  return (
    <AbsoluteFill style={{ background: s.bg, overflow: 'hidden' }}>
      {labels.map((label, i) => (
        <div
          key={label}
          style={{
            position: 'absolute',
            top: H * 0.15 + i * H * 0.145,
            left: W * (0.12 + offsets[i % offsets.length]),
            height: pillH,
            padding: `0 ${pillH * 0.55}px`,
            borderRadius: pillH,
            display: 'flex',
            alignItems: 'center',
            gap: pillH * 0.3,
            whiteSpace: 'nowrap',
            fontFamily: font,
            fontWeight: 600,
            fontSize: pillH * 0.36,
            boxSizing: 'border-box',
            ...styles[i % styles.length],
          }}
        >
          {i === 0 && <Mark width={pillH * 0.6} color={c.onPrimary} />}
          {label}
          <span style={{ fontWeight: 400 }}>→</span>
        </div>
      ))}
    </AbsoluteFill>
  );
};
