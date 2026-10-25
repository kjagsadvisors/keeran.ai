#!/usr/bin/env python3
"""Window visualizer videos: a night apartment block where every window is a light the song switches on and off.

  python3 windows.py new     <project> [--song FILE]          starter plan.json to fill in
  python3 windows.py make    <project> [--voice say|fish|eleven|keep] [--voice-id ID] [--draft]
                                                              voice -> captions -> light -> frames -> sound -> MP4s
  python3 windows.py analyze <project>                        song -> out/audio.json, voice -> out/captions.json
  python3 windows.py render  <project> [--draft] [--still 2,5] [--board]
  python3 windows.py start   <song> [--dur 17]                where the song is busiest (a start point to cut from)
  python3 windows.py tiles   <photo> --out <project>/tiles    cut the lit windows out of a night facade photo

The windows are drawn in code (every one a different room) unless the plan points "windows" at a folder of tiles.
Voiced plans ("scenes", each a spoken "vo" line) use the launch-video skill's vo.py exactly like launch videos
(record / import / auphonic / fish / eleven / say -> timeline.json), and every caption word appears as it's said.
Plans without scenes take hand-timed "captions" instead. "*word*" sets a word in the italic serif.
Outputs in <project>/out: <name>.mp4 (review: voice over the song), <name>-upload.mp4 (voice only: add the song in
the app), <name>-cutnotes.mp4 (720p review copy), board.jpg.
"""
import argparse, glob, json, os, subprocess, sys
import numpy as np

SKILL = os.path.dirname(os.path.abspath(__file__))
LAUNCH = os.path.join(os.path.dirname(SKILL), "launch-video")
sys.path.insert(0, LAUNCH)
import vo as voice      # noqa: E402  (launch-video's voice module: spoken text, timeline)
import audio as mixer   # noqa: E402  (launch-video's mixer: song ducked under the voice, upload without the song)
FPS = 30
SR = 22050
EDGES = [30, 150, 400, 1000, 2500, 6000, 11000]     # six bands; each window listens to one


# ---------- plan ----------
def load(proj):
    return json.load(open(os.path.join(proj, "plan.json")))


def song_path(proj, plan):
    m = plan.get("music") or {}
    f = m.get("file")
    if not f:
        return None
    p = f if os.path.isabs(f) else os.path.normpath(os.path.join(proj, f))
    if not os.path.exists(p):
        sys.exit(f"song not found: {p}")
    return p


def voiced(plan):
    return bool(plan.get("scenes"))


def timeline(proj):
    p = os.path.join(proj, "timeline.json")
    return json.load(open(p)) if os.path.exists(p) else None


def duration(proj, plan):
    if voiced(plan):
        tl = timeline(proj)
        if not tl:
            sys.exit("no timeline.json yet: voice it first (windows.py make --voice say, or vo.py record/import)")
        return float(tl["duration"])
    if plan.get("duration"):
        return float(plan["duration"])
    p = song_path(proj, plan)
    if not p:
        return 15.0
    return max(1.0, probe_len(p) - float((plan.get("music") or {}).get("start", 0)))


