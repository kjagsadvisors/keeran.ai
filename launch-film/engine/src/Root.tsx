import React from 'react';
import { Composition } from 'remotion';
import { Film } from './Film';
import plan from './plan.json';

const frames = Math.round(plan.total * plan.fps);
export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Film" component={Film} durationInFrames={frames} fps={plan.fps} width={1920} height={1080} />
    <Composition id="FilmVertical" component={Film} durationInFrames={frames} fps={plan.fps} width={1080} height={1920} />
  </>
);
