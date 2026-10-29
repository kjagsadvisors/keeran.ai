import React, { useEffect, useMemo } from 'react';
import { AbsoluteFill, Audio, getStaticFiles, prefetch, staticFile, useCurrentFrame } from 'remotion';
import { LogoProvider } from './components/Logo';
import { Shot } from './components/Shot';
import { variants, type Variant } from './config/match-config';
import { buildTimeline, cutAt, timelineDuration } from './lib/timeline';

export const durationOf = (variant: Variant) => timelineDuration(buildTimeline(variants[variant]));

export const MatchFrame: React.FC<{ variant: Variant }> = ({ variant }) => {
  const config = variants[variant];
  const timeline = useMemo(() => buildTimeline(config), [config]);
  const frame = useCurrentFrame();
  const cut = cutAt(timeline, frame);
  const music = config.audio?.music;
  // Reference tracks are gitignored, so render silent rather than fail when one is missing.
  const hasMusic = useMemo(() => !!music && getStaticFiles().some((f) => f.name === music), [music]);

  // Keep Studio playback from stalling on the first pass through the photos.
  useEffect(() => {
    const srcs = config.shots.flatMap((s) => (s.kind === 'photo' ? [s.src, ...(s.srcB ? [s.srcB] : [])] : []));
    const handles = srcs.map((src) => prefetch(staticFile(src)));
    return () => handles.forEach((h) => h.free());
  }, [config]);

  return (
    <LogoProvider src={config.brand.logo}>
      <AbsoluteFill style={{ background: '#000' }}>
        <Shot shot={cut.shot} variant={cut.variant} config={config} />
      </AbsoluteFill>
      {hasMusic && (
        <Audio
          src={staticFile(music!)}
          trimBefore={Math.round((config.audio?.startFrom ?? 0) * config.fps)}
          volume={config.audio?.volume ?? 1}
        />
      )}
    </LogoProvider>
  );
};
