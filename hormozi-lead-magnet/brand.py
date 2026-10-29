"""Restyle a lead magnet to the owner's brand, measured from their own website.

  python3 brand.py <dir> <url>           measure <url>, save <dir>/brand/ and write the brand into <dir>/magnet.json
  python3 brand.py <dir> <url> --dry     measure and report only

What it measures, in headless Chrome (no installs beyond Google Chrome):
  colours   page background, text, and the main button (the accent); falls back to theme-color, then the most-used
            saturated colour
  fonts     heading and body families, heading weight and letter-spacing. Google Fonts are linked; the site's own
            font files are saved to brand/fonts/ and embedded (the owner's own fonts, for the owner's own page)
  shape     button and card corner radius (sharp, rounded or pill)
  logo      the header logo (image or inline SVG, colours resolved), saved to brand/logo.*
  name      og:site_name or the page title

It also saves brand/site.png and brand/site-mobile.png. Compare them with out/shot.png after building; fix anything
that's off by editing "brand" in magnet.json. Never use a brand the owner doesn't own.
"""
import base64, colorsys, html, json, os, re, subprocess, sys, tempfile, urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from magnet import chrome, ink_on  # noqa: E402

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/131.0.0.0 Safari/537.36")
GENERIC = {"system-ui", "-apple-system", "blinkmacsystemfont", "segoe ui", "ui-sans-serif", "ui-serif", "ui-monospace",
           "sans-serif", "serif", "monospace", "cursive", "fantasy", "inherit", "initial", "apple color emoji",
           "segoe ui emoji", "segoe ui symbol", "noto color emoji", "emoji", "math", "fangsong"}
SYSTEM = {"helvetica", "helvetica neue", "arial", "georgia", "times", "times new roman", "verdana", "tahoma",
          "trebuchet ms", "courier new", "sf pro display", "sf pro text", "-apple-system"}

