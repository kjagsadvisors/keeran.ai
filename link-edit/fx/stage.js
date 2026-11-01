// link-edit effects. Every effect is a pure function of time, so renders are deterministic.
// Layers, back to front: #bg (raw frame) · #back · #person (cut-out) · #front. #cam moves them together.
const W = 1080, H = 1920;
const $ = (s) => document.querySelector(s);
const bg = $("#bg"), person = $("#person"), back = $("#back"), front = $("#front"), cam = $("#cam");
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const seg = (t, a, b) => clamp((t - a) / (b - a));
const lerp = (a, b, u) => a + (b - a) * u;
const expo = (u) => (u >= 1 ? 1 : 1 - Math.pow(2, -10 * u));
const cubic = (u) => 1 - Math.pow(1 - u, 3);
const backOut = (u, s = 1.4) => { const v = u - 1; return v * v * ((s + 1) * v + s) + 1; };
const inOut = (u) => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2);
const el = (tag, css, html) => { const e = document.createElement(tag); if (css) e.style.cssText = css; if (html != null) e.innerHTML = html; return e; };

let S = null, FX = null;
const url = (p) => new URL(p, S.base).href;
const head = (t) => { const i = clamp(Math.round(t * S.fps) + (S.offset || 0), 0, S.track.length - 1); return { x: S.track[i][0], y: S.track[i][1] }; };

// Scale the speaker down from the bottom edge so more of the effect shows around them.
const placePerson = (scale, dy = 0, dx = 0) => { person.style.transform = `translate(${dx}px,${dy}px) scale(${scale})`; };
// Where a point of the raw frame lands after placePerson.
const mapPt = (p, scale, dy = 0, dx = 0) => ({ x: 540 + (p.x - 540) * scale + dx, y: H + (p.y - H) * scale + dy });

const EFFECTS = {};

// /logo-wall <domain> ------ context.dev brand API: logo + colours
EFFECTS["logo-wall"] = {
  init(d) {
    const color = d.color, ink = d.ink || "#050505";
    const flood = el("div", `position:absolute;inset:0;background:${color};overflow:hidden`);
    flood.id = "flood";
    flood.appendChild(el("div", "position:absolute;inset:0;background:radial-gradient(70% 45% at 50% 42%,rgba(255,255,255,.34),rgba(255,255,255,0) 70%)"));
    const rows = d.rows || 9, rh = H / rows + 4, lh = rh * 0.68, lw = lh * d.aspect;
    this.rows = [];
    for (let r = 0; r < rows; r++) {
      const row = el("div", `position:absolute;left:0;top:${r * (H / rows) + (rh - lh) / 2 - 2}px;height:${lh}px;width:${(lw + 90) * 6}px;display:flex;gap:90px;will-change:transform`);
      for (let i = 0; i < 6; i++) {
        row.appendChild(el("div", `flex:none;width:${lw}px;height:${lh}px;background:${ink};
          -webkit-mask:url('${url(d.logo)}') center/contain no-repeat;mask:url('${url(d.logo)}') center/contain no-repeat`));
      }
      flood.appendChild(row);
      this.rows.push(row);
    }
    this.lw = lw + 90;
    back.appendChild(flood);
    this.flood = flood;
    this.T = d.in ?? 0.42;
    this.ps = d.personScale ?? 1;
    this.dy = d.personY ?? 0;
  },
  draw(t) {
    const u = seg(t, this.T, this.T + 0.34), e = expo(u);
    const c = mapPt(head(t), 1);
    this.flood.style.clipPath = `circle(${e * 1500}px at ${c.x}px ${c.y + 280}px)`;
    this.rows.forEach((row, r) => {
      const dir = r % 2 ? 1 : -1;
      const inn = expo(seg(t, this.T + r * 0.018, this.T + 0.6 + r * 0.018));
      const offset = -this.lw * 1.5 + dir * (this.lw * 1.3 * (1 - inn)) + dir * (t - this.T) * 46 + (r % 2 ? this.lw * 0.5 : 0);
      row.style.transform = `translate3d(${offset}px,0,0)`;
    });
    const pop = backOut(seg(t, this.T, this.T + 0.42), 2.2);
    const s = lerp(1, this.ps, e) * (t < this.T ? 1 : lerp(0.94, 1, pop));
    placePerson(s, lerp(0, this.dy, e));
    person.style.filter = u > 0 ? "drop-shadow(0 18px 46px rgba(0,0,0,.42)) contrast(1.05)" : "none";
    cam.style.transform = `scale(${1 + 0.03 * cubic(seg(t, 0, 3))})`;
  },
};

