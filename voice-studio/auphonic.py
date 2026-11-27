#!/usr/bin/env python3
"""
Clean voice takes with Auphonic (leveler, loudness, noise reduction), many files in ONE production.

Auphonic bills a 3-minute minimum per production, so takes are joined end to end,
processed once, and split back at their exact sample boundaries. Timing is never
changed: silence/filler cutting stay off, so each output is the same length as its input.

Usage:
    python3 auphonic.py take01.wav take02.wav ...            # → take01.auph.wav, ...
    python3 auphonic.py *.wav --production <uuid>            # re-download a finished production, no new charge
    python3 auphonic.py *.wav --loudness -16 --denoise 12 --denoise-method dynamic
    python3 auphonic.py *.wav --preset "My voice preset"     # use your Auphonic preset instead
    python3 auphonic.py *.wav --dry-run                      # join + split locally, no API call

Needs your Auphonic API key (Auphonic → Account Settings → API Key). Looked up in order:
    1. AUPHONIC_API_KEY environment variable
    2. macOS Keychain, service "auphonic-api-key" (recommended: encrypted, works in every session).
       Store it once; the -w at the end makes `security` prompt, so the key never lands in shell history:
           security add-generic-password -a "$USER" -s auphonic-api-key -U -w
    3. AUPHONIC_API_KEY=... in a .env file in the current folder

Standard library only (plus ffmpeg on PATH).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid as uuidlib
from pathlib import Path

API = "https://auphonic.com/api"
SR = 48000
STATUS_DONE, STATUS_ERROR = 3, 2


KEYCHAIN_SERVICE = os.environ.get("AUPHONIC_KEYCHAIN_SERVICE", "auphonic-api-key")
KEY_HELP = (
    "No Auphonic API key found. Store it once in your macOS Keychain (you'll be prompted for it):\n"
    f'    security add-generic-password -a "$USER" -s {KEYCHAIN_SERVICE} -U -w\n'
    "or set AUPHONIC_API_KEY in the environment or in a .env file in the current folder."
)


def load_key():
    key = os.environ.get("AUPHONIC_API_KEY")
    if key:
        return key.strip()
    if sys.platform == "darwin" and shutil.which("security"):
        r = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    for env in (Path.cwd() / ".env", Path(__file__).resolve().parent / ".env"):
        if env.exists():
            for line in env.read_text().splitlines():
                if line.strip().startswith("AUPHONIC_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def request(method, path, key, body=None, content_type=None, timeout=120):
    url = path if path.startswith("http") else f"{API}{path}"
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"bearer {key}")
    if content_type:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:600]
        sys.exit(f"Auphonic {method} {url} failed: HTTP {e.code} {detail}")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def download(url, key, timeout=600):
    """Result files redirect to a signed storage URL that must NOT get our Authorization header."""
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"bearer {key}")
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
            with urllib.request.urlopen(e.headers["Location"], timeout=timeout) as r:
                return r.read()
        sys.exit(f"Auphonic download failed: HTTP {e.code} {e.read().decode('utf-8', 'replace')[:300]}")


def api_json(method, path, key, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    raw = request(method, path, key, body, "application/json" if body else None)
    data = json.loads(raw)
    if data.get("error_code") or data.get("status_code", 200) >= 400:
        sys.exit(f"Auphonic error: {data.get('error_message') or data}")
    return data.get("data", data)


def upload(uuid, key, wav_path):
    boundary = uuidlib.uuid4().hex
    head = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"input_file\"; filename=\"{wav_path.name}\"\r\n"
        "Content-Type: audio/wav\r\n\r\n"
    ).encode()
    body = head + wav_path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    request("POST", f"/production/{uuid}/upload.json", key, body, f"multipart/form-data; boundary={boundary}", timeout=600)


def samples(path):
    """Length in samples at 48 kHz mono (exact, by decoding)."""
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
        capture_output=True, check=True,
    ).stdout
    return len(out) // 2


def join(inputs, dest):
    """Concatenate inputs as 48 kHz mono PCM, end to end, no gaps."""
    pcm = b"".join(
        subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(p), "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
            capture_output=True, check=True,
        ).stdout
        for p in inputs
    )
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-", "-c:a", "pcm_s16le", str(dest)],
        input=pcm, check=True,
    )


def _f32(path):
    import numpy as np
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def find_offset(joined, processed, lengths):
    """Where the joined takes start inside Auphonic's output.

    Free-plan productions get an Auphonic jingle added (6.4 s at the start in practice), so the
    output can be longer than the input. Locate the first take by cross-correlation, then check
    every take lands at the same offset (r ≥ 0.5) before trusting the split.
    """
    try:
        import numpy as np
    except ImportError:
        sys.exit("Auphonic's output is longer than the input (free-plan jingle?). Install numpy to auto-align: pip install numpy")
    j, q = _f32(joined), _f32(processed)

    def locate(seg, hay):
        n = len(hay) + len(seg)
        c = np.fft.irfft(np.fft.rfft(hay, n) * np.conj(np.fft.rfft(seg, n)), n)[: len(hay) - len(seg) + 1]
        k = int(np.argmax(c))
        r = float(np.dot(hay[k:k + len(seg)], seg) / (np.linalg.norm(hay[k:k + len(seg)]) * np.linalg.norm(seg) + 1e-12))
        return k, r

    # anchor on the loudest second of the first take
    first = j[: lengths[0]]
    w = SR
    start = max(range(0, max(1, len(first) - w), SR // 10), key=lambda s: float((first[s:s + w] ** 2).sum()))
    k, r = locate(first[start:start + w], q)
    offset = k - start
    if r < 0.5:
        sys.exit(f"Couldn't find the takes inside Auphonic's output (best match r={r:.2f}).")
    pos, bad = 0, []
    for i, n in enumerate(lengths):
        seg_in = j[pos:pos + n]
        seg_out = q[offset + pos: offset + pos + n]
        if len(seg_out) == n:
            r = float(np.dot(seg_in, seg_out) / (np.linalg.norm(seg_in) * np.linalg.norm(seg_out) + 1e-12))
            if r < 0.5:
                bad.append(f"take {i + 1} r={r:.2f}")
        pos += n
    if bad:
        sys.exit("Takes don't line up after aligning (" + ", ".join(bad) + "). Not splitting.")
    return offset


def split(processed, inputs, lengths, outputs, joined=None):
    pcm = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(processed), "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
        capture_output=True, check=True,
    ).stdout
    total = sum(lengths)
    got = len(pcm) // 2
    if abs(got - total) > SR // 100 and joined is not None:
        offset = find_offset(joined, processed, lengths)
        print(f"Auphonic output is {got / SR:.3f}s for {total / SR:.3f}s of takes; takes start at {offset / SR:.3f}s "
              f"(free-plan jingle?). Trimmed to the takes.", file=sys.stderr)
        pcm = pcm[offset * 2:(offset + total) * 2]
    elif abs(got - total) > SR // 100:
        sys.exit(f"Processed audio is {got / SR:.3f}s but the takes total {total / SR:.3f}s.")
    pos = 0
    for n, out in zip(lengths, outputs):
        chunk = pcm[pos * 2:(pos + n) * 2]
        chunk += b"\x00\x00" * (n - len(chunk) // 2)  # pad if Auphonic came back a few samples short
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-", "-c:a", "pcm_s16le", str(out)],
            input=chunk, check=True,
        )
        pos += n


def main():
    ap = argparse.ArgumentParser(description="Clean voice takes with Auphonic in one production.")
    ap.add_argument("inputs", nargs="+", help="Audio files, in order")
    ap.add_argument("--suffix", default=".auph", help="Output name suffix before .wav (default .auph)")
    ap.add_argument("--title", default="Voice Studio takes")
    ap.add_argument("--preset", help="Auphonic preset UUID or name (overrides the settings below)")
    ap.add_argument("--loudness", type=int, default=-16, help="Loudness target LUFS (default -16)")
    ap.add_argument("--maxpeak", type=float, default=-1.5, help="True peak limit dBTP (default -1.5)")
    ap.add_argument("--denoise", type=int, default=12, help="Noise reduction dB, -1 = off (default 12)")
    ap.add_argument("--denoise-method", default="dynamic", choices=["classic", "dynamic", "speech_isolation", "static"])
    ap.add_argument("--deverb", type=int, default=-1, help="Reverb reduction dB, -1 = off (default off)")
    ap.add_argument("--debreath", type=int, default=-1, help="Breath reduction dB, -1 = off (default off)")
    ap.add_argument("--no-leveler", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="Join and split locally without calling Auphonic")
    ap.add_argument("--production", help="Reuse a finished production (download + split only, no new charge). "
                                         "Pass the same inputs in the same order.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg is required.")
    inputs = [Path(p).resolve() for p in args.inputs]
    for p in inputs:
        if not p.exists():
            sys.exit(f"Missing input: {p}")
    outputs = [p.with_name(p.stem + args.suffix + ".wav") for p in inputs]
    lengths = [samples(p) for p in inputs]
    minutes = sum(lengths) / SR / 60

    key = None if args.dry_run else load_key()
    if not args.dry_run and not key:
        sys.exit(KEY_HELP)

    with tempfile.TemporaryDirectory() as tmp:
        joined = Path(tmp) / "takes.wav"
        join(inputs, joined)
        if args.dry_run:
            processed, production = joined, None
        elif args.production:
            production = args.production
            info = api_json("GET", f"/production/{production}.json", key)
            if info.get("status") != STATUS_DONE:
                sys.exit(f"Production {production} isn't done yet ({info.get('status_string')}).")
        else:
            payload = {"metadata": {"title": args.title}, "output_files": [{"format": "wav"}]}
            if args.preset:
                payload["preset"] = args.preset
            else:
                payload["algorithms"] = {
                    "filtering": True,
                    "leveler": not args.no_leveler,
                    "normloudness": True,
                    "loudnesstarget": args.loudness,
                    "maxpeak": args.maxpeak,
                    "denoise": args.denoise != -1,
                    "denoisemethod": args.denoise_method,
                    "denoiseamount": max(args.denoise, 0) if args.denoise != -1 else -1,
                    "deverbamount": args.deverb,
                    "debreathamount": args.debreath,
                    "silence_cutter": False,
                    "filler_cutter": False,
                    "cough_cutter": False,
                    "music_cutter": False,
                }
            production = api_json("POST", "/productions.json", key, payload)["uuid"]
            print(f"Production {production}: uploading {minutes:.1f} min of audio…", file=sys.stderr)
            upload(production, key, joined)
            api_json("POST", f"/production/{production}/start.json", key)
            started = time.time()
            while True:
                time.sleep(5)
                info = api_json("GET", f"/production/{production}.json", key)
                status = info.get("status")
                if status == STATUS_DONE:
                    break
                if status == STATUS_ERROR:
                    sys.exit(f"Auphonic production failed: {info.get('error_message') or info.get('status_string')}")
                if time.time() - started > 1200:
                    sys.exit(f"Timed out waiting for production {production} (last status: {info.get('status_string')}).")
                print(f"  {info.get('status_string', status)}…", file=sys.stderr)
        if not args.dry_run:
            print(f"Production {production} done. Downloading (reuse later with --production {production})…", file=sys.stderr)
            files = info.get("output_files") or []
            url = next((f.get("download_url") for f in files if f.get("format", "").startswith("wav")), None) or (files[0].get("download_url") if files else None)
            if not url:
                sys.exit("Production finished but returned no output file.")
            processed = Path(tmp) / "processed.wav"
            processed.write_bytes(download(url, key))
        split(processed, inputs, lengths, outputs, joined=joined)

    summary = {
        "production": production,
        "minutes": round(minutes, 2),
        "billed_minutes_estimate": None if args.dry_run else round(max(3.0, minutes), 2),
        "outputs": [str(o) for o in outputs],
    }
    print(json.dumps(summary, indent=2) if args.json else
          f"{'Dry run: ' if args.dry_run else ''}{len(outputs)} takes → *{args.suffix}.wav ({minutes:.1f} min"
          f"{'' if args.dry_run else f', production {production}'})")


if __name__ == "__main__":
    main()