def probe_len(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def read_mono(p, start=0.0, dur=None, sr=SR):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start), "-i", p] + (["-t", str(dur)] if dur else []) + ["-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32)


# ---------- audio -> light ----------
def bands(x, n, fps=FPS, sr=SR):
    """Log magnitude per band, one row per video frame (2048-point window centred on the frame)."""
    hop, N = sr / fps, 2048
    f = np.fft.rfftfreq(N, 1 / sr)
    sel = [(f >= EDGES[i]) & (f < EDGES[i + 1]) for i in range(len(EDGES) - 1)]
    win, out = np.hanning(N), np.zeros((n, len(sel)))
    for i in range(n):
        s = int(i * hop) - N // 2
        seg = x[max(0, s):s + N]
        if s < 0:
            seg = np.pad(seg, (-s, 0))
        if len(seg) < N:
            seg = np.pad(seg, (0, N - len(seg)))
        sp = np.abs(np.fft.rfft(seg * win))
        out[i] = [np.log1p(sp[m].mean() * 40) for m in sel]
    return out


def envelopes(B, decay=0.85, level=0.1):
    """Hits, not loudness: positive change per band (onset flux) with an instant attack and a fast release, plus a
    little of the level so a loud held note keeps a few windows on. Normalised per band to 0..1."""
    flux = np.maximum(0, np.diff(B, axis=0, prepend=np.zeros((1, B.shape[1])) + B.min(0)))   # a song that starts loud starts on a hit
    env = np.zeros_like(flux)
    for i in range(len(flux)):
        env[i] = np.maximum(flux[i], env[i - 1] * decay if i else 0)
    env /= np.maximum(1e-6, np.percentile(env, 94, axis=0))     # fitted to the reference reel's lit windows
    lo, hi = np.percentile(B, 10, axis=0), np.percentile(B, 99, axis=0)
    lev = np.clip((B - lo) / np.maximum(1e-6, hi - lo), 0, 1) ** 2
    return np.clip((1 - level) * env + level * lev, 0, 1)


def analyze(proj, quiet=False):
    plan = load(proj)
    out = os.path.join(proj, "out")
    os.makedirs(out, exist_ok=True)
    D = duration(proj, plan)
    n = int(round(D * FPS))
    p = song_path(proj, plan)
    r = plan.get("react", {})
    if p:
        x = read_mono(p, float(plan["music"].get("start", 0)), D)
        E = envelopes(bands(x, n), r.get("decay", 0.85), r.get("level", 0.1))
    else:
        E = np.zeros((n, len(EDGES) - 1))
    E = np.clip(E * r.get("gain", 1.0), 0, 1)
    json.dump({"fps": FPS, "duration": D, "bands": [[int(v * 255) for v in row] for row in E]}, open(os.path.join(out, "audio.json"), "w"))
    cp = os.path.join(out, "captions.json")
    if voiced(plan):
        caps = captions(plan, timeline(proj))
        json.dump(caps, open(cp, "w"), indent=1)
    elif os.path.exists(cp):
        os.remove(cp)
    if not quiet:
        print(f"  {n} frames, {D:.2f} s, mean light {E.mean():.2f}" + ("" if p else "  (no song: windows stay dark)"))
    return E


def captions(plan, tl):
    """Voice timeline -> caption changes. Default: one word on screen at a time, each appearing as it's said and
    staying until the next one. "show": "line" puts the whole line up for the scene; "caption" shows other text than
    what's said (e.g. said "comment skill and I'll send it to you", shown "comment *skill*"). Scenes with no voice show
    their "caption" as text only (whole, or "show": "words" one word every "pace" seconds), or nothing."""
    out = []
    for sc, ts in zip(plan["scenes"], tl["scenes"]):
        words = ts.get("words") or []
        if not sc.get("vo") or sc.get("caption") == "":
            text = sc.get("caption") or ""
            if text and sc.get("show") == "words":
                for k, w in enumerate(text.split()):
                    out.append({"at": ts["start"] + k * sc.get("pace", 0.28), "text": w})
            else:
                out.append({"at": ts["start"], "text": text})
            continue
        if sc.get("caption") or sc.get("show") == "line":
            text = sc.get("caption") or sc["vo"]
            out.append({"at": max(ts["start"], (words[0]["s"] if words else ts["start"]) - 0.05), "text": text})
            continue
        shown = sc["vo"].split()                            # keeps *markup*; one shown word per spoken word
        if len(shown) != len(words):
            shown = [w["w"] for w in words]
        out.append({"at": ts["start"], "text": ""})
        for w, s in zip(words, shown):
            out.append({"at": max(ts["start"], w["s"] - 0.03), "text": s})
    out.sort(key=lambda c: c["at"])
    return [{"at": round(c["at"], 3), "text": c["text"]} for c in out]


def grid(song, start=0.0, until=None):
    """The song's beats, bar starts and biggest drop, in video time (seconds after music.start). Same method as
    tools/music.py: librosa beat track (filled in on the same period where the tracker skips the start or end), bar
    phase = the beat-in-4 whose low end hits hardest, drop = biggest 2-bar rise in loudness, looked for only before
    `until` seconds of video (a drop the video never reaches is no use)."""
    import librosa
    y = read_mono(song)
    hop, dur = 512, len(y) / SR
    on = librosa.onset.onset_strength(y=y, sr=SR, hop_length=hop)
    _, bt = librosa.beat.beat_track(onset_envelope=on, sr=SR, hop_length=hop, tightness=120)
    beats = librosa.frames_to_time(bt, sr=SR, hop_length=hop)
    if len(beats) >= 4:
        per = float(np.median(np.diff(beats)))
        beats = np.r_[np.arange(beats[0] - per, -0.01, -per)[::-1], beats, np.arange(beats[-1] + per, dur, per)]
    bt = np.minimum(librosa.time_to_frames(beats, sr=SR, hop_length=hop), len(on) - 1)
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop))
    low = S[librosa.fft_frequencies(sr=SR, n_fft=2048) < 150].sum(0)
    lowb = low[np.minimum(bt, len(low) - 1)]
    phase = int(np.argmax([lowb[p::4].mean() for p in range(4)])) if len(lowb) >= 8 else 0
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    e = np.array([20 * np.log10(rms[a:max(b, a + 1)].mean() + 1e-6) for a, b in zip(bt[:-1], bt[1:])]) if len(bt) > 1 else np.array([])
    drop = None
    if len(e) > 16:
        sm = np.convolve(e, np.ones(8) / 8, "same")
        rise = sm[8:] - sm[:-8]
        at = beats[4:4 + len(rise)] - start
        ok = (at >= 0) & (at <= (until if until is not None else 1e9))
        if ok.any():
            i = int(np.argmax(np.where(ok, rise, -1e9)))
            if rise[i] > 2.0:
                drop = float(at[i])
    v = beats - start
    bars = beats[phase::4] - start
    return v[v >= 0], bars[bars >= 0], drop


