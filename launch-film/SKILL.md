---
name: launch-film
description: Make a 25–30 second launch film for any product, Claude skill or app, set in the Claude app and voiced in the user's own voice, in 16:9 and 9:16. A pause glyph and gradient tiles cut on the music, the product's wordmark, then the user types an ask to Claude and Claude hands back the product; every recorded line gets its own scene (the real product on screen with a click, big dark type said word by word, ticked feature chips, a before/after you can hear, a "use it for — A / B / anything" gradient swap, back in Claude for the result), and it ends on the wordmark with the comment word. Every cut is anchored to when each word was actually said. Built on Remotion; the voice comes from the voice-studio skill. Use when someone wants a launch video, launch reel or showcase film for their product, skill, artifact or app, "put my voiceover in a cool video", a video like the ElevenLabs Agents Architect film, or to turn voice-studio takes into a finished video.
---

# launch-film

A short launch film in one look: cream and soft photographic gradients, whip-blur cuts, the Claude app (never a
terminal), and the user's own voice on top. The story is always the same, which is why it works for any product:

1. **Opener** (0–1 s): a pause glyph, a dot, then four gradient tiles cut on the music with tiny labels around them.
2. **Wordmark**: the product's mark and name blur in.
3. **The ask**: the user types a short ask into Claude (with the skill chip if it's a skill), Claude thinks, replies and
   hands back the product as a card. The cursor clicks Open.
4. **One scene per line** of the voiceover (below), each cut on the words.
5. **End card**: a gradient orb, the wordmark, then the comment line said word by word with the keyword as a black pill.

Everything is driven by one file, `film.json`, in a project folder (`<dir>` below). `film.py` (next to this file) turns it
plus the user's recorded lines into a timeline and renders it. The worked example is `examples/take-one/film.json`:
the Take One launch film, 27 seconds, 6 lines.

## Setup (once)

```bash
python3 <skill>/film.py setup
```

Installs the Remotion engine (`npm install` in `engine/`) and checks ffmpeg, Node 18+, numpy and faster-whisper.
For the voice, the **voice-studio** skill must be installed too (it records the lines and cleans them with Auphonic).

## 1. The words are theirs

Never write the voiceover for them. Ask what the product is, who it's for, what it does that matters, and what they'd
say about it out loud, then build the lines out of their own words. Split it into **5–7 short lines**, 1.5–4 seconds
each, about 70 words at most. The shape that works:

| line | job | example (Take One) |
|---|---|---|
| 1 | what it lets you do | "Therefore, I can voice the lines." |
| 2 | the surprising constraint or proof | "But I'm only using my Mac's mic." |
| 3 | the punch, said flat | "I have no other mics connected." |
| 4 | what it does for you, then what you can do with it | "And it's going to clean up the audio, and Claude can use it for anything." |
| 5 | the payoff | "But I'll have it put in a cool video." |
| 6 | the comment ask | "Comment VOICE if you want me to send this to you." |

Show them the lines and let them change any word before they record. If the film goes on Instagram with ManyChat, the
comment word must be one no other live reel of theirs uses.

## 2. They record, Claude cleans

Use the voice-studio skill: one line per take in the Take One studio on their Mac, then its `clean` (Auphonic, the
voice match EQ when they have a profile, every line the same loudness). Put that folder at `<dir>/voice/` (or point
`"voice"` in film.json at it). It must hold `timings.json` and `lines/01.wav …`; the raw takes in `takes/` are what the
before/after scene plays. Never build on takes that failed voice-studio's dropout check.

Then get the word timings:

```bash
python3 <skill>/film.py words <dir>
```

Read what came back. Where whisper mis-heard a word, add it to `"fixes"` (e.g. `{"mix": "mics"}`); the script's spelling
and punctuation are used wherever a word matches.

## 3. Real screens, not mockups

The product on screen is the real thing: a screenshot or screen recording of the actual app, page, artifact or settings
pane, saved in `<dir>/assets/`. Crop each one to the window (no desktop around it). For 9:16, also crop a tighter part of
it (`imageVertical`) or landscape screens come out small on a phone. The logo goes in as `brand.mark` (SVG or PNG,
square); without one the film uses the name's first letter on the accent colour.

## 4. One scene per line: film.json

Start from the example: `python3 <skill>/film.py new <dir>` writes the Take One film.json into `<dir>`. Then change every
field. Top level:

| field | what |
|---|---|
| `title` | names the output files |
| `voice` | the voice-studio folder, relative to `<dir>` |
| `fixes` | whisper mishearings → the word they said |
| `brand` | `name` (as written in the wordmark), `sub` (grey words after it), `accent` (hex), `mark` (logo file) |
| `opener.labels` | four tiny labels around the opening tiles: facts about the product, 1–3 words each |
| `claude` | `prompt` (what they type, lowercase, short), `skill` (the skill chip, or omit), `title` (the chat's title), `thinking`, `reply` (Claude's one-sentence answer), `card` (`title`, `sub`, `button`). Omit `claude` to skip the scene |
| `beats` | the scenes, in order (below) |
| `music` | `file`, `firstHit` (the second in the track that lands on the first opener tile), `db` (default -15.5) |
| `gap` | seconds between lines (0.3; much more feels slow) |
| `lufs` | the master's loudness (-16.4) |

Each beat takes `"line": n` (a recorded line), or part of one with `"until": "<words>"` / `"from": "<words>"` to split a
line across two scenes, plus `"gapBefore"` to change the gap before it and `"cut": "hard"|"whip"` to override its
transition. The scenes:

| scene | use it for | fields |
|---|---|---|
| `screen` | the real product doing the thing the line says | `image` or `video` (+ `rate`, `from_sec`), `imageVertical`/`videoVertical`, `click: [x, y]` (0–1 inside the image, clicked as the line ends) and `clickVertical`, `title` (adds a window bar; leave it off if the screenshot has its own), `size` (0–1, 16:9 only), `palette` |
| `type` | the punchline, said flat: big dark type, word by word | `grey` (how many last words go grey, default 1) |
| `chips` | what it does, ticked off one by one | `chips` (2–4, a few words each), `wave: true` (a waveform sweeping from raw to clean, from the next compare), `waveLabels` |
| `compare` | a before/after you can hear (audio products) | `before`, `after` (audio files), `length` (seconds of each), `labels: [["Before", "sub"], ["After", "sub"]]`. Not a line: it sits between two beats and ducks the music |
| `list` | "X can do it for — A / B / C / anything" | `prefix`, `items` (3–5), `final`, `on` (the word the final lands on) |
| `chat` | back in Claude: the line typed as it's said, Claude returns the result, the cursor opens it full frame | `typeFrom` (the word typing starts on), `history` (`[{"user": …}, {"claude": …}]` shown above), `thinking`, `reply`, `result` (`label`, and `image` or `video` of the real result) |
| `end` | the end card | `keyword` (the comment word). With a `line`, that line plays over it word by word with the keyword as a pill; without one, `tagline` and a "Comment KEYWORD" pill |

Palettes: `blue`, `plum`, `gold`, `sky`, `violet`, `rose`, `sage`, `ember`. Alternate light and dark scenes: a `type`
beat between two bright ones is what gives the film its punch.

## 5. Music

The opener's tiles cut on the music's first hit, so the film needs a track with a clear hit early on. Use a track the user
owns or has the rights to (or the soundtrack of the reference reel they're copying, for their own use); nothing is
shipped with the skill, and it's fine without music. Find the hits:

```bash
python3 <skill>/film.py hits <dir>/assets/music.m4a
```

and set `"music": {"file": "assets/music.m4a", "firstHit": <time>}`. The music sits about 15 dB under the voice and comes
up between lines; it ducks another 12 dB under a compare.

## 6. Plan, check, render

```bash
python3 <skill>/film.py plan <dir>                        # prints every scene with its start time and words
python3 <skill>/film.py still <dir> --at 6.2 [--vertical] # one frame, to check a scene
python3 <skill>/film.py render <dir> --both               # <dir>/out/<title>-16x9.mp4 and -9x16.mp4
```

`render` re-plans, renders with Remotion, removes Remotion's ~43 ms audio delay and masters to `lufs` under a -1.5 dBTP
ceiling, then prints the measured loudness. `--draft` renders at half size.

Before handing it over: pull a frame from the middle of every scene in both sizes (`film.py still`, or ffmpeg on the
render) and look for text running off the frame, a cursor pointing at the wrong thing, or a screen too small on 9:16.
Claude can't hear the result, so say so, and check the numbers instead: loudness near the target, and every line in the
plan with the words the user said.

## Files

| | |
|---|---|
| `film.py` | the CLI: setup, new, words, hits, plan, still, render |
| `engine/` | the Remotion project. `src/Film.tsx` (scenes), `src/ui.tsx` (the Claude app, gradients, cursor, whip). `film.py plan` writes `src/plan.json` and copies media into `public/p/` |
| `engine/public/sfx/` | key clicks, clicks, whooshes, swishes, pops (synthesized, free to use) |
| `examples/take-one/` | the Take One launch film's film.json and screenshots (bring your own voice folder to render it) |
