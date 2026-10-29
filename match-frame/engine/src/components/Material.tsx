import React, { useId } from 'react';
import { AbsoluteFill } from 'remotion';
import type { Material as MaterialKind } from '../config/types';
import type { Scheme } from '../lib/tones';

/**
 * SVG turbulence → alpha speckle. Alpha = gain × (channel − threshold), so a higher
 * threshold gives sparser marks. `light` speckles are white, otherwise black.
 */
export const Noise: React.FC<{
  freq: string;
  octaves?: number;
  seed?: number;
  gain: number;
  threshold?: number;
  light?: boolean;
  blend?: React.CSSProperties['mixBlendMode'];
}> = ({ freq, octaves = 3, seed = 1, gain, threshold = 0.5, light = false, blend }) => {
  const id = `n${useId().replace(/:/g, '')}`;
  const v = light ? 1 : 0;
  // Read R for dark marks and G for light marks so the two layers don't line up.
  const row = light ? `0 ${gain} 0 0 ${-gain * threshold}` : `${gain} 0 0 0 ${-gain * threshold}`;
  return (
    <svg width="100%" height="100%" style={{ position: 'absolute', inset: 0, mixBlendMode: blend }}>
      <filter id={id} x="0" y="0" width="100%" height="100%" colorInterpolationFilters="sRGB">
        <feTurbulence type="fractalNoise" baseFrequency={freq} numOctaves={octaves} seed={seed} stitchTiles="stitch" />
        <feColorMatrix type="matrix" values={`0 0 0 0 ${v}  0 0 0 0 ${v}  0 0 0 0 ${v}  ${row}`} />
      </filter>
      <rect width="100%" height="100%" filter={`url(#${id})`} />
    </svg>
  );
};

const Lighting: React.FC<{ dark: boolean }> = ({ dark }) => (
  <AbsoluteFill
    style={{
      background: dark
        ? 'radial-gradient(90% 60% at 35% 30%, rgba(255,255,255,0.10), transparent 70%), linear-gradient(180deg, rgba(0,0,0,0.25), transparent 30%, transparent 60%, rgba(0,0,0,0.45))'
        : 'radial-gradient(90% 60% at 35% 25%, rgba(255,255,255,0.35), transparent 70%), linear-gradient(180deg, rgba(0,0,0,0.10), transparent 30%, transparent 65%, rgba(0,0,0,0.22))',
    }}
  />
);

/** Window light: shadow bars on light surfaces, a light beam on dark ones. */
const WindowLight: React.FC<{ dark: boolean }> = ({ dark }) => (
  <AbsoluteFill style={{ mixBlendMode: dark ? 'screen' : 'multiply', overflow: 'hidden' }}>
    <div
      style={{
        position: 'absolute',
        left: '-40%',
        top: '-10%',
        width: '180%',
        height: '120%',
        transform: 'rotate(-32deg)',
        filter: 'blur(22px)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        gap: 70,
      }}
    >
      {(dark ? [520] : [380, 120]).map((h, i) => (
        <div key={i} style={{ height: h, background: dark ? 'rgba(255,255,255,0.16)' : 'rgba(0,0,0,0.30)' }} />
      ))}
    </div>
  </AbsoluteFill>
);

export const Material: React.FC<{ kind: MaterialKind; scheme: Scheme; shadow?: boolean; seed?: number }> = ({
  kind,
  scheme,
  shadow = false,
  seed = 3,
}) => {
  const { bg, dark } = scheme;
  return (
    <AbsoluteFill style={{ background: bg, overflow: 'hidden' }}>
      {kind === 'concrete' && (
        <>
          <Noise freq="0.005" octaves={4} seed={seed} gain={dark ? 0.55 : 0.45} threshold={0.42} />
          <Noise freq="0.004" octaves={3} seed={seed + 7} gain={dark ? 0.3 : 0.6} threshold={0.45} light />
          <Noise freq="0.85" octaves={1} seed={seed + 2} gain={dark ? 0.45 : 0.3} threshold={0.42} />
          <Noise freq="0.6" octaves={1} seed={seed + 5} gain={dark ? 0.25 : 0.4} threshold={0.42} light />
          <Noise freq="0.06" octaves={2} seed={seed + 9} gain={dark ? 4 : 3} threshold={0.76} />
        </>
      )}
      {kind === 'plaster' && (
        <>
          <Noise freq="0.0025" octaves={5} seed={seed} gain={dark ? 0.8 : 0.55} threshold={0.4} />
          <Noise freq="0.012" octaves={3} seed={seed + 4} gain={dark ? 0.35 : 0.8} threshold={0.45} light />
          <Noise freq="0.85" octaves={1} seed={seed + 2} gain={0.3} threshold={0.42} />
        </>
      )}
      {kind === 'paper' && (
        <>
          <Noise freq="0.9" octaves={1} seed={seed} gain={dark ? 0.35 : 0.22} threshold={0.42} />
          <Noise freq="0.03" octaves={3} seed={seed + 3} gain={dark ? 0.2 : 0.3} threshold={0.4} light />
        </>
      )}
      {kind === 'metal' && (
        <>
          <AbsoluteFill
            style={{
              background: dark
                ? 'linear-gradient(115deg, rgba(255,255,255,0) 20%, rgba(255,255,255,0.18) 42%, rgba(255,255,255,0) 60%)'
                : 'linear-gradient(115deg, rgba(0,0,0,0.12) 15%, rgba(255,255,255,0.55) 42%, rgba(0,0,0,0.1) 70%)',
            }}
          />
          <Noise freq="0.0015 0.6" octaves={3} seed={seed} gain={dark ? 1.1 : 0.9} threshold={0.45} />
          <Noise freq="0.002 0.5" octaves={3} seed={seed + 4} gain={dark ? 0.6 : 1} threshold={0.45} light />
        </>
      )}
      {kind === 'gradient' && (
        <>
          <AbsoluteFill
            style={{
              background: dark
                ? 'linear-gradient(172deg, rgba(0,0,0,0.6) 0%, rgba(255,255,255,0.10) 38%, rgba(255,255,255,0.22) 47%, rgba(0,0,0,0.0) 58%, rgba(0,0,0,0.65) 100%)'
                : 'linear-gradient(172deg, rgba(0,0,0,0.35) 0%, rgba(255,255,255,0.0) 30%, rgba(255,255,255,0.75) 46%, rgba(0,0,0,0.05) 62%, rgba(0,0,0,0.45) 100%)',
            }}
          />
          <Noise freq="0.85" octaves={1} seed={seed} gain={0.35} threshold={0.45} />
        </>
      )}
      {kind !== 'flat' && kind !== 'gradient' && <Lighting dark={dark} />}
      {shadow && <WindowLight dark={dark} />}
    </AbsoluteFill>
  );
};
