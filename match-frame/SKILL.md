---
name: match-frame
description: Match-frame (match cut) brand identity reels, 9:16 and 5–9 seconds. The logo holds one spot on screen while hard cuts flash through mockups, textures, construction grids and patterns, each scene shown as a light/dark or colour/mono pair, every 2–3 frames. Covers the style's anatomy (measured frame by frame from two reference reels), shot-sheet planning, rhythm presets (steady strobe, ramp-down), photoreal mockups rendered in Blender Cycles from the brand's logo (cards, wall signage, totem, phone, billboard, packaging, notebook, etched glass), the designer's own renders or photos, cutting to the music, and rendering it all with the bundled engine (Remotion + Blender). Triggers include match cut, match frame, logo match cut, brand identity reel, branding reveal, logo reveal reel, identity case-study reel, mockup montage, rapid-cut / flash-cut brand reel, or "make a reel like this" pointing at a branding studio's Instagram post.
---

# Match Frame

A brand identity reel built from **stills, not motion**. The mark sits on one fixed spot (the **match point**) while everything around it changes every 2–3 frames: concrete, paper, a business card, a sign, an app icon, a pattern. Each scene flashes twice, once dark and once light, so the reel strobes. The eye stays on the mark, and the mark looks like it is everywhere at once.

**References** (measured frame by frame; full numbers in `reference/teardown.md`):

