# reverse-video, a Claude Code skill

Paste a link to any reel: a travel montage, a cinematic edit, a talking head, a tutorial. Claude scrapes the video
with [context.dev](https://link.context.dev/keeran-jagadesan), analyzes every single frame, and writes down exactly
how it was edited. Then it edits your footage the same way.

What it measures, from every frame:

| | |
|---|---|
| Rhythm | every cut, shot lengths, how long the opening holds, whips, flashes and dips, push-ins and pans |
| Sound | tempo, how many cuts land on the beat, where the drop is and how the cutting speeds up after it, the hook |
| Look | full frame or a 16:9 / 4:3 / 2.39:1 band, the colour grade (blacks, contrast, saturation, warm or teal), palette |
| Text | how much is on screen, where it sits, how big, caps or not, how heavy, which colours, word-by-word builds |

You get a `STYLE.md` with every number, a frame from every shot, and a timeline of cuts, text, beats and loudness.
Claude reads it and edits your footage to match: a folder of travel clips and a song becomes a montage cut and graded
like the reference; a talking-head take gets its pacing, captions and look.

## Install

**The easy way:** paste the repo link into Claude Code and say "set up the reverse-video skill":

```
https://github.com/kjagsadvisors/keeran.ai
```

**By hand (Mac):**

1. Copy the `reverse-video` folder into `~/.claude/skills/`.
2. Install the tools once:
   ```bash
   xcode-select --install
   brew install ffmpeg
   pip3 install opencv-python numpy pillow librosa faster-whisper
   ```

## Connect context.dev

The first time you use the skill, Claude walks you through this. To do it yourself:

1. Make your free account with [this link](https://link.context.dev/keeran-jagadesan). The free plan is enough:
   1,000 credits a month, and one video link is 1 credit.
2. Upgrading? Code **KEERAN25OFF** takes 25% off your first 6 months.
3. Connect it:
   ```bash
   claude mcp add --transport http context https://mcp.context.dev/mcp
   ```
   Then type `/mcp` in Claude Code and sign in to `context`. In the Claude app: Settings > Connectors > Add custom
   connector, URL `https://mcp.context.dev/mcp`.
4. Check everything with `python3 ~/.claude/skills/reverse-video/reverse.py setup`.

That's my referral link, so I may earn a commission when you sign up or upgrade through it.

## Use it

```
/reverse-video https://www.instagram.com/reel/...  then edit my-take.mp4 like it
/reverse-video https://www.tiktok.com/@.../video/...  then cut my clips in ~/Travel/Japan to my song like this
```

Works with Instagram reels and TikToks, or any video file you have.

Copy the style, not the content: never reuse someone else's footage, voice, words or music.
