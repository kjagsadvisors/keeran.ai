import React from 'react';
import { AbsoluteFill } from 'remotion';
import type { AppIconShot, BadgeShot, CardShot, SignShot } from '../../config/types';
import { brandFont } from '../../lib/fonts';
import { mix, scheme } from '../../lib/tones';
import { Mark } from '../Logo';
import { Material } from '../Material';
import { matchPx, objectScheme, type ShotProps } from './common';

/** Two business cards lying on a surface: a logo face and a name face. */
export const Card: React.FC<ShotProps<CardShot>> = ({ shot, config, tone }) => {
  const bg = scheme(config.brand, tone);
  const front = objectScheme(config, tone, shot.objectTone);
  const back = scheme(config.brand, bg.dark ? 'light' : 'dark');
  const font = brandFont(config.brand.font);
  const { width: W, height: H } = config;
  const cw = W * 0.6;
  const ch = cw / 1.6;
  const card = (s: typeof front, dx: number, dy: number, rot: number, face: React.ReactNode) => (
    <div
      style={{
        position: 'absolute',
        left: W / 2 - cw / 2 + dx,
        top: H * 0.48 - ch / 2 + dy,
        width: cw,
        height: ch,
        background: `linear-gradient(135deg, ${mix(s.bg, '#ffffff', 0.08)}, ${s.bg} 55%, ${mix(s.bg, '#000000', 0.12)})`,
        borderRadius: 6,
        transform: `rotate(${rot}deg)`,
        boxShadow: `${bg.dark ? '18px 26px 40px rgba(0,0,0,0.65)' : '22px 30px 44px rgba(0,0,0,0.32)'}, 0 1px 0 rgba(255,255,255,0.15) inset`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden',
      }}
    >
      {face}
    </div>
  );
  return (
    <AbsoluteFill>
      <Material kind={shot.material ?? 'plaster'} scheme={bg} />
      <AbsoluteFill style={{ transform: 'perspective(2200px) rotateX(46deg) rotateZ(-24deg) scale(1.05)' }}>
        {card(back, -W * 0.1, -H * 0.13, 6, (
          <div style={{ fontFamily: font, color: back.fg, textAlign: 'left', width: '80%' }}>
            <div style={{ fontWeight: 700, fontSize: cw * 0.08 }}>{config.brand.name}</div>
            {config.brand.tagline && <div style={{ fontSize: cw * 0.035, opacity: 0.7, marginTop: 10 }}>{config.brand.tagline}</div>}
          </div>
        ))}
        {card(front, W * 0.05, H * 0.06, -4, <Mark width={cw * 0.34} color={front.fg} />)}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** App icon tile with a keyline bezel, sitting on the match point. */
export const AppIcon: React.FC<ShotProps<AppIconShot>> = ({ shot, config, tone }) => {
  const bg = scheme(config.brand, tone);
  const tile = objectScheme(config, tone, shot.objectTone);
  const { x, y } = matchPx(config);
  const S = config.width * 0.34 * (shot.logoScale ?? 1);
  const bezel = S * 1.22;
  return (
    <AbsoluteFill style={{ background: `radial-gradient(70% 45% at 50% 45%, ${mix(bg.bg, '#ffffff', 0.08)}, ${bg.bg})` }}>
      <div
        style={{
          position: 'absolute',
          left: x - bezel / 2,
          top: y - bezel / 2,
          width: bezel,
          height: bezel,
          borderRadius: bezel * 0.25,
          background: mix(bg.bg, bg.fg, 0.28),
          boxShadow: `0 ${S * 0.08}px ${S * 0.2}px rgba(0,0,0,${bg.dark ? 0.6 : 0.25})`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: x - S / 2,
          top: y - S / 2,
          width: S,
          height: S,
          borderRadius: S * 0.225,
          background: `linear-gradient(160deg, ${mix(tile.bg, '#ffffff', 0.18)}, ${tile.bg} 50%, ${mix(tile.bg, '#000000', 0.15)})`,
          boxShadow: 'inset 0 2px 0 rgba(255,255,255,0.35), inset 0 -3px 6px rgba(0,0,0,0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Mark width={S * 0.56} color={tile.fg} />
      </div>
    </AbsoluteFill>
  );
};

/** ID badge on a lanyard over concrete. */
export const Badge: React.FC<ShotProps<BadgeShot>> = ({ shot, config, tone }) => {
  const bg = scheme(config.brand, tone);
  const card = objectScheme(config, tone, shot.objectTone);
  const c = config.brand.colors;
  const font = brandFont(config.brand.font);
  const { width: W, height: H } = config;
  const bw = W * 0.46;
  const bh = bw * 1.55;
  const top = H * 0.36;
  return (
    <AbsoluteFill>
      <Material kind="concrete" scheme={bg} />
      {/* strap */}
      <div
        style={{
          position: 'absolute',
          left: W / 2 - W * 0.045,
          top: 0,
          width: W * 0.09,
          height: top - H * 0.015,
          background: `linear-gradient(90deg, ${mix(c.primary, '#000000', 0.25)}, ${c.primary} 30%, ${c.primary} 70%, ${mix(c.primary, '#000000', 0.25)})`,
          boxShadow: '10px 0 24px rgba(0,0,0,0.35)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: '50%',
            top: H * 0.02,
            transform: 'translateX(-50%) rotate(90deg)',
            transformOrigin: 'center',
            whiteSpace: 'nowrap',
            fontFamily: font,
            fontWeight: 700,
            fontSize: W * 0.03,
            color: c.onPrimary,
            letterSpacing: '0.2em',
            marginTop: H * 0.12,
          }}
        >
          {`${config.brand.name.toUpperCase()}   ${config.brand.name.toUpperCase()}`}
        </div>
      </div>
      {/* clip */}
      <div
        style={{
          position: 'absolute',
          left: W / 2 - W * 0.035,
          top: top - H * 0.035,
          width: W * 0.07,
          height: H * 0.045,
          borderRadius: 10,
          background: 'linear-gradient(90deg, #8a8d91, #e9ebee 45%, #9a9da2)',
          boxShadow: '4px 6px 10px rgba(0,0,0,0.4)',
        }}
      />
      {/* card */}
      <div
        style={{
          position: 'absolute',
          left: W / 2 - bw / 2,
          top,
          width: bw,
          height: bh,
          borderRadius: 18,
          transform: 'rotate(3deg)',
          transformOrigin: '50% 0',
          background: `linear-gradient(165deg, ${mix(card.bg, '#ffffff', 0.1)}, ${card.bg} 60%, ${mix(card.bg, '#000000', 0.12)})`,
          boxShadow: `24px 34px 50px rgba(0,0,0,${bg.dark ? 0.7 : 0.38})`,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          fontFamily: font,
          color: card.fg,
        }}
      >
        <div style={{ width: bw * 0.22, height: bw * 0.045, borderRadius: 99, background: bg.bg, marginTop: bw * 0.06, opacity: 0.85 }} />
        <div style={{ flex: 1, display: 'flex', alignItems: 'center' }}>
          <Mark width={bw * 0.5} color={card.fg} />
        </div>
        <div style={{ fontWeight: 600, fontSize: bw * 0.075 }}>{shot.person ?? 'Alex Morgan'}</div>
        <div style={{ fontSize: bw * 0.05, opacity: 0.7, marginTop: 6, marginBottom: bw * 0.12 }}>{shot.role ?? 'Creative Director'}</div>
      </div>
    </AbsoluteFill>
  );
};

/** Free-standing totem in a soft studio corner. */
export const Sign: React.FC<ShotProps<SignShot>> = ({ shot, config, tone }) => {
  const bg = scheme(config.brand, tone);
  const panel = objectScheme(config, tone, shot.objectTone);
  const font = brandFont(config.brand.font);
  const { width: W, height: H } = config;
  const { y } = matchPx(config);
  const pw = W * 0.42;
  const floorY = H * 0.8;
  const top = y - H * 0.12;
  return (
    <AbsoluteFill style={{ background: `linear-gradient(180deg, ${mix(bg.bg, '#000000', 0.18)}, ${bg.bg} 70%)` }}>
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: floorY,
          bottom: 0,
          background: `linear-gradient(180deg, ${mix(bg.bg, '#000000', bg.dark ? 0.3 : 0.12)}, ${mix(bg.bg, '#000000', bg.dark ? 0.5 : 0.25)})`,
        }}
      />
      {/* floor shadow */}
      <div
        style={{
          position: 'absolute',
          left: W / 2 - pw * 0.4,
          top: floorY - 20,
          width: pw * 1.4,
          height: 60,
          borderRadius: '50%',
          background: 'rgba(0,0,0,0.45)',
          filter: 'blur(18px)',
        }}
      />
      <div style={{ position: 'absolute', inset: 0, perspective: 2000 }}>
        <div
          style={{
            position: 'absolute',
            left: W / 2 - pw / 2,
            top,
            width: pw,
            height: floorY - top,
            borderRadius: '24px 24px 4px 4px',
            transform: 'rotateY(-16deg)',
            background: `linear-gradient(100deg, ${mix(panel.bg, '#ffffff', 0.12)}, ${panel.bg} 45%, ${mix(panel.bg, '#000000', 0.2)})`,
            boxShadow: `-18px 0 0 ${mix(panel.bg, '#000000', 0.35)}`,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            paddingTop: H * 0.07,
            boxSizing: 'border-box',
            fontFamily: font,
            color: panel.fg,
          }}
        >
          <Mark width={pw * 0.42} color={panel.fg} />
          <div style={{ fontWeight: 700, fontSize: pw * 0.15, marginTop: pw * 0.12, letterSpacing: '-0.02em' }}>{config.brand.name}</div>
          {config.brand.tagline && (
            <div style={{ fontSize: pw * 0.05, opacity: 0.75, marginTop: pw * 0.04, width: '75%', textAlign: 'center' }}>
              {config.brand.tagline}
            </div>
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};
