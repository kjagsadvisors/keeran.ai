#!/usr/bin/env python3
"""in-this-town: cut Higgsfield clips and voice lines into a finished, looping 9:16 reel.

    python3 town.py setup                 check ffmpeg, Pillow, faster-whisper
    python3 town.py prep   <project>      clean the raw voice lines (raw/ -> vo/)
    python3 town.py build  <project>      timeline, word captions, CTA, loop, final MP4
    python3 town.py frame  <video> <sec> <out.png>   grab one frame (use -1 for the last frame)
    python3 town.py sheet  <project>      contact sheet of every clip, to check them at a glance

A project folder holds:
    plan.json      the lines, which lines play over which clip, the comment keyword
    raw/NN.wav     one voice take per line, straight from Higgsfield
    clips/bNN.mp4  one clip per block, straight from Higgsfield
    music.mp3      optional music bed, ducked under the voice
It writes vo/, timeline.json, words.json and out/in-this-town.mp4 (+ a smaller -phone.mp4).
"""
import json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "LuckiestGuy.ttf")
FW, FH, FPS = 1080, 1920, 30
YEL, BLK, WHT = (255, 225, 0, 255), (0, 0, 0, 255), (255, 255, 255, 255)


def run(*a):
    subprocess.run([str(x) for x in a], check=True)


def dur(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]))


def load_plan(p):
    with open(os.path.join(p, "plan.json")) as f:
        plan = json.load(f)
    plan.setdefault("gap", 0.2)
    plan.setdefault("speed", 1.12)
    plan.setdefault("tail", 3.0)
    return plan


# ---------------------------------------------------------------- setup
def setup():
    ok = True
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool):
            print(f"ok  {tool}")
        else:
            ok = False
            print(f"!!  {tool} missing. Mac: brew install ffmpeg   Windows: winget install ffmpeg   Linux: apt install ffmpeg")
    try:
        import PIL  # noqa: F401
        print("ok  Pillow")
    except ImportError:
        ok = False
        print("!!  Pillow missing: python3 -m pip install --user pillow")
    try:
        import soundfile  # noqa: F401
        import numpy  # noqa: F401
        print("ok  soundfile + numpy")
    except ImportError:
        ok = False
        print("!!  soundfile/numpy missing: python3 -m pip install --user soundfile numpy")
    try:
        import faster_whisper  # noqa: F401
        print("ok  faster-whisper (word-accurate captions)")
    except ImportError:
        print("--  faster-whisper not installed. Captions will still work, timed by word length instead of by ear.")
        print("    For word-accurate captions: python3 -m pip install --user faster-whisper")
    print("ok  font" if os.path.exists(FONT) else "!!  fonts/LuckiestGuy.ttf is missing: re-download the skill")
    print("ready" if ok else "fix the !! lines, then run setup again")


# ---------------------------------------------------------------- prep
def prep(p):
    plan = load_plan(p)
    os.makedirs(os.path.join(p, "vo"), exist_ok=True)
    ids = sorted({l for blk in plan["blocks"] for l in blk})
    missing = [i for i in ids if not os.path.exists(os.path.join(p, "raw", f"{i}.wav"))]
    if missing:
        sys.exit(f"missing raw takes: {', '.join(missing)} (save each Higgsfield line as raw/<id>.wav)")
    s = plan["speed"]
    for i in ids:
        af = ("silenceremove=start_periods=1:start_threshold=-45dB:stop_periods=-1:stop_duration=0.16:stop_threshold=-45dB,"
              f"atempo={s},highpass=f=90,acompressor=threshold=-18dB:ratio=2.5,apad=pad_dur=0.06")
        run("ffmpeg", "-loglevel", "error", "-y", "-i", os.path.join(p, "raw", f"{i}.wav"), "-af", af,
            "-ac", "2", "-ar", "48000", os.path.join(p, "vo", f"{i}.wav"))
    print(f"cleaned {len(ids)} lines at {s}x into vo/")


# ---------------------------------------------------------------- timeline + words
def word_times(path, text, model):
    """Word timings for one line. Uses faster-whisper when present, else spreads the words by length."""
    import soundfile as sf
    toks = text.split()
    d = sf.info(path).duration
    if model is not None:
        segs, _ = model.transcribe(path, word_timestamps=True, language="en")
        ws = [(w.start, w.end) for s in segs for w in s.words]
        if len(ws) == len(toks):
            return [(a, b, t) for (a, b), t in zip(ws, toks)]
        a, b = (ws[0][0], ws[-1][1]) if ws else (0.0, d)
    else:
        a, b = 0.05, max(0.1, d - 0.1)
    total = sum(len(t) for t in toks) or 1
    out, t = [], a
    for tok in toks:
        span = (b - a) * len(tok) / total
        out.append((t, t + span, tok))
        t += span
    return out


