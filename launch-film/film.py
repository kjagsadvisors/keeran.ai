#!/usr/bin/env python3
"""launch-film: a launch film for any product, set in the Claude app, voiced by you.

    python3 film.py setup                     # one time: installs the Remotion engine (npm) and checks ffmpeg / numpy
    python3 film.py new films/my-product      # starts a project with a film.json to fill in
    python3 film.py words films/my-product    # word timings for your recorded lines (faster-whisper)
    python3 film.py hits assets/music.m4a     # strong hits in a track, to pick music.firstHit
    python3 film.py plan films/my-product     # builds the timeline from film.json + your lines, prints it
    python3 film.py still films/my-product --at 6.0 [--vertical]
    python3 film.py render films/my-product [--vertical | --both] [--draft]

The voice comes from the voice-studio skill: a folder with timings.json and lines/01.wav, 02.wav ...
Every scene is anchored to when you actually said each word, so nothing drifts.
"""
import argparse
import difflib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = HERE / "engine"
PUB = ENGINE / "public" / "p"
FPS = 30
SR = 48000
CPS = 28            # typing speed in the Claude composer (characters a second)
TILES = [0.5, 0.6, 0.733, 0.867]   # opener cuts: land the music's first hit on the first one
AAC_DELAY = 0.043   # Remotion's AAC encoder delay, removed when mastering

KINDS = {"screen", "type", "chips", "compare", "list", "chat", "end"}
HARD = {  # (hard cut in, hard cut out) per scene; everything else whips
    "screen": (False, False), "type": (False, True), "chips": (True, True), "compare": (True, True),
    "list": (True, True), "chat": (True, True), "end": (True, False),
}


def die(msg):
    sys.exit(f"launch-film: {msg}")


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def np_():
    try:
        import numpy as np
        return np
    except ImportError:
        die("needs numpy: python3 -m pip install --user numpy")


# ── audio helpers ──────────────────────────────────────────────────────────────────────────────
def pcm(path):
    np = np_()
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def bars(a, n=96):
    np = np_()
    if len(a) == 0:
        return [0.04] * n
    step = max(1, len(a) // n)
    v = np.array([np.abs(a[i * step:(i + 1) * step]).max() if len(a[i * step:(i + 1) * step]) else 0 for i in range(n)])
    top = v.max() or 1
    return [round(float(max(0.04, x / top)), 3) for x in v]


def levels(a):
    """Per-frame level 0..1 (RMS dB mapped from -60..-6)."""
    np = np_()
    hop = SR // FPS
    out = []
    for i in range(0, len(a), hop):
        r = np.sqrt(np.mean(a[i:i + hop] ** 2)) if len(a[i:i + hop]) else 0
        out.append(round(float(np.clip((20 * np.log10(r + 1e-9) + 60) / 54, 0, 1)), 3))
    return out


def write_wav(path, a):
    run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-c:a", "pcm_s16le", str(path)],
        input=a.astype("float32").tobytes())


def speech_onset(a):
    """Where speech starts: the first 20 ms window 15 dB over the room tone."""
    np = np_()
    win = SR // 50
    if len(a) <= win:
        return 0.0
    db = np.array([20 * np.log10(np.sqrt(np.mean(a[i:i + win] ** 2)) + 1e-9) for i in range(0, len(a) - win, win)])
    return int(np.argmax(db > np.percentile(db, 10) + 15)) * win / SR


def media_size(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True).stdout.strip()
    w, h = out.split("\n")[0].split(",")[:2]
    return int(w), int(h)


# ── words ──────────────────────────────────────────────────────────────────────────────────────
NORM = lambda x: re.sub(r"[^a-z0-9']", "", x.lower())


