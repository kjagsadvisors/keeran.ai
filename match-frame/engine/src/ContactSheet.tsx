import React from 'react';
import { AbsoluteFill } from 'remotion';
import { LogoProvider } from './components/Logo';
import { Shot } from './components/Shot';
import { config } from './config/match-config';
import { expandShots } from './lib/timeline';

/** QA still: every cut in list order, A and B side by side, with a crosshair on the match point. */
const COLS = 8;
const SCALE = 0.2;
const GAP = 8;
const LABEL = 30;

const cuts = expandShots(config.shots);
const tileW = config.width * SCALE;
const tileH = config.height * SCALE;

export const sheetSize = {
  width: COLS * tileW + (COLS + 1) * GAP,
  height: Math.ceil(cuts.length / COLS) * (tileH + LABEL + GAP) + GAP,
};

export const ContactSheet: React.FC = () => (
  <LogoProvider src={config.brand.logo}>
    <AbsoluteFill style={{ background: '#2a2a2a', padding: GAP, display: 'flex', flexDirection: 'row', flexWrap: 'wrap', gap: GAP, alignContent: 'flex-start' }}>
      {cuts.map((c, i) => (
        <div key={i} style={{ width: tileW, height: tileH + LABEL }}>
          <div style={{ height: LABEL, color: '#ddd', font: '600 17px/30px monospace' }}>
            {i + 1}. {c.shot.id}:{c.variant}
          </div>
          <div style={{ width: tileW, height: tileH, overflow: 'hidden', position: 'relative' }}>
            <div style={{ width: config.width, height: config.height, transform: `scale(${SCALE})`, transformOrigin: '0 0', position: 'relative' }}>
              <Shot shot={c.shot} variant={c.variant} config={config} />
            </div>
            <div style={{ position: 'absolute', left: config.match.x * tileW - 8, top: config.match.y * tileH, width: 16, height: 1, background: '#ff2d55' }} />
            <div style={{ position: 'absolute', left: config.match.x * tileW, top: config.match.y * tileH - 8, width: 1, height: 16, background: '#ff2d55' }} />
          </div>
        </div>
      ))}
    </AbsoluteFill>
  </LogoProvider>
);
