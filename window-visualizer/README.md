# window-visualizer, a Claude Code skill

Turns any song into a building at night: a 9 x 20 grid of apartment windows that switch on and off with the music,
your voice saying the lines, and every caption word landing as you say it. Rendered in code to a 9:16 MP4 in under
a minute.

- **Every window is drawn in code**, each one a different room (lamps, curtains, plants, blinds), so there's no
  stock footage to license. Or cut real windows out of your own night photo of a building (`windows.py tiles`).
- **The song drives the light**: each window listens to one part of the song, so the building flashes on the drums
  and goes dark in the gaps.
- **Your voice, on the beat**: record yourself line by line with a teleprompter (or use Fish Audio / ElevenLabs).
  It transcribes your takes so the captions follow what you actually said, then moves each line so it starts on the
  song's beat, with your payoff line on the drop.
- **Ready to post**: you also get an `-upload.mp4` without the song, so you can add the official sound in Instagram
  or TikTok.

## Install

This skill uses the voice recorder, mixer and renderer from the **launch-video** skill, so you need both.

1. Get launch-video (free): https://keeran-ai.beehiiv.com/products/launch-video
2. Put both folders, `window-visualizer` (this one) and `launch-video`, side by side in `~/.claude/skills/` (every
   project) or `<your project>/.claude/skills/` (one project).
3. Install the renderer and the Python bits once:
   ```bash
   cd ~/.claude/skills/launch-video/engine && npm install
   pip3 install numpy scipy librosa pillow requests sounddevice faster-whisper
   ```
   Needs Google Chrome and ffmpeg (`brew install ffmpeg`).
4. Optional keys go in `launch-video/.env` (copy `.env.example`): Fish Audio, ElevenLabs, Auphonic.
5. In Claude Code, say "make a window visualizer video with this song" (or run `/window-visualizer`).

Example: `examples/starter/plan.json`. Put a song next to it as `song.m4a`, then
`python3 ~/.claude/skills/window-visualizer/windows.py make <that folder> --voice say` for a draft in a free Mac
voice.