def lock(proj, plan):
    """Line the voice up with the song: each spoken line moves so its anchor word lands on a beat (a bar start when
    that's close); a scene with "on": "drop" lands on the drop, planned backwards so the windows-only stretch before
    it takes up the slack; other windows-only scenes end on a bar; the ending holds to a bar. Lines only ever wait
    (never overlap). Writes pre / dur / hold into plan.json for vo.py build."""
    tl = timeline(proj)
    song = song_path(proj, plan)
    if not tl or not song:
        return False
    L = plan["lock"] if isinstance(plan["lock"], dict) else {}
    cfg = plan.get("vo") or {}
    lead, dpre, dpost, dhold = cfg.get("lead", 0.3), cfg.get("pre", 0.12), cfg.get("post", 0.28), cfg.get("hold", 1.3)
    beats, bars, drop = grid(song, float(plan["music"].get("start", 0)), until=tl["duration"] + 6)
    if len(beats) < 4:
        return False
    bl = float(np.median(np.diff(beats)))
    note = None
    prefer = L.get("bar", 0.7) * bl                  # waiting up to this much longer for a bar start beats an off-bar beat
    minpre = L.get("min_pre", 0.06)
    isbar = lambda b: bool(len(bars)) and np.min(np.abs(bars - b)) < 0.03
    sc_, n = plan["scenes"], len(plan["scenes"])
    # what each spoken line needs: where its anchor word sits in the take, the take's length, the gap after it
    info = {}
    for i, (sc, ts) in enumerate(zip(sc_, tl["scenes"])):
        if not sc.get("vo") or sc.get("join"):
            continue
        words, a_old = ts["words"], ts["start"] + sc.get("pre", dpre)
        post = sc.get("post", dpost)
        k = sc.get("anchor", 0)
        k = len(words) - 1 if k == "last" else min(int(k), len(words) - 1)
        info[i] = {"off": words[k]["s"] - a_old, "post": post, "word": words[k]["w"], "was": words[k]["s"],
                   "clip": ts["end"] - a_old - post - (sc.get("hold", dhold) if i == n - 1 else 0)}
    tag = lambda T: "drop" if drop is not None and abs(T - drop) < 0.03 else "bar" if isbar(T) else "beat"
    moves, anchor = [], {}

    def place(i, t):                                   # forward: first good beat at or after the earliest moment
        f = info[i]
        earliest = t + minpre + f["off"]
        cands = [b for b in beats if earliest - 0.02 <= b <= earliest + 6 * bl]
        return min(cands, key=lambda b: (b - earliest) + (0 if isbar(b) else prefer)) if cands else earliest

    t, i = lead, 0
    while i < n:
        sc = sc_[i]
        if not sc.get("vo"):
            sc.setdefault("dur_want", float(sc.get("dur", 1.2)))     # what was asked for; "dur" becomes the locked length
            j = next((k for k in range(i + 1, n) if not sc_[k].get("vo")), n)
            pin = next((k for k in range(i + 1, j) if sc_[k].get("on") == "drop" and k in info), None)
            end = None
            if pin is not None and drop is not None:   # backwards from the drop: the windows stretch takes the slack
                T, plan_b = drop, {pin: drop}
                start = T - info[pin]["off"] - minpre
                for k in range(pin - 1, i, -1):
                    if k not in info:
                        continue
                    f = info[k]
                    latest = start - (f["clip"] - f["off"]) - f["post"]
                    cands = [b for b in beats if latest - 6 * bl <= b <= latest + 0.02]
                    Tk = max(cands, key=lambda b: -(latest - b) - (0 if isbar(b) else prefer)) if cands else latest
                    plan_b[k] = Tk
                    start = Tk - f["off"] - minpre
                stretch = start - t - sc["dur_want"]
                if L.get("min_windows", 1.5) <= start - t and stretch <= L.get("max_stretch", 8 * bl):
                    end = start
                    anchor.update(plan_b)
                else:                                  # out of reach: say where the song should start instead
                    shift = start - (t + sc["dur_want"])
                    note = (f"  the drop ({drop:.2f} s) is {'too far' if shift > 0 else 'too early'} for \"{info[pin]['word']}\": "
                            f"set music.start to about {float(plan['music'].get('start', 0)) + shift:.2f} to land it")
            if end is None:
                want = t + sc["dur_want"]
                near = [b for b in bars if abs(b - want) <= bl * 1.5 and b > t + 0.5] or \
                       [b for b in beats if abs(b - want) <= bl and b > t + 0.5]
                end = min(near, key=lambda b: abs(b - want)) if near else want
            sc["dur"] = round(end - t, 3)
            moves.append(f"  windows {t:5.2f}-{end:5.2f}" + ("  (ends on a bar)" if isbar(end) else ""))
            t, i = end, i + 1
            continue
        if i not in info:                              # chained into the previous take: it moves with it
            i += 1
            continue
        f = info[i]
        T = anchor.get(i)
        if T is None or T - f["off"] - t < minpre - 0.02:
            T = place(i, t)
        sc["pre"] = round(T - f["off"] - t, 3)
        moves.append(f"  \"{f['word']}\" {f['was']:5.2f} -> {T:5.2f} ({tag(T)})")
        t = T - f["off"] + f["clip"] + f["post"]
        if i == n - 1:
            fin = [b for b in bars if b >= t + L.get("min_hold", 0.9)]
            end = fin[0] if fin and fin[0] - t <= L.get("max_hold", 2.6) else t + sc.get("hold", dhold)
            sc["hold"] = round(end - t, 3)
            moves.append(f"  end {end:5.2f}" + ("  (on a bar)" if isbar(end) else ""))
        i += 1
    json.dump(plan, open(os.path.join(proj, "plan.json"), "w"), indent=1)
    print(f"beat lock: {60 / bl:.1f} BPM, bar every {4 * bl:.2f} s" + (f", drop {drop:.2f} s" if drop is not None else ""))
    print("\n".join(moves + ([note] if note else [])))
    return True


