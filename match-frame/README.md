# match-frame, a Claude Code skill

Turns any logo into a match-cut brand identity reel. Your mark holds one spot on screen while everything around it
flashes through photoreal mockups of it: business cards, wall letters, a phone, a street banner, packaging, a
notebook, etched glass. Each mockup shows twice, dark then light, up to ten cuts a second. 9:16 MP4, 5-8 seconds,
loops.

- **Rendered, not drawn**: Blender builds each mockup from your logo SVG with real lighting and materials (free
  Poly Haven scans), so the frames read as photos, not animation. Nine scenes, each rendered dark and light, plus a
  few flat brand frames (construction grid, pattern, name).
- **Two rhythms from real reels**: a steady 3-frame strobe, or a cut that starts frantic and brakes onto your logo.
  Both were measured frame by frame from branding studios' reels (`reference/teardown.md`).
- **Cut to the music**: `npm run cuts` finds a track's hits and starts a cut on each one, so the ramp version
  lands every cut on a tick. The audio is lined back up after rendering, so the cuts don't look a frame early.
- **Ready to post**: you also get an `-upload.mp4` without sound, so you can add the sound in Instagram.

## Install

1. Copy the `match-frame` folder into `~/.claude/skills/` (every project) or `<your project>/.claude/skills/` (one
   project).
2. Install the tools once (Mac):
   ```bash
   brew install node ffmpeg && brew install --cask blender
   pip3 install numpy scipy librosa
   ```
3. In Claude Code, say "make a match-cut reel for my logo" and give it your logo as an SVG plus your brand colours.

Claude copies `engine/` into a folder for your reel, fills in your brand, downloads the lighting and materials once
(~60 MB), renders the mockups (5-10 minutes the first time) and cuts the reel. The engine ships with a sample brand,
"Northfold", so you can see the whole pipeline before using your own logo.

## Music

The sample timings come from the soundtracks of the two reference reels (links in `reference/teardown.md`). Those
tracks aren't in this repo because they belong to their creators. For a draft, Claude can pull a reel's sound onto
your machine. To post, upload the `-upload.mp4` and add the sound in Instagram ("Use audio" on the original reel).
Any other track works too: Claude finds its hits and re-cuts the reel to them.

Heads-up: ten full-screen light/dark flips a second is far past the usual photosensitivity guideline (3 a second).
The skill can make a gentler version.
