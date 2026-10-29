# Match Frame

Match-frame (match cut) brand identity reels, 9:16, 5–9s. **Load the `match-frame` skill before planning or editing a reel in this style.** It holds the grammar (match point, A/B pairs, luminance strobe, photographs not graphics), story order, rhythm presets and the Blender scene catalogue.

## Key files

| File | Purpose |
|------|---------|
| `src/config/identity.json` | Brand (name, tagline, logo, colours, font) + match point. Read by Remotion and Blender |
| `src/config/match-config.ts` | Shot-sheet comment, `shots[]` (`render('<scene>')` for Blender stills), rhythm, audio |
| `src/config/types.ts` | Field reference for every shot kind and rhythm segment |
| `src/config/rhythms.ts` | `steady` and `rampDown` presets measured from the reference reels |
| `blender/render_shots.py` | Photoreal mockup scenes (Cycles): relief, cards, wallsign, totem, phone, billboard, boxes, notebook, glass |
| `blender/fetch_assets.py` | CC0 Poly Haven HDRIs + materials → `blender/assets/` (gitignored) |
| `src/Textures.tsx` | Logo / lockup masks and phone screens Blender prints with → `blender/build/` (gitignored) |
| `src/lib/timeline.ts` | Expands shots into A/B cuts and lays them on the rhythm; `beatFrames()` for BPM |
| `src/components/shots/Photo.tsx` | Photo cuts: `srcB` or treatment, perspective logo quad, film grain |
| `src/components/shots/flat.tsx` | Flat brand frames: grid, pattern, lockup, surface |
| `src/ContactSheet.tsx` | QA still: every cut in order with a crosshair on the match point |
| `scripts/measure.mjs` | Cut lengths, luma per cut, weak light/dark flips for any MP4 |
| `scripts/cuts_from_track.py` | `npm run cuts`: a track's hits → cut lengths JSON for `rhythms.fromTrack()` |
| `scripts/align_audio.py` | Run after every render: removes Remotion's ~43ms AAC delay by remuxing (lossless) |
| `src/config/cuts/*.json` | Cut lengths per track |

## Workflow

1. Fill in `src/config/identity.json`, put the logo SVG in `public/brand/`.
2. `npm run assets` (once), `npm run textures`.
3. `npm run shots -- <scene> --samples 64 --scale 0.5` to look, then `npm run shots` for full-res A/B stills in `public/shots/`. Read every JPG.
4. Write the shot-sheet comment and `shots[]`: about 3 renders per flat frame, every A dark and every B light.
5. Music: a reference reel's sound goes in `public/audio/ref-<name>.m4a` (gitignored). For a track with hits, `npm run cuts -- <track> --out src/config/cuts/<name>.json` and `rhythms.fromTrack()`. `variants` holds one composition per cut/track.
6. `npm run sheet`, `npm run render:preview`, `npm run measure -- out/preview.mp4`, `npm run render` (which also runs `align_audio.py`).

## Conventions

- Mockups are Blender renders or real photos. The drawn `card` / `badge` / `sign` / `app-icon` / `ui` kinds are a no-Blender fallback and read as animation.
- Blender scenes are Z-up, metres, walls face -Y, camera yaw 0 looks from -Y. `camera(fit=<mark width>)` sizes and places the mark on the match point.
- Positions in Remotion are fractions of the 1080×1920 frame (`match`, `logo.quad`).
- The first shot is the hero: the end hold shows it by default, so the loop is seamless.
- Shots are stills; the cutting is the motion. Footage, if ever added, goes through `<OffthreadVideo>`.
