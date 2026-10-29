import React from 'react';
import { AbsoluteFill } from 'remotion';
import type { MatchFrameConfig, Shot as ShotT } from '../config/types';
import { toneFor, treatmentFilter } from '../lib/tones';
import { Grid, Lockup, Pattern, Surface, Ui } from './shots/flat';
import { AppIcon, Badge, Card, Sign } from './shots/mockups';
import { Photo } from './shots/Photo';

/** Renders one cut. Procedural B variants are a tone swap, or a filtered A when `treatment` is set. */
export const Shot: React.FC<{ shot: ShotT; variant: 'a' | 'b'; config: MatchFrameConfig }> = ({ shot, variant, config }) => {
  if (shot.kind === 'photo') return <Photo shot={shot} config={config} tone="light" variant={variant} />;

  const filtered = variant === 'b' && shot.treatment && shot.treatment !== 'none';
  const tone = toneFor(config.brand, shot, filtered ? 'a' : variant);
  const props = { config, tone };
  const body = (() => {
    switch (shot.kind) {
      case 'surface':
        return <Surface shot={shot} {...props} />;
      case 'grid':
        return <Grid shot={shot} {...props} />;
      case 'pattern':
        return <Pattern shot={shot} {...props} />;
      case 'lockup':
        return <Lockup shot={shot} {...props} />;
      case 'ui':
        return <Ui shot={shot} {...props} />;
      case 'card':
        return <Card shot={shot} {...props} />;
      case 'app-icon':
        return <AppIcon shot={shot} {...props} />;
      case 'badge':
        return <Badge shot={shot} {...props} />;
      case 'sign':
        return <Sign shot={shot} {...props} />;
    }
  })();
  return <AbsoluteFill style={{ filter: filtered ? treatmentFilter(shot.treatment!) : undefined }}>{body}</AbsoluteFill>;
};
