#!/usr/bin/env python3
"""Pull a render's audio back into sync with its source track, losslessly.

Remotion's AAC starts with encoder padding (2048 samples, ~43ms at 48kHz) and no edit
list to skip it, so every player hears the music a frame late. Cuts timed to hits then
land early. This measures the lag against the source by cross-correlation and remuxes
with an edit list that skips it (stream copy, no re-encode). It leaves the file alone if
the source doesn't match the render or the lag is implausible. --upload also writes
<name>-upload.mp4 without sound, to post with the sound added in the app.

  python3 scripts/align_audio.py out/match-frame.mp4 public/audio/track.m4a [--start 12.4] [--upload]
"""
import argparse
import os
import subprocess
import tempfile

import numpy as np
from scipy.signal import correlate

SR = 48000
WINDOW = 4  # seconds compared


def decode(path: str, start: float = 0) -> np.ndarray:
    cmd = ['ffmpeg', '-v', 'error', '-ss', str(start), '-i', path, '-t', str(WINDOW), '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-']
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32)


def lag_of(render: str, track: str, start: float) -> tuple[float, float]:
    """Seconds the render's audio trails the track, and how well they match (0-1)."""
    a, b = decode(render), decode(track, start)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    c = correlate(a, b, mode='full', method='fft')
    i = int(np.argmax(c))
    return (i - (n - 1)) / SR, float(c[i] / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('render')
    p.add_argument('track')
    p.add_argument('--start', type=float, default=0, help='audio.startFrom in seconds')
    p.add_argument('--upload', action='store_true', help='also write <name>-upload.mp4 without sound')
    a = p.parse_args()

    align(a.render, a.track, a.start)
    if a.upload:
        upload = os.path.splitext(a.render)[0] + '-upload.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', a.render, '-an', '-c', 'copy', '-movflags', '+faststart', upload], check=True)
        print(f'{upload}: no sound, for posting with the sound added in the app')


def align(render: str, track: str, start: float) -> None:
    if not os.path.exists(track):
        print(f'{render}: {track} not found; left as is')
        return
    lag, match = lag_of(render, track, start)
    if match < 0.5 or not 0.002 < lag < 0.2:
        print(f'{render}: audio lag {lag * 1000:+.1f}ms, match {match:.2f}; left as is')
        return
    fd, tmp = tempfile.mkstemp(suffix='.mp4', dir=os.path.dirname(os.path.abspath(render)))
    os.close(fd)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', render, '-itsoffset', f'{-lag:.6f}', '-i', render,
                    '-map', '0:v', '-map', '1:a', '-c', 'copy', '-movflags', '+faststart', tmp], check=True)
    os.replace(tmp, render)
    after, _ = lag_of(render, track, start)
    print(f'{render}: audio lag {lag * 1000:+.1f}ms → {after * 1000:+.1f}ms')


if __name__ == '__main__':
    main()
