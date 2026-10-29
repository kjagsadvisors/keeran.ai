import React from 'react';
import { AbsoluteFill } from 'remotion';
import { LogoProvider, Mark, useLogo } from './components/Logo';
import { config } from './config/match-config';
import { brandFont } from './lib/fonts';

/*
 * Textures for the Blender scenes (npm run textures → blender/build/).
 * Masks are white on black and square, so Blender can map them without knowing the
 * layout. Keep these numbers in sync with LOCKUP_* in blender/render_shots.py.
 */
export const MASK = 2048;
export const LOCKUP_MARK_Y = 0.36; // mark centre, fraction from top
export const LOCKUP_MARK_W = 0.4; // mark width, fraction of the square

const { brand } = config;

/** The mark, full width, centred. */
export const LogoMask: React.FC = () => (
  <LogoProvider src={brand.logo}>
    <AbsoluteFill style={{ background: '#000', alignItems: 'center', justifyContent: 'center' }}>
      <Mark width={MASK} color="#fff" />
    </AbsoluteFill>
  </LogoProvider>
);

const Lockup: React.FC = () => {
  const logo = useLogo();
  const font = brandFont(brand.font);
  const markW = MASK * LOCKUP_MARK_W;
  const markH = markW / logo.aspect;
  return (
    <AbsoluteFill style={{ background: '#000', color: '#fff', fontFamily: font }}>
      <div style={{ position: 'absolute', left: (MASK - markW) / 2, top: MASK * LOCKUP_MARK_Y - markH / 2 }}>
        <Mark width={markW} color="#fff" />
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, top: MASK * 0.56, textAlign: 'center' }}>
        <div style={{ fontWeight: 700, fontSize: MASK * 0.13, letterSpacing: '-0.02em', lineHeight: 1 }}>{brand.name}</div>
        {brand.tagline && <div style={{ fontWeight: 400, fontSize: MASK * 0.042, marginTop: MASK * 0.045, opacity: 0.85 }}>{brand.tagline}</div>}
      </div>
    </AbsoluteFill>
  );
};

/** Mark + name + tagline, mark centre at LOCKUP_MARK_Y. */
export const LockupMask: React.FC = () => (
  <LogoProvider src={brand.logo}>
    <Lockup />
  </LogoProvider>
);

const Screen: React.FC<{ dark: boolean }> = ({ dark }) => {
  const c = brand.colors;
  const bg = dark ? c.primary : c.paper;
  const fg = dark ? c.onPrimary : c.ink;
  const font = brandFont(brand.font);
  const W = 1179;
  return (
    <AbsoluteFill style={{ background: bg, color: fg, fontFamily: font }}>
      <div style={{ position: 'absolute', top: 52, left: 120, fontWeight: 600, fontSize: 52 }}>9:41</div>
      <div style={{ position: 'absolute', top: 60, right: 110, display: 'flex', gap: 14, alignItems: 'flex-end' }}>
        {[18, 26, 34, 42].map((h) => (
          <div key={h} style={{ width: 11, height: h, background: fg, borderRadius: 3 }} />
        ))}
        <div style={{ width: 70, height: 36, border: `4px solid ${fg}`, borderRadius: 10, marginLeft: 16, padding: 4, boxSizing: 'border-box' }}>
          <div style={{ width: '75%', height: '100%', background: fg, borderRadius: 4 }} />
        </div>
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 2556 * 0.4, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Mark width={W * 0.4} color={fg} />
        <div style={{ fontWeight: 700, fontSize: 104, marginTop: 90, letterSpacing: '-0.02em' }}>{brand.name}</div>
      </div>
      <div
        style={{
          position: 'absolute',
          left: 90,
          right: 90,
          bottom: 190,
          height: 150,
          borderRadius: 75,
          background: fg,
          color: bg,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 600,
          fontSize: 50,
        }}
      >
        Get started
      </div>
      <div style={{ position: 'absolute', left: W / 2 - 200, width: 400, bottom: 30, height: 14, borderRadius: 7, background: fg, opacity: 0.8 }} />
    </AbsoluteFill>
  );
};

/** Phone screen with the mark at 40% width, centred horizontally. */
export const ScreenA: React.FC = () => (
  <LogoProvider src={brand.logo}>
    <Screen dark />
  </LogoProvider>
);
export const ScreenB: React.FC = () => (
  <LogoProvider src={brand.logo}>
    <Screen dark={false} />
  </LogoProvider>
);