// /site-spin <domain> ------ context.dev map + scrape: real pages orbit the speaker
EFFECTS["site-spin"] = {
  init(d) {
    const mk = () => {
      const wrap = el("div", "position:absolute;inset:0;perspective:1500px;perspective-origin:50% 46%");
      const ring = el("div", `position:absolute;left:50%;top:${d.ringY ?? 56}%;transform-style:preserve-3d;transform:rotateX(${d.tilt ?? -17}deg) rotateZ(-7deg)`);
      wrap.appendChild(ring);
      return { wrap, ring };
    };
    this.b = mk(); this.f = mk();
    back.appendChild(el("div", "position:absolute;inset:0;background:radial-gradient(70% 46% at 50% 40%,#2a3358,#0a0b12 74%)"));
    back.lastChild.id = "glow";
    back.appendChild(this.b.wrap); front.appendChild(this.f.wrap);
    this.n = d.cards.length;
    this.cw = d.cardW ?? 500; this.ch = this.cw * 1.4;
    const card = (src) => el("div", `position:absolute;left:${-this.cw / 2}px;top:${-this.ch / 2}px;width:${this.cw}px;height:${this.ch}px;border-radius:26px;overflow:hidden;background:#fff;
      box-shadow:0 24px 70px rgba(0,0,0,.55);backface-visibility:visible;will-change:transform`, `<img src="${url(src)}" style="width:100%;height:100%;object-fit:cover;object-position:top;display:block">`);
    this.cards = d.cards.map((src) => {
      const a = card(src), b = card(src);
      this.b.ring.appendChild(a); this.f.ring.appendChild(b);
      return { a, b };
    });
    this.T = d.in ?? 0.32;
    this.R = d.radius ?? 620;
    this.ps = d.personScale ?? 1;
    this.dy = d.personY ?? 0;
  },
  draw(t) {
    const tt = Math.max(0, t - this.T), on = expo(seg(t, this.T, this.T + 0.6));
    const theta = -5.0 * (1 - Math.exp(-2.1 * tt)) - 0.42 * tt + 0.5;
    bg.style.filter = `brightness(${lerp(1, 0.2, on)}) blur(${on * 16}px) saturate(${lerp(1, 0.5, on)})`;
    $("#glow").style.opacity = on;
    this.cards.forEach((c, i) => {
      const a = theta + (i / this.n) * Math.PI * 2;
      const R = this.R * on + 40, z = Math.cos(a) * R, x = Math.sin(a) * R;
      const isFront = z > 0;
      const face = a + (isFront ? 0 : Math.PI);
      const scale = lerp(0.55, 1, on);
      const dim = isFront ? 1 : lerp(0.72, 1, clamp(1 + z / R));
      const tf = `translate3d(${x}px,0,${z}px) rotateY(${face}rad) scale(${scale})`;
      const show = isFront ? c.b : c.a, hide = isFront ? c.a : c.b;
      show.style.transform = tf; show.style.opacity = t < this.T ? 0 : isFront ? seg(on, 0.5, 0.9) : 1; show.style.filter = `brightness(${dim})`;
      hide.style.opacity = 0;
    });
    placePerson(lerp(1, this.ps, on), lerp(0, this.dy, on));
    person.style.filter = on > 0 ? "drop-shadow(0 0 60px rgba(150,170,255,.25))" : "none";
    cam.style.transform = `scale(${1 + 0.04 * cubic(seg(t, 0, 3))})`;
  },
};

// /news-hit <topic> ------ context.dev news search + scrape: the real article, the line highlighted
EFFECTS["news-hit"] = {
  init(d) {
    this.d = d;
    const page = el("div", `position:absolute;left:0;top:0;width:1000px;height:1400px;background:#fff;transform-origin:0 0;will-change:transform;
      box-shadow:0 40px 120px rgba(0,0,0,.45)`, `<img src="${url(d.shot)}" style="width:100%;display:block">`);
    this.marks = (d.marks || []).map((m) => {
      const k = el("div", `position:absolute;left:${m.x}px;top:${m.y}px;width:${m.w}px;height:${m.h}px;background:${d.mark || "#ffd84d"};mix-blend-mode:multiply;transform-origin:0 50%;transform:scaleX(0);border-radius:4px`);
      page.appendChild(k);
      return k;
    });
    this.page = page;
    back.appendChild(el("div", "position:absolute;inset:0;background:#f3f0ea"));
    back.lastChild.id = "paper";
    back.appendChild(page);
    this.T = d.in ?? 0.3;
    this.ps = d.personScale ?? 0.82;
    this.dy = d.personY ?? 120;
  },
  draw(t) {
    const d = this.d, T = this.T;
    const u = expo(seg(t, T, T + 0.42));
    const z = lerp(d.zoom ?? 1.75, (d.zoom ?? 1.75) * 1.06, cubic(seg(t, T, T + 3)));
    const fx = d.focus?.x ?? 40, fy = d.focus?.y ?? 268;
    const px = 40 - fx * z, py = lerp(H + 100, (d.top ?? 190) - fy * z, u);
    this.page.style.transform = `translate(${px}px,${py}px) rotate(${lerp(4, -1.6, u)}deg) scale(${z})`;
    $("#paper").style.opacity = u;
    this.marks.forEach((k, i) => {
      const a = T + 0.5 + i * 0.26;
      k.style.transform = `scaleX(${inOut(seg(t, a, a + 0.3))})`;
    });
    placePerson(lerp(1, this.ps, u), lerp(0, this.dy, u));
    person.style.filter = u > 0 ? "drop-shadow(0 -6px 44px rgba(0,0,0,.34))" : "none";
    cam.style.transform = `scale(${1 + 0.02 * cubic(seg(t, 0, 3))})`;
  },
};