| | change.branding, "Streak" ([DYPdkFGN65m](https://www.instagram.com/reel/DYPdkFGN65m/)) | obrazur, "SkillShift" ([DcQ0pPJtsMT](https://www.instagram.com/reel/DcQ0pPJtsMT/)) |
|---|---|---|
| Length | 5.73s, 720×1280, 30fps | 8.1s, 720×1280, 30fps |
| Shots | 17 scenes → 34 stills | ~16 scenes → ~33 stills |
| Rhythm | Every cut exactly **3 frames** (10 cuts/s): 56 cuts in 5.6s, the list plays 1.65×, no end hold | **14×2f, ~10×3f, then cuts ease 4→19f** onto the opening shot |
| Sound | A continuous ~164 BPM groove; the cuts ignore its beat | Ticks that roll, then slow down. The last ~9 cuts land one per tick and the end hold runs to the final tick |
| B variant | Light/dark render of the same mockup | Colour → mono, sometimes a photographic negative |
| Match point | Mark centred at ~47% height, ~22% of frame width, nearly every cut | Smaller mark, centred on flat frames; mockups move it more |
| Motion inside a shot | None (frame diff = 0) | None |

**Borrow the grammar, not the identity.** Don't reuse their marks, mockups or captions. Their soundtrack can be the music when the user asks for it (see **Music**).

## Grammar

1. **Match point.** Same position, same size, every cut you can manage. Default `{ x: 0.5, y: 0.46, width: 0.2 }`. The cut is invisible on the mark and violent everywhere else, and that contrast is the effect. Allow a **breather** (card on a desk, UI chips, a person) about 1 cut in 4, then come back.
2. **Pairs.** Every scene is two consecutive cuts, A then B. B is either a **tone swap** (dark ↔ light, reel 1) or a **treatment** (mono / negative, reel 2). Pairs double the cut count without doubling the sourcing, and the A→B flicker is the signature.
3. **Luminance strobe.** Adjacent cuts alternate dark and light. If every A is dark and every B is light, the whole reel alternates automatically. Reel 1's measured mean luma runs 146, 125, 131, 95, 160, 198, 56, 185, 70, 225, 30, 252, 3… Check with `npm run measure`.
4. **Stills only.** No camera moves, no animation inside a shot. The cutting is the motion. (This is also why it renders fast.)
5. **Photographs, not graphics.** Nearly every cut in both references is a photo or a physically lit render: a billboard against real sky, a phone in a hand, foil catching window light, people. Only one or two cuts per reel are flat brand frames (a solid colour, a grid). Mockups drawn with CSS or SVG (flat cards, fake shadows, noise textures) read as *animation*, and the first user test rejected them for exactly that. Mockups must come from Blender, real photos or the designer's renders. The template's procedural `card` / `badge` / `sign` / `app-icon` / `ui` kinds are only a no-Blender fallback for a rough draft.
6. **Story order:**
   - **Open** on the mark as an object (embossed in concrete, foil on paper). This is also the end hold.
   - **Origin**, early: the thing the mark is drawn from (the falcon, the cap-and-arrow). Use a photo on the match point.
   - **Construction:** keyline grid, guide lines.
   - **Applications:** print, signage, wearables, digital, packaging, people.
   - **System:** the pattern, colour fields, the lockup with the name.
   - **Close** back on the opening shot. The end hold loops into frame 0 on Instagram.
7. **Mix.** About 3 photoreal cuts for every flat brand frame (grid, pattern, lockup, solid). Never two breathers in a row.
8. **No voiceover, no on-screen copy** beyond the brand name and tagline. Nothing is readable in 0.1s. The story goes in the post caption, in three short paragraphs: origin → concept → result. Use the client's own words. Don't invent a tagline or concept story: ask.

## Rhythm

| Preset | Code | Feel | Use when |
|---|---|---|---|
| Steady strobe | `rhythms.steady({ cuts, frames: 3, passes: 2, hold: 12 })` | Relentless, techy | Short loop, one hard-hitting track |
| Ramp-down | `rhythms.rampDown()` (15×2f, 10×3f, 22 cuts easing 3→16f, 24f hold) | Starts frantic, brakes onto the logo | You want the end card to land |
| Cut to the track | `rhythms.fromTrack(json)`, lengths from `npm run cuts` | Every cut on a hit of the music | The track has ticks or hits that set the pace (ramp references usually do) |

Segments compose: `steady`, `ramp` (`from`/`to` frames, `ease: 'in' | 'linear'`), `lengths` (explicit frames) and `hold` (`cut: 'hero'` or `'hero:b'`, default the very first cut). Cuts walk through the expanded A/B list in order and wrap.

**Tempo:** frames per cut = `fps × 60 / (bpm × cutsPerBeat)`. At 30fps, 3 frames = 150 BPM 16th notes; 2 frames = 112.5 BPM 32nds. Fractional values are fine (`beatFrames()` in `src/lib/timeline.ts`): lengths are rounded cumulatively so the cuts never drift off the grid. Set `audio.startFrom` so the drop lands on frame 0, and in ramp mode end the hold on a hit.

**Music from a reference reel:** when the user wants the sound of a reel they sent, use it.
1. Open the reel's embed page (`https://www.instagram.com/reel/<ID>/embed/captioned/`) in a browser you can script, such as Claude Code's built-in browser pane. `document.querySelector('video').currentSrc` is a progressive MP4 with audio. `curl` it to a temp folder, then `ffmpeg -i reel.mp4 -vn -c:a copy public/audio/ref-<name>.m4a`. The sample config expects the two references as `ref-streak.m4a` and `ref-skillshift.m4a`. `ref-*` is gitignored, and a missing track renders silent.
2. Continuous groove (steady reels): make the reel exactly as long as the track (`hold` takes up the slack).
3. Ticks or hits: `npm run cuts -- public/audio/ref-<name>.m4a --out src/config/cuts/<name>.json`, then `rhythm: rhythms.fromTrack(json)` and `audio.music: json.track`. A cut starts on a hit once the previous one has run `--min` frames (default 2).
4. Tell the user once: the sound belongs to that reel's creator or label, so it never ships with this skill. It's fine in a draft, but Instagram may mute an upload with it baked in. To post with it, upload `out/<name>-upload.mp4` (no sound) and add the sound from the original reel ("Use audio"), which carries the licence.

`MatchFrame` and `MatchFrameRamp` in `variants` (`match-config.ts`) are two cuts of the same shots to two tracks; add an entry for each extra version.

**Other music:** the client's licensed track or one they have rights to: fast electronic, phonk, minimal house or a percussive loop. Run it through `npm run cuts` if it has hits.

**Photosensitivity:** 10 full-screen light/dark flips per second is far above the WCAG 2.3.1 limit of 3 flashes a second. Both references do it anyway. Tell the user once. The gentler version keeps every cut on the same side of mid-grey (all A and B dark, B = `treatment: 'mono'`) or slows cuts to 10+ frames. It's their call.

## Production: `engine/`

Two stages. **Blender** renders photoreal mockup stills of the brand. **Remotion** cuts them with a few flat brand frames on the rhythm.

`engine/` sits next to this file. Copy it to a folder for each reel, never edit it in place:

```bash
cp -r <this skill>/engine ~/reels/<brand> && cd ~/reels/<brand> && npm install
# edit src/config/identity.json (brand + match point), drop the logo SVG in public/brand/
npm run assets           # once: CC0 Poly Haven lighting + materials → blender/assets/ (~60 MB)
npm run textures         # logo / lockup / phone-screen textures → blender/build/
npm run shots -- --list  # the Blender scenes
npm run shots -- cards relief --samples 64 --scale 0.5   # quick look (~5s each)
npm run shots            # every scene, A + B, full res → public/shots/<scene>_<a|b>.jpg
npm run sheet            # out/contact-sheet.png: every cut, red crosshair on the match point
npm run render:preview && npm run measure -- out/preview.mp4
npm run render           # out/match-frame.mp4 + out/match-frame-upload.mp4 (no sound)
npm run render:ramp      # the same shots cut to the ramp track → out/match-frame-ramp.mp4
```

Needs Node 18+, ffmpeg, Python 3 with `numpy scipy librosa`, and Blender 4.2+ (`brew install --cask blender`). Ask before installing anything. On Apple silicon Cycles renders on the GPU through Metal. The very first render compiles kernels for a few minutes; after that a full-res still at 192 samples takes about 25–35s (M5 Pro).

### Intake (ask before building)

1. **Logo:** a single-colour SVG with a `viewBox`. Fills are overridden per shot, so a multi-colour mark comes out flat. Blender also extrudes it into real 3D letters. If they only have a PNG, ask for the SVG or vectorise it (`potrace`) and show them the result.
2. **Colours:** ink (near-black), paper (near-white), primary + text-on-primary, accent + text-on-accent.
3. **Name, tagline, typeface.** Typefaces are keyed in `src/lib/fonts.ts`. Add a Google font with one import.
4. **Which reference feel:** steady or ramp-down.
5. **What they already have:** mockup renders, an origin/inspiration photo, music (or the sound of the reference reel).

All of this goes in `src/config/identity.json`, which both Blender and Remotion read.

### Blender scenes (`blender/render_shots.py`)

Each scene is a Python function that builds geometry, materials, lights and camera from the identity. It renders A (dark) and B (light) and aims the camera so the mark lands on the match point at `match.width` of the frame (`camera(..., fit=<mark width in metres>)` with lens shift).

| Scene | What it is | A → B |
|---|---|---|
| `relief` | The mark raised out of a plaster wall, raking light | charcoal → white plaster |
| `cards` | Business-card stack + name card on a table, f/2.8 | silver foil on black stock (concrete) → black ink on white (linen) |
| `wallsign` | Extruded letters on stand-offs, gallery wall, spot pool | brushed steel on charcoal → matte black on white |
| `totem` | Free-standing panel with the lockup, warehouse behind | brand colour → white |
| `phone` | Phone on a table, the brand app on screen | walnut + brand screen → marble + light screen |
| `billboard` | Street banner on a pole against real sky, from below | brand colour → white |
| `boxes` | Packaging stack on a seamless sweep | black sweep → white sweep |
| `notebook` | Cloth-bound hardcover with the mark on the cover | foil on brand cloth → blind deboss on natural cloth |
| `glass` | Etched-glass partition, office blurred behind | dim → bright |

Building blocks for a new scene: `box`, `plane`, `cylinder`, `cyclorama`, `uv_plane`, `logo_mesh` (SVG → solid), `surface` (Poly Haven material, tinted), `printed` (ink / foil / blind deboss decal on one face, optionally on a cloth or paper texture), `etched_glass`, `screen_material`, `world` (HDRI), `area` / `spot` / `sun`, `camera`. Add the function to `SCENES` and a `render('<id>')` line in `match-config.ts`.

What makes a render read as a photo, roughly in order of impact:
- **Light from an HDRI,** plus at most one area light or spot as the key. Never flat ambient.
- **Real materials:** Poly Haven diffuse, roughness and normal maps. Paper gets fibre bump, ink is slightly glossier than stock, foil is metal.
- **Depth of field** at f/2–4 for tabletop shots, focused on the mark.
- **Physical scale:** cards are 85×55×0.7mm, a phone is 72×148×8mm, a sign letter 3cm deep.
- **Imperfection:** stacked cards slightly misaligned, a bevel on every edge.
- **Film grain:** the template adds it to photo cuts (`grain`, default 1).

`npm run shots -- <scene> --save-blend` also writes `blender/build/<scene>_<v>.blend` for hand tweaking in the Blender UI.

### Shot kinds (Remotion)

| Kind | Use |
|---|---|
| `photo` | Every mockup: Blender renders (`render('<id>')` → `src` + `srcB`), the designer's own renders, or real photos with `logo.quad` |
| `grid` | Flat construction frame: `keyline` icon grid or full-bleed `guides` |
| `pattern` | Flat: the mark tiled as a signature pattern |
| `lockup` | Flat: mark + name + tagline |
| `surface` | Flat: mark on a solid colour (`material: 'flat'`) |
| `card`, `app-icon`, `badge`, `sign`, `ui` | Drawn fallbacks for a no-Blender draft only. They look like animation |

Tone fields for flat frames: `tone` (A), `toneB` (default: whichever of light/dark contrasts), `treatment` (B = filtered copy). Photo B is `srcB`, or a `treatment` (`mono`, `negative`, `dim`) when there's only one image.

### Other photo sources

1. **The designer's own mockup renders** (PSD mockups). Export each at 1080×1920, ideally dark and light → `src` + `srcB`.
2. **A blank-object photo + `logo.quad`:** the four corners (TL, TR, BR, BL, as frame fractions) where the mark goes. The template maps it on in perspective. Use `blend: 'multiply'` for ink on light material and `'screen'` for light on dark.
3. **An origin photo** (the falcon, the cap): a plain photo shot with the subject on the match point.

Crop every photo to exactly 1080×1920 first: `ffmpeg -i in.jpg -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" public/shots/x.jpg`.

### Workflow

1. Run the intake and fill in `identity.json`. Then `npm run assets` (once) and `npm run textures`.
2. Pick 10–15 scenes: about 3 renders for every flat frame. Write the shot-sheet comment, then `shots[]`.
3. Quick-look renders at half scale. Read each JPG and check that the mark sits on the match point, nothing clips, and A is dark and B light. Then `npm run shots` at full res.
4. `npm run sheet` and read the contact sheet.
5. Pick the music, then the rhythm: `rhythms.fromTrack()` for a track with hits, or a preset sized to the track's length. Set `audio.music` and `audio.startFrom`.
6. `npm run render:preview`, then `npm run measure -- out/preview.mp4`. Expect the planned lengths and no weak flips except deliberate ones.
7. `npm run render`. Hand over both MP4s (with sound for review, `-upload` for posting) and a draft caption the user rewrites in their own words.

## Analysing a reference reel

Instagram reel pages need a login, but `https://www.instagram.com/reel/<ID>/embed/captioned/` plays logged out and shows the post caption. In the built-in browser pane:

1. Open the embed URL and click play.
2. Make a CORS-clean copy of the video so canvas reads work. Nothing is downloaded:
   ```js
   const v = document.querySelector('video'); const v2 = document.createElement('video');
   v2.crossOrigin = 'anonymous'; v2.muted = true; v2.src = v.currentSrc;
   await new Promise(r => v2.onloadeddata = r); window.__v2 = v2;
   ```
3. Seek in 1/30s steps, draw each frame at 36×64, and take the mean absolute difference from the previous frame. Spikes are cuts, and 0 means a still. Record mean luma per cut too.
4. Draw one frame per cut into a grid of canvases on the page and screenshot it. That's the contact sheet: it shows the pairs, the match point and the shot order.

`npm run measure` does steps 3–4's numbers for any local MP4.

## Pitfalls

- **Broken match:** a mockup puts the mark somewhere else for three cuts in a row, and the reel turns into a slideshow. Keep breathers isolated.
- **Weak flips:** two light cuts next to each other flatten the strobe. A `brand` or `accent` tone near mid-grey is the usual cause. Set `toneB` explicitly.
- **`invert` on photos** turns brand colours to their complements. Use `mono`, `negative` or `srcB`.
- **The hold isn't the hero:** `hold` defaults to the very first cut, so make shot 1 the shot you want to end on.
- **Text cuts:** a tagline on a 3-frame cut is unreadable. Only the name has to register, and the lockup should be big.
- **Fonts and SVG:** Google fonts load over the network at render time. A logo without a `viewBox` throws.
- **Drawn mockups:** a CSS/SVG card or sign next to real renders gives the whole reel away as animation. If Blender isn't available, use fewer, flatter brand frames rather than fake 3D.
- **Blender world positions:** `obj.matrix_world` is stale until `view_layer.update()`. Use `world_point()`, or the camera aims at the origin and the frame comes out empty.
- **First Cycles render** on a machine compiles Metal kernels for several minutes. Later renders take seconds, so don't kill it.
- **Music a frame late:** Remotion's AAC carries ~43ms of encoder padding with no edit list, so cuts on hits look early. `npm run render` runs `scripts/align_audio.py <mp4> <track>` to fix it; run it by hand after any other render with music.
- **Timing cuts from a decoder Remotion doesn't use:** librosa's audioread path for m4a/AAC sits about a frame off from ffmpeg. `cuts_from_track.py` decodes with ffmpeg; do the same in any ad-hoc analysis.
- **Dark A that isn't dark:** strong key light lifts a charcoal wall to mid-grey and kills the strobe. Check luma in the contact sheet and lower the material `value` or the light power.