def busiest(song, dur=17.0):
    """Start of the busiest `dur` seconds (most onsets): usually the drop or the chorus."""
    x = read_mono(song, sr=11025)
    hop = 11025 // 10
    fr = np.array([np.sqrt((x[i:i + hop] ** 2).mean() + 1e-12) for i in range(0, len(x) - hop, hop)])
    on = np.maximum(0, np.diff(np.log(fr), prepend=np.log(fr[0])))
    k = int(dur * 10)
    if len(on) <= k:
        return 0.0
    score = np.convolve(on, np.ones(k), "valid") + 0.5 * np.convolve(fr / fr.max(), np.ones(k), "valid")
    i = int(np.argmax(score))
    j = i + int(np.argmax(on[i:i + 10]))          # land on the hit right after
    return round(j / 10, 2)


# ---------- window tiles from a photo ----------
def tiles(photo, out, aspect=1.58, min_px=18):
    """Find lit windows in a night facade photo (bright blobs on a dark wall) and save each as a tile."""
    from PIL import Image
    from scipy import ndimage
    im = Image.open(photo).convert("RGB")
    a = np.asarray(im, float)
    g = a.max(2)
    th = max(70, np.percentile(g, 80))
    m = ndimage.binary_closing(g > th, iterations=2)
    m = ndimage.binary_opening(m, iterations=1)
    lab, k = ndimage.label(m)
    boxes = ndimage.find_objects(lab)
    os.makedirs(out, exist_ok=True)
    for f in glob.glob(os.path.join(out, "tile_*.jpg")):
        os.remove(f)
    sizes = [((b[1].stop - b[1].start), (b[0].stop - b[0].start)) for b in boxes]
    areas = np.array([w * h for w, h in sizes]) if sizes else np.array([0])
    lo, hi = np.percentile(areas, 30), np.percentile(areas, 99)
    n = 0
    for b, (w, h) in zip(boxes, sizes):
        if w < min_px or h < min_px * 0.6 or not lo <= w * h <= hi or not 0.5 < w / h < 3.5:
            continue
        cx, cy = (b[1].start + b[1].stop) / 2, (b[0].start + b[0].stop) / 2
        tw = max(w, h * aspect) * 1.08
        th_ = tw / aspect
        box = (int(cx - tw / 2), int(cy - th_ / 2), int(cx + tw / 2), int(cy + th_ / 2))
        im.crop(box).resize((240, int(240 / aspect)), Image.LANCZOS).save(os.path.join(out, f"tile_{n:03d}.jpg"), quality=92)
        n += 1
    print(f"  {n} windows -> {out}" + ("  (few found: try a sharper, darker night photo)" if n < 40 else ""))