# Runs inside the mirrored page. Measured from computed styles and layout boxes only.
MEASURE = r"""
(function () {
  function run() {
    if (document.getElementById("__brand")) return;
    var cs = function (e) { return getComputedStyle(e); };
    var clear = function (c) { return !c || /rgba\(0, 0, 0, 0\)|transparent/.test(c); };
    var vis = function (e) { var r = e.getBoundingClientRect(), s = cs(e); return r.width > 0 && r.height > 0 && s.display !== "none" && s.visibility !== "hidden"; };
    var bgOf = function (e) { for (var n = e; n && n.nodeType === 1; n = n.parentElement) { var c = cs(n).backgroundColor; if (!clear(c)) return c; } return "rgb(255, 255, 255)"; };
    var out = {};
    out.page_bg = clear(cs(document.body).backgroundColor) ? bgOf(document.documentElement) : cs(document.body).backgroundColor;
    var p = Array.prototype.find.call(document.querySelectorAll("main p, article p, p"), function (e) { return vis(e) && e.textContent.trim().length > 40; }) || document.body;
    var ps = cs(p);
    out.body = { color: ps.color, font: ps.fontFamily, size: parseFloat(ps.fontSize), bg: bgOf(p) };
    out.headings = Array.prototype.filter.call(document.querySelectorAll("h1, h2"), vis).slice(0, 6).map(function (h) {
      var s = cs(h);
      // coloured or italic words inside the heading: the brand's second accent (and often a second font)
      var accents = Array.prototype.filter.call(h.querySelectorAll("span, em, i, strong, b, mark"), function (e) {
        var t = cs(e); return e.textContent.trim() && (t.color !== s.color || t.fontStyle !== s.fontStyle || t.fontFamily !== s.fontFamily);
      }).slice(0, 4).map(function (e) { var t = cs(e); return { text: e.textContent.trim().slice(0, 40), color: t.color, font: t.fontFamily, style: t.fontStyle, weight: t.fontWeight }; });
      return { tag: h.tagName, text: h.textContent.trim().slice(0, 60), font: s.fontFamily, weight: s.fontWeight, size: parseFloat(s.fontSize), track: s.letterSpacing, transform: s.textTransform, color: s.color, top: h.getBoundingClientRect().top + scrollY, accents: accents };
    });
    out.buttons = Array.prototype.filter.call(document.querySelectorAll("a, button, input[type=submit], [role=button]"), vis).map(function (e) {
      var s = cs(e), r = e.getBoundingClientRect();
      return { text: (e.textContent || e.value || "").trim().replace(/\s+/g, " ").slice(0, 40), bg: s.backgroundColor, color: s.color, radius: s.borderTopLeftRadius,
               h: r.height, w: r.width, top: r.top + scrollY, font: s.fontFamily, weight: s.fontWeight, border: s.borderTopColor, bw: parseFloat(s.borderTopWidth),
               transform: s.textTransform, track: s.letterSpacing, size: parseFloat(s.fontSize) };
    }).filter(function (b) { return b.h >= 28 && b.h <= 96 && b.w >= 56 && b.w <= 520 && b.text && b.top >= 0 && !/^skip to/i.test(b.text); }).slice(0, 60);
    out.links = Array.prototype.filter.call(document.querySelectorAll("main a, p a"), vis).slice(0, 60).map(function (a) { return cs(a).color; });
    var tally = {};
    var add = function (c, w) { if (!clear(c)) tally[c] = (tally[c] || 0) + w; };
    Array.prototype.slice.call(document.querySelectorAll("body *"), 0, 4000).forEach(function (e) {
      if (!vis(e)) return;
      var r = e.getBoundingClientRect(), s = cs(e), area = Math.min(r.width * r.height, 1440 * 900);
      add(s.backgroundColor, area);
      if (Array.prototype.some.call(e.childNodes, function (n) { return n.nodeType === 3 && n.textContent.trim(); })) add(s.color, Math.min(area, 30000) * 0.5);
      if (parseFloat(s.borderTopWidth) > 0) add(s.borderTopColor, (r.width + r.height) * 2);
    });
    out.colors = Object.keys(tally).map(function (k) { return [k, Math.round(tally[k])]; }).sort(function (a, b) { return b[1] - a[1]; }).slice(0, 40);
    var meta = function (n) { var m = document.querySelector('meta[name="' + n + '"], meta[property="' + n + '"]'); return m ? m.content : null; };
    out.meta = { theme_color: meta("theme-color"), site_name: meta("og:site_name"), og_image: meta("og:image"), title: document.title };
    out.icons = Array.prototype.map.call(document.querySelectorAll('link[rel~="icon"], link[rel="apple-touch-icon"]'), function (l) { return { rel: l.rel, href: l.href, sizes: l.sizes ? l.sizes.value : "" }; });
    var words = function (e) { if (!e || e.nodeType !== 1) return ""; var c = e.className; return [e.id, c && (c.baseVal !== undefined ? c.baseVal : c), e.getAttribute("alt"), e.getAttribute("aria-label"), e.getAttribute("src"), e.getAttribute("title")].join(" "); };
    var cands = [];
    Array.prototype.forEach.call(document.querySelectorAll("img, svg"), function (e) {
      if (e.closest("svg") && e.closest("svg") !== e) return;
      if (!vis(e)) return;
      var r = e.getBoundingClientRect();
      if (r.width < 18 || r.height < 10 || r.width > 520 || r.height > 200 || r.top + scrollY > 400) return;
      var head = !!e.closest("header, nav, [class*=header], [class*=Header], [class*=navbar], [class*=nav-]");
      var a = e.closest("a"), home = !!(a && /^(\/|\.\/|#?)$/.test((a.getAttribute("href") || "").replace(location.origin, "")));
      var named = /logo|brand|wordmark/i.test(words(e) + " " + words(e.parentElement) + " " + words(a));
      var score = (named ? 3 : 0) + (head ? 2 : 0) + (home ? 2 : 0) + (r.left < innerWidth / 2 ? 1 : 0);
      if (score < 3) return;
      var c = { score: score, top: r.top, left: r.left, w: r.width, h: r.height };
      if (e.tagName.toLowerCase() === "img") { c.type = "img"; c.src = e.currentSrc || e.src; }
      else {
        var clone = e.cloneNode(true), src = [e].concat(Array.prototype.slice.call(e.querySelectorAll("*"))), dst = [clone].concat(Array.prototype.slice.call(clone.querySelectorAll("*")));
        src.forEach(function (n, i) { var s = cs(n); if (dst[i] && dst[i].setAttribute) { if (s.fill && s.fill !== "none") dst[i].setAttribute("fill", s.fill); if (s.stroke && s.stroke !== "none") dst[i].setAttribute("stroke", s.stroke); } });
        clone.setAttribute("width", Math.round(r.width)); clone.setAttribute("height", Math.round(r.height));
        if (!clone.getAttribute("xmlns")) clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
        c.type = "svg"; c.svg = clone.outerHTML.slice(0, 300000);
      }
      cands.push(c);
    });
    out.logos = cands.sort(function (a, b) { return b.score - a.score || a.top - b.top || a.left - b.left; }).slice(0, 6);
    out.stylesheets = Array.prototype.map.call(document.styleSheets, function (s) { return s.href; }).filter(Boolean);
    var pre = document.createElement("pre"); pre.id = "__brand"; pre.textContent = JSON.stringify(out); document.body.appendChild(pre);
  }
  addEventListener("load", function () { setTimeout(run, 400); });
  setTimeout(run, 5000);
})();
"""


