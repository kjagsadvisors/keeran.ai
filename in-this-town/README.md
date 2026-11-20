# in-this-town

"In this town, everybody is out partying except me. Huss huss huss." Claude writes the script about your own grind,
Higgsfield voices it and makes the blocky toy-town characters and every scene, and you get a finished 9:16 reel with
one yellow word on screen at a time, a "comment KEYWORD" call to action and an ending that loops back to the first
frame.

## Set it up in one paste

1. **Make a Higgsfield account through my link, which gets you a discount:** https://keeranai.com/go/higgsfield-skills.
   A full 90-second reel uses about 300 credits and a 45-second one about 130. (That's my affiliate link: I may earn
   a commission if you sign up through it.)
2. **Paste this into Claude Code** (the Code tab in the Claude desktop app works):

   ```
   Set up the in-this-town skill from https://github.com/kjagsadvisors/keeran.ai for me.

   1. Download the repo to a temporary folder and copy its in-this-town folder to ~/.claude/skills/in-this-town.
   2. Read its SKILL.md and take me through the Onboarding section, one step at a time. Run the commands yourself where you can.
   3. If I need to restart Claude, tell me, and I'll paste this prompt again.
   4. Once Higgsfield is connected, ask me what I grind at while everyone parties and what I want people to comment, then make the video. Use its defaults for everything else.
   ```

   Claude downloads the skill, checks your setup and connects Higgsfield with you. You sign in to Higgsfield once. If
   it asks you to restart, restart and paste the same prompt again.
3. **Make another one.** After the first time, this is all you type:

   ```
   /in-this-town make one about me grinding on my bakery while everyone parties, comment keyword BREAD
   ```

The same steps, with the reel I made: https://keeranai.com/in-this-town

## What it does

| Step | Made by |
|---|---|
| The script, in the trend's beats, about your grind | Claude |
| The voice (high, deadpan cartoon read) and the "huss" chant | Higgsfield, Seed Audio |
| The hero, the mayor, the neighbor, the six-legged cat, the room, the street | Higgsfield, Seedream 5 Pro |
| One clip per beat, plus a last clip that lands on the first frame | Higgsfield, MiniMax H3 (2K, 9:16) |
| Captions, the CTA pill and card, the loop, the mix | `town.py` (ffmpeg + Pillow, on your machine) |

You see the script and the characters before any clip is made. Re-cutting after a change is free.

## Music

The trend's song is "Numbers" by TEMPOREX. Add it in the Instagram or TikTok music picker when you post, so the app
handles the license. For music in the file, drop a track you have the rights to at `music.mp3` in the project folder,
or let the skill make an original one in Higgsfield (about 13 credits).

## Install by hand

Copy this folder into `~/.claude/skills/` (or your project's `.claude/skills/`). It needs Python 3.9+, ffmpeg,
`python3 -m pip install --user pillow soundfile numpy` (add `faster-whisper` for captions timed by ear), and the
Higgsfield connector: `claude mcp add --transport http higgsfield https://mcp.higgsfield.ai/mcp`, then `/mcp` to sign
in, then restart. In the Claude app: Settings > Connectors > Add custom connector, URL `https://mcp.higgsfield.ai/mcp`.

## What you get

`town/<name>/out/in-this-town.mp4` (1080x1920, 30 fps) plus a smaller `-phone.mp4`, and the plan, voice lines and
clips, so you can swap one line or one clip and cut it again.

The caption font is Luckiest Guy by Astigmatic (Apache 2.0, `fonts/LICENSE.txt`).
