import { Composition, Still } from 'remotion';
import { ContactSheet, sheetSize } from './ContactSheet';
import { MatchFrame, durationOf } from './MatchFrame';
import { LockupMask, LogoMask, MASK, ScreenA, ScreenB } from './Textures';
import { variants, type Variant } from './config/match-config';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {(Object.keys(variants) as Variant[]).map((id) => (
        <Composition
          key={id}
          id={id}
          component={MatchFrame}
          defaultProps={{ variant: id }}
          durationInFrames={durationOf(id)}
          fps={variants[id].fps}
          width={variants[id].width}
          height={variants[id].height}
        />
      ))}
      <Still id="ContactSheet" component={ContactSheet} width={sheetSize.width} height={sheetSize.height} />
      {/* Textures for the Blender scenes */}
      <Still id="LogoMask" component={LogoMask} width={MASK} height={MASK} />
      <Still id="LockupMask" component={LockupMask} width={MASK} height={MASK} />
      <Still id="ScreenA" component={ScreenA} width={1179} height={2556} />
      <Still id="ScreenB" component={ScreenB} width={1179} height={2556} />
    </>
  );
};
