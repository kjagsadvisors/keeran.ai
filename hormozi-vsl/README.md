# hormozi-vsl, a Claude Code skill

Takes an offer that doesn't have a sales video yet and ends with a finished VSL (video sales letter) you can put on your landing page.

**The structure is the VSL framework Alex Hormozi teaches on a whiteboard:**
1. An intro: promise, pain, proof, plan, and a road map.
2. Your process.
3. Each objection, broken in four moves: what they think, why that's wrong, what's actually right, and proof.
4. One clear call to action.

The frame-by-frame breakdown of his lesson and the research behind it are in this folder.

## How it works

- Claude asks you questions about your offer. Your answers become the lines, in your words.
- Then pick one:
  - **On-screen:** record each line yourself, and every word lands on screen as you say it, with your proof in between.
  - **On camera:** film the whole script on your phone, and it cuts your footage line by line with proof shots in between.
- Either way, it renders a 1080p MP4.

## Install

It runs on the **launch-video** skill, so install both:

1. Get launch-video (free): keeran-ai.beehiiv.com/products/launch-video
2. Put the `hormozi-vsl` and `launch-video` folders side by side in `~/.claude/skills/`.
3. Install the renderer and the voice tools once:
   ```bash
   cd ~/.claude/skills/launch-video/engine && npm install
   pip3 install numpy scipy requests sounddevice faster-whisper
   ```
   You need Google Chrome and ffmpeg (`brew install ffmpeg`).
4. In Claude Code, say "make a VSL for my offer" (or run `/hormozi-vsl`).

Start from `examples/skeleton/plan.json` to see the structure.

Only real proof: every number, review and before/after in your VSL has to be yours.
