#!/usr/bin/env python3
"""reverse-video: take any video apart, frame by frame, into a style another edit can follow.

  python3 reverse.py setup
      First run: checks the tools, builds the on-device text reader, and checks the context.dev connector.
  python3 reverse.py fetch <video_url> <study-dir>
      Download the file a context.dev parser returned (instagram-post / tiktok-video video_url).
  python3 reverse.py analyze <video> [-o study] [--no-words]
      Every frame: cuts, shot lengths, motion. Every 1/3 s: on-screen text and faces (on-device).
      Audio: tempo, beats, cuts on the beat, loudness, the words. Writes style.json, STYLE.md,
      shots.jpg (one frame per shot) and timeline.png. Open STYLE.md, shots.jpg and timeline.png.
"""
import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
VISION = os.path.join(HERE, "bin", "vision")
SIGNUP = "https://link.context.dev/keeran-jagadesan"
CODE = "KEERAN25OFF"
MCP_URL = "https://mcp.context.dev/mcp"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def die(msg):
    print(f"reverse: {msg}", file=sys.stderr)
    sys.exit(1)


def setup():
    """First-run checks. Prints what's missing and how to fix it; never installs anything by itself."""
    import importlib.util
    ok = True
    print("reverse-video setup\n")
    print("1. Tools")
    if sys.platform != "darwin":
        print("   ! macOS needed: the text and face reader uses Apple Vision.")
        ok = False
    for tool, fix in (("ffmpeg", "brew install ffmpeg"), ("swiftc", "xcode-select --install")):
        found = shutil.which(tool)
        print(f"   {'ok' if found else '!!'} {tool}" + ("" if found else f"   ->  {fix}"))
        ok &= bool(found)
    missing = [m for m, p in (("cv2", "opencv-python"), ("numpy", "numpy"), ("PIL", "pillow"),
                              ("librosa", "librosa"), ("faster_whisper", "faster-whisper"))
               if importlib.util.find_spec(m) is None]
    pips = {"cv2": "opencv-python", "PIL": "pillow", "faster_whisper": "faster-whisper"}
    if missing:
        print("   !! python packages   ->  pip3 install " + " ".join(pips.get(m, m) for m in missing))
        ok = False
    else:
        print("   ok python packages")
    if shutil.which("swiftc") and sys.platform == "darwin":
        try:
            ensure_vision()
            print("   ok on-device text reader (bin/vision)")
        except Exception as e:
            print(f"   !! couldn't build bin/vision: {e}")
            ok = False

    print("\n2. context.dev (gets the video from a link)")
    connected = None
    if shutil.which("claude"):
        r = subprocess.run(["claude", "mcp", "list"], capture_output=True, text=True, timeout=60)
        connected = "context.dev" in (r.stdout + r.stderr)
    if connected:
        print("   ok connector found in `claude mcp list`. If a call asks you to sign in, open /mcp and sign in to context.")
    else:
        if connected is False:
            print("   !! not connected yet")
        print(f"""
   a) Make a free account: {SIGNUP}
      (1,000 free credits a month. One video link is 1 credit.)
   b) Upgrading? Code {CODE} takes 25% off your first 6 months.
   c) Connect it to Claude Code:
        claude mcp add --transport http context {MCP_URL}
      then type /mcp in Claude Code and sign in to "context".
      In the Claude app instead: Settings > Connectors > Add custom connector, URL {MCP_URL}
   (That's Keeran's referral link: he may earn a commission when you sign up or upgrade through it.)""")
        ok = False
    print("\n" + ("All set. Paste a video link." if ok else "Fix the !! lines above, then run setup again."))


def fetch(url, out):
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "video.mp4")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
        shutil.copyfileobj(r, f)
    print(path, os.path.getsize(path), "bytes")


def ensure_vision():
    if os.path.exists(VISION):
        return True
    if sys.platform != "darwin" or not shutil.which("swiftc"):
        return False
    os.makedirs(os.path.dirname(VISION), exist_ok=True)
    subprocess.run(["swiftc", "-O", os.path.join(HERE, "vision.swift"), "-o", VISION], check=True)
    return True


def hexc(rgb):
    return "#%02x%02x%02x" % tuple(int(round(v)) for v in rgb)


# ------------------------------------------------------------------ every frame

