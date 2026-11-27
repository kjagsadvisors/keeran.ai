---
name: voice-studio
description: Record your own voiceover one line at a time in Take One, a voice studio Claude puts in your Claude account as a private artifact that installs as a Mac app and records your Mac's mic, then get it back as one clean, mastered track with timings and captions. Claude splits the script into takes, the user records each line right in the studio (installed as an app from the Claude desktop app) or drops in files from a phone, listens, keeps the best take and taps Ready for edit; Claude pulls the takes straight out of the studio, runs them through Auphonic (the user's own free account, set up once with the key kept in the Mac's Keychain), trims the dead air, levels every line, joins them and masters to -16 LUFS, then can put the finished video back in the studio to watch. Use when someone wants to record a voiceover in their own voice, a "voice studio", a teleprompter-style line-by-line recording, says "Voiceover finished for <title>", or wants their own voice instead of AI voices for a reel, ad, VSL, explainer or launch video.
---

# voice-studio

Take One is a voice studio page (`studio.html`, next to this file). Claude publishes it once as the user's own private
artifact. It keeps their scripts and every take in the artifact's storage, so they can record on their phone and finish
on their laptop. Claude reads the takes straight out of it with the Artifact tools, and `voice_studio.py` turns them into
one clean track. Work in one folder per voiceover, `voice/<slug>/` in the user's project (called `<dir>` below).

**Recording in the page:** a Claude artifact in a browser tab can't use the mic, but installed as an app from the Claude
desktop app it can (the `desktop` capability). In that window the studio shows **Record**: it uses the web mic if the
window grants it, otherwise Apple's AVAudioRecorder records the Mac's default mic, raw, as a 48 kHz WAV. The studio
builds that recorder once from `recorder/takeone-rec.swift` with `swiftc` (Apple's command line tools; if they're
missing it says to run `xcode-select --install`). Not ffmpeg: its avfoundation input drops 512-sample packets, which
sounds like the voice cutting in and out. Every take gets a dropout check when it stops, and `voice_studio.py clean`
refuses takes with dropouts. The first time, the person allows the recorder to run, and macOS asks about the mic: both are their
clicks, never Claude's. Anywhere else the studio offers **Install to record here**, and still takes dropped files
(Voice Memos, QuickTime, any recorder), one per line. Mac only.

## Onboarding (first run)

1. `python3 <skill>/voice_studio.py check`. If ffmpeg is missing, show the install line it prints and offer to run it.
   It also reports Apple's command line tools (the recorder) and Auphonic.
