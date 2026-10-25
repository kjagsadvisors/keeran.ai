# Teardown: the windows reel

The reference: a viral window-visualizer reel (51.5k likes, 80 comments) · 17.0 s, 1076x1914, 30 fps.

## Picture
- Pure black frame. Grid of 9 columns x 20 rows, centred both ways: x 138-937, y 136-1770 (of 1076 x 1914).
  Pitch 90 x 83.4 px, each window 76 x 48 (landscape, 1.58:1). In frame-width units: pitch 0.0836 x 0.0775,
  window 0.0706 x 0.0446 - the engine uses these.
- Lit window = a photo of a real lit window: deep orange/amber/yellow mostly, some green, teal, blue, the odd red.
  Typical build: thick black frame, a big pane + a narrow side pane, a striped balcony band along the bottom,
  curtains/lamps/plants/trees as dark silhouettes. 109 of 171 cells ever light; the rest stay dark (empty flats).
- Unlit window = black, its frame barely visible (max ~18/255).
- Windows snap on and off (no fades). The pattern holds 4-5 frames at a time in places (the source was a screen
  recording of the web app).

## Light vs sound
- Driven by hits, not loudness: lit share correlates 0.39 with RMS but 0.66 with onset flux held by a fast release.
  A loud sustained chorus sits at ~5 % lit with spikes to 40-60 % on the drums.
- Fitted model (engine defaults): six bands (30-150-400-1000-2500-6000-11000 Hz), positive log-magnitude change per
  band, instant attack, release x0.85 per frame, normalised at the 94th percentile, +10 % of the band level; each
  window takes one band and a threshold in 0.25-0.85, 70 % of windows can light. Correlation 0.79 with the reel's
  lit share, average 15.5 % vs 14.6 %, 66 % lit on the big hit at 9.75 s vs 62 %.

## Captions
- White, neo-grotesk ~600 weight, tight tracking, font size ~0.05 x frame width, centred at 43.2 % of the height,
  no box. One word on screen at a time at talking pace; the last two lines are whole phrases; one word set in an
  italic serif for emphasis.
- Word changes at 0.0 1.0 1.2 1.5 1.6 2.8 3.9 4.0 4.2 4.4 4.8 5.0 5.2 5.5 5.7 | 9.5 9.8 10.0 | 11.6 | 13.2 | 14.4 s.

## Structure
| s | what |
|---|---|
| 0-6.4 | grid + hook, one word at a time (what this is and that it isn't hand-edited) |
| 6.4-9.5 | proof: a phone lying on a marble table running the web app, filmed handheld, warm lamp light |
| 9.5-11.5 | grid + what it was made with |
| 11.6-13.2 | "it works with any song." |
| 13.2-17.0 | call to action + the app's URL |

## Sound
- The reel's own soundtrack (a song). No voice-over, no SFX. The song isn't credited in the scraped metadata; the
  reel's audio page in the Instagram app shows it ("Use audio" reuses the exact sound).
