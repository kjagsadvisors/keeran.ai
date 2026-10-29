import { loadFont as loadInter } from '@remotion/google-fonts/Inter';
import { loadFont as loadSpaceGrotesk } from '@remotion/google-fonts/SpaceGrotesk';
import { loadFont as loadManrope } from '@remotion/google-fonts/Manrope';
import { loadFont as loadSyne } from '@remotion/google-fonts/Syne';
import { loadFont as loadDMSans } from '@remotion/google-fonts/DMSans';

/** Brand typefaces by config key. Add a Google font here with one more import + entry. */
const loaders: Record<string, () => string> = {
  inter: () => loadInter('normal', { weights: ['400', '600', '700'], subsets: ['latin'] }).fontFamily,
  'space-grotesk': () => loadSpaceGrotesk('normal', { weights: ['400', '500', '700'], subsets: ['latin'] }).fontFamily,
  manrope: () => loadManrope('normal', { weights: ['400', '600', '800'], subsets: ['latin'] }).fontFamily,
  syne: () => loadSyne('normal', { weights: ['400', '600', '800'], subsets: ['latin'] }).fontFamily,
  'dm-sans': () => loadDMSans('normal', { weights: ['400', '500', '700'], subsets: ['latin'] }).fontFamily,
};

const cache: Record<string, string> = {};

export const brandFont = (key: string): string => {
  if (!loaders[key]) throw new Error(`Unknown font "${key}". Options: ${Object.keys(loaders).join(', ')}`);
  cache[key] ??= loaders[key]();
  return cache[key];
};