2. **Auphonic, the most important step.** It does the main cleanup, and the voice sounds noticeably worse without it.
   If `check` printed "OK: Auphonic account …", skip ahead. Otherwise walk them through it, with browser control when
   this session has it (Claude in Chrome, else the built-in browser; without either, give them the links):
   1. Open https://auphonic.com/accounts/register/ and let them make a free account (2 hours of audio a month, no
      card). The email, password and verification code are theirs: never type them, never sign in for them.
   2. Once they're signed in, open https://auphonic.com/accounts/settings/#api-key. Ask them to create an API key
      named "Claude voice studio" and copy it (its copy button, or select it and press Cmd+C). **Never read, zoom
      into, screenshot or type the key.** If you need to see the page, look before the key exists.
   3. Run `python3 <skill>/voice_studio.py auphonic-key`. It takes the key from the clipboard, checks it with Auphonic,
      saves it in the Mac's Keychain (service `auphonic-api-key`) and clears the clipboard. It prints only the account
      name and credits left. If it says the clipboard doesn't hold a key, ask them to copy it again.
   4. If `check` flagged numpy as missing, run `python3 -m pip install --user numpy` (it lines the takes back up
      after Auphonic's free-plan jingle).
   Never put the key in a file in the project, in chat, or in a command you echo. Not on a Mac: they set
   `AUPHONIC_API_KEY` in their environment, and `auphonic-key --stdin` can check it.
3. Look for the Artifact and ArtifactData tools (load them with ToolSearch if they're deferred). Take One needs them:
   they're in the Code tab of the Claude desktop app. Without them, say so and stop.
4. Find their studio: read `~/.claude/voice-studio.json` (`{"studio": "<url>"}`). If it's missing, publish one:
   Artifact `publish` with `file_path: <skill>/studio.html`, `capabilities: {"db": {}, "assets": {}, "downloads": true, "desktop": {}}`,
   `icon: "mic"`, description "My voice studio: one line at a time." Write the URL it returns to
   `~/.claude/voice-studio.json`. It's private to them; nobody else can open it unless they share it.
5. Give them the link and how to record in it: open it in the Claude desktop app and press **Install to record here**
   (or Install as app in the artifact's menu), open Take One from the Dock, press Record or Space for each line, keep
   the best take, tap Ready for edit, then tell me. On a phone or another computer: record each line anywhere and drop
   it on its card.

## 1. The words come first, and they're theirs

Ask what the voiceover is for and what they want to say. Take their words: notes, a rough outline, a transcript of them
riffing, or what they type. Tidy only: split it into takes, fix typos, keep their phrasing.

- One take = one breath: a sentence or two, about 6 to 20 words. A take is what they'll re-record if they fluff it, so
  keep them short.
- Budget about 2.5 words a second. A 30-second reel is about 70 words.
- If they ask Claude to write it, write the way people talk out loud: short sentences, plain words. No "Here's the
  thing:" hooks, no colon reveals, no lists of three, no tidy metaphor at the end. Show them the lines and let them
  change anything before it goes in the studio. Words written to be read sound read.

Put the script in the studio:

```bash
python3 <skill>/voice_studio.py seed "<Title>" <dir>/script.txt --out <dir>/studio-doc.json
```

`script.txt` has a blank line between takes. The command prints a `doc_id`. Then ArtifactData `set` with the studio
`url`, `collection: "scripts"`, that `doc_id` and `file_path: <dir>/studio-doc.json`. It shows up in their studio
straight away. (They can also paste a script in the studio themselves with **New script**.)

## 2. They record

Tell them, briefly:

- Quiet room, soft furnishings beat bare walls. Phone or mic 6 to 8 inches away, the same distance every take.
- Leave a second of silence before and after each line. Claude trims it.
- In the installed app: **Space** records, **Space** again stops, **P** plays it back, **Enter** keeps it and moves to
  the next line. Takes are raw on purpose (no auto gain or noise suppression): the cleanup works on the real signal.
- Anywhere else, one file per line (Voice Memos on a phone, rename it to the line number if they like). Drop several
  files at once and they fill the lines in order of file name. Listen (**P**), keep (**Enter**), replace (**R**).
- When every line is kept, tap **Ready for edit** and tell Claude: "Voiceover finished for <Title>."

## 3. Pull the takes

1. ArtifactData `list`, `url: <studio>`, `collection: "scripts"`, `out_dir: <dir>/studio`. Find the file whose
   `title` matches. Check `status` is `ready`, or that every line has `take.status: "kept"`. If lines are missing,
   name them and ask whether to go on without them (`--allow-missing`).
2. For every kept line, Artifact `read` with `url: <studio>`, `path: <take.assetId>` and
   `out_dir: <dir>/studio/assets`. One asset per call (the `paths` list doesn't take asset ids). Send the calls together.
3. ```bash
   python3 <skill>/voice_studio.py unpack --doc <dir>/studio/scripts/<doc_id>.json --assets <dir>/studio/assets --out <dir>
   ```
   This writes `<dir>/takes/01.m4a, 02.m4a, ...` exactly as they were recorded, and `<dir>/lines.json`.

No Artifact tools in this session? They can tap **Download session ZIP** in the studio instead:
`voice_studio.py unpack --zip ~/Downloads/<Title>.zip --out <dir>`.

## 4. Clean it

```bash
python3 <skill>/voice_studio.py clean <dir>
```

Per take: finds the speech against that take's own room tone (so it works in a quiet studio and a noisy kitchen),
keeps 0.12 s before the first word and 0.2 s after the last, cuts rumble below 80 Hz, reduces steady noise, pulls the
room tone in the pauses down, and sets every line to the same loudness. Then it joins the lines with 0.3 s between
them and masters the whole track to -16 LUFS with the true peak under -1.5 dBTP (right for Reels, TikTok and
YouTube). Nothing inside a line is sped up, slowed down or cut.

Outputs in `<dir>`: `voiceover.wav` and `voiceover.mp3` (the track), `lines/NN.wav` (each line, mastered),
`timings.json` (where each line starts and ends) and `captions.srt` (one caption per line).

Options: `--gap 0.5` for more air between lines, `--lufs -14` for louder, `--no-gate` to leave the room tone in,
`--no-trim` to keep whole files, `--tail 0.4` if line endings sound clipped.

**Auphonic runs first, automatically, whenever their key is set up** (onboarding step 2). All the takes go to
[Auphonic](https://auphonic.com) as ONE production, then come back split at the exact same sample boundaries. The
settings are fixed on purpose, so keep them: filtering on, Adaptive Leveler on, loudness -16 LUFS, max peak -1.5 dBTP,
dynamic noise reduction at 12 dB, de-reverb and de-breath off, and the silence, filler, cough and music cutters **off**.
The cutters would change the timing, and the edit is timed to the takes. Don't swap in an Auphonic preset. One
production for all the takes matters too: Auphonic bills at least 3 minutes per production. The free plan adds a short
jingle; `auphonic.py` finds where the takes start by cross-correlation, cuts it off and checks every line lines up
before splitting. On their own Auphonic, the local gate is skipped: Auphonic already pulls the room down, and a gate on
top eats the quiet ends of words. Cleaned files are cached as `takes/NN.auph.wav`; `--fresh` redoes them,
`--no-auphonic` skips it. Before a big batch, `voice_studio.py auphonic-check` shows the credits left.

**Check before handing it over.** Claude can't hear audio, so say that, and check the numbers instead: the table
`clean` prints (how much was cut before and after each line, each line's level and gain), the final LUFS and true peak.
Flag a line that needed more than +12 dB (they were far from the mic), or a take where almost nothing was cut (the
trim may not have found the speech: suggest a re-record or `--no-trim`). Ask them to listen to `voiceover.mp3`.

## 5. Use it

- Build the video on the real timings, not estimates: every line's `start` and `end` in `timings.json` is where it
  lands in `voiceover.wav`. Anchor each scene or caption to those. A scene that needs more time gets a longer gap
  there, never a stretched voice.
- `lines/NN.wav` drop straight into Remotion, CapCut, Premiere or Final Cut one by one.
- `captions.srt` imports into CapCut, Premiere and YouTube.

**Put the finished video back in their studio** so they can watch it where they recorded: Artifact `publish` with
`url: <studio>`, `asset: true`, `file_path: <video.mp4>` (15 MB at most; make a 720p copy if it's bigger). Then
ArtifactData `update` on `scripts/<doc_id>` with the `if_version` from your last read and
`data: {"cut": {"assetId": "<id>", "title": "The <Title> cut.", "note": "<one line on what changed>"}}`.
A **Watch the cut** link appears in the studio.

## Re-records

They replace a take in the studio (**R**), keep it, and say so. Pull again (steps 3 and 4): `unpack` clears
`<dir>/takes/` first, and `clean` rebuilds everything. Changing a line's words in the studio drops that line's take, so
it must be recorded again.

## Files

- `studio.html`: the studio page. Scripts live in the artifact database (`scripts/<id>`: `title`, `status`,
  `lines[] {id, text, take}`); each take is an asset holding a JSON envelope
  (`format: "take-one-take"`, `fileName`, `mime`, `data` = the original file, base64), because artifact storage
  doesn't take audio files directly.
- `voice_studio.py`: `check`, `seed`, `unpack`, `clean`. Python 3.9+, standard library, ffmpeg.
- `auphonic.py`: the optional Auphonic pass.