def align(script, words, fixes):
    """Your words with whisper's timings. Where a word matches the script, the script's spelling and punctuation are
    used; where you said something else, your word stays. Script words you didn't say are dropped."""
    sw = script.split()
    heard = [dict(w, w=fixes[NORM(w["w"])]) if NORM(w["w"]) in fixes else dict(w) for w in words]
    sm = difflib.SequenceMatcher(a=[NORM(x) for x in sw], b=[NORM(x["w"]) for x in heard], autojunk=False)
    out = []
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        for k in range(b1 - b0):
            w = heard[b0 + k]
            out.append({"w": sw[a0 + k] if op == "equal" else w["w"], "s": w["s"], "e": w["e"]})
    if out:
        out[0]["w"] = out[0]["w"][:1].upper() + out[0]["w"][1:]
        if not re.search(r"[.!?]$", out[-1]["w"]):
            out[-1]["w"] += "."
    return out


def find_phrase(words, phrase, after=0):
    """Index of the first word of `phrase` in words (at or after index `after`)."""
    p = [NORM(x) for x in phrase.split() if NORM(x)]
    ws = [NORM(w["w"]) for w in words]
    for i in range(after, len(ws) - len(p) + 1):
        if ws[i:i + len(p)] == p or (len(p) == 1 and ws[i].startswith(p[0])):
            return i
    die(f'can\'t find "{phrase}" in: {" ".join(w["w"] for w in words)}')


# ── project ────────────────────────────────────────────────────────────────────────────────────
def load(project):
    proj = Path(project).resolve()
    f = proj / "film.json"
    if not f.exists():
        die(f"no film.json in {proj} (start one with: python3 film.py new {project})")
    cfg = json.loads(f.read_text())
    return proj, cfg


def voice_dir(proj, cfg):
    v = proj / cfg.get("voice", "voice")
    if not (v / "timings.json").exists():
        die(f"no timings.json in {v}: record and clean your lines with the voice-studio skill first")
    return v


def cmd_new(a):
    proj = Path(a.project).resolve()
    if (proj / "film.json").exists():
        die(f"{proj}/film.json already exists")
    (proj / "assets").mkdir(parents=True, exist_ok=True)
    tpl = json.loads((HERE / "examples" / "take-one" / "film.json").read_text())
    tpl["title"] = proj.name.replace("-", " ").title()
    tpl["voice"] = "voice"
    (proj / "film.json").write_text(json.dumps(tpl, indent=2, ensure_ascii=False) + "\n")
    print(f"{proj}/film.json written from the Take One example. Change every field to your product, put your "
          f"screenshots in {proj}/assets/ and your voice-studio folder at {proj}/voice/.")


def cmd_words(a):
    proj, cfg = load(a.project)
    v = voice_dir(proj, cfg)
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        die("needs faster-whisper: python3 -m pip install --user faster-whisper")
    t = json.loads((v / "timings.json").read_text())
    model = WhisperModel(a.model, device="cpu", compute_type="int8")
    out = []
    for ln in t["lines"]:
        segs, _ = model.transcribe(str(v / ln["file"]), word_timestamps=True, beam_size=5, condition_on_previous_text=False)
        words = [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)} for s in segs for w in s.words]
        out.append({"n": ln["n"], "script": ln["text"], "said": " ".join(w["w"] for w in words), "duration": ln["duration"], "words": words})
        print(ln["n"], out[-1]["said"])
    (v / "words.json").write_text(json.dumps(out, indent=1))
    print(f"-> {v / 'words.json'}")


def cmd_hits(a):
    """Strong onsets in a track: spectral-flux peaks, loudest first."""
    np = np_()
    x = pcm(a.file)
    hop, n = 512, 2048
    win = np.hanning(n)
    frames = [np.abs(np.fft.rfft(x[i:i + n] * win)) for i in range(0, len(x) - n, hop)]
    S = np.log1p(np.array(frames))
    flux = np.maximum(0, np.diff(S, axis=0)).sum(axis=1)
    flux = (flux - flux.mean()) / (flux.std() + 1e-9)
    peaks = [i for i in range(1, len(flux) - 1) if flux[i] > flux[i - 1] and flux[i] >= flux[i + 1] and flux[i] > 2.5]
    peaks = sorted(peaks, key=lambda i: -flux[i])[: a.top]
    print("time (s)   strength")
    for i in sorted(peaks):
        print(f"{(i + 1) * hop / SR:8.2f}   {flux[i]:.1f}")
    print('\nPick the hit you want the opener to cut on and put it in film.json as "music": {"firstHit": <time>}.')


