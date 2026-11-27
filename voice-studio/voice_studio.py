#!/usr/bin/env python3
"""
Voice Studio: turn the lines you recorded in your Take One studio into one clean voiceover track.

    python3 voice_studio.py check
        Checks that ffmpeg and ffprobe are installed.

    python3 voice_studio.py seed "My launch video" script.txt --out doc.json
        Splits a script into takes (a blank line between takes) and writes a studio document
        for Claude to put in your studio (ArtifactData set, collection "scripts").

    python3 voice_studio.py unpack --doc scripts/<id>.json --assets <folder> --out voice/<name>
    python3 voice_studio.py unpack --zip ~/Downloads/<Title>.zip --out voice/<name>
        Pulls the kept takes out of the studio (the script document plus the take files Claude
        saved from the studio) or out of a session ZIP from "Download session ZIP".
        Writes voice/<name>/takes/01.m4a, 02.m4a, ... and voice/<name>/lines.json.

    python3 voice_studio.py clean voice/<name>
    python3 voice_studio.py clean voice/<name> --auphonic
        Trims the dead air around every line, filters rumble, reduces noise, softens room tone in
        the pauses, sets every line to the same loudness, joins them with a short gap and masters
        the result. Writes:
            voice/<name>/voiceover.wav and voiceover.mp3   the finished track
            voice/<name>/lines/01.wav ...                  each line on its own, mastered
            voice/<name>/timings.json                      where each line starts and ends
            voice/<name>/captions.srt                      one caption per line
        --auphonic sends the takes to Auphonic first (your own key; see auphonic.py).

Needs Python 3.9+ and ffmpeg. Standard library only.
"""

import argparse
import array
import base64
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from pathlib import Path

SR = 48000
WIN = SR // 50  # 20 ms analysis windows
HERE = Path(__file__).resolve().parent
EXT_FOR_MIME = {
    "audio/wav": "wav", "audio/x-wav": "wav", "audio/wave": "wav", "audio/mpeg": "mp3", "audio/mp4": "m4a",
    "audio/x-m4a": "m4a", "audio/aac": "aac", "audio/ogg": "ogg", "audio/webm": "webm", "audio/flac": "flac",
    "audio/x-caf": "caf", "video/mp4": "mp4", "video/webm": "webm",
}
AUDIO_EXT = {"wav", "mp3", "m4a", "aac", "ogg", "opus", "webm", "flac", "caf", "mp4", "aif", "aiff"}


# ── small helpers ──────────────────────────────────────────────────────────

def die(msg):
    sys.exit(msg)


def need_ffmpeg():
    missing = [t for t in ("ffmpeg", "ffprobe") if not shutil.which(t)]
    if missing:
        die("Missing " + " and ".join(missing) + ". Install ffmpeg: `brew install ffmpeg` on a Mac, "
            "`winget install ffmpeg` on Windows, `sudo apt install ffmpeg` on Linux.")


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "voiceover"


def split_script(text):
    """Same rule as the studio: a blank line between takes, line breaks inside a take become spaces."""
    parts = re.split(r"\n\s*\n", text.replace("\r", ""))
    return [re.sub(r"\s*\n\s*", " ", p).strip() for p in parts if p.strip()]


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, **kw)


def ffmpeg_json(cmd):
    """Runs an ffmpeg analysis command and returns the last {...} block it prints (loudnorm's report)."""
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    m = re.findall(r"\{[^{}]*\}", err, re.S)
    if not m:
        die("ffmpeg gave no measurement:\n" + err[-800:])
    return json.loads(m[-1])


def duration(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], text=True).stdout
    return float(out.strip() or 0)


