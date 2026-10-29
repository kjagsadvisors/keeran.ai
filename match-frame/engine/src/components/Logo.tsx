import React, { createContext, useContext, useEffect, useState } from 'react';
import { continueRender, delayRender, staticFile } from 'remotion';
import type { Finish } from '../config/types';

interface LogoData {
  viewBox: string;
  /** width / height of the viewBox. */
  aspect: number;
  /** Inner SVG markup with fills stripped so a group fill can recolour it. */
  inner: string;
}

const LogoContext = createContext<LogoData | null>(null);

const parse = (svg: string): LogoData => {
  const viewBox = svg.match(/viewBox="([^"]+)"/)?.[1];
  if (!viewBox) throw new Error('Logo SVG needs a viewBox');
  const [, , w, h] = viewBox.split(/[\s,]+/).map(Number);
  const inner = svg
    .replace(/^[\s\S]*?<svg[^>]*>/, '')
    .replace(/<\/svg>\s*$/, '')
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\sfill="(?!none)[^"]*"/g, '')
    .replace(/fill:\s*(?!none)[^;"]+;?/g, '');
  return { viewBox, aspect: w / h, inner };
};

/** Loads the SVG once and holds the render until it is ready, so every frame has the logo. */
export const LogoProvider: React.FC<{ src: string; children: React.ReactNode }> = ({ src, children }) => {
  const [data, setData] = useState<LogoData | null>(null);
  const [handle] = useState(() => delayRender(`logo ${src}`));
  useEffect(() => {
    fetch(staticFile(src))
      .then((r) => r.text())
      .then((t) => {
        setData(parse(t));
        continueRender(handle);
      });
  }, [src, handle]);
  return data ? <LogoContext.Provider value={data}>{children}</LogoContext.Provider> : null;
};

export const useLogo = () => {
  const d = useContext(LogoContext);
  if (!d) throw new Error('useLogo outside LogoProvider');
  return d;
};

const finishFilter = (finish: Finish, dark: boolean) => {
  if (finish === 'emboss') {
    return dark
      ? 'drop-shadow(-2px -2px 0 rgba(255,255,255,0.3)) drop-shadow(4px 6px 5px rgba(0,0,0,0.85))'
      : 'drop-shadow(-2px -2px 0 rgba(255,255,255,0.85)) drop-shadow(4px 6px 6px rgba(0,0,0,0.4))';
  }
  if (finish === 'deboss') {
    return dark
      ? 'drop-shadow(1.5px 2px 0 rgba(255,255,255,0.14)) drop-shadow(-1px -1.5px 1px rgba(0,0,0,0.8))'
      : 'drop-shadow(1.5px 2px 0 rgba(255,255,255,0.8)) drop-shadow(-1px -1.5px 1px rgba(0,0,0,0.4))';
  }
  return undefined;
};

/** The mark, recoloured. Width in px; height follows the SVG aspect. */
export const Mark: React.FC<{
  width: number;
  color: string;
  finish?: Finish;
  dark?: boolean;
  style?: React.CSSProperties;
}> = ({ width, color, finish = 'flat', dark = false, style }) => {
  const logo = useLogo();
  return (
    <svg
      viewBox={logo.viewBox}
      width={width}
      height={width / logo.aspect}
      style={{ display: 'block', overflow: 'visible', filter: finishFilter(finish, dark), ...style }}
    >
      <g fill={color} dangerouslySetInnerHTML={{ __html: logo.inner }} />
    </svg>
  );
};

/** The mark centred on a point (frame px). Used for the match point. */
export const PinnedMark: React.FC<{
  x: number;
  y: number;
  width: number;
  color: string;
  finish?: Finish;
  dark?: boolean;
  style?: React.CSSProperties;
}> = ({ x, y, width, ...rest }) => {
  const logo = useLogo();
  const h = width / logo.aspect;
  return (
    <div style={{ position: 'absolute', left: x - width / 2, top: y - h / 2 }}>
      <Mark width={width} {...rest} />
    </div>
  );
};