def fetch(url, limit=6_000_000, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=25) as r:
        body = r.read(limit)
        return (body if binary else body.decode(r.headers.get_content_charset() or "utf-8", "replace")), r.geturl(), r.headers.get("Content-Type", "")


# ---- colour helpers ----
def oklab_to_rgb(L, a, b):
    l_, m_, s_ = (L + 0.3963377774 * a + 0.2158037573 * b, L - 0.1055613458 * a - 0.0638541728 * b,
                  L - 0.0894841775 * a - 1.2914855480 * b)
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    lin = (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
           -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
           -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)
    enc = lambda c: 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return tuple(int(round(max(0.0, min(1.0, enc(max(0.0, c)))) * 255)) for c in lin)


def rgb(c):
    """'rgb(1, 2, 3)' / 'rgba(...)' / 'oklch(...)' / 'oklab(...)' / 'color(srgb ...)' / '#abc' -> (r, g, b, a) or None.
    Chrome reports colours in whatever space the site's CSS used (Tailwind v4 uses oklch)."""
    if not c:
        return None
    num = lambda v, pct=1.0: float(v[:-1]) / 100 * pct if v.endswith("%") else float(v)
    m = re.match(r"(oklch|oklab|color)\(\s*(srgb\s+)?([-\d.%]+)\s+([-\d.%]+)\s+([-\d.%]+)(?:\s*/\s*([\d.]+%?))?\s*\)", c.strip())
    if m:
        kind, x, y, z, al = m.group(1), m.group(3), m.group(4), m.group(5), m.group(6)
        alpha = 1.0 if al is None else num(al)
        if kind == "color":
            return tuple(int(round(max(0, min(1, num(v))) * 255)) for v in (x, y, z)) + (alpha,)
        L = num(x)
        if kind == "oklch":
            import math
            C, H = num(y, 0.4), float(z.rstrip("deg") or 0)
            a, b = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
        else:
            a, b = num(y, 0.4), num(z, 0.4)
        return oklab_to_rgb(L, a, b) + (alpha,)
    m = re.match(r"rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:[,\s/]+([\d.]+%?))?", c)
    if m:
        a = m.group(4)
        a = 1.0 if a is None else (float(a[:-1]) / 100 if a.endswith("%") else float(a))
        return tuple(int(float(m.group(i))) for i in (1, 2, 3)) + (a,)
    m = re.match(r"#([0-9a-f]{3}|[0-9a-f]{6})$", c.strip().lower())
    if m:
        h = m.group(1)
        h = "".join(x * 2 for x in h) if len(h) == 3 else h
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0)
    return None


def hexc(t):
    return "#%02x%02x%02x" % t[:3]


def lum(t):
    c = [x / 255 for x in t[:3]]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def sat(t):
    h, l, s = colorsys.rgb_to_hls(*(x / 255 for x in t[:3]))
    return s if 0.08 < l < 0.92 else 0.0


def dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a[:3], b[:3])) ** 0.5


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# ---- fonts ----
def families(stack):
    out = []
    for f in (stack or "").split(","):
        f = f.strip().strip('"\'').strip()
        if f:
            out.append(f)
    return out