def pcm16(path):
    raw = run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"]).stdout
    a = array.array("h")
    a.frombytes(raw[: len(raw) // 2 * 2])
    if sys.byteorder != "little":
        a.byteswap()
    return a


def window_db(samples):
    out = []
    for i in range(0, len(samples), WIN):
        chunk = samples[i:i + WIN]
        if not chunk:
            break
        ms = sum(x * x for x in chunk) / len(chunk)
        out.append(10 * math.log10(ms / (32768.0 ** 2)) if ms > 0 else -120.0)
    return out


def pct(values, p):
    s = sorted(values)
    return s[min(len(s) - 1, max(0, int(round(p / 100 * (len(s) - 1)))))]


def speech_bounds(db):
    """First and last 20 ms window of speech, measured against this take's own room tone and voice level.

    Speech = at least 8 dB above the room tone (10th percentile) and within 22 dB of the voice (95th
    percentile). A run of 3 windows (60 ms) is needed, so a click or a breath on its own doesn't count.
    """
    if not db:
        return 0, 0, -120.0, -120.0
    room, voice = pct(db, 10), pct(db, 95)
    thr = max(room + 8, voice - 22)
    hot = [v >= thr for v in db]
    first = next((i for i in range(len(hot) - 2) if hot[i] and hot[i + 1] and hot[i + 2]), None)
    last = next((i for i in range(len(hot) - 1, 1, -1) if hot[i] and hot[i - 1] and hot[i - 2]), None)
    if first is None or last is None or last < first:
        return 0, len(db), room, thr
    return first, last + 1, room, thr


def dropouts(samples):
    """Splices on 512-sample boundaries: what a recorder that dropped packets leaves behind. 0 = clean."""
    n = len(samples)
    if n < 2048:
        return 0
    a = [x / 32768.0 for x in samples]
    W = 96
    d = [0.0] + [abs(a[i] - a[i - 1]) for i in range(1, n)]
    loc, acc = [0.0] * n, 0.0
    for i in range(1, n):
        acc += d[i]
        if i > W:
            acc -= d[i - W]
        loc[i] = acc / min(i, W)
    bins, total = [0] * 512, 0
    for i in range(1, n - 1):
        if a[i] == 0:
            continue
        l = loc[min(n - 1, i + W // 2)]
        if abs(a[i + 1] - 2 * a[i] + a[i - 1]) / (l + 1e-5) > 8:
            bins[i % 512] += 1
            total += 1
    if total < 8:
        return 0
    best = max(sum(bins[(r + k) % 512] for k in range(-2, 3)) for r in range(512))
    return best if best / total > 0.5 and best >= 8 else 0


def loudness(path):
    r = ffmpeg_json(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "loudnorm=print_format=json", "-f", "null", "-"])
    return {k: float(r[k]) for k in ("input_i", "input_tp", "input_lra", "input_thresh")}


def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ── seed ───────────────────────────────────────────────────────────────────

def cmd_seed(a):
    text = sys.stdin.read() if a.script == "-" else Path(a.script).expanduser().read_text()
    lines = split_script(text)
    if not lines:
        die("The script is empty. Put a blank line between takes.")
    now = int(time.time() * 1000)
    doc_id = f"{slugify(a.title)}-{uuid.uuid4().hex[:6]}"
    doc = {
        "title": a.title.strip(),
        "lines": [{"id": uuid.uuid4().hex[:12], "text": t} for t in lines],
        "status": "recording",
        "createdAt": now,
        "updatedAt": now,
    }
    out = Path(a.out or f"{doc_id}.json").expanduser()
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    long_lines = [i + 1 for i, t in enumerate(lines) if len(t.split()) > 30]
    print(json.dumps({"doc_id": doc_id, "collection": "scripts", "file": str(out), "lines": len(lines),
                      "long_lines": long_lines}, indent=2))


# ── unpack ─────────────────────────────────────────────────────────────────

def ext_for(mime, name):
    if name and "." in name:
        e = name.rsplit(".", 1)[1].lower()
        if e in AUDIO_EXT:
            return e
    return EXT_FOR_MIME.get((mime or "").split(";")[0], "bin")


def read_envelope(path):
    """A studio take: a JSON envelope holding the file exactly as it was uploaded (base64)."""
    raw = path.read_bytes()
    try:
        env = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return raw, "", path.name  # already plain audio
    if not isinstance(env, dict) or "data" not in env:
        die(f"{path.name} isn't a Take One take.")
    return base64.b64decode(env["data"]), env.get("mime", ""), env.get("fileName", "")


def cmd_unpack(a):
    out = Path(a.out).expanduser()
    takes_dir = out / "takes"
    takes_dir.mkdir(parents=True, exist_ok=True)
    for old in takes_dir.iterdir():
        if old.is_file():
            old.unlink()
    rows, missing = [], []

    if a.zip:
        z = zipfile.ZipFile(Path(a.zip).expanduser())
        meta = json.loads(z.read("take-one-session.json"))
        title = meta.get("title") or Path(a.zip).stem
        for i, line in enumerate(meta.get("lines", [])):
            n = i + 1
            path = line.get("audioPath")
            if not path or path not in z.namelist():
                missing.append(n)
                rows.append({"n": n, "text": line["text"], "file": None})
                continue
            dest = takes_dir / f"{n:02d}.{ext_for('', path)}"
            dest.write_bytes(z.read(path))
            rows.append({"n": n, "text": line["text"], "file": f"takes/{dest.name}"})
    else:
        if not a.doc or not a.assets:
            die("Give --doc and --assets, or --zip.")
        doc = json.loads(Path(a.doc).expanduser().read_text())
        title = doc.get("title") or "voiceover"
        assets = Path(a.assets).expanduser()
        for i, line in enumerate(doc.get("lines", [])):
            n = i + 1
            take = line.get("take") or {}
            if take.get("status") != "kept" or not take.get("assetId"):
                missing.append(n)
                rows.append({"n": n, "text": line["text"], "file": None})
                continue
            found = sorted(assets.glob(take["assetId"] + "*"))
            if not found:
                die(f"Line {n}: take {take['assetId']} isn't in {assets}. Save it from the studio first "
                    f"(Artifact read with path={take['assetId']}).")
            data, mime, name = read_envelope(found[0])
            dest = takes_dir / f"{n:02d}.{ext_for(mime or take.get('mime'), name or take.get('fileName'))}"
            dest.write_bytes(data)
            rows.append({"n": n, "text": line["text"], "file": f"takes/{dest.name}", "source": take.get("fileName")})

    (out / "lines.json").write_text(json.dumps({"title": title, "lines": rows}, indent=2, ensure_ascii=False) + "\n")
    have = len(rows) - len(missing)
    print(f"{title}: {have} of {len(rows)} lines have a kept take → {takes_dir}")
    if missing:
        print("No kept take for line " + ", ".join(map(str, missing)) + ". They're skipped unless you record them.",
              file=sys.stderr)
        if not a.allow_missing:
            sys.exit(2)


# ── clean ──────────────────────────────────────────────────────────────────

def cmd_clean(a):
    need_ffmpeg()
    root = Path(a.folder).expanduser()
    manifest = json.loads((root / "lines.json").read_text())
    rows = [r for r in manifest["lines"] if r.get("file")]
    if not rows:
        die("No takes to clean. Run unpack first.")

    sources = [root / r["file"] for r in rows]
    bad = [(r["n"], c) for r, src in zip(rows, sources) for c in [dropouts(pcm16(src))] if c]
    if bad:
        msg = ", ".join(f"line {n} ({c})" for n, c in bad)
        if not a.force_dropouts:
            die(f"Dropouts in {msg}: the recorder missed bits of the voice, so these lines will sound choppy. "
                "Record them again (or pass --force-dropouts to clean them anyway).")
        print(f"Warning: dropouts in {msg}.", file=sys.stderr)
    if a.auphonic:
        auph = [p.with_name(p.stem + ".auph.wav") for p in sources]
        if a.fresh or not all(q.exists() and q.stat().st_mtime >= p.stat().st_mtime for p, q in zip(sources, auph)):
            print("Sending the takes to Auphonic (one production for all of them)…", file=sys.stderr)
            subprocess.run([sys.executable, str(HERE / "auphonic.py"), *map(str, sources),
                            "--title", f"{manifest['title']} (Take One)"], check=True)
        else:
            print("Reusing the Auphonic files from last time (--fresh to redo them).", file=sys.stderr)
        sources = auph

    lines_dir = root / "lines"
    lines_dir.mkdir(exist_ok=True)
    for old in lines_dir.glob("*.wav"):
        old.unlink()

    report, pieces = [], []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for r, src in zip(rows, sources):
            n = r["n"]
            raw_len = duration(src)
            samples = pcm16(src)
            db = window_db(samples)
            if a.no_trim:
                start, end, room, thr = 0.0, raw_len, pct(db, 10) if db else -120.0, -120.0
            else:
                f0, f1, room, thr = speech_bounds(db)
                start = max(0.0, f0 * WIN / SR - a.lead)
                end = min(raw_len, f1 * WIN / SR + a.tail)
            length = max(0.05, end - start)

            chain = [f"atrim=start={start:.3f}:end={end:.3f}", "asetpts=PTS-STARTPTS", "highpass=f=80"]
            if not a.auphonic and not a.no_denoise:
                chain.append("afftdn=nr=10:nf=-50:tn=1")
            # Auphonic already pulls the room down in the pauses; a gate on top of it eats the quiet ends of words
            if not a.no_gate and not a.auphonic and thr > -100:
                gate = 10 ** ((thr - 4) / 20)  # just under where speech starts for this take
                chain.append(f"agate=threshold={gate:.6f}:range=0.1:ratio=3:attack=8:release=250:knee=3")
            if a.eq:
                chain.append(a.eq)
            fade_out = min(0.06, length / 4)
            chain += ["afade=t=in:d=0.03", f"afade=t=out:st={max(0.0, length - fade_out):.3f}:d={fade_out:.3f}"]

            stage = tmp / f"{n:02d}.stage.wav"
            run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", ",".join(chain),
                 "-ac", "1", "-ar", str(SR), "-c:a", "pcm_f32le", str(stage)])
            before = loudness(stage)
            gain = a.line_lufs - before["input_i"] if before["input_i"] > -70 else 0.0
            leveled = tmp / f"{n:02d}.level.wav"
            run(["ffmpeg", "-v", "error", "-y", "-i", str(stage), "-af", f"volume={gain:.2f}dB",
                 "-c:a", "pcm_f32le", str(leveled)])
            pieces.append(leveled)
            report.append({"n": n, "raw": round(raw_len, 2), "start": round(start, 2), "end": round(end, 2),
                           "kept": round(length, 2), "room_db": round(room, 1), "line_lufs_before": round(before["input_i"], 1),
                           "gain_db": round(gain, 1)})

        # join: every line back to back with the same gap, read as raw float PCM so nothing drifts
        gap = b"\x00\x00\x00\x00" * int(round(a.gap * SR))
        joined_raw, timings, t = bytearray(), [], 0.0
        for r, p, rep in zip(rows, pieces, report):
            pcm = run(["ffmpeg", "-v", "error", "-i", str(p), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]).stdout
            dur = len(pcm) / 4 / SR
            timings.append({"n": r["n"], "text": r["text"], "start": round(t, 3), "end": round(t + dur, 3),
                            "duration": round(dur, 3), "file": f"lines/{r['n']:02d}.wav"})
            joined_raw += pcm
            t += dur
            if r is not rows[-1]:
                joined_raw += gap
                t += a.gap
        joined_raw += b"\x00\x00\x00\x00" * int(round(a.end_pad * SR))
        joined = tmp / "joined.wav"
        run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
             "-c:a", "pcm_f32le", str(joined)], input=bytes(joined_raw))

        # master: one linear gain to the target loudness, true peak held under the ceiling
        m = loudness(joined)
        master_af = (f"loudnorm=I={a.lufs}:TP={a.true_peak}:LRA=20:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
                     f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:linear=true:print_format=json")
        wav = root / "voiceover.wav"
        run(["ffmpeg", "-v", "error", "-y", "-i", str(joined), "-af", master_af, "-ar", str(SR), "-ac", "1",
             "-c:a", "pcm_s24le", str(wav)])

    run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-c:a", "libmp3lame", "-b:a", "192k", str(root / "voiceover.mp3")])
    for tm in timings:
        run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-ss", f"{tm['start']:.3f}", "-t", f"{tm['duration']:.3f}",
             "-c:a", "pcm_s24le", str(root / tm["file"])])

    final = loudness(wav)
    total = duration(wav)
    (root / "timings.json").write_text(json.dumps({
        "title": manifest["title"], "total": round(total, 3), "gap": a.gap, "lufs": round(final["input_i"], 1),
        "true_peak": round(final["input_tp"], 1), "auphonic": bool(a.auphonic), "lines": timings,
    }, indent=2, ensure_ascii=False) + "\n")
    (root / "captions.srt").write_text("".join(
        f"{i + 1}\n{srt_time(tm['start'])} --> {srt_time(tm['end'])}\n{tm['text']}\n\n" for i, tm in enumerate(timings)))

    print(f"\n{manifest['title']}: {len(timings)} lines, {total:.2f}s, {final['input_i']:.1f} LUFS, "
          f"true peak {final['input_tp']:.1f} dBTP")
    print(" line   recorded  →  kept   (cut before / after)   level before → gain")
    for rep in report:
        print(f"  {rep['n']:>3}   {rep['raw']:>6.2f}s → {rep['kept']:>5.2f}s   ({rep['start']:.2f}s / {rep['raw'] - rep['end']:.2f}s)"
              f"          {rep['line_lufs_before']:>6.1f} LUFS → {rep['gain_db']:+.1f} dB")
    print(f"\n→ {wav}\n→ {root / 'voiceover.mp3'}\n→ {root / 'timings.json'}\n→ {root / 'captions.srt'}\n→ {lines_dir}/")
    if a.json:
        print(json.dumps({"lines": report, "timings": timings, "lufs": final["input_i"], "true_peak": final["input_tp"]}))


