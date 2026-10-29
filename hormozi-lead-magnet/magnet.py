"""Lead magnets from one magnet.json: the owner's words in, one self-contained page out (works on any host, prints to PDF).

  python3 magnet.py check <dir>            validate <dir>/magnet.json against Hormozi's rules
  python3 magnet.py build <dir>            -> <dir>/out/index.html (images inlined, no external files)
  python3 magnet.py pdf   <dir>            -> <dir>/out/<slug>.pdf (print view, needs Google Chrome)
  python3 magnet.py shot  <dir> [--mobile] -> <dir>/out/shot.png (first screen, needs Google Chrome)

Three types, one per Hormozi lead magnet category:
  assessment  reveal a problem: questions -> score -> the specific problems their answers reveal -> CTA
  guide       one step of a multi-step process: numbered steps with checklists, CTAs mid-way and at the end
  claim       a free service or trial for qualified people: what you get, what it's worth, the limit, a claim form
"""
import base64, html, json, mimetypes, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "google-chrome", "chromium", "chromium-browser"]


def load(d):
    p = os.path.join(d, "magnet.json")
    if not os.path.exists(p):
        sys.exit(f"no magnet.json in {d} (start from examples/skeleton/magnet.json)")
    return json.load(open(p))


def check(m, d):
    """Errors stop the build. Warnings are Hormozi's rules the draft doesn't meet yet."""
    err, warn = [], []
    t = m.get("type")
    if t not in ("assessment", "guide", "claim"):
        err.append('type must be "assessment", "guide" or "claim"')
    if not m.get("title"):
        err.append("title is missing (the name is the most important part: pick it from the tested options)")
    elif len(plain(m["title"])) > 90:
        warn.append(f"title is {len(plain(m['title']))} characters; names that win are short and specific")
    if not m.get("who"):
        warn.append("who is missing: say who it's for, so the wrong people self-select out")
    cta = m.get("cta") or {}
    if not cta.get("main"):
        err.append("cta.main is missing: every lead magnet ends with one clear next step")
    for k, c in cta.items():
        if not c.get("url"):
            warn.append(f"cta.{k}.url is empty")
        if not c.get("reason"):
            warn.append(f"cta.{k}.reason is empty: give a reason to act now (a real capacity limit beats none, any reason beats none)")
    cap = m.get("capture") or {}
    if not cap.get("action"):
        warn.append("capture.action is empty: the page works but leads go nowhere (fine for a draft, not for live)")
    q = cap.get("qualify")
    if q:
        for o in q.get("options", []):
            if o.get("route", "main") not in cta:
                err.append(f'qualify option "{o.get("label")}" routes to cta.{o.get("route")}, which doesn\'t exist')
    if not m.get("proof") and not m.get("stats"):
        warn.append("no proof or stats: add a real result (yours, never invented)")
    if not m.get("next_problem"):
        warn.append("next_problem is empty: say what problem solving this one reveals (the one your paid offer solves)")

    if t == "assessment":
        qs = m.get("questions") or []
        if not 3 <= len(qs) <= 12:
            warn.append(f"{len(qs)} questions; 5-10 keeps it fast to finish")
        for i, x in enumerate(qs, 1):
            opts = x.get("options") or []
            if len(opts) < 2:
                err.append(f"question {i} needs at least 2 options")
            if not any(o.get("problem") for o in opts):
                warn.append(f'question {i} reveals nothing: give the weak answers a "problem" (specific, in the owner\'s words)')
        rs = sorted(m.get("results") or [], key=lambda r: r.get("min", 0))
        if not rs:
            err.append("results is empty: add score buckets (min/max 0-100)")
        else:
            covered, at = True, 0
            for r in rs:
                if r.get("min", 0) > at:
                    covered = False
                at = max(at, r.get("max", 0) + 1)
            if not covered or at < 101:
                err.append("results buckets must cover every score from 0 to 100 with no gaps")
            if not any(r.get("delta") for r in rs):
                warn.append("no result has a delta: show where they are vs where they could be, in real numbers")
    elif t == "guide":
        st = m.get("steps") or []
        if not st:
            err.append("steps is empty")
        if len(st) > 9:
            warn.append(f"{len(st)} steps: it should solve one narrow problem completely; split it or cut it")
    elif t == "claim":
        if not m.get("includes"):
            err.append("includes is empty: list exactly what they get")
        if not m.get("limit"):
            warn.append("limit is empty: say your real capacity (e.g. 4 a week); only give free services to qualified leads")
        if not q:
            warn.append("no capture.qualify: free services should only go to qualified prospects")

    for p in images(m):
        if not p.startswith(("http", "data:")) and not os.path.exists(os.path.join(d, p)):
            err.append(f"image not found: {p}")
    return err, warn