def primary(stack):
    """First real family in a CSS stack, or None if the site uses the system font."""
    for f in families(stack):
        if f.lower() in GENERIC:
            continue
        return f
    return None


def unhash(fam):
    """The Google Fonts name behind a site's local name: next/font's __Name_1a2b3c, or 'Inter Variable' / 'Inter VF'."""
    m = re.match(r"^__(.+?)(?:_Fallback)?_[0-9a-f]{5,8}$", fam)
    name = m.group(1).replace("_", " ") if m else fam
    name = re.sub(r"\s+(Variable|VF|Var|Web)$", "", name, flags=re.I)
    return name if name != fam else None


def google(family, weights):
    """The css2 family param that Google Fonts serves for this family, or None if it isn't a Google font."""
    base = "https://fonts.googleapis.com/css2?family=" + urllib.parse.quote(family).replace("%20", "+")
    tries = [":wght@" + ";".join(str(w) for w in sorted(set(weights))), ":wght@100..900", ""]
    for t in tries:
        try:
            fetch(base + t, limit=200_000)
            return family + t
        except urllib.error.HTTPError:
            continue
        except Exception:
            return None
    return None


def font_faces(css, base_url):
    """@font-face rules in a stylesheet -> [{family, weight, style, url}]."""
    out = []
    for block in re.findall(r"@font-face\s*{([^}]*)}", css, re.I):
        fam = re.search(r"font-family\s*:\s*([^;]+)", block, re.I)
        src = re.search(r"src\s*:\s*([^;]+)", block, re.I)
        if not fam or not src:
            continue
        urls = re.findall(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)\s*(?:format\(\s*['\"]?([\w-]+)['\"]?\s*\))?", src.group(1))
        if not urls:
            continue
        rank = {"woff2": 0, "woff": 1, "truetype": 2, "opentype": 3}
        urls.sort(key=lambda u: rank.get(u[1] or u[0].rsplit(".", 1)[-1].split("?")[0], 4))
        if urls[0][0].startswith("data:"):
            continue
        w = re.search(r"font-weight\s*:\s*([^;]+)", block, re.I)
        st = re.search(r"font-style\s*:\s*([^;]+)", block, re.I)
        out.append({"family": fam.group(1).strip().strip('"\''), "weight": (w.group(1).strip() if w else "400"),
                    "style": (st.group(1).strip() if st else "normal"), "url": urllib.parse.urljoin(base_url, urls[0][0])})
    return out


def weight_hits(wspec, want):
    """Does a @font-face font-weight ('400', '100 900', 'bold') cover the weight we want?"""
    nums = [int(x) for x in re.findall(r"\d+", wspec.replace("bold", "700").replace("normal", "400"))] or [400]
    return min(nums) <= want <= max(nums), min(abs(n - want) for n in nums)


def embed_fonts(fam, weights, css_texts, out_dir, style="normal"):
    """Download the site's own files for one family (nearest match per weight). Returns [{family, weight, style, file}]."""
    faces = [f for css, url in css_texts for f in font_faces(css, url) if f["family"].lower() == fam.lower() and f["style"] == style]
    got, files = set(), []
    for want in sorted(set(weights)):
        if not faces:
            break
        best = min(faces, key=lambda f: (not weight_hits(f["weight"], want)[0], weight_hits(f["weight"], want)[1]))
        if best["url"] in got:
            continue
        try:
            data, _, _ = fetch(best["url"], limit=800_000, binary=True)
        except Exception as e:
            print(f"  warn   couldn't download {fam} ({e.__class__.__name__}); pick a close Google font by hand")
            return []
        ext = best["url"].split("?")[0].rsplit(".", 1)[-1].lower()
        ext = ext if ext in ("woff2", "woff", "ttf", "otf") else "woff2"
        name = re.sub(r"[^a-z0-9]+", "-", fam.lower()).strip("-") + "-" + re.sub(r"\s+", "-", best["weight"]) + ("-italic" if style == "italic" else "") + "." + ext
        os.makedirs(os.path.join(out_dir, "fonts"), exist_ok=True)
        open(os.path.join(out_dir, "fonts", name), "wb").write(data)
        got.add(best["url"])
        files.append({"family": fam, "weight": best["weight"], "style": style, "file": "brand/fonts/" + name})
    return files


# ---- measuring ----
def measure(url, work):
    page, final, _ = fetch(url)
    stripped = re.sub(r"<script\b[^>]*>.*?</script\s*>", "", page, flags=re.S | re.I)
    stripped = re.sub(r"<meta[^>]+http-equiv=[\"']?content-security-policy[^>]*>", "", stripped, flags=re.I)
    head = re.search(r"<head[^>]*>", stripped, re.I)
    base = f'<base href="{html.escape(final)}">'
    stripped = stripped[:head.end()] + base + stripped[head.end():] if head else base + stripped
    stripped += "<script>" + MEASURE + "</script>"
    mirror = os.path.join(work, "mirror.html")
    open(mirror, "w").write(stripped)
    dom = subprocess.run([chrome(), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1440,900",
                          "--virtual-time-budget=12000", "--run-all-compositor-stages-before-draw", "--dump-dom",
                          "file://" + mirror], capture_output=True, text=True, timeout=120).stdout
    m = re.search(r'<pre id="__brand">(.*?)</pre>', dom, re.S)
    if not m:
        sys.exit("couldn't measure the page (it may need JavaScript to render). Set the brand by hand: see SKILL.md.")
    data = json.loads(html.unescape(m.group(1)))
    inline_css = [(c, final) for c in re.findall(r"<style[^>]*>(.*?)</style>", page, re.S | re.I)]
    return data, final, inline_css


def shoot(url, dst, size):
    subprocess.run([chrome(), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=8000",
                    f"--window-size={size}", "--force-device-scale-factor=1", f"--screenshot={dst}", url],
                   capture_output=True, timeout=120)


def pick_accent(data, bg):
    """The main button's colour: prominent, saturated, near the top. Falls back to theme-color, then the page's colours."""
    scored = []
    for b in data["buttons"]:
        c = rgb(b["bg"])
        if not c or c[3] < 0.9 or dist(c, bg) < 40:
            continue
        s = b["w"] * b["h"] * (1.5 if b["top"] < 900 else 1) * (1 + 2 * sat(c))
        scored.append((s, c, b))
    if scored:
        scored.sort(key=lambda x: -x[0])
        tot = {}
        for s, c, b in scored:
            tot[c[:3]] = tot.get(c[:3], 0) + s
        best = max(tot, key=tot.get)
        b = next(b for s, c, b in scored if c[:3] == best)
        return best, rgb(b["color"]), "the main button", b
    tc = rgb(data["meta"].get("theme_color"))
    if tc and sat(tc) > 0.2:
        return tc[:3], None, "theme-color", None
    for c, w in data["colors"]:
        t = rgb(c)
        if t and t[3] > 0.9 and sat(t) > 0.35:
            return t[:3], None, "the most-used saturated colour", None
    links = [rgb(c) for c in data["links"]]
    links = [l for l in links if l and sat(l) > 0.3]
    if links:
        return links[0][:3], None, "link colour", None
    return None, None, "nothing found", None


def save_logo(cand, out_dir):
    if cand["type"] == "svg":
        svg = cand["svg"].replace("currentColor", "#000")
        open(os.path.join(out_dir, "logo.svg"), "w").write(svg)
        return "brand/logo.svg"
    data, _, ctype = fetch(cand["src"], limit=3_000_000, binary=True)
    ext = {"image/svg+xml": "svg", "image/png": "png", "image/webp": "webp", "image/jpeg": "jpg", "image/gif": "gif"}.get(
        ctype.split(";")[0].strip(), cand["src"].split("?")[0].rsplit(".", 1)[-1].lower())
    ext = ext if ext in ("svg", "png", "webp", "jpg", "jpeg", "gif") else "png"
    open(os.path.join(out_dir, "logo." + ext), "wb").write(data)
    return "brand/logo." + ext


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    d, url = sys.argv[1], sys.argv[2]
    if not re.match(r"https?://", url):
        url = "https://" + url
    dry = "--dry" in sys.argv
    out_dir = os.path.join(d, "brand")
    os.makedirs(out_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as work:
        print(f"measuring {url} ...")
        data, final, inline_css = measure(url, work)
    shoot(final, os.path.join(out_dir, "site.png"), "1440,900")
    shoot(final, os.path.join(out_dir, "site-mobile.png"), "500,1000")

    bg = rgb(data["page_bg"]) or (255, 255, 255, 1)
    theme = "dark" if lum(bg) < 0.35 else "light"
    h1c = next((rgb(h["color"]) for h in data["headings"] if h["tag"] == "H1" and rgb(h["color"]) and contrast(rgb(h["color"]), bg) > 4.5), None)
    ink = h1c or rgb(data["body"]["color"]) or (17, 17, 17, 1)
    accent, on, why, btn = pick_accent(data, bg)
    notes = []
    if not accent:
        notes.append("no accent colour found: set brand.color by hand")
    if accent and contrast(accent, bg) < 1.6:
        notes.append(f"accent {hexc(accent)} is close to the background: check the buttons in out/shot.png")

    # fonts
    h1s = [h for h in data["headings"] if h["tag"] == "H1"]
    h1 = h1s[0] if h1s else (max(data["headings"], key=lambda h: h["size"]) if data["headings"] else None)
    disp_stack = h1["font"] if h1 else data["body"]["font"]
    body_stack = data["body"]["font"]
    disp, body = primary(disp_stack), primary(body_stack)
    weight = int(h1["weight"]) if h1 and str(h1["weight"]).isdigit() else 700
    track = 0.0
    if h1 and h1["track"] not in ("normal", "") and h1["size"]:
        px = re.match(r"(-?[\d.]+)px", h1["track"])
        track = round(float(px.group(1)) / h1["size"], 3) if px else 0.0
    track = max(-0.06, min(0.06, track))
    fonts = {"weight": weight, "tracking": track}
    if h1 and h1.get("transform") == "uppercase":
        fonts["transform"] = "uppercase"
    # second accent: a saturated colour on words inside a heading; an italic in another font becomes the serif accent
    highlight, serif = None, None
    for h in ([h1] if h1 else []) + [h for h in data["headings"] if h is not h1]:
        for a in h.get("accents", []):
            c = rgb(a["color"])
            if c and sat(c) > 0.3 and (not accent or dist(c, accent) > 60) and not highlight:
                highlight = c[:3]
            if a["style"] == "italic" and primary(a["font"]) and primary(a["font"]) != primary(h["font"]) and not serif:
                serif = a["font"]
    roles = [("display", disp, disp_stack, [weight]), ("body", body, body_stack, [400, 500, 600])]
    if serif:
        roles.append(("serif", primary(serif), serif, [400]))
    css_texts = None
    for role, fam, stack, weights in roles:
        if not fam:
            fonts[role + "_stack"] = ", ".join(f'"{f}"' if " " in f else f for f in families(stack))
            fonts[role] = families(stack)[0] if families(stack) else "system-ui"
            notes.append(f"{role} font is the system font ({stack[:60]})")
            continue
        fonts[role] = fam
        if fam.lower() in SYSTEM:
            fonts[role + "_stack"] = ", ".join(f'"{f}"' if " " in f else f for f in families(stack))
            continue
        real = unhash(fam)
        g = google(real or fam, weights + ([700] if role == "display" else [])) if role != "serif" else \
            google(real or fam, []) and (real or fam) + ":ital@1"
        if g:
            name = real or fam
            fonts[role] = name
            fonts.setdefault("google", [])
            # one entry per family: Google rejects a request that names the same family twice
            same = [x for x in fonts["google"] if x.split(":")[0] == name]
            if same and role != "serif":
                had = [int(w) for x in same for w in re.findall(r"\d{3}", x.split("@")[-1]) if ".." not in x]
                merged = google(name, weights + [700] + had)
                fonts["google"] = [x for x in fonts["google"] if x not in same] + [merged or same[0]]
            elif not same:
                fonts["google"].append(g)
            continue
        if css_texts is None:
            css_texts = list(inline_css)
            for href in data["stylesheets"][:12]:
                try:
                    css, u, _ = fetch(href, limit=3_000_000)
                    css_texts.append((css, u))
                except Exception:
                    pass
        files = embed_fonts(fam, weights, css_texts, out_dir, "italic" if role == "serif" else "normal")
        if files:
            fonts.setdefault("files", []).extend(f for f in files if f not in fonts.get("files", []))
        else:
            notes.append(f"{role} font '{fam}' isn't on Google Fonts and its files weren't found: set "
                         f"brand.fonts.{role} to the closest Google font")
    if fonts.get("display") == fonts.get("body"):
        fonts.pop("display_stack", None)

    # shape
    rb = None
    if btn:
        r = re.match(r"([\d.]+)px", btn["radius"] or "")
        rb = int(float(r.group(1))) if r else 0
        if rb >= btn["h"] / 2 - 1:
            rb = 999
    radius = None if rb is None else (18 if rb == 999 else min(28, max(0, round(rb * 1.4))))
    button = None
    if btn:
        bf = primary(btn["font"])
        role = "display" if bf and bf == disp else "body" if bf and bf == body else None
        bt = re.match(r"(-?[\d.]+)px", btn.get("track") or "")
        button = {"font": role, "weight": int(btn["weight"]) if str(btn["weight"]).isdigit() else 600,
                  "transform": btn.get("transform") if btn.get("transform") in ("uppercase", "none") else "none",
                  "tracking": round(float(bt.group(1)) / btn["size"], 3) if bt and btn.get("size") else 0.0}

    # logo + name
    logo = None
    for cand in data["logos"]:
        try:
            logo = save_logo(cand, out_dir)
            break
        except Exception:
            continue
    if not logo:
        notes.append("no logo found: add brand.logo by hand (a file in the project folder)")
    title = data["meta"].get("site_name") or re.split(r"\s+[|\-–—:·]\s+", data["meta"].get("title") or "")[0]
    name = (title or urllib.parse.urlparse(final).netloc.replace("www.", "")).strip()[:40]

    brand = {"name": name, "theme": theme, "bg": hexc(bg), "ink": hexc(ink), "fonts": fonts, "source": final}
    if accent:
        brand["color"] = hexc(accent)
        if on and contrast(on, accent) >= 3:
            brand["on"] = hexc(on)
        elif accent:
            brand["on"] = ink_on(hexc(accent))
    if theme == "light" and lum(ink) < 0.08:
        brand["cover"] = hexc(ink)
    if rb is not None:
        brand["button_radius"], brand["radius"] = rb, radius
    if button:
        brand["button"] = button
    if highlight:
        brand["highlight"] = hexc(highlight)
        if serif:
            brand["em"] = hexc(highlight)
    if logo:
        brand["logo"] = logo

    json.dump({"brand": brand, "accent_from": why, "notes": notes, "measured": data}, open(os.path.join(out_dir, "brand.json"), "w"), indent=1)
    print(f"  name     {name}")
    print(f"  theme    {theme}   bg {brand['bg']}   ink {brand['ink']}")
    print(f"  accent   {brand.get('color', '-')} (from {why})   text on it {brand.get('on', '-')}")
    print(f"  fonts    display {fonts.get('display')} {weight} {track:+.3f}em   body {fonts.get('body')}   "
          f"google {fonts.get('google', [])}   embedded {[f['file'] for f in fonts.get('files', [])]}")
    print(f"  shape    button radius {rb}   card radius {radius}")
    print(f"  logo     {logo or '-'}   (padding is trimmed in the page; a wide wordmark hides the name text)")
    print(f"  accent 2 {brand.get('highlight', '-')}   accent font {fonts.get('serif', '-')}   heading case {fonts.get('transform', 'as typed')}")
    print(f"  button   {button}")
    for n in notes:
        print(f"  check    {n}")
    print(f"  saved    {out_dir}/site.png, site-mobile.png, brand.json")

    if not dry:
        p = os.path.join(d, "magnet.json")
        m = json.load(open(p))
        old = m.get("brand") or {}
        keep = {k: old[k] for k in ("header",) if k in old}
        m["brand"] = {**brand, **keep}
        m["brand"].pop("source", None)
        json.dump(m, open(p, "w"), indent=2, ensure_ascii=False)
        print(f"  wrote    brand into {p}; now build, shoot, and compare out/shot.png with brand/site.png")


if __name__ == "__main__":
    main()