def frame_pass(video):
    import cv2
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    rows, prev_g, prev_h, i = [], None, None, 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        small = cv2.resize(f, (72, 128), interpolation=cv2.INTER_AREA)
        g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32)
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        h = cv2.calcHist([hsv], [0, 1, 2], None, [16, 4, 4], [0, 180, 0, 256, 0, 256])
        cv2.normalize(h, h)
        d = float(np.abs(g - prev_g).mean() / 255) if prev_g is not None else 0.0
        hb = float(cv2.compareHist(prev_h, h, cv2.HISTCMP_BHATTACHARYYA)) if prev_h is not None else 0.0
        mid = cv2.cvtColor(cv2.resize(f, (180, 320), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        sharp = float(cv2.Laplacian(mid, cv2.CV_32F).var())
        rows.append({"frame": i, "t": round(i / fps, 3), "diff": round(d, 4), "hist": round(hb, 4),
                     "bright": round(float(g.mean() / 255), 3), "sat": round(float(hsv[..., 1].mean() / 255), 3),
                     "sharp": round(sharp, 1)})
        prev_g, prev_h, i = g, h, i + 1
    cap.release()
    return fps, W, H, rows


def find_cuts(rows):
    d = np.array([r["diff"] for r in rows])
    h = np.array([r["hist"] for r in rows])
    score = np.maximum(h, d * 2.2)
    med = float(np.median(score[1:])) if len(score) > 1 else 0
    mad = float(np.median(np.abs(score[1:] - med))) if len(score) > 1 else 0
    thr = max(0.28, med + 8 * mad)
    cuts = []
    for i in range(1, len(score)):
        if score[i] >= thr and (score[i] >= score[max(0, i - 1)]) and (i + 1 >= len(score) or score[i] >= score[i + 1]):
            if not cuts or i - cuts[-1] >= 3:
                cuts.append(i)
    for i in cuts:
        rows[i]["cut"] = 1
    return cuts, round(thr, 3)


def shot_motion(video, a, b):
    """Zoom and pan across one shot, from matched features between its first and last frames."""
    import cv2
    if b - a < 6:
        return None
    cap = cv2.VideoCapture(video)
    frames = []
    for k in (a + 1, b - 2):
        cap.set(cv2.CAP_PROP_POS_FRAMES, k)
        ok, f = cap.read()
        if not ok:
            return None
        frames.append(cv2.cvtColor(cv2.resize(f, None, fx=0.5, fy=0.5), cv2.COLOR_BGR2GRAY))
    cap.release()
    orb = cv2.ORB_create(800)
    k1, d1 = orb.detectAndCompute(frames[0], None)
    k2, d2 = orb.detectAndCompute(frames[1], None)
    if d1 is None or d2 is None or len(k1) < 12 or len(k2) < 12:
        return None
    m = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(d1, d2)
    if len(m) < 12:
        return None
    p1 = np.float32([k1[x.queryIdx].pt for x in m])
    p2 = np.float32([k2[x.trainIdx].pt for x in m])
    M, inl = cv2.estimateAffinePartial2D(p1, p2, ransacReprojThreshold=3)
    if M is None or inl is None or inl.sum() < 10:
        return None
    s = float(np.sqrt(M[0, 0] ** 2 + M[1, 0] ** 2))
    return {"scale": round(s, 4), "dx": round(float(M[0, 2]) * 2, 1), "dy": round(float(M[1, 2]) * 2, 1),
            "inliers": int(inl.sum())}


def grab(video, frames, width=540):
    import cv2
    cap = cv2.VideoCapture(video)
    out = {}
    for k in sorted(set(frames)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, k)
        ok, f = cap.read()
        if ok:
            out[k] = cv2.resize(f, (width, int(f.shape[0] * width / f.shape[1])), interpolation=cv2.INTER_AREA)
    cap.release()
    return out


# ------------------------------------------------------------------ framing, grade, transitions

ASPECTS = [(9 / 16, "9:16"), (4 / 5, "4:5"), (1.0, "1:1"), (4 / 3, "4:3"), (16 / 9, "16:9"), (1.9, "1.9:1"),
           (2.0, "2:1"), (2.39, "2.39:1")]


def framing(imgs, size=None):
    """Black bars: a 16:9 band in a 9:16 frame, 2.39:1 letterbox, 4:3, pillarbox. Median over the samples."""
    import cv2
    tops, bots, lefts, rights = [], [], [], []
    for im in imgs:
        g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
        H, W = g.shape
        def run(mask):
            n = 0
            for v in mask:
                if not v:
                    break
                n += 1
            return n
        # a bar row is mostly black; a caption sitting in the bar only lights a few pixels of it
        dark_r = np.percentile(g, 60, axis=1) < 24
        t_, b_ = run(dark_r), run(dark_r[::-1])
        inner = g[t_:H - b_] if H - b_ - t_ > 8 else g
        dark_c = np.percentile(inner, 60, axis=0) < 24
        tops.append(t_ / H); bots.append(b_ / H)
        lefts.append(run(dark_c) / W); rights.append(run(dark_c[::-1]) / W)
    t, b, l, r = (float(np.median(x)) for x in (tops, bots, lefts, rights))
    H, W = imgs[0].shape[:2]
    if size:
        W, H = size
    if max(t, b, l, r) < 0.02 or t + b > 0.95 or l + r > 0.95:
        return {"kind": "full frame", "content_aspect": round(W / H, 3), "label": "full frame",
                "bars_pct": [0, 0, 0, 0], "box": [0, 0, 1, 1]}
    cw, ch = W * (1 - l - r), H * (1 - t - b)
    asp = cw / max(ch, 1)
    name = min(ASPECTS, key=lambda a: abs(a[0] - asp))[1]
    kind = "letterbox band" if t + b > 0.04 and l + r < 0.04 else ("pillarbox" if l + r > 0.04 and t + b < 0.04 else "boxed")
    return {"kind": kind, "content_aspect": round(asp, 3), "label": f"{name} {kind} in a {W}x{H} frame",
            "bars_pct": [round(t * 100, 1), round(b * 100, 1), round(l * 100, 1), round(r * 100, 1)],
            "content_center_y_pct": round((t + (1 - t - b) / 2) * 100, 1), "box": [l, t, 1 - r, 1 - b]}


def grade(imgs, box):
    """Measured look inside the picture area: black/white points, contrast, saturation, warmth, split toning."""
    import cv2
    L_all, a_all, b_all, s_all = [], [], [], []
    for im in imgs:
        H, W = im.shape[:2]
        x0, y0, x1, y1 = int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H)
        crop = im[y0:y1, x0:x1]
        if crop.size == 0:
            continue
        small = cv2.resize(crop, (90, int(90 * crop.shape[0] / max(crop.shape[1], 1)) or 1))
        lab = cv2.cvtColor(small, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV).reshape(-1, 3).astype(np.float32)
        L_all.append(lab[:, 0] * 100 / 255); a_all.append(lab[:, 1] - 128); b_all.append(lab[:, 2] - 128)
        s_all.append(hsv[:, 1] / 255)
    if not L_all:
        return {}
    L, A, B, S = (np.concatenate(x) for x in (L_all, a_all, b_all, s_all))
    sh, hi = L <= np.percentile(L, 20), L >= np.percentile(L, 80)
    m = lambda arr, mask: round(float(arr[mask].mean()), 1) if mask.any() else 0.0
    g = {"black_point": round(float(np.percentile(L, 2)), 1), "white_point": round(float(np.percentile(L, 98)), 1),
         "contrast": round(float(np.percentile(L, 95) - np.percentile(L, 5)), 1),
         "saturation": round(float(S.mean()), 3), "warmth_b": round(float(B.mean()), 1), "tint_a": round(float(A.mean()), 1),
         "shadows_ab": [m(A, sh), m(B, sh)], "highlights_ab": [m(A, hi), m(B, hi)]}

    def tone(ab):
        """Name a Lab a*/b* pair by its hue angle: +a magenta, +b yellow, -a green, -b blue."""
        import math
        a, b = ab
        if math.hypot(a, b) < 3:
            return "neutral"
        h = math.degrees(math.atan2(b, a)) % 360
        for lim, name in ((30, "magenta/red"), (70, "orange"), (105, "yellow/warm"), (150, "yellow-green"),
                          (195, "green"), (250, "teal/cyan"), (290, "blue"), (330, "purple"), (360, "magenta/red")):
            if h < lim:
                return name
    words = []
    if g["saturation"] < 0.08:
        words.append("black & white")
    words.append("lifted blacks (faded)" if g["black_point"] > 12 else "crushed blacks" if g["black_point"] < 3 else "normal blacks")
    words.append("low contrast" if g["contrast"] < 45 else "high contrast" if g["contrast"] > 75 else "medium contrast")
    words.append("muted colour" if g["saturation"] < 0.25 else "rich colour" if g["saturation"] > 0.45 else "natural saturation")
    words.append(f"{tone(g['shadows_ab'])} shadows, {tone(g['highlights_ab'])} highlights")
    g["read"] = ", ".join(words)
    return g


def transitions(rows, cuts, fps):
    """What each cut is: hard cut, flash, dip to black, or a whip (motion blur around the cut)."""
    sharp = np.array([r["sharp"] for r in rows])
    bright = np.array([r["bright"] for r in rows])
    out = []
    for c in cuts:
        a, b = max(0, c - 4), min(len(rows), c + 4)
        before = bright[max(0, c - 12):max(1, c - 4)].mean() if c > 4 else bright[c]
        after = bright[min(len(rows) - 1, c + 4):min(len(rows), c + 12)].mean() if c + 4 < len(rows) else bright[c]
        local = bright[a:b]
        base = np.median(sharp[max(0, c - 30):min(len(rows), c + 30)]) or 1
        kind = "hard cut"
        if local.max() > max(before, after) + 0.25 and local.max() > 0.7:
            kind = "flash"
        elif local.min() < 0.05 and min(before, after) > 0.1:
            kind = "dip to black"
        elif sharp[a:b].min() < 0.3 * base:
            kind = "whip / blur"
        out.append({"t": round(c / fps, 3), "kind": kind})
    return out


# ------------------------------------------------------------------ text, faces, color

def stroke_weight(img, box):
    """Median stroke width over text height: ~0.08 regular, ~0.12 bold, 0.16+ black/heavy."""
    import cv2
    H, W = img.shape[:2]
    x, y, w, h = [int(v) for v in (box[0] * W, box[1] * H, box[2] * W, box[3] * H)]
    if w < 8 or h < 8:
        return None
    crop = cv2.cvtColor(img[max(0, y):y + h, max(0, x):x + w], cv2.COLOR_BGR2GRAY)
    _, bw = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if (bw > 0).mean() > 0.5:
        bw = 255 - bw
    dist = cv2.distanceTransform(bw, cv2.DIST_L2, 3)
    vals = dist[dist > 0]
    if len(vals) < 20:
        return None
    return round(float(np.percentile(vals, 90) * 2 / h), 3)


def text_colors(img, box):
    import cv2
    H, W = img.shape[:2]
    x, y, w, h = [int(v) for v in (box[0] * W, box[1] * H, box[2] * W, box[3] * H)]
    crop = img[max(0, y):y + h, max(0, x):x + w].reshape(-1, 3).astype(np.float32)
    if len(crop) < 30:
        return None, None
    _, lab, cen = cv2.kmeans(crop, 2, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1), 3,
                             cv2.KMEANS_PP_CENTERS)
    n = np.bincount(lab.ravel(), minlength=2)
    fg, bg = (0, 1) if n[0] < n[1] else (1, 0)
    return hexc(cen[fg][::-1]), hexc(cen[bg][::-1])


