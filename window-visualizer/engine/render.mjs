#!/usr/bin/env node
// Render a window visualizer project: windows.html frames in headless Chrome -> ffmpeg (picture only; windows.py adds the sound).
//   node render.mjs <project>                 -> <project>/out/picture.mp4
//   node render.mjs <project> --draft         15 fps, quick look at timing
//   node render.mjs <project> --still 2.5,7   PNG frames -> <project>/out/stills/
//   node render.mjs <project> --board         one frame per caption / insert -> <project>/out/board.jpg
// Uses playwright-core from the launch-video skill's engine (npm install there once).
import { createRequire } from "module";
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(path.join(HERE, "..", "..", "launch-video", "engine", "package.json"));
const { chromium } = require("playwright-core");
const argv = process.argv.slice(2);
const opt = (n, d) => { const i = argv.indexOf("--" + n); return i >= 0 && argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[i + 1] : d; };
const PROJ = path.resolve(argv[0]);
const OUT = path.join(PROJ, "out");
const plan = JSON.parse(fs.readFileSync(path.join(PROJ, "plan.json"), "utf8"));
const audio = JSON.parse(fs.readFileSync(path.join(OUT, "audio.json"), "utf8"));
// voiced plans: captions come from the voice's word timings (windows.py analyze writes them)
if (fs.existsSync(path.join(OUT, "captions.json"))) plan.captions = JSON.parse(fs.readFileSync(path.join(OUT, "captions.json"), "utf8"));
const draft = argv.includes("--draft");
const fps = draft ? 15 : 30, workers = Number(opt("workers", 4));
const src = plan.windows && plan.windows.source && plan.windows.source !== "code" ? path.join(PROJ, plan.windows.source) : null;
const tileFiles = src && fs.existsSync(src) ? fs.readdirSync(src).filter((f) => /\.(jpe?g|png|webp)$/i.test(f)).sort() : [];
const CHROME = [process.env.CHROME, "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/usr/bin/google-chrome", "/usr/bin/chromium"].find((p) => p && fs.existsSync(p));
const browser = await chromium.launch({ executablePath: CHROME, args: ["--allow-file-access-from-files", "--hide-scrollbars", "--force-color-profile=srgb", "--autoplay-policy=no-user-gesture-required"] });
const [W, H] = [1080, 1920];
async function open() {
  const page = await browser.newPage({ viewport: { width: W, height: H } });
  page.on("pageerror", (e) => console.error("[page error]", e.message));
  page.on("console", (m) => { if (m.type() === "error") console.error("[page]", m.text()); });
  await page.goto(pathToFileURL(path.join(HERE, "windows.html")).href);
  const info = await page.evaluate((d) => window.__load(d), { plan, audio, base: pathToFileURL(PROJ).href + "/", tileFiles });
  return { page, info };
}
const shot = async (page, t, type = "jpeg") => { await page.evaluate((t) => window.__seek(t), t); return page.screenshot(type === "png" ? { type } : { type, quality: 94 }); };
const run = (cmd, args) => { const r = spawnSync(cmd, args, { stdio: "inherit" }); if (r.status) throw new Error(cmd + " failed"); };

const { page, info } = await open();
const D = info.duration;
if (opt("still")) {
  const dir = path.join(OUT, "stills"); fs.mkdirSync(dir, { recursive: true });
  for (const t of opt("still").split(",").map(Number)) { const f = path.join(dir, `t${t.toFixed(2)}.png`); fs.writeFileSync(f, await shot(page, t, "png")); console.log(f); }
} else if (argv.includes("--board")) {
  const dir = path.join(OUT, "board"); fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir, { recursive: true });
  const at = info.scenes.map((s) => Math.min(D - 0.05, (s.start + s.end) / 2));
  const cols = Math.min(6, at.length), rows = Math.ceil(at.length / cols);
  for (let i = 0; i < cols * rows; i++) fs.writeFileSync(path.join(dir, `${String(i).padStart(3, "0")}.jpg`), await shot(page, at[Math.min(i, at.length - 1)]));
  run("ffmpeg", ["-v", "error", "-y", "-i", path.join(dir, "%03d.jpg"), "-vf", `scale=270:-1,tile=${cols}x${rows}:padding=6:color=0x222222`, "-frames:v", "1", path.join(OUT, "board.jpg")]);
  console.log(path.join(OUT, "board.jpg"));
} else {
  // windows switch on and off between frames, so no motion blur: every frame is one moment
  const total = Math.round(D * fps), per = Math.ceil(total / workers), segs = [];
  let done = 0; const t0 = Date.now();
  const pages = [page]; for (let k = 1; k < workers; k++) pages.push((await open()).page);
  await Promise.all(pages.map(async (pg, k) => {
    const seg = path.join(OUT, `.seg${k}.mp4`); segs[k] = seg;
    const ff = spawn("ffmpeg", ["-v", "error", "-y", "-f", "image2pipe", "-framerate", String(fps), "-c:v", "mjpeg", "-i", "-",
      "-c:v", "libx264", "-preset", draft ? "veryfast" : "medium", "-crf", draft ? "23" : "16", "-pix_fmt", "yuv420p", "-r", String(fps), seg]);
    const closed = new Promise((ok, bad) => ff.on("close", (c) => (c === 0 ? ok() : bad(new Error("ffmpeg failed")))));
    const put = async (buf) => { if (!ff.stdin.write(buf)) await new Promise((ok) => ff.stdin.once("drain", ok)); };
    for (let f = k * per; f < Math.min(total, (k + 1) * per); f++) {
      await put(await shot(pg, f / fps));
      if (++done % 60 === 0) process.stdout.write(`\r  ${done}/${total} frames  ${((Date.now() - t0) / 1000).toFixed(0)} s`);
    }
    ff.stdin.end(); await closed;
  }));
  process.stdout.write(`\r  ${total}/${total} frames  ${((Date.now() - t0) / 1000).toFixed(0)} s\n`);
  const list = path.join(OUT, ".segs.txt");
  fs.writeFileSync(list, segs.map((s) => `file '${s}'`).join("\n"));
  run("ffmpeg", ["-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", list, "-c", "copy", path.join(OUT, "picture.mp4")]);
  segs.forEach((s) => fs.rmSync(s, { force: true })); fs.rmSync(list, { force: true });
  console.log(path.join(OUT, "picture.mp4"));
}
await browser.close();