def copy_in(proj, rel, name):
    src = (proj / rel).resolve()
    if not src.exists():
        die(f"missing file: {src}")
    PUB.mkdir(parents=True, exist_ok=True)
    dst = PUB / f"{name}{src.suffix.lower()}"
    shutil.copyfile(src, dst)
    return f"p/{dst.name}", src


def media(proj, b, key, name):
    if key == "media":
        rel = b.get("video") or b.get("image")
        is_video = bool(b.get("video"))
    else:
        rel = b.get("videoVertical") or b.get("imageVertical")
        is_video = bool(b.get("videoVertical"))
    if not rel:
        return None
    path, src = copy_in(proj, rel, name)
    w, h = media_size(src)
    m = {"src": path, "w": w, "h": h, "video": is_video}
    if is_video:
        m.update({"rate": b.get("rate", 1), "from": b.get("from_sec", 0)})
    return m


def cmd_plan(a, quiet=False):
    np = np_()
    proj, cfg = load(a.project)
    v = voice_dir(proj, cfg)
    if not (v / "words.json").exists():
        die(f"no words.json in {v}: run  python3 film.py words {a.project}")
    timings = json.loads((v / "timings.json").read_text())
    wordsj = {w["n"]: w for w in json.loads((v / "words.json").read_text())}
    fixes = {NORM(k): val for k, val in cfg.get("fixes", {}).items()}
    if PUB.exists():
        shutil.rmtree(PUB)
    (PUB / "vo").mkdir(parents=True)

    lines = {}
    for ln in timings["lines"]:
        n = ln["n"]
        src = v / ln["file"]
        dst = PUB / "vo" / f"line{n}.wav"
        shutil.copyfile(src, dst)
        wd = wordsj.get(n)
        if not wd:
            die(f"line {n} has no word timings: run words again")
        lines[n] = {"file": f"p/vo/line{n}.wav", "dur": ln["duration"], "audio": pcm(src), "words": align(ln["text"], wd["words"], fixes)}

    brand = dict(cfg["brand"])
    brand.setdefault("sub", "")
    brand.setdefault("accent", "#2957e9")
    brand["mark"] = copy_in(proj, brand["mark"], "mark")[0] if brand.get("mark") else None

    gap = cfg.get("gap", 0.3)
    T = {}
    wordmark = TILES[-1] + 0.1
    claude = None
    if cfg.get("claude"):
        c = cfg["claude"]
        prompt = c["prompt"]
        T["claude"] = wordmark + 0.9
        T["typeStart"] = T["claude"] + 0.2
        T["typeEnd"] = T["typeStart"] + len(prompt) / CPS
        T["send"] = T["typeEnd"] + 0.2
        T["think"] = T["send"] + 0.1
        T["reply"] = T["think"] + 0.35
        T["card"] = T["reply"] + 0.55
        T["open"] = T["card"] + 0.4
        claude = {"prompt": prompt, "skill": c.get("skill"), "title": c.get("title", prompt[:1].upper() + prompt[1:]),
                  "thinking": c.get("thinking", "Thinking…"), "reply": c["reply"], "model": c.get("model", "Opus 5.5"),
                  "card": {"title": c.get("card", {}).get("title", brand["name"]), "sub": c.get("card", {}).get("sub", "Artifact"),
                           "button": c.get("card", {}).get("button", "Open")},
                  "T": {k: round(x, 3) for k, x in T.items()}}
        t = T["open"] + 0.2
    else:
        t = wordmark + 1.2

    audio, sfx, voice_spans, quiet_spans, beats = [], [], [], [], []
    cfg_beats = cfg["beats"]
    # the compare clips first, so a chips wave before them can show the same raw → clean
    compares = {}
    for i, b in enumerate(cfg_beats):
        if b.get("scene") == "compare":
            length = b.get("length", 1.5)
            raw = pcm(proj / b["before"])
            on = speech_onset(raw)
            raw_from = max(0.0, on - 0.3)
            rc = raw[int(raw_from * SR): int((raw_from + length + 0.3) * SR)]
            cc = pcm(proj / b["after"])[: int(length * SR)]
            write_wav(PUB / "vo" / f"before{i}.wav", rc)
            write_wav(PUB / "vo" / f"after{i}.wav", cc)
            compares[i] = {"length": length, "before": bars(rc, 120), "after": bars(cc, 120)}

    prev = None
    used = {}
    for i, b in enumerate(cfg_beats):
        kind = b.get("scene")
        if kind not in KINDS:
            die(f"beat {i + 1}: scene must be one of {sorted(KINDS)}")
        hard_in, hard_out = HARD[kind]
        if "cut" in b:
            hard_in = hard_out = b["cut"] == "hard"
        out = {"kind": kind, "hardIn": hard_in, "hardOut": hard_out}
        for key in ("palette", "title", "size", "grey", "chips", "prefix", "items", "final", "history", "thinking", "keyword", "tagline"):
            if key in b:
                out[key] = b[key]
        if prev is not None:
            t = prev["tail"] + b.get("gapBefore", 0.0 if prev["kind"] == "chat" else gap)

        if kind == "compare":
            cm = compares[i]
            L = cm["length"]
            labels = b.get("labels", [["Before", "raw"], ["After", brand["name"]]])
            start = t
            rb, ra = start + 0.25, start + 0.25 + L + 0.35
            out.update({"at": start, "end": ra + L, "rows": [
                {"name": labels[0][0], "sub": labels[0][1], "bars": cm["before"], "at": rb, "d": L + 0.3},
                {"name": labels[1][0], "sub": labels[1][1], "bars": cm["after"], "at": ra, "d": L}]})
            audio += [{"src": f"p/vo/before{i}.wav", "at": rb, "from": 0, "dur": L + 0.3},
                      {"src": f"p/vo/after{i}.wav", "at": ra, "from": 0, "dur": L}]
            quiet_spans.append([start, ra + L])
            sfx += [{"src": "sfx/pop.wav", "at": rb - 0.1, "db": -14}, {"src": "sfx/pop.wav", "at": ra - 0.1, "db": -14}]
            out["inAt"] = start
            out["tail"] = out["end"]
        elif kind == "end" and "line" not in b:
            out.update({"at": t, "end": t + 4.2, "inAt": t, "tail": t + 4.2, "cta": False})
            sfx.append({"src": "sfx/whoosh.wav", "at": t - 0.1, "db": -12})
        else:
            n = b.get("line")
            if n not in lines:
                die(f"beat {i + 1}: line {n} isn't in your recording (lines {sorted(lines)})")
            ln = lines[n]
            ws = ln["words"]
            i0 = find_phrase(ws, b["from"], used.get(n, 0)) if b.get("from") else 0
            i1 = find_phrase(ws, b["until"], i0) + len(b["until"].split()) - 1 if b.get("until") else len(ws) - 1
            used[n] = i1 + 1
            seg_from = 0.0 if i0 == 0 else round((ws[i0 - 1]["e"] + ws[i0]["s"]) / 2, 3)
            seg_to = ln["dur"] if i1 == len(ws) - 1 else round((ws[i1]["e"] + ws[i1 + 1]["s"]) / 2, 3)
            seg_words = [{"w": w["w"], "s": round(w["s"] - seg_from, 3), "e": round(w["e"] - seg_from, 3)} for w in ws[i0:i1 + 1]]
            dur = round(seg_to - seg_from, 3)
            seg = ln["audio"][int(seg_from * SR): int(seg_to * SR)]
            if kind == "end":  # the comment line, said over the end card once the wordmark is up
                card = t
                t = card + 0.7
                out.update({"inAt": card, "cta": True})
                sfx.append({"src": "sfx/whoosh.wav", "at": card - 0.1, "db": -12})
            at = t
            clip = {"src": ln["file"], "at": at, "from": seg_from, "dur": dur}
            if seg_from > 0:
                clip["fadeIn"] = 0.03
            if seg_to < ln["dur"]:
                clip["fadeOut"] = 0.03
            audio.append(clip)
            voice_spans.append([at, at + dur])
            out.update({"at": at, "end": at + dur, "dur": dur, "words": seg_words, "bars": bars(seg), "levels": levels(seg)})
            out["tail"] = at + dur
            if kind == "end":
                out["tail"] = at + dur + 1.3
            if kind == "screen":
                for key, name in (("media", f"screen{i}"), ("mediaVertical", f"screen{i}v")):
                    m = media(proj, b, key, name)
                    if m:
                        out[key] = m
                if "media" not in out:
                    die(f"beat {i + 1}: a screen needs an image (or video) of the real product")
                if b.get("clickVertical"):
                    out["clickVertical"] = b["clickVertical"]
                if b.get("click"):
                    out["click"] = b["click"]
                    out["clickAt"] = at + dur + 0.12
                    sfx.append({"src": "sfx/click.wav", "at": at + dur + 0.12, "db": -8})
            if kind == "chips" and b.get("wave"):
                nxt = next((compares[j] for j in sorted(compares) if j > i), None)
                bb = bars(seg, 120)
                out["wave"] = {"before": nxt["before"] if nxt else bb, "after": nxt["after"] if nxt else bb,
                               "labels": b.get("waveLabels", ["Raw", "Cleaned"])}
            if kind == "list":
                out["onAt"] = at + (seg_words[find_phrase(seg_words, b["on"])]["s"] if b.get("on") else dur)
                sfx.append({"src": "sfx/whoosh.wav", "at": at - 0.1, "db": -16})
            if kind == "chat":
                k0 = find_phrase(seg_words, b["typeFrom"]) if b.get("typeFrom") else 0
                out["typed"] = [{"w": w["w"], "at": round(at + w["s"], 3)} for w in seg_words[k0:]]
                for w in out["typed"]:
                    sfx.append({"src": "sfx/key2.wav", "at": w["at"], "db": -18})
                send = at + dur + 0.15
                out.update({"send": send, "reply": send + 0.4, "watch": send + 1.15, "replyText": b.get("reply", "Done."),
                            "thinking": b.get("thinking", "Working on it…")})
                res = dict(b.get("result", {}))
                if res.get("image") or res.get("video"):
                    path, _ = copy_in(proj, res.get("video") or res.get("image"), f"result{i}")
                    res = {"src": path, "video": bool(res.get("video")), "label": res.get("label", "")}
                out["result"] = {"src": res.get("src"), "video": res.get("video", False), "label": res.get("label", "")}
                out["tail"] = send + 1.5
                sfx += [{"src": "sfx/click.wav", "at": send, "db": -6}, {"src": "sfx/click.wav", "at": send + 1.15, "db": -6}]
            if kind in ("screen", "type", "chips") and beats:
                sfx.append({"src": "sfx/swish.wav", "at": at - 0.25, "db": -16})
            if "inAt" not in out:
                first_after_claude = not beats and claude
                out["inAt"] = at - (0.05 if first_after_claude else 0.12 if hard_in else 0.2)
        beats.append(out)
        prev = out

    total = round(prev["tail"], 3)
    for j, b in enumerate(beats):
        nxt = beats[j + 1] if j + 1 < len(beats) else None
        b["outAt"] = (nxt["inAt"] + (0 if nxt["hardIn"] else 0.08)) if nxt else total
        b.pop("tail", None)
    for b in beats:
        for key in ("at", "end", "inAt", "outAt", "onAt", "clickAt", "send", "reply", "watch"):
            if key in b:
                b[key] = round(b[key], 3)

    if claude:
        for i, ch in enumerate(claude["prompt"]):
            if ch != " ":
                sfx.append({"src": f"sfx/key{1 + i % 3}.wav", "at": round(T["typeStart"] + i / CPS, 3), "db": -16})
        sfx += [{"src": "sfx/click.wav", "at": T["send"], "db": -6}, {"src": "sfx/click.wav", "at": T["open"], "db": -6},
                {"src": "sfx/whoosh.wav", "at": T["open"] + 0.05, "db": -14}]

    music = None
    if cfg.get("music") and cfg["music"].get("file"):
        mc = cfg["music"]
        path, _ = copy_in(proj, mc["file"], "music")
        music = {"src": path, "offset": round(max(0.0, mc.get("firstHit", TILES[0]) - TILES[0]), 3),
                 "db": mc.get("db", -15.5), "lift": mc.get("lift", 11.5)}

    # voice spans closer than 1.5 s count as one, so the music doesn't pump between lines
    voice_spans.sort()
    merged = []
    for s in voice_spans:
        if merged and s[0] - merged[-1][1] < 1.5:
            merged[-1][1] = max(merged[-1][1], s[1])
        else:
            merged.append(list(s))

    plan = {"fps": FPS, "total": total, "cps": CPS, "brand": brand,
            "opener": {"tiles": TILES, "labels": cfg.get("opener", {}).get("labels", ["", "", "", ""]), "wordmark": round(wordmark, 3),
                       "next": round(T["claude"] if claude else beats[0]["inAt"], 3)},
            "claude": claude, "beats": beats,
            "audio": [dict(x, at=round(x["at"], 3), dur=round(x["dur"], 3)) for x in audio],
            "sfx": sorted(({**x, "at": round(x["at"], 3)} for x in sfx), key=lambda x: x["at"]),
            "music": music, "voice": [[round(a, 3), round(b, 3)] for a, b in merged],
            "quiet": [[round(a, 3), round(b, 3)] for a, b in quiet_spans]}
    (ENGINE / "src" / "plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False))
    if not quiet:
        print(f"{cfg.get('title', proj.name)}: {total:.2f} s")
        if claude:
            print(f"  {0:6.2f}  opener, wordmark, Claude ({claude['prompt']!r}), voice in at {beats[0]['at']:.2f}")
        for b in beats:
            said = " ".join(w["w"] for w in b.get("words", []))
            print(f"  {b['at']:6.2f}  {b['kind']:<8} {said}")
    return proj, cfg, plan


# ── render ─────────────────────────────────────────────────────────────────────────────────────
def need_engine():
    if not (ENGINE / "node_modules" / "remotion").exists():
        die(f"the engine isn't installed: python3 {HERE / 'film.py'} setup")


def loudness(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    p = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r.stderr)
    return (float(m[-1]) if m else None), (float(p[-1]) if p else None)


def master(src, dst, lufs):
    """Remove Remotion's AAC delay and bring the mix to the target loudness under a -1.5 dBTP ceiling."""
    tmp = dst.with_suffix(".tmp.wav")
    run(["ffmpeg", "-v", "error", "-y", "-ss", str(AAC_DELAY), "-i", str(src), "-vn", "-ac", "2", "-ar", "48000", str(tmp)])
    have, _ = loudness(tmp)
    gain = (lufs - have) if have is not None else 0.0
    run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ss", str(AAC_DELAY), "-i", str(src), "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-af", f"apad,volume={gain:.2f}dB,alimiter=limit=0.84:attack=5:release=60:level=disabled:latency=enabled",
         "-shortest", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", str(dst)])
    tmp.unlink(missing_ok=True)
    return loudness(dst)


def render_one(proj, cfg, vertical, draft):
    comp = "FilmVertical" if vertical else "Film"
    slug = re.sub(r"[^a-z0-9]+", "-", cfg.get("title", proj.name).lower()).strip("-") or "film"
    out_dir = proj / "out"
    out_dir.mkdir(exist_ok=True)
    raw = out_dir / f".render-{comp}.mp4"
    cmd = ["npx", "remotion", "render", "src/index.ts", comp, str(raw), "--log=error"]
    if draft:
        cmd += ["--scale=0.5"]
    run(cmd, cwd=ENGINE)
    dst = out_dir / f"{slug}-{'9x16' if vertical else '16x9'}{'-draft' if draft else ''}.mp4"
    lu, pk = master(raw, dst, cfg.get("lufs", -16.4))
    raw.unlink(missing_ok=True)
    print(f"-> {dst}  ({lu} LUFS, peak {pk} dBFS)")
    return dst


def cmd_render(a):
    need_engine()
    proj, cfg, plan = cmd_plan(a, quiet=True)
    print(f"{cfg.get('title', proj.name)}: {plan['total']:.2f} s")
    if a.both:
        render_one(proj, cfg, False, a.draft)
        render_one(proj, cfg, True, a.draft)
    else:
        render_one(proj, cfg, a.vertical, a.draft)


def cmd_still(a):
    need_engine()
    proj, cfg, plan = cmd_plan(a, quiet=True)
    comp = "FilmVertical" if a.vertical else "Film"
    out = Path(a.out).resolve() if a.out else proj / "out" / f"still-{a.at:05.2f}{'-v' if a.vertical else ''}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    run(["npx", "remotion", "still", "src/index.ts", comp, str(out), f"--frame={min(int(round(a.at * FPS)), int(plan['total'] * FPS) - 1)}", "--log=error"], cwd=ENGINE)
    print(f"-> {out}")


def cmd_setup(a):
    ok = True
    for tool in ("ffmpeg", "ffprobe", "node", "npm"):
        if not shutil.which(tool):
            print(f"✗ {tool} is missing" + (" (brew install ffmpeg)" if tool.startswith("ff") else " (install Node.js 18+ from nodejs.org)"))
            ok = False
    try:
        import numpy  # noqa: F401
        print("✓ numpy")
    except ImportError:
        print("✗ numpy: python3 -m pip install --user numpy")
        ok = False
    try:
        import faster_whisper  # noqa: F401
        print("✓ faster-whisper")
    except ImportError:
        print("✗ faster-whisper (for word timings): python3 -m pip install --user faster-whisper")
        ok = False
    if shutil.which("npm"):
        if not (ENGINE / "node_modules" / "remotion").exists():
            print("installing the Remotion engine (npm install, about a minute)…")
            run(["npm", "install", "--no-audit", "--no-fund", "--loglevel=error"], cwd=ENGINE)
        print("✓ engine")
    if not (ENGINE / "src" / "plan.json").exists():
        (ENGINE / "src" / "plan.json").write_text(json.dumps({"fps": FPS, "total": 1, "cps": CPS, "brand": {"name": "", "sub": "", "accent": "#2957e9", "mark": None},
                                                              "opener": {"tiles": TILES, "labels": [], "wordmark": 1, "next": 1}, "claude": None, "beats": [],
                                                              "audio": [], "sfx": [], "music": None, "voice": [], "quiet": []}))
    print("ready" if ok else "fix the ✗ lines above, then run setup again")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup")
    s = sub.add_parser("new"); s.add_argument("project")
    s = sub.add_parser("words"); s.add_argument("project"); s.add_argument("--model", default="medium.en")
    s = sub.add_parser("hits"); s.add_argument("file"); s.add_argument("--top", type=int, default=12)
    s = sub.add_parser("plan"); s.add_argument("project")
    s = sub.add_parser("still"); s.add_argument("project"); s.add_argument("--at", type=float, required=True)
    s.add_argument("--vertical", action="store_true"); s.add_argument("--out")
    s = sub.add_parser("render"); s.add_argument("project")
    g = s.add_mutually_exclusive_group(); g.add_argument("--vertical", action="store_true"); g.add_argument("--both", action="store_true")
    s.add_argument("--draft", action="store_true")
    a = p.parse_args()
    {"setup": cmd_setup, "new": cmd_new, "words": cmd_words, "hits": cmd_hits, "plan": cmd_plan, "still": cmd_still,
     "render": cmd_render}[a.cmd](a)


if __name__ == "__main__":
    main()
