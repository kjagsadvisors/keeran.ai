#!/usr/bin/env node
// Render one effect: stage.html frames in headless Chrome -> ffmpeg -> mp4 with the clip's own audio.
//
//   node render.mjs <spec.json>                 -> spec.out
//   node render.mjs <spec.json> --still 1.2,2   -> <out>.still-1.2.png ...
//
// Paths in the spec are relative to the spec file.
import { chromium } from "playwright-core";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const opt = (n) => { const i = argv.indexOf("--" + n); return i >= 0 ? argv[i + 1] : null; };
const specPath = path.resolve(argv[0]);
const BASE = path.dirname(specPath);
const spec = JSON.parse(fs.readFileSync(specPath, "utf8"));
const W = 1080, H = 1920, fps = spec.fps || 30;
const work = path.resolve(BASE, spec.work);
const clip = JSON.parse(fs.readFileSync(path.join(work, "clip.json"), "utf8"));
const from = spec.from || 0;
const dur = spec.dur || clip.frames / fps - from;
const frames = Math.round(dur * fps);
const out = path.resolve(BASE, spec.out || `${spec.fx}.mp4`);
fs.mkdirSync(path.dirname(out), { recursive: true });

const CHROME = [process.env.CHROME, "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium", "/usr/bin/google-chrome", "/usr/bin/chromium"].find((p) => p && fs.existsSync(p));
const browser = await chromium.launch({ executablePath: CHROME, headless: true,
  args: ["--allow-file-access-from-files", "--disable-web-security", "--hide-scrollbars", "--force-color-profile=srgb"] });

const load = { ...spec, fps, dur, offset: Math.round(from * fps), frames: clip.frames, track: clip.track,
  work: pathToFileURL(work).href, base: pathToFileURL(BASE).href + "/" };

async function open() {
  const ctx = await browser.newContext({ viewport: { width: W, height: H } });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => console.error("[page error]", e.message));
  page.on("console", (m) => { if (m.type() === "error") console.error("[page]", m.text()); });
  await page.goto(pathToFileURL(path.join(HERE, "stage.html")).href);
  await page.evaluate((s) => window.__load(s), load);
  return page;
}

const still = opt("still");
if (still) {
  const page = await open();
  for (const t of still.split(",").map(Number)) {
    await page.evaluate((i) => window.__seek(i), Math.round(t * fps));
    const file = out.replace(/\.mp4$/, `.still-${t}.jpg`);
    await page.screenshot({ path: file, type: "jpeg", quality: 90 });
    console.log(file);
  }
  await browser.close();
  process.exit(0);
}

const args = ["-v", "error", "-y", "-f", "image2pipe", "-framerate", String(fps), "-c:v", "mjpeg", "-i", "-",
  "-ss", String((clip.start || 0) + from), "-i", clip.clip, "-t", String(dur),
  "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
  "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out];
const ff = spawn("ffmpeg", args, { stdio: ["pipe", "inherit", "inherit"] });
const write = (buf) => new Promise((ok) => (ff.stdin.write(buf) ? ok() : ff.stdin.once("drain", ok)));

const WORKERS = 4;
const pages = await Promise.all(Array.from({ length: WORKERS }, open));
const done = new Map();
let next = 0, flushed = 0;
const t0 = Date.now();
await Promise.all(pages.map(async (page) => {
  while (next < frames) {
    if (next - flushed > 24) { await new Promise((r) => setTimeout(r, 10)); continue; }
    const i = next++;
    await page.evaluate((n) => window.__seek(n), i);
    done.set(i, await page.screenshot({ type: "jpeg", quality: 94 }));
    while (done.has(flushed)) { const b = done.get(flushed); done.delete(flushed); flushed++; await write(b); }
  }
}));
ff.stdin.end();
await new Promise((ok) => ff.on("close", ok));
await browser.close();
console.log(`${out}  ${frames} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
