# Teardown: the two reference reels

Both measured frame by frame (`npm run measure`, plus onset detection on the soundtrack with librosa, decoded with ffmpeg).
Neither reel's audio is in this repo; the links below are where Claude pulls each sound for a draft.

## Steady: change.branding, "Streak"

<https://www.instagram.com/reel/DYPdkFGN65m/> · 5.6 s, 720x1280, 30 fps.

- **Cuts:** 56, every one exactly 3 frames (10 cuts/s). 34 distinct stills (17 scenes x A/B), so the list plays 1.65
  times; cut 35 repeats cut 1. No end hold: the last cut runs into the loop.
- **Mean luma per cut** (0-255), the first pass:
  106 145 122 130 93 158 196 54 183 68 223 27 250 2 126 125 62 191 219 31 156 95 171 80 166 85 86 168 113 138 131 119 106 146.
  Mostly alternating dark/light, with a few weak flips near the start where neighbouring mockups share a tone.
- **Match point:** the mark centred at ~47 % height, ~22 % of the frame width, on nearly every cut.
- **Inside a shot:** nothing moves (frame difference 0). The cutting is the only motion.
- **Sound:** a continuous groove at ~164 BPM, steady loudness (-15 dB RMS) to 5.6 s, then silence. The cuts don't
  follow its beat; at 10 cuts/s the eye can't tell. The engine's steady reel is sized to it: 52 cuts x 3 f + a 12 f
  hold = 168 frames, the length of the track.

## Ramp: obrazur, "SkillShift"

<https://www.instagram.com/reel/DcQ0pPJtsMT/> · 7.97 s, 720x1280, 30 fps.

- **Cuts:** 50. Lengths in frames:
  `2x14 3 2 3x9 2 4 4 3 3 3 3 3 4 4 5 4 6 6 6 6 7 8 10 10 12 13 16 18 19`.
  Frantic, then braking onto the opening shot, which holds 19 frames to the end.
- **B variant:** colour, then mono or a photographic negative of the same frame. Smaller mark than Streak, centred
  on the flat frames; the mockups move it more.
- **Sound:** a tick that rolls (ticks ~1 frame apart around 0.6-0.9 s), then slows down. 59 hits; the late ones at
  frames 118 121 124 132 140 149 159 171 184 200 218 239. The video follows them: the last 9 cuts each start on a
  tick, and the final tick lands on frame 239, the loop point.
- **Offset:** in the posted file the cuts sit ~1.5 frames after their ticks.
- **The engine's ramp reel** (`src/config/cuts/skillshift.json`) puts a cut on a tick whenever the previous cut has
  run 2 frames: 49 cuts, `6 4 3 3 2 3 2 2 2 3 2 2 2 2 2 3 2 3 2 2 2 3 2 3 2 3 3 3 3 4 3 4 4 5 5 5 5 7 3 3 8 8 9 10
  12 13 16 18 21`. Every cut is within 1 frame of a tick in the render.

## What carries over

- One fixed match point, A/B pairs, alternating luminance, stills only.
- Photos or physically lit renders on nearly every cut. Only 1-2 flat brand frames per reel.
- The music's hits, when it has them, set the cut lengths. A steady groove sets only the length.