def palette(imgs, k=8):
    import cv2
    px = np.concatenate([cv2.resize(i, (60, 107)).reshape(-1, 3) for i in imgs]).astype(np.float32)
    _, lab, cen = cv2.kmeans(px, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1), 3,
                             cv2.KMEANS_PP_CENTERS)
    share = np.bincount(lab.ravel(), minlength=k) / len(lab)
    out = []
    for c, s in sorted(zip(cen, share), key=lambda z: -z[1]):
        rgb = c[::-1]
        mx, mn = max(rgb), min(rgb)
        sat = 0 if mx < 90 else (mx - mn) / mx   # near-black colors aren't an accent
        out.append({"hex": hexc(rgb), "share": round(float(s), 3), "sat": round(float(sat), 2)})
    accent = max(out, key=lambda c: c["sat"] * (c["share"] ** 0.3) if c["sat"] > 0.35 else -1)
    return out, (accent["hex"] if accent["sat"] > 0.35 else None)


# ------------------------------------------------------------------ audio

def audio(video, cuts_t, words=True):
    tmp = tempfile.mkdtemp(prefix="reverse-")
    wav = os.path.join(tmp, "a.wav")
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "22050", wav])
    if r.returncode or not os.path.exists(wav):
        return {"has_audio": False}
    import librosa
    y, sr = librosa.load(wav, sr=22050)
    out = {"has_audio": True}
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    bt = librosa.frames_to_time(beats, sr=sr)
    out["tempo_bpm"] = round(float(np.atleast_1d(tempo)[0]), 1)
    out["beats"] = [round(float(b), 3) for b in bt]
    onsets = librosa.frames_to_time(librosa.onset.onset_detect(y=y, sr=sr), sr=sr)
    near = lambda t, arr, tol: len(arr) and float(np.min(np.abs(np.asarray(arr) - t))) <= tol
    if cuts_t:
        out["cuts_on_beat"] = round(sum(bool(near(t, bt, 0.08)) for t in cuts_t) / len(cuts_t), 2)
        out["cuts_on_onset"] = round(sum(bool(near(t, onsets, 0.06)) for t in cuts_t) / len(cuts_t), 2)
    rms_ = librosa.feature.rms(y=y)[0]
    rt = librosa.times_like(rms_, sr=sr)
    if len(rms_) > 10:
        # the drop: where the energy jumps most (1 s window after vs before), ignoring the first second
        win = max(1, int(1.0 / (rt[1] - rt[0])))
        best, bt_ = 0, None
        for i in range(win, len(rms_) - win):
            if rt[i] < 1.0:
                continue
            jump = rms_[i:i + win].mean() - rms_[i - win:i].mean()
            if jump > best:
                best, bt_ = jump, rt[i]
        if bt_ is not None and best > 0.08 * (rms_.max() or 1):
            out["drop"] = round(float(bt_), 2)
            if cuts_t:
                pre = [c for c in cuts_t if c < bt_]
                post = [c for c in cuts_t if c >= bt_]
                total = len(y) / sr
                out["cuts_per_s_before_drop"] = round(len(pre) / max(bt_, 0.1), 2)
                out["cuts_per_s_after_drop"] = round(len(post) / max(total - bt_, 0.1), 2)
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=1102)[0]
    out["loudness_curve"] = [round(float(v), 4) for v in rms]
    lufs = subprocess.run(["ffmpeg", "-v", "info", "-nostats", "-i", wav, "-af", "ebur128", "-f", "null", "-"],
                          capture_output=True, text=True).stderr
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", lufs)
    if m:
        out["lufs"] = float(m[-1])
    if words:
        try:
            from faster_whisper import WhisperModel
            segs, _ = WhisperModel("small", device="cpu", compute_type="int8").transcribe(
                wav, word_timestamps=True, vad_filter=True)
            ws = [{"w": w.word.strip(), "start": round(w.start, 2), "end": round(w.end, 2)}
                  for s in segs for w in (s.words or [])]
            out["words"] = ws
        except ImportError:
            out["words_note"] = "pip3 install faster-whisper to get the words"
    shutil.rmtree(tmp, ignore_errors=True)
    return out