def cmd_check(_):
    need_ffmpeg()
    v = run(["ffmpeg", "-version"], text=True).stdout.splitlines()[0]
    print(f"OK: {v}\nOK: Python {sys.version.split()[0]}")
    if sys.platform == "darwin":
        if shutil.which("swiftc"):
            print("OK: swiftc (records inside the Take One app)")
        else:
            print("!! Apple's command line tools are missing, so Take One can't record inside the app. "
                  "Fix: xcode-select --install   (dropping in recorded files still works)")


def main():
    ap = argparse.ArgumentParser(description="Voice Studio: your recorded lines → one clean voiceover track.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="check ffmpeg is installed").set_defaults(fn=cmd_check)

    s = sub.add_parser("seed", help="script → studio document")
    s.add_argument("title")
    s.add_argument("script", help="text file (or - for stdin), a blank line between takes")
    s.add_argument("--out")
    s.set_defaults(fn=cmd_seed)

    u = sub.add_parser("unpack", help="studio takes or session ZIP → takes/NN.ext")
    u.add_argument("--doc", help="the script document saved from the studio (scripts/<id>.json)")
    u.add_argument("--assets", help="folder with the take files saved from the studio")
    u.add_argument("--zip", help="a session ZIP from the studio's Download session ZIP")
    u.add_argument("--out", required=True)
    u.add_argument("--allow-missing", action="store_true", help="go on when some lines have no kept take")
    u.set_defaults(fn=cmd_unpack)

    c = sub.add_parser("clean", help="trim, clean, level, join and master")
    c.add_argument("folder")
    c.add_argument("--gap", type=float, default=0.3, help="seconds between lines (default 0.3)")
    c.add_argument("--lead", type=float, default=0.12, help="room kept before the first word (default 0.12 s)")
    c.add_argument("--tail", type=float, default=0.2, help="room kept after the last word (default 0.2 s)")
    c.add_argument("--end-pad", type=float, default=0.3, help="silence after the last line (default 0.3 s)")
    c.add_argument("--line-lufs", type=float, default=-18.0, help="every line is set to this first (default -18)")
    c.add_argument("--lufs", type=float, default=-16.0, help="final loudness (default -16, right for Reels/TikTok/YouTube)")
    c.add_argument("--true-peak", type=float, default=-1.5, help="true peak ceiling in dBTP (default -1.5)")
    c.add_argument("--auphonic", action="store_true", help="clean the takes with Auphonic first (your own key)")
    c.add_argument("--fresh", action="store_true", help="with --auphonic: process again instead of reusing")
    c.add_argument("--no-trim", action="store_true", help="keep each whole file")
    c.add_argument("--no-gate", action="store_true", help="leave the room tone in the pauses")
    c.add_argument("--no-denoise", action="store_true")
    c.add_argument("--eq", help="an ffmpeg EQ filter applied to every line before leveling (e.g. a firequalizer from voice matching)")
    c.add_argument("--force-dropouts", action="store_true", help="clean takes even if they have recorder dropouts")
    c.add_argument("--json", action="store_true")
    c.set_defaults(fn=cmd_clean)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