def timeline(p, plan):
    import numpy as np
    import soundfile as sf
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("small", compute_type="int8")
    except Exception:
        model = None
    lines = plan["lines"]
    t, tl, words, pieces, cache = 0.0, [], [], [], {}
    for b, blk in enumerate(plan["blocks"], 1):
        for l in blk:
            f = os.path.join(p, "vo", f"{l}.wav")
            y, sr = sf.read(f)
            if y.ndim == 1:
                y = np.stack([y, y], 1)
            d = len(y) / sr
            tl.append({"block": b, "line": l, "start": round(t, 3), "dur": round(d, 3)})
            pieces.append((t, y, sr))
            if l not in cache:
                cache[l] = word_times(f, lines[l], model)
            for a, e, w in cache[l]:
                words.append({"t0": round(t + a, 3), "t1": round(t + e, 3), "w": w.strip(",.;:")})
            t += d + plan["gap"]
    sr = pieces[0][2]
    buf = np.zeros((int((t + plan["tail"] + 2) * sr), 2))
    for st, y, _ in pieces:
        i = int(st * sr)
        buf[i:i + len(y)] += y
    sf.write(os.path.join(p, "vo_master.wav"), buf, sr)
    json.dump(tl, open(os.path.join(p, "timeline.json"), "w"), indent=1)
    json.dump(words, open(os.path.join(p, "words.json"), "w"))
    return tl, words