# ---------- render + sound ----------
def render(proj, extra=()):
    eng = os.path.join(SKILL, "engine")
    if not os.path.exists(os.path.join(LAUNCH, "engine", "node_modules")):
        sys.exit("run `npm install` in skills/launch-video/engine first (playwright-core + fonts)")
    r = subprocess.run(["node", os.path.join(eng, "render.mjs"), proj, *extra])
    if r.returncode:
        sys.exit("render failed")


def audio(proj):
    """mix.wav = the song cut to the video (review copy); mix-upload.wav = silence (add the same sound in the app).
    Voiced: the launch-video mixer, voice over the song ducked under it (review) and the voice alone (upload)."""
    plan = load(proj)
    o = os.path.join(proj, "out")
    D = duration(proj, plan)
    p = song_path(proj, plan)
    if voiced(plan):
        mixer.mix(proj, no_music=True)
        if p:
            mixer.mix(proj)
        else:
            subprocess.run(["cp", os.path.join(o, "mix-upload.wav"), os.path.join(o, "mix.wav")], check=True)
        return
    m = plan.get("music") or {}
    fade = float(m.get("fade_out", 0.4))
    if p:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(m.get("start", 0)), "-t", str(D), "-i", p, "-ac", "2", "-ar", "48000",
                        "-af", f"volume={m.get('gain', 1.0)},afade=t=out:st={max(0, D - fade)}:d={fade},apad=whole_dur={D}",
                        "-t", str(D), os.path.join(o, "mix.wav")], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", str(D),
                    os.path.join(o, "mix-upload.wav")], check=True)
    if not p:
        subprocess.run(["cp", os.path.join(o, "mix-upload.wav"), os.path.join(o, "mix.wav")], check=True)


