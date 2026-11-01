#!/usr/bin/env python3
"""link-edit: a talking-head clip + assets scraped with context.dev -> a finished effect clip.

  python3 link_edit.py prep <clip> <workdir> [--start 0] [--dur 3.2]
      1080x1920 frames, a cut-out of the speaker per frame, and a head track.
  python3 link_edit.py render <spec.json> [--still 1.2,2.0]
      Runs fx/render.mjs on a spec (see SKILL.md).

The cut-out uses Apple's Vision framework through bin/segment (on-device, no model download).
Build it once with:  swiftc -O segment.swift -o bin/segment
"""
import argparse
import json
import os
import queue
import struct
import subprocess
import sys
import threading

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SEG = os.path.join(HERE, "bin", "segment")
W, H = 1080, 1920


def ensure_segment():
    if os.path.exists(SEG):
        return
    os.makedirs(os.path.dirname(SEG), exist_ok=True)
    subprocess.run(["swiftc", "-O", os.path.join(HERE, "segment.swift"), "-o", SEG], check=True)


def clean_mask(raw, prev):
    """Mask from Vision -> full size, soft edge, steady from frame to frame (0..1 float)."""
    m = Image.fromarray(raw).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(2.2))
    a = np.asarray(m, dtype=np.float32) / 255.0
    if prev is not None:
        a = 0.62 * a + 0.38 * prev
    return a


def head_point(a):
    ys = np.where(a.max(axis=1) > 0.5)[0]
    if len(ys) == 0:
        return None
    top = int(ys[0])
    band = a[top:top + 300]
    cols = band.sum(axis=0)
    x = float((cols * np.arange(W)).sum() / max(cols.sum(), 1))
    return [x, float(top)]


def smooth(track, win=9):
    arr = np.array(track, dtype=np.float32)
    out = arr.copy()
    for i in range(len(arr)):
        lo, hi = max(0, i - win // 2), min(len(arr), i + win // 2 + 1)
        out[i] = arr[lo:hi].mean(axis=0)
    return [[round(float(x), 1), round(float(y), 1)] for x, y in out]


def prep(clip, work, start, dur, fps=30):
    ensure_segment()
    os.makedirs(os.path.join(work, "frames"), exist_ok=True)
    os.makedirs(os.path.join(work, "person"), exist_ok=True)
    vf = (f"fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,"
          f"crop={W}:{H},unsharp=5:5:0.5")
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start), "-i", clip]
    if dur:
        cmd += ["-t", str(dur)]
    cmd += ["-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    ff = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    seg = subprocess.Popen([SEG, "--stream", str(W), str(H), "accurate"],
                           stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    q = queue.Queue(maxsize=8)
    size = W * H * 3

    def feed():
        while True:
            buf = ff.stdout.read(size)
            if len(buf) < size:
                break
            q.put(buf)
            seg.stdin.write(buf)
            seg.stdin.flush()
        seg.stdin.close()

    threading.Thread(target=feed, daemon=True).start()
    i, prev, track = 0, None, []
    while True:
        hdr = seg.stdout.read(8)
        if len(hdr) < 8:
            break
        mw, mh = struct.unpack("<II", hdr)
        raw = np.frombuffer(seg.stdout.read(mw * mh), np.uint8).reshape(mh, mw)
        rgb = np.frombuffer(q.get(), np.uint8).reshape(H, W, 3)
        a = clean_mask(raw, prev)
        prev = a
        alpha = (np.clip((a - 0.32) / 0.42, 0, 1) * 255).astype(np.uint8)
        pt = head_point(a)
        track.append(pt if pt else (track[-1] if track else [W / 2, 300.0]))
        i += 1
        name = f"{i:05d}"
        Image.fromarray(rgb).save(os.path.join(work, "frames", name + ".jpg"), quality=93)
        Image.fromarray(np.dstack([rgb, alpha])).save(
            os.path.join(work, "person", name + ".webp"), quality=90, method=1, exact=False)
    json.dump({"fps": fps, "frames": i, "track": smooth(track), "clip": os.path.abspath(clip), "start": start},
              open(os.path.join(work, "clip.json"), "w"))
    print(json.dumps({"frames": i, "work": work}))


def render(spec, still):
    cmd = ["node", os.path.join(HERE, "fx", "render.mjs"), spec]
    if still:
        cmd += ["--still", still]
    sys.exit(subprocess.run(cmd).returncode)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prep")
    p.add_argument("clip")
    p.add_argument("work")
    p.add_argument("--start", type=float, default=0)
    p.add_argument("--dur", type=float, default=None)
    r = sub.add_parser("render")
    r.add_argument("spec")
    r.add_argument("--still")
    a = ap.parse_args()
    if a.cmd == "prep":
        prep(a.clip, a.work, a.start, a.dur)
    else:
        render(a.spec, a.still)


if __name__ == "__main__":
    main()