def images(m):
    out = [m["image"]] if m.get("image") else []
    if (m.get("brand") or {}).get("logo"):
        out.append(m["brand"]["logo"])
    for x in (m.get("proof") or []) + (m.get("steps") or []):
        if x.get("img"):
            out.append(x["img"])
    return out


def inline(m, d):
    """Local image paths -> data URIs, so out/index.html is one file that works anywhere."""
    def uri(p):
        if p.startswith(("http", "data:")):
            return p
        f = os.path.join(d, p)
        mt = mimetypes.guess_type(f)[0] or "image/png"
        return f"data:{mt};base64," + base64.b64encode(open(f, "rb").read()).decode()
    m = json.loads(json.dumps(m))
    if m.get("image"):
        m["image"] = uri(m["image"])
    if (m.get("brand") or {}).get("logo"):
        m["brand"]["logo"] = uri(m["brand"]["logo"])
    for x in (m.get("proof") or []) + (m.get("steps") or []):
        if x.get("img"):
            x["img"] = uri(x["img"])
    return m


def plain(s):
    """Strip the page markup (**bold**, ==highlight==, *italic*) for the tab title and file names."""
    return re.sub(r"\*\*|==|\*", "", s or "")


def ink_on(hex_color):
    """Text colour on the brand colour. White wherever it reads at button size (3:1, WCAG large text), as designers do
    on mid-blues and reds; black on light colours (yellows, greens, light greys)."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    lum = [(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)]
    lum = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in lum]
    y = 0.2126 * lum[0] + 0.7152 * lum[1] + 0.0722 * lum[2]
    return "#ffffff" if 1.05 / (y + 0.05) >= 3.0 else "#0a0a0a"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", plain(s).lower()).strip("-")[:60] or "lead-magnet"


def build(d):
    m = load(d)
    err, warn = check(m, d)
    report(err, warn)
    if err:
        sys.exit(1)
    brand = m.get("brand") or {}
    color = brand.get("color") or "#22c55e"
    for k in ("color", "on", "bg", "ink", "cover"):
        if brand.get(k) and not re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", brand[k]):
            sys.exit(f"brand.{k} must be a hex colour like #22c55e, got {brand[k]!r}")
    mode = brand.get("theme", "dark")
    if mode not in ("dark", "light"):
        sys.exit('brand.theme must be "dark" or "light"')
    data = json.dumps(inline(m, d), ensure_ascii=False).replace("</", "<\\/")
    page = (open(os.path.join(HERE, "template.html")).read()
            .replace("{{TITLE}}", html.escape(plain(m["title"])))
            .replace("{{DESC}}", html.escape(plain(m.get("subtitle", ""))))
            .replace("{{MODE}}", mode)
            .replace("{{BRAND}}", color)
            .replace("{{ONBRAND}}", brand.get("on") or ink_on(color))
            .replace("{{HEAD}}", brand_head(brand, d))
            .replace("{{DATA}}", data))
    os.makedirs(os.path.join(d, "out"), exist_ok=True)
    out = os.path.join(d, "out", "index.html")
    open(out, "w").write(page)
    print(f"wrote {out} ({len(page) // 1024} KB)")
    return out


def css_str(name):
    return '"' + name.replace("\\", "").replace('"', "") + '"'


def brand_head(brand, d):
    """The owner's fonts and colours (from brand.py or set by hand), as tags that override the template's defaults."""
    fonts, out, root = brand.get("fonts") or {}, [], []
    if fonts.get("google"):
        fam = "&".join("family=" + f.replace(" ", "+") for f in fonts["google"])
        out.append(f'<link href="https://fonts.googleapis.com/css2?{html.escape(fam)}&display=swap" rel="stylesheet">')
    faces = []
    for f in fonts.get("files") or []:
        path = os.path.join(d, f["file"])
        if not os.path.exists(path):
            print(f"  warn   font file missing: {f['file']}")
            continue
        fmt = {"woff2": "woff2", "woff": "woff", "ttf": "truetype", "otf": "opentype"}.get(path.rsplit(".", 1)[-1], "woff2")
        b64 = base64.b64encode(open(path, "rb").read()).decode()
        faces.append(f'@font-face{{font-family:{css_str(f["family"])};src:url(data:font/{fmt};base64,{b64}) format("{fmt}");'
                     f'font-weight:{f.get("weight", "400")};font-style:{f.get("style", "normal")};font-display:swap}}')
    if fonts.get("body"):
        root.append(f"--sans:{fonts['body_stack'] if fonts.get('body_stack') else css_str(fonts['body'])}, var(--fallback)")
    if fonts.get("display"):
        root.append(f"--display:{fonts['display_stack'] if fonts.get('display_stack') else css_str(fonts['display'])}, var(--fallback)")
    if fonts.get("weight"):
        root.append(f"--hw:{int(fonts['weight'])}")
    if fonts.get("tracking") is not None:
        root.append(f"--track:{float(fonts['tracking']):.3f}em")
    for key, var in (("bg", "--bg"), ("ink", "--ink"), ("cover", "--cover")):
        if brand.get(key):
            root.append(f"{var}:{brand[key]}")
    if brand.get("radius") is not None:
        root.append(f"--r:{max(0, min(32, int(brand['radius'])))}px")
    if brand.get("button_radius") is not None:
        root.append(f"--rb:{max(0, min(999, int(brand['button_radius'])))}px")
    if fonts.get("serif"):
        root.append(f'--serif:{css_str(fonts["serif"])}, "Instrument Serif", ui-serif, Georgia, serif')
    if fonts.get("transform") in ("uppercase", "none"):
        root.append(f"--h-tf:{fonts['transform']}")
    if brand.get("highlight"):
        root.append(f"--hl:{brand['highlight']};--hl-ink:{ink_on(brand['highlight'])}")
    if brand.get("em"):
        root.append(f"--em:{brand['em']}")
    b = brand.get("button") or {}
    if b:
        if b.get("font") in ("display", "body"):
            root.append("--btn-font:" + ("var(--display)" if b["font"] == "display" else "var(--sans)"))
        if b.get("weight"):
            root.append(f"--btn-weight:{int(b['weight'])}")
        if b.get("transform") in ("uppercase", "none"):
            root.append(f"--btn-tf:{b['transform']}")
        if b.get("tracking") is not None:
            root.append(f"--btn-track:{float(b['tracking']):.3f}em")
    if faces or root:
        out.append("<style id=\"brand\">" + "".join(faces) + (":root{" + ";".join(root) + "}" if root else "") + "</style>")
    return "\n".join(out)


def chrome():
    for c in CHROME:
        if os.path.exists(c) or shutil.which(c):
            return c
    sys.exit("Google Chrome not found (needed for pdf and shot)")


def pdf(d):
    out = build(d)
    m = load(d)
    dst = os.path.join(d, "out", slug(m["title"]) + ".pdf")
    subprocess.run([chrome(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=3000",
                    f"--print-to-pdf={dst}", "file://" + os.path.abspath(out) + "?print=1"],
                   check=True, capture_output=True)
    print(f"wrote {dst}")


def shot(d, mobile):
    out = build(d)
    dst = os.path.join(d, "out", "shot-mobile.png" if mobile else "shot.png")
    size = "390,844" if mobile else "1280,900"
    subprocess.run([chrome(), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=3000",
                    f"--window-size={size}", "--force-device-scale-factor=2", f"--screenshot={dst}",
                    "file://" + os.path.abspath(out) + "?clean=1"], check=True, capture_output=True)
    print(f"wrote {dst}")


def report(err, warn):
    for e in err:
        print("  ERROR  " + e)
    for w in warn:
        print("  warn   " + w)
    if not err and not warn:
        print("  ok")


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("check", "build", "pdf", "shot"):
        sys.exit(__doc__)
    cmd, d = sys.argv[1], sys.argv[2]
    if cmd == "check":
        e, w = check(load(d), d)
        report(e, w)
        sys.exit(1 if e else 0)
    elif cmd == "build":
        build(d)
    elif cmd == "pdf":
        pdf(d)
    else:
        shot(d, "--mobile" in sys.argv)