def mux(proj, plan):
    name = plan.get("name") or os.path.basename(proj)
    o = os.path.join(proj, "out")
    pic = os.path.join(o, "picture.mp4")
    for wav, dst in (("mix.wav", f"{name}.mp4"), ("mix-upload.wav", f"{name}-upload.mp4")):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", pic, "-i", os.path.join(o, wav), "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", os.path.join(o, dst)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(o, f"{name}.mp4"), "-vf", "scale=720:1280:flags=lanczos",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-maxrate", "3M", "-bufsize", "6M", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", os.path.join(o, f"{name}-cutnotes.mp4")], check=True)
    for f in (f"{name}.mp4", f"{name}-upload.mp4", f"{name}-cutnotes.mp4"):
        print(f"  {os.path.join(o, f)}  {os.path.getsize(os.path.join(o, f)) / 1e6:.1f} MB")


def make(proj, a):
    plan = load(proj)
    if voiced(plan):                                      # the launch-video voice protocol, unchanged
        vo = os.path.join(LAUNCH, "vo.py")
        if a.voice == "say":
            subprocess.run(["python3", vo, "say", proj] + (["--voice", a.voice_id] if a.voice_id else []), check=True)
        elif a.voice in ("fish", "eleven"):
            if not a.voice_id:
                sys.exit(f"--voice-id is needed for {a.voice} (vo.py {a.voice}-voices lists them)")
            subprocess.run(["python3", vo, a.voice, proj, "--voice", a.voice_id], check=True)
        elif os.path.exists(os.path.join(proj, "vo", "clips.json")):
            subprocess.run(["python3", vo, "build", proj], check=True)
        if plan.get("lock") and lock(proj, load(proj)):
            subprocess.run(["python3", vo, "build", proj], check=True, stdout=subprocess.DEVNULL)
    analyze(proj)
    render(proj, ["--draft"] if a.draft else [])
    audio(proj)
    mux(proj, plan)


def new(proj, song=None):
    os.makedirs(proj, exist_ok=True)
    p = os.path.join(proj, "plan.json")
    if os.path.exists(p):
        sys.exit(f"{p} exists")
    music = {"file": os.path.relpath(os.path.abspath(song), proj), "start": busiest(song, 15.0)} if song else {"file": "", "start": 0}
    music.update({"gain": 0.7})
    plan = {
        "name": os.path.basename(os.path.abspath(proj)), "music": music, "mix": {"duck": 0.6}, "lock": {"bar": 0.7},
        "windows": {"source": "code", "seed": 7},
        "scenes": [
            {"type": "line", "vo": "these windows follow the song."},
            {"type": "line", "dur": 2.5},
            {"type": "line", "vo": "it works with *any* song.", "show": "line"},
            {"type": "line", "vo": "your call to action here.", "show": "line", "hold": 1.5},
        ],
    }
    json.dump(plan, open(p, "w"), indent=1)
    print("wrote", p)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new"); n.add_argument("project"); n.add_argument("--song")
    m = sub.add_parser("make"); m.add_argument("project"); m.add_argument("--draft", action="store_true")
    m.add_argument("--voice", default="keep", choices=["say", "fish", "eleven", "keep"],
                   help="keep = use the voice clips already in the project (recorded, imported or generated)")
    m.add_argument("--voice-id")
    sub.add_parser("analyze").add_argument("project")
    r = sub.add_parser("render"); r.add_argument("project"); r.add_argument("--draft", action="store_true")
    r.add_argument("--still"); r.add_argument("--board", action="store_true")
    s = sub.add_parser("start"); s.add_argument("song"); s.add_argument("--dur", type=float, default=17.0)
    t = sub.add_parser("tiles"); t.add_argument("photo"); t.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "start":
        print(busiest(a.song, a.dur))
        return
    if a.cmd == "tiles":
        tiles(a.photo, a.out)
        return
    proj = os.path.abspath(a.project)
    if a.cmd == "new":
        new(proj, a.song)
    elif a.cmd == "make":
        make(proj, a)
    elif a.cmd == "analyze":
        analyze(proj)
    elif a.cmd == "render":
        analyze(proj, quiet=True)
        render(proj, (["--draft"] if a.draft else []) + (["--still", a.still] if a.still else []) + (["--board"] if a.board else []))


if __name__ == "__main__":
    main()