# ------------------------------------------------------------------ outputs

def contact(images, labels, path, cols=6, w=240):
    from PIL import Image, ImageDraw
    if not images:
        return
    ims = [Image.fromarray(i[..., ::-1]) for i in images]
    h = int(ims[0].size[1] * w / ims[0].size[0])
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * (h + 26)), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    for n, (im, lab) in enumerate(zip(ims, labels)):
        x, y = (n % cols) * w, (n // cols) * (h + 26)
        sheet.paste(im.resize((w - 6, h - 6)), (x + 3, y + 3))
        d.text((x + 6, y + h + 4), lab, fill=(230, 230, 230))
    sheet.save(path, quality=88)


def timeline(path, dur, rows, cuts_t, text_ev, au, thumbs):
    from PIL import Image, ImageDraw
    W, lane = 1800, 40
    H = 120 + lane * 4 + 40
    im = Image.new("RGB", (W, H), (16, 16, 16))
    d = ImageDraw.Draw(im)
    X = lambda t: int(t / dur * (W - 20)) + 10
    for t, th in thumbs:
        tim = Image.fromarray(th[..., ::-1]).resize((60, 107))
        im.paste(tim, (min(W - 70, X(t)), 6))
    y0 = 120
    names = ["cuts", "text on screen", "beats", "loudness"]
    for k, n in enumerate(names):
        d.text((12, y0 + k * lane + 2), n, fill=(140, 140, 140))
    for t in cuts_t:
        d.line([X(t), y0, X(t), y0 + lane - 4], fill=(255, 90, 70), width=3)
    for e in text_ev:
        d.rectangle([X(e["start"]), y0 + lane + 10, max(X(e["start"]) + 2, X(e["end"])), y0 + 2 * lane - 6],
                    fill=(90, 160, 255))
    for b in au.get("beats", []):
        d.line([X(b), y0 + 2 * lane + 8, X(b), y0 + 3 * lane - 6], fill=(240, 200, 80), width=1)
    lc = au.get("loudness_curve", [])
    if lc:
        mx = max(lc) or 1
        pts = [(X(i * dur / len(lc)), y0 + 4 * lane - 4 - int(v / mx * (lane - 8))) for i, v in enumerate(lc)]
        d.line(pts, fill=(120, 220, 140), width=2)
    for s in range(0, int(dur) + 1):
        d.text((X(s), H - 22), f"{s}s", fill=(110, 110, 110))
    im.save(path)


def analyze(video, out, words=True):
    os.makedirs(out, exist_ok=True)
    fps, W, H, rows = frame_pass(video)
    n = len(rows)
    dur = n / fps
    cuts, thr = find_cuts(rows)
    with open(os.path.join(out, "frames.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["frame", "t", "diff", "hist", "bright", "sat", "sharp", "cut"])
        w.writeheader()
        for r in rows:
            w.writerow({**{"cut": 0}, **r})
    edges = [0] + cuts + [n]
    shots = []
    for a, b in zip(edges[:-1], edges[1:]):
        if b - a < 1:
            continue
        mo = shot_motion(video, a, b)
        sd = (b - a) / fps
        kind = "static"
        if mo:
            zr = (mo["scale"] - 1) / max(sd, 0.1)
            pr = (abs(mo["dx"]) + abs(mo["dy"])) / W / max(sd, 0.1)
            if zr > 0.025:
                kind = "push-in"
            elif zr < -0.025:
                kind = "pull-out"
            elif pr > 0.06:
                kind = "pan"
        else:
            kind = "animated / no match"
        energy = float(np.mean([rows[k]["diff"] for k in range(a + 1, b)])) if b - a > 1 else 0.0
        shots.append({"i": len(shots), "start": round(a / fps, 3), "end": round(b / fps, 3), "dur": round(sd, 3),
                      "frames": b - a, "move": kind, "motion": mo, "energy": round(energy * 100, 2)})
    lens = np.array([s["dur"] for s in shots])
    trans = transitions(rows, cuts, fps)
    for s, tr in zip(shots[1:], trans):
        s["in"] = tr["kind"]

    # one frame per shot, and every 1/3 s for text, faces and color
    key = {s["i"]: int((s["start"] + s["dur"] / 2) * fps) for s in shots}
    samp = list(range(0, n, max(1, int(round(fps / 3)))))
    imgs = grab(video, list(key.values()) + samp)
    os.makedirs(os.path.join(out, "shots"), exist_ok=True)
    import cv2
    for s in shots:
        cv2.imwrite(os.path.join(out, "shots", f"{s['i']:03d}.jpg"), imgs[key[s["i"]]])
        s["frame"] = f"shots/{s['i']:03d}.jpg"
    contact([imgs[key[s["i"]]] for s in shots], [f"#{s['i']} {s['start']:.2f}s  {s['dur']:.2f}s" for s in shots],
            os.path.join(out, "shots.jpg"))

    vis, text_ev, faces = [], [], []
    if ensure_vision():
        tmp = tempfile.mkdtemp(prefix="reverse-v-")
        paths = []
        for k in samp:
            p = os.path.join(tmp, f"{k:05d}.jpg")
            cv2.imwrite(p, imgs[k])
            paths.append(p)
        for c in range(0, len(paths), 60):
            res = subprocess.run([VISION, *paths[c:c + 60]], capture_output=True)
            vis += json.loads(res.stdout or b"[]")
        shutil.rmtree(tmp, ignore_errors=True)
        cur = {}
        for v in vis:
            k = int(os.path.basename(v["file"])[:5])
            t = k / fps
            faces.append({"t": round(t, 2), "faces": v["faces"]})
            seen = set()
            for tx in v["texts"]:
                if tx["c"] < 0.5 or sum(ch.isalpha() for ch in tx["s"]) < 3:
                    continue
                key_ = re.sub(r"\W+", "", tx["s"].lower())[:40]
                seen.add(key_)
                if key_ in cur:
                    cur[key_]["end"] = round(t + 1 / 3, 2)
                else:
                    fg, bg = text_colors(imgs[k], tx["b"])
                    cur[key_] = {"text": tx["s"], "start": round(t, 2), "end": round(t + 1 / 3, 2),
                                 "y": round(tx["b"][1] + tx["b"][3] / 2, 3), "x": round(tx["b"][0] + tx["b"][2] / 2, 3),
                                 "h": round(tx["b"][3], 4), "w": round(tx["b"][2], 3),
                                 "weight": stroke_weight(imgs[k], tx["b"]), "fg": fg, "bg": bg}
            for key_ in list(cur):
                if key_ not in seen:
                    text_ev.append(cur.pop(key_))
        text_ev += cur.values()
        text_ev.sort(key=lambda e: e["start"])

    pal, accent = palette([imgs[k] for k in key.values()] or list(imgs.values())[:20])
    frm = framing([imgs[k] for k in samp], (W, H))
    grd = grade([imgs[k] for k in key.values()] or [imgs[k] for k in samp], frm["box"])
    au = audio(video, [s["start"] for s in shots[1:]], words)

    # summary
    def pct(v):
        return round(float(v) * 100)
    caps = [e for e in text_ev if sum(ch.isalpha() for ch in e["text"]) >= 3]
    upper = [e for e in caps if e["text"].upper() == e["text"]]
    big = [e for e in text_ev if e["h"] * H >= 40] or text_ev
    face_share = sum(1 for f in faces if f["faces"]) / max(1, len(faces))
    # time with any text on screen (union of events), and text that builds word by word
    spans, covered = sorted((e["start"], min(e["end"], dur)) for e in text_ev), 0.0
    cs, ce = None, None
    for a_, b_ in spans:
        if cs is None or a_ > ce:
            covered += (ce - cs) if cs is not None else 0
            cs, ce = a_, b_
        else:
            ce = max(ce, b_)
    covered += (ce - cs) if cs is not None else 0
    norm = lambda s_: re.sub(r"\W+", " ", s_.lower()).strip()
    builds = sum(1 for i, e in enumerate(text_ev) if any(
        norm(f["text"]).startswith(norm(e["text"])) and len(norm(f["text"])) > len(norm(e["text"]))
        and abs(f["y"] - e["y"]) < 0.04 and 0 < f["start"] - e["start"] < 2 for f in text_ev[i + 1:i + 12]))
    face_y = [f["faces"][0][1] + f["faces"][0][3] / 2 for f in faces if f["faces"]]
    style = {
        "video": os.path.abspath(video), "size": [W, H], "fps": round(fps, 3), "duration": round(dur, 2),
        "frames_analyzed": n, "cut_threshold": thr,
        "cuts": len(cuts), "shots": len(shots),
        "cuts_per_second": round(len(cuts) / dur, 2) if dur else 0,
        "shot_len": {"median": round(float(np.median(lens)), 2), "mean": round(float(lens.mean()), 2),
                     "min": round(float(lens.min()), 2), "max": round(float(lens.max()), 2)},
        "first_cut": round(cuts[0] / fps, 2) if cuts else None,
        "opening_hold": round(shots[0]["dur"], 2) if shots else None,
        "moves": {k: sum(1 for s in shots if s["move"] == k) for k in sorted({s["move"] for s in shots})},
        "transitions": {k: sum(1 for x in trans if x["kind"] == k) for k in sorted({x["kind"] for x in trans})},
        "framing": {k: v for k, v in frm.items() if k != "box"},
        "grade": grd,
        "text": {"events": len(text_ev), "on_screen_share": pct(covered / dur) if dur else 0,
                 "builds_word_by_word": pct(builds / len(text_ev)) if text_ev else 0,
                 "uppercase_share": pct(len(upper) / len(caps)) if caps else None,
                 "median_y_pct": pct(np.median([e["y"] for e in big])) if big else None,
                 "median_cap_px": int(np.median([e["h"] * H for e in big])) if big else None,
                 "median_weight": float(np.median([e["weight"] for e in big if e["weight"]])) if [e for e in big if e["weight"]] else None,
                 "words_per_event": round(float(np.median([len(e["text"].split()) for e in text_ev])), 1) if text_ev else None,
                 "colors": sorted({(e["fg"], e["bg"]) for e in big if e["fg"]})[:8]},
        "faces": {"share_of_frames": pct(face_share), "median_y_pct": pct(np.median(face_y)) if face_y else None},
        "palette": pal, "accent": accent,
        "brightness": round(float(np.mean([r["bright"] for r in rows])), 3),
        "saturation": round(float(np.mean([r["sat"] for r in rows])), 3),
        "audio": {k: v for k, v in au.items() if k not in ("loudness_curve", "beats", "words")},
    }
    if au.get("words"):
        ws = au["words"]
        style["audio"]["words_per_second"] = round(len(ws) / dur, 2)
        style["audio"]["first_word"] = ws[0]["start"]
        style["hook"] = " ".join(w["w"] for w in ws if w["start"] < 3.0)
    json.dump(style, open(os.path.join(out, "style.json"), "w"), indent=1)
    json.dump({"shots": shots, "text": text_ev, "faces": faces, "beats": au.get("beats", []),
               "words": au.get("words", [])}, open(os.path.join(out, "detail.json"), "w"), indent=1)
    timeline(os.path.join(out, "timeline.png"), dur, rows, [s["start"] for s in shots[1:]], text_ev, au,
             [(s["start"], imgs[key[s["i"]]]) for s in shots])
    write_md(out, style, shots, text_ev)
    print(open(os.path.join(out, "STYLE.md")).read())


def write_md(out, s, shots, text_ev):
    t, a = s["text"], s["audio"]
    L = [f"# Style: {os.path.basename(s['video'])}", "",
         f"Measured from all {s['frames_analyzed']} frames ({s['duration']} s, {s['size'][0]}x{s['size'][1]}, {s['fps']} fps).",
         "Numbers are measured. The read at the bottom is Claude's, from shots.jpg and timeline.png.", "",
         "## Rhythm", "", "| | |", "|---|---|",
         f"| Cuts | {s['cuts']} ({s['cuts_per_second']} per second) |",
         f"| Shot length | median {s['shot_len']['median']} s, mean {s['shot_len']['mean']} s, {s['shot_len']['min']}-{s['shot_len']['max']} s |",
         f"| Opening hold | {s['opening_hold']} s before the first cut |",
         f"| Camera moves | {', '.join(f'{k}: {v}' for k, v in s['moves'].items())} |",
         f"| Transitions | {', '.join(f'{k}: {v}' for k, v in s['transitions'].items()) or 'none (one shot)'} |"]
    if a.get("has_audio"):
        if a.get("drop") is not None:
            L += [f"| The drop | {a['drop']} s; cuts per second {a.get('cuts_per_s_before_drop')} before, "
                  f"{a.get('cuts_per_s_after_drop')} after |"]
        L += [f"| Tempo | {a.get('tempo_bpm')} BPM |",
              f"| Cuts on the beat | {round((a.get('cuts_on_beat') or 0) * 100)}% within 80 ms; {round((a.get('cuts_on_onset') or 0) * 100)}% on an audio hit |",
              f"| Loudness | {a.get('lufs')} LUFS integrated |"]
        if a.get("words_per_second"):
            L += [f"| Talking | {a['words_per_second']} words/s, first word at {a['first_word']} s |"]
    L += ["", "## Text on screen", "", "| | |", "|---|---|",
          f"| Events | {t['events']}, text on screen {t['on_screen_share']}% of the time, ~{t['words_per_event']} words each |",
          f"| Builds | {t['builds_word_by_word']}% of text appears word by word |",
          f"| Case | {t['uppercase_share']}% ALL CAPS |",
          f"| Size | median cap height {t['median_cap_px']} px at {s['size'][1]} px tall |",
          f"| Position | median {t['median_y_pct']}% down the frame |",
          f"| Weight | stroke/height {t['median_weight']} (0.08 regular, 0.12 bold, 0.16+ black) |",
          f"| Colors (text on background) | {', '.join(f'{fg} on {bg}' for fg, bg in t['colors'])} |",
          "", "## Look", "", "| | |", "|---|---|",
          f"| Framing | {s['framing']['label']} (bars top/bottom/left/right % {s['framing']['bars_pct']}) |",
          f"| Grade | {s['grade'].get('read', '')} |",
          f"| Grade numbers | black point {s['grade'].get('black_point')}, white point {s['grade'].get('white_point')}, "
          f"contrast {s['grade'].get('contrast')} (L*, 0-100); saturation {s['grade'].get('saturation')}; "
          f"warmth b* {s['grade'].get('warmth_b')}; shadows a*/b* {s['grade'].get('shadows_ab')}, "
          f"highlights a*/b* {s['grade'].get('highlights_ab')} |",
          f"| Accent | {s['accent']} |",
          f"| Palette | {', '.join(c['hex'] + ' ' + str(round(c['share'] * 100)) + '%' for c in s['palette'])} |",
          f"| Brightness / saturation | {s['brightness']} / {s['saturation']} |",
          f"| Faces | in {s['faces']['share_of_frames']}% of frames, median {s['faces']['median_y_pct']}% down |"]
    if s.get("hook"):
        L += ["", f"**First 3 seconds said:** {s['hook']}"]
    L += ["", "## Shots", "", "| # | start | length | in | move | energy | frame |", "|---|---|---|---|---|---|---|"]
    for sh in shots:
        L.append(f"| {sh['i']} | {sh['start']} | {sh['dur']} | {sh.get('in', 'opening')} | {sh['move']} | "
                 f"{sh['energy']} | {sh['frame']} |")
    L += ["", "## Text track", "", "| start | end | y | text |", "|---|---|---|---|"]
    for e in text_ev[:80]:
        L.append(f"| {e['start']} | {e['end']} | {round(e['y'] * 100)}% | {e['text'][:60]} |")
    L += ["", "## The read (Claude fills this in)", "", "- Format:", "- Hook:", "- What makes it feel like itself:",
          "- To copy it on a new clip:", "- Don't copy: the creator's face, voice, words, logo or footage."]
    open(os.path.join(out, "STYLE.md"), "w").write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup")
    p = sub.add_parser("fetch"); p.add_argument("url"); p.add_argument("out")
    p = sub.add_parser("analyze"); p.add_argument("video"); p.add_argument("-o", default="study")
    p.add_argument("--no-words", action="store_true")
    a = ap.parse_args()
    if a.cmd == "setup":
        setup()
    elif a.cmd == "fetch":
        fetch(a.url, a.out)
    else:
        if not os.path.exists(a.video):
            die(f"{a.video} not found")
        analyze(a.video, a.o, not a.no_words)


if __name__ == "__main__":
    main()