# ---------------------------------------------------------------- captions
def captions(p, plan, tl, words, starts, END):
    from PIL import Image, ImageDraw, ImageFont
    F = lambda n: ImageFont.truetype(FONT, n)
    fw, fb, fs, fC, fH, fS = F(104), F(84), F(46), F(150), F(270), F(54)
    cta = plan.get("cta")
    os.makedirs(os.path.join(p, "cap"), exist_ok=True)

    def ctext(d, y, txt, font, fill, stroke=0):
        w = d.textlength(txt, font=font)
        d.text(((FW - w) / 2, y), txt, font=font, fill=fill, stroke_width=stroke, stroke_fill=BLK)

    def banner(d):
        x0, x1, y0, y1 = 150, 930, 150, 345
        d.rounded_rectangle((x0 + 6, y0 + 8, x1 + 6, y1 + 8), radius=48, fill=(0, 0, 0, 140))
        d.rounded_rectangle((x0, y0, x1, y1), radius=48, fill=YEL, outline=BLK, width=7)
        ctext(d, y0 + 22, f'COMMENT "{cta["keyword"].upper()}"', fb, BLK)
        ctext(d, y0 + 122, cta.get("banner_sub", "FOR THE FREE CLAUDE SKILL").upper(), fs, BLK)

    POP = [0.55, 0.8, 1.06, 1.0]

    def card(scale):
        im = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        cx, cy = 540, 420
        d.ellipse((cx - 95, cy - 80, cx + 95, cy + 80), fill=WHT, outline=BLK, width=10)
        d.polygon([(cx - 60, cy + 55), (cx - 95, cy + 120), (cx - 15, cy + 75)], fill=WHT, outline=BLK)
        for dx in (-45, 0, 45):
            d.ellipse((cx + dx - 14, cy - 14, cx + dx + 14, cy + 14), fill=BLK)
        ctext(d, 540, "COMMENT", fC, WHT, 10)
        ctext(d, 690, cta["keyword"].upper(), fH, YEL, 14)
        for k, line in enumerate(cta.get("card_sub", ["FREE CLAUDE SKILL", "IN YOUR DMS"])):
            ctext(d, 985 + 70 * k, line.upper(), fS, WHT, 7)
        if scale != 1.0:
            w, h = int(FW * scale), int(FH * scale)
            sm = im.resize((w, h), Image.LANCZOS)
            im = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
            im.paste(sm, ((FW - w) // 2, 780 - int(780 * scale)), sm)
        return im

    def draw(word, ban, cardp, path):
        im = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
        if cardp is not None:
            im = Image.alpha_composite(im, Image.new("RGBA", (FW, FH), (0, 0, 0, 120)))
            im = Image.alpha_composite(im, card(POP[cardp]))
        d = ImageDraw.Draw(im)
        if cardp is None and ban:
            banner(d)
        if word:
            bb = d.textbbox((0, 0), word, font=fw, stroke_width=9)
            x, y = (FW - (bb[2] - bb[0])) // 2, 1250
            d.text((x + 5, y + 8), word, font=fw, fill=(0, 0, 0, 150), stroke_width=9, stroke_fill=(0, 0, 0, 150))
            d.text((x, y), word, font=fw, fill=YEL, stroke_width=9, stroke_fill=BLK)
        im.save(path)

    ev = []
    for i, w in enumerate(words):
        nxt = words[i + 1]["t0"] if i + 1 < len(words) else None
        t1 = nxt if nxt is not None and nxt - w["t1"] < 0.35 else w["t1"] + 0.15
        ev.append((w["t0"], t1, w["w"].upper()))
    ban0 = ban1 = card0 = card1 = -1
    if cta:
        ban0 = starts[min(cta.get("banner_from_block", 2), len(starts))]
        ban1 = END - 1.6
        hit = [e for e in tl if e["line"] == cta.get("card_line")]
        if hit:
            card0, card1 = hit[0]["start"] - 0.15, hit[0]["start"] + hit[0]["dur"] + 0.6
    pops = [card0 + k / FPS for k in range(len(POP))] if card0 >= 0 else []
    cuts = sorted({0, END, ban0, ban1, card1, *pops, *[e[0] for e in ev], *[e[1] for e in ev]})
    cuts = [c for c in cuts if 0 <= c <= END]
    states, cache = [], {}
    for a, b in zip(cuts, cuts[1:]):
        if b - a < 0.005:
            continue
        m = (a + b) / 2
        word = next((e[2] for e in ev if e[0] <= m < e[1]), "")
        ban = ban0 <= m < ban1
        cardp = min(len(POP) - 1, int((m - card0) * FPS)) if card0 <= m < card1 else None
        key = (word, ban, cardp)
        if key not in cache:
            path = os.path.join(p, "cap", f"{len(cache):04d}.png")
            draw(word, ban, cardp, path)
            cache[key] = path
        states.append((cache[key], b - a))
    lst = os.path.join(p, "cap", "list.txt")
    with open(lst, "w") as f:
        for path, d in states:
            f.write(f"file '{os.path.basename(path)}'\nduration {d:.4f}\n")
        f.write(f"file '{os.path.basename(states[-1][0])}'\n")
    out = os.path.join(p, "captions.mov")
    run("ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
        "-vf", f"fps={FPS},format=argb", "-c:v", "qtrle", out)
    return out


# ---------------------------------------------------------------- build
def build(p):
    plan = load_plan(p)
    n = len(plan["blocks"])
    for b in range(1, n + 1):
        if not os.path.exists(os.path.join(p, "clips", f"b{b:02d}.mp4")):
            sys.exit(f"missing clips/b{b:02d}.mp4 ({n} blocks in plan.json)")
    if not os.path.isdir(os.path.join(p, "vo")):
        prep(p)
    tl, words = timeline(p, plan)
    starts = {}
    for e in tl:
        starts.setdefault(e["block"], e["start"])
    last = tl[-1]
    END = last["start"] + last["dur"] + plan["tail"]
    bounds = [starts[b] for b in range(1, n + 1)] + [END]
    starts_list = [0] + bounds  # 1-based lookup for banner_from_block
    seg = os.path.join(p, "seg")
    os.makedirs(seg, exist_ok=True)
    vf = f"fps={FPS},scale={FW}:{FH}:force_original_aspect_ratio=increase,crop={FW}:{FH},setsar=1"
    for b in range(1, n + 1):
        slot = bounds[b] - bounds[b - 1]
        src = os.path.join(p, "clips", f"b{b:02d}.mp4")
        d = dur(src)
        out = os.path.join(seg, f"{b:02d}.mp4")
        if b == n and plan.get("loop", True):
            # the loop clip ends on the opening frame, so keep its END
            run("ffmpeg", "-loglevel", "error", "-y", "-ss", f"{max(0, d - slot):.3f}", "-i", src, "-t", f"{slot:.3f}",
                "-vf", vf, "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", out)
        else:
            pad = max(0, slot - d) + 0.1
            run("ffmpeg", "-loglevel", "error", "-y", "-i", src, "-vf", vf + f",tpad=stop_mode=clone:stop_duration={pad:.3f}",
                "-t", f"{slot:.3f}", "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", out)
    with open(os.path.join(seg, "list.txt"), "w") as f:
        for b in range(1, n + 1):
            f.write(f"file '{b:02d}.mp4'\n")
    raw = os.path.join(p, "video_raw.mp4")
    run("ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(seg, "list.txt"), "-c", "copy", raw)
    cap = captions(p, plan, tl, words, starts_list, END)

    # audio: voice, a tinny "In this town" under the last second so the loop lands, optional ducked music
    vo = os.path.join(p, "vo_master.wav")
    first = os.path.join(p, "vo", f"{plan['blocks'][0][0]}.wav")
    tiny = os.path.join(p, "tiny.wav")
    run("ffmpeg", "-loglevel", "error", "-y", "-i", first, "-t", "1.25", "-af",
        "highpass=f=700,lowpass=f=3200,volume=0.8,afade=t=out:st=1.05:d=0.2", "-ar", "48000", "-ac", "2", tiny)
    ms = int((END - 1.25) * 1000) if plan.get("loop", True) else None
    music = next((os.path.join(p, m) for m in ("music.mp3", "music.wav", "music.m4a") if os.path.exists(os.path.join(p, m))), None)
    ins = ["-i", vo, "-i", tiny]
    chain = f"[0]atrim=0:{END:.3f}[v0];"
    chain += f"[1]adelay={ms}|{ms}[t];[v0][t]amix=inputs=2:normalize=0[v];" if ms is not None else "[v0]anull[v];"
    if music:
        ins += ["-stream_loop", "-1", "-i", music]
        vol = plan.get("music_volume", 0.22)
        chain += (f"[2]aresample=48000,volume={vol},atrim=0:{END:.3f},afade=t=out:st={END - 1.5:.3f}:d=1.5[m];"
                  "[v]asplit[vv][sc];[m][sc]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=300[md];"
                  "[vv][md]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5[a]")
    else:
        chain += "[v]loudnorm=I=-14:TP=-1.5[a]"
    audio = os.path.join(p, "audio.wav")
    run("ffmpeg", "-loglevel", "error", "-y", *ins, "-filter_complex", chain, "-map", "[a]", "-ar", "48000", audio)

    os.makedirs(os.path.join(p, "out"), exist_ok=True)
    final = os.path.join(p, "out", plan.get("name", "in-this-town") + ".mp4")
    run("ffmpeg", "-loglevel", "error", "-y", "-i", raw, "-i", cap, "-i", audio, "-filter_complex",
        "[0:v][1:v]overlay=0:0:eof_action=pass[v]", "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", final)
    phone = final[:-4] + "-phone.mp4"
    run("ffmpeg", "-loglevel", "error", "-y", "-i", final, "-c:v", "libx264", "-preset", "medium", "-crf", "26",
        "-maxrate", "2.2M", "-bufsize", "4M", "-c:a", "aac", "-b:a", "128k", phone)
    print(f"done  {final}  ({dur(final):.1f}s{', with music' if music else ', no music'})")
    print(f"      {phone}  (smaller copy for your phone)")


# ---------------------------------------------------------------- helpers
def frame(video, sec, out):
    if float(sec) < 0:
        run("ffmpeg", "-loglevel", "error", "-y", "-sseof", "-0.1", "-i", video, "-frames:v", "1", "-update", "1", out)
    else:
        run("ffmpeg", "-loglevel", "error", "-y", "-ss", sec, "-i", video, "-frames:v", "1", out)
    print(out)


def sheet(p):
    from PIL import Image
    clips = sorted(f for f in os.listdir(os.path.join(p, "clips")) if f.endswith(".mp4"))
    os.makedirs(os.path.join(p, "cap"), exist_ok=True)
    rows = []
    for c in clips:
        src = os.path.join(p, "clips", c)
        d = dur(src)
        ims = []
        for k, t in enumerate((0.2, d / 2, max(0, d - 0.3))):
            f = os.path.join(p, "cap", f"sheet_{c}_{k}.png")
            run("ffmpeg", "-loglevel", "error", "-y", "-ss", f"{t:.2f}", "-i", src, "-frames:v", "1", "-vf", "scale=240:-1", f)
            ims.append(Image.open(f))
        rows.append(ims)
    w, h = rows[0][0].size
    out = Image.new("RGB", (w * 3, h * len(rows)), "white")
    for r, ims in enumerate(rows):
        for k, im in enumerate(ims):
            out.paste(im, (k * w, r * h))
    path = os.path.join(p, "contact-sheet.jpg")
    out.save(path, quality=80)
    print(path)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
    elif a[0] == "setup":
        setup()
    elif a[0] == "prep":
        prep(a[1])
    elif a[0] == "build":
        build(a[1])
    elif a[0] == "frame":
        frame(a[1], a[2], a[3])
    elif a[0] == "sheet":
        sheet(a[1])
    else:
        sys.exit(__doc__)
