---
name: window-visualizer
description: Make a "window visualizer" reel in code - a night apartment block, a grid of lit windows that switch on and off with a song, captions in the middle timed word by word to a voiceover - rendered to a 9:16 MP4. Any song drives it; the voice is recorded line by line (or Fish Audio, ElevenLabs or a macOS draft voice) and lined up with the song's beat. Use when someone wants windows lighting up to music, a building / city lights audio visualizer, a music-reactive grid reel, "the windows reel", or an audio visualizer for Reels or TikTok.
---

# Window visualizer

A black frame holding a 9 x 20 grid of apartment windows at night. Every window listens to one band of the song and
switches on when that band hits harder than its own threshold, so the building flashes with the drums and goes dark
in the gaps. A voiceover says the lines, each line starting on the song's beat; each caption word appears as it's
said. Format and numbers measured from a viral reel (17 s, 51.5k likes): see `reference/teardown.md`.

Everything is code: `windows.py` turns the song into per-frame light (onset flux in six bands), lines the voice up
with the beat and turns its word timings into captions; `engine/windows.html` draws the rooms (each window a
different room, drawn once from a seed), the grid and the captions; `engine/render.mjs` renders it in headless Chrome.
The voice and the mix come from the launch-video skill (`vo.py`, `audio.py`), which must sit next to this folder.
About 30 s to render a 15 s video.

## Make one

1. **Song**: any audio file. `python3 windows.py start <song> --dur 15` finds its busiest stretch (usually the drop)
   to use as `music.start`. Prefer a stretch without singing under the voice.
2. **Script**: `python3 windows.py new <project> --song <file>` writes a starter `plan.json`, or copy
   `examples/starter/plan.json`. One scene = one spoken line; a scene with only `dur` lets the windows play alone.
3. **Draft**: `python3 windows.py make <project> --voice say` (free macOS voice; `--voice-id "Samantha"` to pick one).
   One command: voice -> beat lock -> captions -> light -> frames -> mix -> MP4s.
4. **Real voice** (LV = the launch-video folder next to this one):
   - Record: `python3 <LV>/vo.py record <project>` (teleprompter, one take per line, `--line N` redoes one). It needs
     the mic and Enter presses, so give the user the command to run in their own terminal; never run it yourself, and
     don't render while they record (the fan gets into the takes). Or `vo.py import <project> take.m4a` (one take of
     the whole script, recorded anywhere).
   - Match their words: people ad-lib. `vo.py build` transcribes the takes; rewrite each scene's `vo` to what was
     actually said so the captions match (check word timings without a whisper hint: a hint can drop words).
   - Master (optional): `python3 <LV>/vo.py auphonic <project>` (leveler, denoise, voice EQ, -16 LUFS; needs
     AUPHONIC_API_KEY in `<LV>/.env`). Re-run after re-recording a line.
   - Or a generated voice: `--voice fish --voice-id <id>` / `--voice eleven --voice-id <id>` (keys in `<LV>/.env`).
   - Then `python3 windows.py make <project>` (`--voice keep`, the default, rebuilds from the takes).
5. **Check**: `windows.py render <project> --still 1.2,7.5` or `--board`. Captions on their words, lines on the beat,
   the song not fighting the voice, the first frame on a hit.

Outputs in `<project>/out`: `<name>.mp4` (review: voice over the song, ducked under each line), `<name>-upload.mp4`
(voice only: post this and add the song in the app, turned down), `<name>-cutnotes.mp4` (720p), `board.jpg`,
`audio.json` (the light, 0-255 per band per frame), `captions.json`. `timeline.json` and `vo/` sit in the project.

## Plan

```jsonc
{
  "name": "windows",
  "music": {"file": "song.m4a", "start": 42.3, "gain": 0.7},
  "mix": {"duck": 0.6},                              // how far the song dips under the voice
  "lock": {"bar": 0.7},                              // line the voice up with the song's beat (see below)
  "windows": {"source": "code", "seed": 7, "lit": 0.7, "ghost": 0.045},  // source: "code" or a folder of tiles
  "react": {"decay": 0.85, "level": 0.1, "low": 0.25, "high": 0.85, "gain": 1.0, "tick": 30},
  "grid": {"cols": 9, "rows": 20, "scale": 1.0, "y": 0},
  "caption": {"y": 0.4323, "size": 0.0505},          // centre height and font size, fractions of the frame
  "scenes": [
    {"type": "line", "vo": "these windows aren't edited by hand."},            // one word on screen at a time
    {"type": "line", "dur": 3.0},                                             // windows alone, no caption
    {"type": "line", "vo": "it works with *any* song.", "show": "line", "on": "drop"},  // whole line, on the drop
    {"type": "line", "vo": "follow for the next one.", "caption": "follow", "hold": 1.6}
  ]
}
```
- Scenes take vo.py's fields: `vo` (what's said), `pre` / `post` (silence before / after the line), `dur` (minimum
  length), `hold` (on the last scene), `join` (chain with the previous line into one take). `type` is free text.
