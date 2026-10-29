#!/usr/bin/env python3
"""Cut lengths from a music track's hits, so every cut lands on a sound.

Finds the track's onsets (ticks, kicks, hits) and turns them into cut lengths at the
reel's frame rate. A cut starts on an onset once the previous cut has run --min frames,
so a dense roll becomes a 2-3 frame strobe and slowing ticks become a ramp. The last
length is the end hold. It runs to the track's final hit, so the loop restarts on it.

  npm run cuts -- public/audio/track.m4a --out src/config/cuts/track.json
  python3 scripts/cuts_from_track.py public/audio/track.m4a --start 12.4 --end 8
"""
import argparse
import json
import subprocess
import warnings
from pathlib import Path

import librosa
import numpy as np

SR = 44100
HOP = 147  # 1/300 s
warnings.filterwarnings('ignore')


def decode(path: str, start: float) -> np.ndarray:
    """Mono float samples via ffmpeg, the decoder Remotion renders with (others can sit a frame off)."""
    cmd = ['ffmpeg', '-v', 'error', '-ss', str(start), '-i', path, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-']
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('track')
    p.add_argument('--fps', type=float, default=30)
    p.add_argument('--min', type=int, default=2, help='shortest cut in frames (default 2)')
    p.add_argument('--start', type=float, default=0, help='seconds into the track that frame 0 plays (audio.startFrom)')
    p.add_argument('--end', type=float, help='reel length in seconds (default: the last hit, or where the sound stops)')
    p.add_argument('--out', help='write {track, fps, startFrom, lengths} JSON here')
    a = p.parse_args()

    y = decode(a.track, a.start)
    env = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP)
    hits = librosa.onset.onset_detect(onset_envelope=env, sr=SR, hop_length=HOP, units='time') * a.fps

    if a.end:
        end = round(a.end * a.fps)
    else:
        # Where the sound stops (last frame above -45 dBFS); end on the final hit if it's that close.
        win = int(SR / a.fps)
        rms = librosa.feature.rms(y=y, frame_length=win, hop_length=win)[0]
        loud = np.nonzero(20 * np.log10(rms + 1e-9) > -45)[0]
        sound_end = (loud[-1] + 1) if len(loud) else len(rms)
        end = round(hits[-1]) if len(hits) and sound_end - hits[-1] < 0.25 * a.fps else int(sound_end)

    starts = [0]
    for h in hits:
        b = round(h)
        if b - starts[-1] >= a.min and end - b >= a.min:
            starts.append(b)
    lengths = np.diff(starts + [end]).astype(int).tolist()

    print(f'{a.track}: {len(hits)} hits → {len(lengths)} cuts, {end} frames ({end / a.fps:.2f}s)')
    print('lengths:', ' '.join(map(str, lengths)))
    if a.out:
        track = Path(a.track).as_posix()
        track = track.split('public/', 1)[1] if 'public/' in track else track
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps({'track': track, 'fps': a.fps, 'startFrom': a.start, 'lengths': lengths}) + '\n')
        print('wrote', a.out)


if __name__ == '__main__':
    main()
