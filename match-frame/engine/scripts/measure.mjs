#!/usr/bin/env node
// Measure a match-frame reel: cut lengths, mean luma per cut, and pairs that don't flip.
// Usage: npm run measure -- out/match-frame.mp4 [--threshold 6]

import { execFileSync } from 'node:child_process';

const args = process.argv.slice(2);
const file = args.find((a) => !a.startsWith('--')) ?? 'out/match-frame.mp4';
const ti = args.indexOf('--threshold');
const threshold = ti >= 0 ? Number(args[ti + 1]) : 6;

const fps = (() => {
  const r = execFileSync('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate', '-of', 'csv=p=0', file])
    .toString()
    .trim();
  const [n, d] = r.split('/').map(Number);
  return n / (d || 1);
})();

const W = 36;
const H = 64;
const raw = execFileSync('ffmpeg', ['-v', 'error', '-i', file, '-vf', `scale=${W}:${H},format=gray`, '-f', 'rawvideo', '-'], {
  maxBuffer: 1 << 30,
});
const N = W * H;
const frames = [];
for (let i = 0; i + N <= raw.length; i += N) frames.push(raw.subarray(i, i + N));

const diff = (a, b) => {
  let s = 0;
  for (let k = 0; k < N; k++) s += Math.abs(a[k] - b[k]);
  return s / N;
};
const luma = (f) => Math.round(f.reduce((s, v) => s + v, 0) / N);

const starts = [0];
for (let i = 1; i < frames.length; i++) if (diff(frames[i], frames[i - 1]) > threshold) starts.push(i);
const cuts = starts.map((s, i) => ({ from: s, frames: (starts[i + 1] ?? frames.length) - s, luma: luma(frames[s]) }));

console.log(`${file}: ${frames.length} frames @ ${fps}fps (${(frames.length / fps).toFixed(2)}s), ${cuts.length} cuts`);
console.log(`lengths: ${cuts.map((c) => c.frames).join(' ')}`);
console.log(`luma:    ${cuts.map((c) => c.luma).join(' ')}`);

// Adjacent cuts with a small luma change weaken the strobe. Report them by cut number.
const flat = cuts.slice(1).flatMap((c, i) => (Math.abs(c.luma - cuts[i].luma) < 40 ? [`${i + 1}→${i + 2} (${cuts[i].luma}→${c.luma})`] : []));
console.log(flat.length ? `weak flips (|Δluma| < 40): ${flat.join(', ')}` : 'every adjacent cut flips luma by 40+');
const flashes = cuts.filter((c) => c.frames < fps / 3).length;
console.log(`cuts shorter than 1/3s: ${flashes} of ${cuts.length}`);
