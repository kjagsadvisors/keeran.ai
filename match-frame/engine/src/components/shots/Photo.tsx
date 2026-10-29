import React from 'react';
import { AbsoluteFill, Img, staticFile } from 'remotion';
import type { PhotoShot } from '../../config/types';
import { treatmentFilter } from '../../lib/tones';
import { Mark, PinnedMark, useLogo } from '../Logo';
import { Noise } from '../Material';
import { matchPx, type ShotProps } from './common';

type Pt = [number, number];

/** Homography taking the w×h rectangle at the origin onto quad (TL, TR, BR, BL), as a CSS matrix3d. */
const quadMatrix = (w: number, h: number, q: [Pt, Pt, Pt, Pt]): string => {
  const src: Pt[] = [
    [0, 0],
    [w, 0],
    [w, h],
    [0, h],
  ];
  const A: number[][] = [];
  const b: number[] = [];
  src.forEach(([x, y], i) => {
    const [u, v] = q[i];
    A.push([x, y, 1, 0, 0, 0, -u * x, -u * y]);
    b.push(u);
    A.push([0, 0, 0, x, y, 1, -v * x, -v * y]);
    b.push(v);
  });
  // Gaussian elimination with partial pivoting on the 8×8 system.
  for (let c = 0; c < 8; c++) {
    let p = c;
    for (let r = c + 1; r < 8; r++) if (Math.abs(A[r][c]) > Math.abs(A[p][c])) p = r;
    [A[c], A[p]] = [A[p], A[c]];
    [b[c], b[p]] = [b[p], b[c]];
    for (let r = 0; r < 8; r++) {
      if (r === c) continue;
      const f = A[r][c] / A[c][c];
      for (let k = c; k < 8; k++) A[r][k] -= f * A[c][k];
      b[r] -= f * b[c];
    }
  }
  const [a, bb, c, d, e, f, g, hh] = b.map((v, i) => v / A[i][i]);
  return `matrix3d(${a},${d},0,${g},${bb},${e},0,${hh},0,0,1,0,${c},${f},0,1)`;
};

/** A prepared 9:16 image. B is `srcB` or a filtered copy; the logo can be composited on a quad. */
export const Photo: React.FC<ShotProps<PhotoShot> & { variant: 'a' | 'b' }> = ({ shot, config, variant }) => {
  const logo = useLogo();
  const { width: W, height: H } = config;
  const useB = variant === 'b' && shot.srcB;
  const filter = variant === 'b' && !shot.srcB ? treatmentFilter(shot.treatment ?? 'mono') : undefined;
  const l = shot.logo;
  const color = l?.color ?? config.brand.colors.paper;
  let overlay: React.ReactNode = null;
  if (l?.quad) {
    const mw = 400;
    const mh = mw / logo.aspect;
    const q = l.quad.map(([x, y]) => [x * W, y * H]) as [Pt, Pt, Pt, Pt];
    overlay = (
      <div style={{ position: 'absolute', left: 0, top: 0, width: mw, height: mh, transformOrigin: '0 0', transform: quadMatrix(mw, mh, q) }}>
        <Mark width={mw} color={color} />
      </div>
    );
  } else if (l) {
    const { x, y, w } = matchPx(config, shot.logoScale);
    overlay = <PinnedMark x={x} y={y} width={w} color={color} />;
  }
  const grain = shot.grain ?? 1;
  // A new grain pattern per cut, like separate photographs.
  const seed = [...`${shot.id}${variant}`].reduce((h, ch) => (h * 31 + ch.charCodeAt(0)) % 997, 7);
  return (
    <AbsoluteFill style={{ filter, background: '#000' }}>
      <Img src={staticFile(useB ? shot.srcB! : shot.src)} style={{ width: W, height: H, objectFit: 'cover' }} />
      {overlay && (
        <AbsoluteFill style={{ mixBlendMode: l?.blend ?? 'normal', opacity: l?.opacity ?? 1 }}>{overlay}</AbsoluteFill>
      )}
      {grain > 0 && (
        <AbsoluteFill style={{ opacity: Math.min(1, grain) }}>
          <Noise freq="0.95" octaves={1} seed={seed} gain={0.16} threshold={0.4} />
          <Noise freq="0.9" octaves={1} seed={seed + 3} gain={0.12} threshold={0.4} light />
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};