// /price-tag <url> ------ context.dev scrape with a JSON schema: real prices on real strings
EFFECTS["price-tag"] = {
  init(d) {
    this.d = d;
    const light = d.color || "#d97757";
    back.appendChild(el("div", "position:absolute;inset:0;background:radial-gradient(85% 55% at 50% 38%,#4a3f35,#17120f 78%)"));
    back.lastChild.id = "shade";
    this.tags = d.tags.map((g, i) => {
      const hang = el("div", `position:absolute;left:${g.x}px;top:-40px;width:0;height:${g.len}px;transform-origin:0 0;will-change:transform`);
      hang.appendChild(el("div", `position:absolute;left:-1.5px;top:0;width:3px;height:${g.len}px;background:linear-gradient(#e9e2d4,#cbbfa9);box-shadow:0 2px 8px rgba(0,0,0,.4)`));
      const w = g.big ? 400 : 290, h = g.big ? 250 : 180;
      const hot = g.big;
      const tag = el("div", `position:absolute;left:${-w / 2}px;top:${g.len - 26}px;width:${w}px;height:${h}px;border-radius:26px;
        background:${hot ? light : "#f8f3e9"};color:${hot ? "#fff" : "#1d1b18"};box-shadow:0 22px 50px rgba(0,0,0,.42);box-sizing:border-box;padding:${g.big ? 58 : 46}px 0 0;text-align:center`,
        `<div style="position:absolute;left:50%;top:14px;width:22px;height:22px;margin-left:-11px;border-radius:50%;background:#2a2622;box-shadow:inset 0 2px 3px rgba(0,0,0,.6)"></div>
         <div style="font-weight:600;font-size:${g.big ? 42 : 32}px;letter-spacing:-.01em;opacity:.78;line-height:1">${g.name}</div>
         <div style="font-weight:800;font-size:${g.big ? 112 : 72}px;letter-spacing:-.045em;line-height:1.08;margin-top:4px">${g.price}<span style="font-size:.34em;font-weight:600;letter-spacing:-.01em;opacity:.7">/mo</span></div>`);
      hang.appendChild(tag);
      (g.behind ? back : front).appendChild(hang);
      return { hang, g, at: (d.in ?? 0.3) + i * (d.gap ?? 0.26), side: i % 2 ? 1 : -1 };
    });
    this.ps = d.personScale ?? 0.9;
    this.dy = d.personY ?? 60;
    this.T = d.in ?? 0.3;
  },
  draw(t) {
    const on = expo(seg(t, this.T - 0.1, this.T + 0.3));
    $("#shade").style.opacity = on;
    this.tags.forEach(({ hang, g, at, side }) => {
      const tau = t - at;
      const drop = backOut(seg(tau, 0, 0.42), 1.5);
      const y = lerp(-g.len - 280, 0, drop);
      const swing = tau > 0 ? side * 13 * Math.exp(-1.5 * tau) * Math.cos(6.4 * tau) : 0;
      hang.style.transform = `translateY(${y}px) rotate(${swing + (g.tilt || 0)}deg)`;
      hang.style.opacity = tau < 0 ? 0 : 1;
    });
    placePerson(lerp(1, this.ps, on), lerp(0, this.dy, on));
    cam.style.transform = `scale(${1 + 0.025 * cubic(seg(t, 0, 3))})`;
  },
};