- Captions: by default each spoken word replaces the last as it's said. `"show": "line"` puts the whole line up;
  `"caption"` shows other text than what's said (`""` = none). `*word*` sets that word in the italic serif
  (Instrument Serif), spoken normally; the rest is Inter 600, tight.
- Text-only lines (on screen, not spoken): a scene with `caption` and `dur` and no `vo`, e.g.
  `{"caption": "made with claude.", "show": "words", "pace": 0.28, "dur": 1.8}` (one word every `pace` s, the last
  holds) or `{"caption": "it works with *any* song.", "dur": 1.7}` (whole line). Voiced lines are the default.
- `lock`: after the voice is built, `make` moves each spoken line so its first word (or `"anchor": n` / `"last"`)
  lands on a beat of the song, a bar start when waiting at most `bar` beats more gets one; `"on": "drop"` lands a
  line on the song's drop, planned backwards so the windows-only stretch before it absorbs the difference (it stays at
  least `min_windows`, 1.5 s); windows-only scenes otherwise end on the bar nearest their `dur` (kept as `dur_want`);
  the ending holds to a bar. It writes `pre` / `dur` / `hold` into the plan and rebuilds, so lines only wait, never
  overlap. Beats come from the song (librosa). The rhythm inside a line isn't changed.
- Without a voice: leave out `scenes`, set `"duration"` and hand-time `"captions": [{"at": 0.0, "text": "these"}, ...]`
  (each replaces the last; `""` clears). Then the review copy is the song alone and the upload copy is silent.
- `windows.seed` picks a different building; `lit` = share of windows that can light at all (the rest stay dark,
  like empty flats); `ghost` = how visible an unlit frame is.
- `react`: `decay` = how fast a window goes dark after a hit (per frame), `level` = how much plain loudness (not just
  hits) keeps windows on, `low`/`high` = the range of window thresholds, `gain` > 1 = busier, `tick` < 30 = the
  light updates in steps (15 looks like a phone screen recording). The light always follows the song, never the voice.
- `inserts` (off unless asked for): `{"type": "clip", "file": "me.mp4", "start", "end", "in"}` cuts to your own
  footage; `{"type": "phone", "start", "end"}` draws a phone on a marble table running the same windows (plan
  `phone`: `gain`, `label`, `time`). Captions hide during an insert unless it has `"captions": true`.

Real photos instead of drawn rooms: `python3 windows.py tiles night-facade.jpg --out <project>/tiles` cuts every lit
window out of a night photo of a building, then set `"windows": {"source": "tiles"}`. Use a photo you shot or one
with a free licence (e.g. Unsplash).

## Making it good
- The structure that worked (51.5k likes, 17 s): the hook over the grid at talking pace (0-6.4 s), a break where
  the windows play alone (6.4-9.5 s), who made it (9.5-11.5 s), "it works with *any* song." (11.6 s), the call to
  action to the end. Short lines: 3-7 words each.
- Start the song on a hit so the first frame flashes (`windows.py start` lands on one); put the payoff line on the
  drop (`"on": "drop"`).
- A song with its own vocals fights a voiceover: prefer an instrumental stretch, or raise `mix.duck`.
- Captions must be true: say what the video really is and who made it; no invented apps, links or numbers.
- Sound: the review copy carries the song; the upload copy carries only the voice. On Instagram or TikTok add the
  song from the app's sound picker, start it at `music.start` and turn it down. Never post a file with someone
  else's track baked in.

## Notes
- Fitted to the reference: its lit-window share per frame correlates 0.78 with this engine's on the same sound
  (average 14 % vs 15 %, same hits). `react` defaults are those numbers.
- Needs Chrome, ffmpeg, python (numpy, scipy, librosa, Pillow, requests, faster-whisper for word timings,
  sounddevice to record) and `npm install` once in `launch-video/engine` (playwright-core and the fonts).