// /brand-caps <domain> ------ context.dev styleguide: captions in the site's real font, colours and button
EFFECTS["brand-caps"] = {
  async init(d) {
    this.d = d;
    const sg = d.styleguide;
    const face = new FontFace("BrandFont", `url('${url(d.font)}')`, { weight: "100 900" });
    await face.load(); document.fonts.add(face);
    const page = el("div", `position:absolute;inset:0;background:${sg.colors.background}`);
    page.id = "site";
    if (d.grid) page.style.backgroundImage = `linear-gradient(${d.grid} 2px,transparent 2px),linear-gradient(90deg,${d.grid} 2px,transparent 2px)`, page.style.backgroundSize = "180px 180px";
    back.appendChild(page);
    const h1 = sg.typography.headings.h1;
    const ratio = parseFloat(h1.letterSpacing) / parseFloat(h1.fontSize);
    const fs = d.size ?? 188;
    this.words = d.lines.flatMap((ln, r) => ln.split(" ").map((w, i) => ({ w, r, i })));
    let idx = 0;
    const box = el("div", `position:absolute;left:0;right:0;top:${d.top ?? 150}px;text-align:center;font-family:BrandFont,sans-serif;font-weight:${h1.fontWeight >= 500 ? h1.fontWeight : 500};font-size:${fs}px;line-height:.98;letter-spacing:${ratio}em;color:${sg.colors.text}`);
    d.lines.forEach((ln, r) => {
      const row = el("div", "white-space:nowrap");
      ln.split(" ").forEach((w, i) => {
        const hot = (d.accent || []).includes(w);
        const s = el("span", `display:inline-block;margin:0 .13em;will-change:transform,opacity${hot ? ";color:" + sg.colors.accent : ""}`, w);
        row.appendChild(s); this.words[idx++].el = s;
      });
      box.appendChild(row);
    });
    back.appendChild(box);
    const b = sg.components.button.primary;
    this.btn = el("div", `position:absolute;left:50%;top:${d.btnY ?? 1610}px;transform:translateX(-50%);padding:32px 62px;background:${b.backgroundColor};color:${b.color};border-radius:${b.borderRadius};border:${b.borderColor ? "3px solid " + b.borderColor : "none"};
      font-family:BrandFont,sans-serif;font-weight:${b.fontWeight};font-size:50px;white-space:nowrap;box-shadow:0 22px 50px rgba(0,0,0,.3)`, d.button || "");
    if (d.button) front.appendChild(this.btn);
    this.T = d.in ?? 0.3;
    this.gap = d.gap ?? 0.17;
    this.ps = d.personScale ?? 0.86;
    this.dy = d.personY ?? 60;
  },
  draw(t) {
    const T = this.T, u = expo(seg(t, T, T + 0.3));
    const ax = 540, ay = 980;
    $("#site").style.clipPath = `circle(${u * 1600}px at ${ax}px ${ay}px)`;
    this.words.forEach((w, i) => {
      const a = T + 0.14 + i * this.gap, k = seg(t, a, a + 0.24);
      w.el.style.opacity = k > 0 ? 1 : 0;
      w.el.style.transform = `translateY(${lerp(46, 0, expo(k))}px) scale(${lerp(1.16, 1, expo(k))})`;
    });
    if (this.btn.parentNode) {
      const a = T + 0.2 + this.words.length * this.gap, k = backOut(seg(t, a, a + 0.34), 1.7);
      this.btn.style.opacity = t < a ? 0 : 1;
      this.btn.style.transform = `translateX(-50%) scale(${lerp(0.7, 1, k)})`;
    }
    placePerson(lerp(1, this.ps, u), lerp(0, this.dy, u));
    person.style.filter = u > 0 ? "drop-shadow(0 10px 40px rgba(0,0,0,.2))" : "none";
    cam.style.transform = `scale(${1 + 0.02 * cubic(seg(t, 0, 3))})`;
  },
};

// Plain clip, no effect: useful as a before shot.
EFFECTS["raw"] = { init() {}, draw() {} };

window.__load = async (spec) => {
  S = spec;
  FX = EFFECTS[spec.fx];
  if (!FX) throw new Error("unknown effect " + spec.fx);
  await FX.init(spec.data || {});
  await document.fonts.ready;
  await Promise.all([...document.images].map((i) => (i.src ? i.decode().catch(() => {}) : null)));
  return true;
};

const pad = (n) => String(n).padStart(5, "0");
const setImg = (img, src) => new Promise((ok) => {
  img.onload = () => ok(); img.onerror = () => ok(); img.src = src;
});

window.__seek = async (i) => {
  const n = clamp(i + 1 + (S.offset || 0), 1, S.frames);
  await Promise.all([setImg(bg, `${S.work}/frames/${pad(n)}.jpg`), setImg(person, `${S.work}/person/${pad(n)}.webp`)]);
  FX.draw(i / S.fps);
  await Promise.all([bg.decode().catch(() => {}), person.decode().catch(() => {})]);
};
