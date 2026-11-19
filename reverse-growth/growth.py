#!/usr/bin/env python3
"""reverse-growth: the local half of the skill. Claude pulls pages, ad libraries, social feeds, reviews and news with
context.dev; this script reads the open feeds that need no scraper (sitemaps, the Wayback Machine, Wikipedia page
views, YouTube's channel page and feed, X's public embed timeline), does every sum, ranks the posts,
downloads the thumbnails, builds the contact sheets and writes the one-file report.

python3 growth.py setup
python3 growth.py site     <domain> -o <dir> [--html home.html] [--urls urls.txt]   sitemap -> page families, homepage -> stack + links
python3 growth.py wayback  <domain> -o <dir> [--pages /pricing,/templates]   when the homepage and named pages were first saved
python3 growth.py wiki     <domain> -o <dir> [--title "Article title"]
python3 growth.py youtube  <@handle or channel URL> -o <dir>
python3 growth.py x        <handle> -o <dir>
python3 growth.py rows     <channel> <saved answer file> -o <dir>  a long context.dev answer Claude Code saved to a file -> posts.json
python3 growth.py rank     <dir>            every content/<channel>/posts.json -> posts.csv, img/, sheet.jpg
python3 growth.py ads      <dir> [--advertiser "Name|Other name"] ads/<network>.json -> ads.csv, summary.csv
python3 growth.py curve    <dir>            every monthly series -> curve/monthly.csv + the inflection
python3 growth.py moves    <dir>            moves.json vs the curve -> moves-vs-growth.csv
python3 growth.py report   <dir> [playbook.md]                    -> playbook.html (one file)
"""
import base64, csv, datetime as dt, gzip, html, io, json, math, os, re, subprocess, sys, time, urllib.parse, urllib.request
from collections import Counter, defaultdict

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
TODAY = dt.date.today()


# ---------------------------------------------------------------- small helpers

def get(url, timeout=30, headers=None, tries=2, raw=False):
    """One public GET. Returns text (or bytes with raw=True), or None when the site refuses."""
    h = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.8", "Accept-Encoding": "gzip"}
    h.update(headers or {})
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
                b = r.read()
                if r.headers.get("Content-Encoding") == "gzip" or b[:2] == b"\x1f\x8b":
                    try:
                        b = gzip.decompress(b)
                    except OSError:
                        pass
                return b if raw else b.decode("utf-8", "replace")
        except Exception as e:                                           # blocked, timed out, gone
            err = e
            time.sleep(1.5 * (i + 1))
    print(f"  !! could not read {url[:90]}: {type(err).__name__} {str(err)[:80]}", file=sys.stderr)
    return None


def opt(args, name, default=None):
    return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else default


def out_dir(args):
    d = opt(args, "-o")
    if not d:
        sys.exit("say where the study lives: -o growth/<company>")
    os.makedirs(d, exist_ok=True)
    return d


def write_csv(path, rows, cols=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cols = cols or (list(rows[0].keys()) if rows else [])
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return path


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
    return path


def read_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


def num(v):
    """'17K', '1.2M views', '3,402', 17000 -> a number, or None."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"(-?[\d][\d,]*\.?\d*)\s*([KkMmBb])?", str(v))
    if not m:
        return None
    x = float(m.group(1).replace(",", ""))
    return x * {"k": 1e3, "m": 1e6, "b": 1e9}.get((m.group(2) or "").lower(), 1)


REL = re.compile(r"(\d+)\s*(s|sec|second|m|min|minute|h|hr|hour|d|day|w|wk|week|mo|month|y|yr|year)s?\b(\s*ago)?", re.I)
UNIT_DAYS = {"s": 0, "sec": 0, "second": 0, "m": 0, "min": 0, "minute": 0, "h": 1 / 24, "hr": 1 / 24, "hour": 1 / 24, "d": 1, "day": 1,
             "w": 7, "wk": 7, "week": 7, "mo": 30.4, "month": 30.4, "y": 365, "yr": 365, "year": 365}


def when(v, pulled=None):
    """Any date a feed gives -> (date, exact?). '3 weeks ago' and '2mo' count back from the day of the pull."""
    if v in (None, ""):
        return None, False
    pulled = pulled or TODAY
    if isinstance(v, (int, float)) or re.fullmatch(r"\d{10,13}", str(v)):
        x = float(v)
        return dt.datetime.utcfromtimestamp(x / 1000 if x > 1e11 else x).date(), True
    s = str(v).strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))), True
    for fmt in ("%a %b %d %H:%M:%S %z %Y", "%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y", "%m/%d/%Y", "%b %Y", "%B %Y"):
        try:
            return dt.datetime.strptime(s, fmt).date(), "%d" in fmt
        except ValueError:
            pass
    m = REL.search(s)
    if m:
        return pulled - dt.timedelta(days=round(int(m.group(1)) * UNIT_DAYS[m.group(2).lower()])), False
    return None, False


def month(d):
    return f"{d.year}-{d.month:02d}"


def months_between(a, b):
    y, m, out = int(a[:4]), int(a[5:7]), []
    while f"{y}-{m:02d}" <= b:
        out.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def bare(domain):
    d = re.sub(r"^https?://", "", domain.strip().lower()).split("/")[0]
    return d[4:] if d.startswith("www.") else d


# ---------------------------------------------------------------- site: sitemap families, stack, links

LOCALE = re.compile(r"^[a-z]{2}([-_][a-zA-Z]{2,4})?$")

STACK = [  # (tool, what it is for, pattern in the HTML or in a tag-manager container)
    ("Google Analytics", "analytics", r"gtag/js\?id=G-|google-analytics\.com|G-[A-Z0-9]{8,12}\b"),
    ("Google Tag Manager", "tag manager", r"googletagmanager\.com/gtm\.js|GTM-[A-Z0-9]{5,9}"),
    ("Google Ads pixel", "ads", r"\bAW-\d{8,12}\b|googleadservices\.com|doubleclick\.net"),
    ("Meta pixel", "ads", r"connect\.facebook\.net|fbq\(|facebook\.com/tr\?"),
    ("TikTok pixel", "ads", r"analytics\.tiktok\.com|ttq\.load"),
    ("LinkedIn insight tag", "ads", r"snap\.licdn\.com|_linkedin_partner_id|px\.ads\.linkedin\.com"),
    ("X pixel", "ads", r"static\.ads-twitter\.com|twq\("),
    ("Reddit pixel", "ads", r"redditstatic\.com/ads|rdt\("),
    ("Microsoft Ads (UET)", "ads", r"bat\.bing\.com"),
    ("Snap pixel", "ads", r"sc-static\.net/scevent"),
    ("Pinterest tag", "ads", r"pinimg\.com/ct|pintrk\("),
    ("Segment", "analytics", r"cdn\.segment\.com|analytics\.load\("),
    ("RudderStack", "analytics", r"rudderlabs|rudderstack"),
    ("Amplitude", "analytics", r"amplitude\.com|cdn\.amplitude"),
    ("Mixpanel", "analytics", r"mixpanel"),
    ("PostHog", "analytics", r"posthog"),
    ("Heap", "analytics", r"heapanalytics|heap\.io"),
    ("Plausible", "analytics", r"plausible\.io"),
    ("Fathom", "analytics", r"usefathom\.com"),
    ("Vercel Analytics", "analytics", r"_vercel/insights|va\.vercel-scripts"),
    ("Hotjar", "session replay", r"hotjar"),
    ("FullStory", "session replay", r"fullstory"),
    ("Microsoft Clarity", "session replay", r"clarity\.ms"),
    ("LogRocket", "session replay", r"logrocket"),
    ("Optimizely", "A/B testing", r"optimizely"),
    ("VWO", "A/B testing", r"visualwebsiteoptimizer|vwo\.com"),
    ("Statsig", "A/B testing", r"statsig"),
    ("LaunchDarkly", "A/B testing", r"launchdarkly"),
    ("GrowthBook", "A/B testing", r"growthbook"),
    ("Intercom", "chat", r"intercom"),
    ("Drift", "chat", r"js\.driftt\.com|drift\.com"),
    ("Crisp", "chat", r"client\.crisp\.chat"),
    ("Zendesk", "chat", r"zdassets\.com|zendesk"),
    ("Qualified", "sales chat", r"qualified\.com"),
    ("HubSpot", "CRM and email", r"js\.hs-scripts\.com|hsforms|hubspot"),
    ("Marketo", "CRM and email", r"marketo|munchkin"),
    ("Customer.io", "lifecycle email", r"customer\.io|customerioforms"),
    ("Klaviyo", "lifecycle email", r"klaviyo"),
    ("Braze", "lifecycle email", r"braze"),
    ("Mailchimp", "email", r"chimpstatic|list-manage\.com"),
    ("beehiiv", "newsletter", r"beehiiv"),
    ("Substack", "newsletter", r"substack"),
    ("Rewardful", "affiliate program", r"rewardful|r\.wdfl\.co"),
    ("FirstPromoter", "affiliate program", r"firstpromoter"),
    ("PartnerStack", "affiliate program", r"partnerstack|grsm\.io"),
    ("Impact", "affiliate program", r"impact\.com|impactradius"),
    ("Tolt", "affiliate program", r"tolt\.io"),
    ("Dub", "links and affiliates", r"dubcdn\.com|dub\.co"),
    ("Viral Loops", "referral program", r"viral-loops"),
    ("Clearbit", "visitor identification", r"clearbit"),
    ("RB2B", "visitor identification", r"rb2b"),
    ("6sense", "visitor identification", r"6sc\.co|6sense"),
    ("Koala", "visitor identification", r"getkoala"),
    ("Apollo", "visitor identification", r"apollo\.io/.*tracker|assets\.apollo\.io"),
    ("Stripe", "payments", r"js\.stripe\.com"),
    ("Paddle", "payments", r"paddle\.com|cdn\.paddle"),
    ("Chargebee", "payments", r"chargebee"),
    ("Clerk", "sign-in", r"clerk\.(com|dev|accounts)"),
    ("Auth0", "sign-in", r"auth0"),
    ("Calendly", "booking", r"calendly"),
    ("Chili Piper", "booking", r"chilipiper"),
    ("Typeform", "forms", r"typeform"),
    ("Tally", "forms", r"tally\.so"),
    ("Webflow", "site builder", r"webflow"),
    ("Framer", "site builder", r"framerusercontent|framer\.com"),
    ("WordPress", "site builder", r"wp-content|wp-includes"),
    ("Shopify", "site builder", r"cdn\.shopify\.com"),
    ("Next.js", "framework", r"/_next/static|__NEXT_DATA__"),
    ("Sentry", "error tracking", r"sentry"),
    ("Datadog RUM", "error tracking", r"datadoghq|dd_rum"),
    ("Cookie banner (OneTrust, Cookiebot, Osano)", "consent", r"onetrust|cookiebot|osano"),
]

LINKS = [("x", r"https?://(?:www\.)?(?:x|twitter)\.com/(?!intent|share|home|i/|search)[A-Za-z0-9_]{1,15}\b"),
         ("instagram", r"https?://(?:www\.)?instagram\.com/[A-Za-z0-9_.]+"),
         ("tiktok", r"https?://(?:www\.)?tiktok\.com/@[A-Za-z0-9_.]+"),
         ("youtube", r"https?://(?:www\.)?youtube\.com/(?:@[A-Za-z0-9_.\-]+|c/[^\"'\s<>/]+|channel/[A-Za-z0-9_\-]+|user/[^\"'\s<>/]+)"),
         ("linkedin", r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/(?:company|school|showcase)/[A-Za-z0-9_\-%.]+"),
         ("facebook", r"https?://(?:www\.)?facebook\.com/(?!sharer|tr\b|plugins|dialog)[A-Za-z0-9_.\-/]+"),
         ("github", r"https?://(?:www\.)?github\.com/[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)?"),
         ("discord", r"https?://(?:www\.)?discord\.(?:gg|com/invite)/[A-Za-z0-9\-]+"),
         ("reddit", r"https?://(?:www\.)?reddit\.com/(?:r|user)/[A-Za-z0-9_\-]+"),
         ("threads", r"https?://(?:www\.)?threads\.(?:net|com)/@[A-Za-z0-9_.]+"),
         ("app store", r"https?://apps\.apple\.com/[^\"'\s<>]+"),
         ("google play", r"https?://play\.google\.com/store/apps/details\?id=[A-Za-z0-9_.]+"),
         ("chrome store", r"https?://chrom(?:e\.google\.com/webstore|ewebstore\.google\.com)/detail/[^\"'\s<>]+"),
         ("g2", r"https?://(?:www\.)?g2\.com/products/[A-Za-z0-9\-]+"),
         ("product hunt", r"https?://(?:www\.)?producthunt\.com/(?:posts|products)/[A-Za-z0-9\-]+")]

PAGES = [("pricing", r"pric|plans"), ("careers", r"career|jobs|join-us|work-with-us"), ("affiliates and partners", r"affiliat|partner|referral|ambassador|creator"),
         ("changelog", r"changelog|release|whats-new|updates"), ("blog", r"/blog|/resources|/learn"), ("docs", r"/docs|developers|/api\b"),
         ("templates and use cases", r"template|use-case|solutions|examples|gallery|showcase"), ("integrations", r"integration|/apps\b|connect"),
         ("compare", r"/vs|compare|alternative"), ("customers", r"customer|case-stud|stories"), ("sign up", r"sign-?up|signup|register|get-started|waitlist")]


def sitemap_urls(domain):
    robots = get(f"https://{domain}/robots.txt", timeout=20) or ""
    todo = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots) or [f"https://{domain}/sitemap.xml", f"https://{domain}/sitemap_index.xml",
                                                                 f"https://{domain}/sitemap-index.xml", f"https://www.{domain}/sitemap.xml"]
    seen, rows, blocked = set(), {}, []
    while todo and len(seen) < 150 and len(rows) < 150000:
        u = todo.pop(0)
        if u in seen:
            continue
        seen.add(u)
        x = get(u, timeout=40)
        if not x or "<loc" not in x:
            blocked.append(u)
            continue
        for block in re.findall(r"<sitemap>(.*?)</sitemap>", x, re.S):
            m = re.search(r"<loc>\s*(.*?)\s*</loc>", block, re.S)
            if m:
                todo.append(html.unescape(m.group(1)))
        for block in re.findall(r"<url>(.*?)</url>", x, re.S):
            m = re.search(r"<loc>\s*(.*?)\s*</loc>", block, re.S)
            if m:
                lm = re.search(r"<lastmod>\s*(.*?)\s*</lastmod>", block, re.S)
                rows.setdefault(html.unescape(m.group(1)), (lm.group(1)[:10] if lm else ""))
    return rows, sorted(seen - set(blocked)), blocked


def family(url, domain):
    """-> (family, page without its language folder, language folder or '')."""
    p = urllib.parse.urlparse(url)
    host = bare(p.netloc)
    segs = [s for s in p.path.split("/") if s]
    loc = ""
    while segs and LOCALE.match(segs[0]):
        loc, segs = segs[0], segs[1:]
    sub = "" if host == domain else host
    page = sub + "/" + "/".join(segs)
    if len(segs) <= 1:
        return (sub + " " if sub else "") + "(top-level pages)", page, loc
    return sub + "/" + segs[0] + "/", page, loc


def cmd_site(args):
    domain, d = bare(args[0]), out_dir(args)
    listed = opt(args, "--urls")                                         # context.dev's web-map answer, or any file with the URLs in it
    if listed:
        found = re.findall(r"https?://[^\s\"'\\<>,)\]]+", open(listed, errors="replace").read())
        urls = {u.rstrip("/.") or u: "" for u in found if bare(u) == domain or bare(u).endswith("." + domain)}
        maps, blocked = [listed], []
    else:
        print(f"reading {domain}'s sitemaps...")
        urls, maps, blocked = sitemap_urls(domain)
    fams = defaultdict(list)
    for u, lm in urls.items():
        f, page, loc = family(u, domain)
        fams[f].append((u, lm, page, loc))
    write_csv(os.path.join(d, "site/urls.csv"), [{"url": u, "family": family(u, domain)[0], "page": family(u, domain)[1], "language": family(u, domain)[2], "lastmod": lm}
                                                 for u, lm in sorted(urls.items())])
    rows = []
    for f, items in sorted(fams.items(), key=lambda kv: -len(set(i[2] for i in kv[1]))):
        dates = sorted(lm for _, lm, _, _ in items if lm)
        pages = Counter(i[2] for i in items)
        rows.append({"family": f, "pages": len(pages), "urls": len(items), "languages": len(set(i[3] for i in items if i[3])) + (1 if any(not i[3] for i in items) else 0),
                     "share_of_pages": "", "oldest_lastmod": dates[0] if dates else "", "newest_lastmod": dates[-1] if dates else "",
                     "example": min((u for u, _, _, _ in items), key=len), "pages_named": ", ".join(p for p, _ in pages.most_common(25)) if f.endswith("(top-level pages)") else ""})
    total_pages = sum(r["pages"] for r in rows)
    for r in rows:
        r["share_of_pages"] = f"{100 * r['pages'] / max(1, total_pages):.1f}%"
    write_csv(os.path.join(d, "site/families.csv"), rows)
    langs = len(set(i[3] for items in fams.values() for i in items if i[3]))
    print(f"  {len(urls)} URLs = {total_pages} distinct pages" + (f" in {langs + 1} languages" if langs else "") + f", {len(fams)} page families"
          + (" (from the file given: a sample, not the whole site)" if listed else f", from {len(maps)} sitemap files") + (f" ({len(blocked)} sitemap URLs unreadable)" if blocked else ""))
    for r in rows[:14]:
        print(f"  {r['pages']:>7} pages  {r['share_of_pages']:>6}  {r['languages']:>3} lang  {r['family']:<30} {r['example'][:60]}")
        if r["pages_named"]:
            print(f"           top-level pages: {r['pages_named'][:300]}")
    if not urls:
        print("  the site refused this script or has no sitemap. Don't work around it: map it with context.dev's web-map, save its answer to a file, and run again with --urls <file>")

    src = opt(args, "--html")
    page = open(src, errors="replace").read() if src else (get(f"https://{domain}/") or get(f"https://www.{domain}/") or "")   # --html: the page, or the script/link lists context.dev returned
    if not page:
        print("  the site refused this script. Don't work around it: read the homepage with context.dev's web-scrape and note the stack as 'not read' unless you save its HTML and pass --html <file>")
        return
    hay = [("homepage HTML", page)]
    for gtm in sorted(set(re.findall(r"GTM-[A-Z0-9]{5,9}", page)))[:3]:        # a tag-manager container lists what it loads
        js = get(f"https://www.googletagmanager.com/gtm.js?id={gtm}", timeout=20)
        if js:
            hay.append((f"inside tag manager {gtm}", js))
    stack = []
    page_only = ("site builder", "framework", "payments", "sign-in", "forms", "booking", "error tracking", "consent", "newsletter", "tag manager")
    for tool, kind, pat in STACK:
        for where, text in hay:
            if where != hay[0][0]:                                         # a container's own code names many vendors: trust it only for tags, by their full addresses
                if kind in page_only or tool == "Google Ads pixel":
                    continue
                pat = "|".join(x for x in pat.split("|") if "\\." in x) or pat
            m = re.search(pat, text, re.I)
            if m:
                stack.append({"tool": tool, "for": kind, "seen_in": where, "evidence": text[max(0, m.start() - 30):m.end() + 30].replace("\n", " ")[:110]})
                break
    write_csv(os.path.join(d, "site/stack.csv"), stack, ["tool", "for", "seen_in", "evidence"])
    links = defaultdict(list)
    for kind, pat in LINKS:
        for m in re.findall(pat, page):
            m = m.rstrip("/.,\\")
            if m not in links[kind] and not re.search(r"/(share|intent|sharer|login|signup|legal|privacy|policies|about|help)\b", m):
                links[kind].append(m)
    hrefs = sorted(set(re.findall(r'href="(/[^"#?]{1,80}|https?://[^"#?]{1,120})', page) + re.findall(r"(?m)^\s*(/[^\s#?]{1,80}|https?://[^\s#?]{1,120})\s*$", page)))
    pages = {}
    for name, pat in PAGES:
        hit = [h for h in hrefs if re.search(pat, h, re.I) and (h.startswith("/") or domain in h)]
        if hit:
            pages[name] = hit[:6]
    write_json(os.path.join(d, "site/links.json"), {"domain": domain, "read": str(TODAY), "socials": links, "pages": pages,
                                                     "title": (re.search(r"<title[^>]*>(.*?)</title>", page, re.S) or [None, ""])[1].strip()[:200]})
    by = defaultdict(list)
    for s in stack:
        by[s["for"]].append(s["tool"])
    print("  stack seen: " + ("; ".join(f"{k}: {', '.join(v)}" for k, v in by.items()) or "nothing recognised"))
    print("  social links in the homepage: " + (", ".join(f"{k} {v[0].split('/')[-1]}" for k, v in links.items()) or "none in the HTML (the page may draw them with JavaScript: use context.dev's brand data)"))
    print("  pages linked: " + (", ".join(f"{k} ({v[0]})" for k, v in pages.items()) or "none found in what was read"))
    print(f"  wrote {d}/site/")


# ---------------------------------------------------------------- dated signals: Wayback, Wikipedia

def cmd_wayback(args):
    domain, d = bare(args[0]), out_dir(args)
    x = get(f"http://web.archive.org/cdx/search/cdx?url={domain}&output=json&fl=timestamp&collapse=timestamp:8&from={TODAY.year - 6}", timeout=90)
    days = Counter()
    try:
        for (ts,) in json.loads(x)[1:]:
            days[f"{ts[:4]}-{ts[4:6]}"] += 1
    except Exception:
        print("  the Wayback Machine did not answer: skip it, the other dated signals still work")
    if days:
        ms = months_between(min(days), month(TODAY))
        write_csv(os.path.join(d, "site/wayback.csv"), [{"month": m, "value": days.get(m, 0)} for m in ms])
        print(f"  homepage first saved {min(days)}; days saved per month, last 6: " + ", ".join(f"{m} {days.get(m, 0)}" for m in ms[-6:]))
    pages = [u.strip() for u in (opt(args, "--pages") or "").split(",") if u.strip()]     # full addresses, or paths like /pricing
    if not pages:                                                          # default: each page family's example page
        pages = [r["example"] for r in read_csv(os.path.join(d, "site/families.csv")) if r.get("example")][:10]
    rows = []
    for u in pages:                                                        # one exact address: its saves come back oldest first, and quickly
        u = u if u.startswith("http") else f"https://{domain}{u if u.startswith('/') else '/' + u}"
        x = get("http://web.archive.org/cdx/search/cdx?output=json&fl=timestamp&filter=statuscode:200&limit=1&url=" + urllib.parse.quote(re.sub(r"^https?://", "", u), safe="/"), timeout=45, tries=1)
        try:
            ts = json.loads(x)[1][0]
            rows.append({"page": u, "first_saved": f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"})
        except Exception:
            rows.append({"page": u, "first_saved": ""})
    if rows:
        write_csv(os.path.join(d, "site/first_seen.csv"), rows)
        for r in rows:
            print(f"  first saved {r['first_saved'] or 'never (or the archive did not answer)':<12} {r['page'][:80]}")
    print("  a page can exist before its first save: treat these as 'no later than'.")


def cmd_wiki(args):
    domain, d = bare(args[0]), out_dir(args)
    title = opt(args, "--title")
    if not title:
        x = get("https://en.wikipedia.org/w/api.php?action=query&list=exturlusage&eunamespace=0&eulimit=50&format=json&euquery=" + urllib.parse.quote(domain))
        try:
            hits = json.loads(x)["query"]["exturlusage"]
        except Exception:
            hits = []
        own = [h["title"] for h in hits if bare(h["url"]) == domain and urllib.parse.urlparse(h["url"]).path in ("", "/")]
        if not own:
            print(f"  no English Wikipedia article lists {domain} as its website: no page-view curve (pass --title if you know the article)")
            return
        title = own[0]
        if len(set(own)) > 1:
            print(f"  several articles link the homepage ({', '.join(sorted(set(own))[:4])}): using {title!r}; pass --title to choose")
    x = get("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/" + urllib.parse.quote(title.replace(" ", "_"), safe="")
            + f"/monthly/2015070100/{TODAY.year}{TODAY.month:02d}0100", headers={"User-Agent": "reverse-growth skill (public page views)"})
    try:
        rows = [{"month": f"{i['timestamp'][:4]}-{i['timestamp'][4:6]}", "value": i["views"]} for i in json.loads(x)["items"]]
    except Exception:
        print(f"  Wikipedia has no page views for {title!r}")
        return
    rows = [r for r in rows if r["month"] < month(TODAY)]                 # the running month is not complete
    write_csv(os.path.join(d, "curve/wikipedia.csv"), rows)
    write_json(os.path.join(d, "curve/wikipedia.json"), {"article": title, "url": "https://en.wikipedia.org/wiki/" + title.replace(" ", "_"), "read": str(TODAY)})
    print(f"  {title!r}: {len(rows)} months of page views, first {rows[0]['month']} ({rows[0]['value']}), latest {rows[-1]['month']} ({rows[-1]['value']})")


# ---------------------------------------------------------------- open feeds: YouTube and X

def yt_data(page):
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", page or "", re.S)
    try:
        return json.loads(m.group(1))
    except Exception:
        return None


def walk(o, key, out):
    if isinstance(o, dict):
        if key in o:
            out.append(o[key])
        for v in o.values():
            walk(v, key, out)
    elif isinstance(o, list):
        for v in o:
            walk(v, key, out)
    return out


def contents(o, out):
    if isinstance(o, dict):
        if isinstance(o.get("content"), str):
            out.append(o["content"])
        for v in o.values():
            contents(v, out)
    elif isinstance(o, list):
        for v in o:
            contents(v, out)
    return out


def cmd_youtube(args):
    h, d = args[0].strip().rstrip("/"), out_dir(args)
    base = h if h.startswith("http") else "https://www.youtube.com/" + (h if h.startswith("@") or h.startswith("channel/") else "@" + h)
    ck = {"Cookie": "CONSENT=YES+1; SOCS=CAI"}
    page = get(base + "/videos", headers=ck)
    data = yt_data(page)
    if not data:
        print("  YouTube did not return the channel page: note the channel as 'not read'")
        return
    posts = {}
    for l in walk(data, "lockupViewModel", []):
        vid = l.get("contentId")
        t = contents(l.get("metadata", {}), [])
        if not vid or not t:
            continue
        length = re.findall(r'"text": "(\d+:\d\d(?::\d\d)?)"', json.dumps(l.get("contentImage", {})))
        views = next((x for x in t[1:4] if re.fullmatch(r"[\d.,]+[KMB]?( views?)?", x)), None)
        age = next((x for x in t[1:5] if REL.search(x)), None)
        day, exact = when(age)
        posts[vid] = {"id": vid, "url": f"https://www.youtube.com/watch?v={vid}", "kind": "video", "title": t[0], "views": num(views), "date": str(day) if day else "",
                      "date_exact": exact, "length": length[0] if length else "", "image": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg"}
    for v in walk(data, "videoRenderer", []):                              # the older page layout
        vid = v.get("videoId")
        if vid and vid not in posts:
            day, exact = when((v.get("publishedTimeText") or {}).get("simpleText"))
            posts[vid] = {"id": vid, "url": f"https://www.youtube.com/watch?v={vid}", "kind": "video", "title": "".join(r.get("text", "") for r in (v.get("title") or {}).get("runs", [])),
                          "views": num((v.get("viewCountText") or {}).get("simpleText")), "date": str(day) if day else "", "date_exact": exact,
                          "length": (v.get("lengthText") or {}).get("simpleText", ""), "image": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg"}
    shorts = yt_data(get(base + "/shorts", headers=ck)) or {}
    for s in walk(shorts, "shortsLockupViewModel", []):
        vid = (((s.get("onTap") or {}).get("innertubeCommand") or {}).get("reelWatchEndpoint") or {}).get("videoId")
        m = re.match(r"(.*), ([\d.,]+ ?(?:thousand|million|billion|[KMB])?) views?", s.get("accessibilityText", ""))
        if vid and m:
            v = m.group(2).replace(" thousand", "K").replace(" million", "M").replace(" billion", "B")
            posts[vid] = {"id": vid, "url": f"https://www.youtube.com/shorts/{vid}", "kind": "short", "title": m.group(1), "views": num(v), "date": "", "date_exact": False,
                          "length": "", "image": f"https://i.ytimg.com/vi/{vid}/frame0.jpg"}
    cid = (re.search(r'"externalId":"(UC[\w-]+)"', page) or re.search(r'"channelId":"(UC[\w-]+)"', page) or [None, None])[1]
    feed = get(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}") if cid else None
    exact_n = 0
    for e in re.findall(r"<entry>(.*?)</entry>", feed or "", re.S):        # the feed has exact dates and view counts for the newest 15
        vid = (re.search(r"<yt:videoId>(.*?)</yt:videoId>", e) or [None, None])[1]
        pub = (re.search(r"<published>(.*?)</published>", e) or [None, ""])[1][:10]
        vw = re.search(r'<media:statistics views="(\d+)"', e)
        if vid:
            p = posts.setdefault(vid, {"id": vid, "url": f"https://www.youtube.com/watch?v={vid}", "kind": "video", "length": "",
                                       "title": html.unescape((re.search(r"<title>(.*?)</title>", e, re.S) or [None, ""])[1]), "image": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg"})
            p["date"], p["date_exact"] = pub, True
            if vw:
                p["views"] = float(vw.group(1))
            exact_n += 1
    subs = re.search(r'"content":"([\d.,KMB]+) subscribers"', page)
    total = re.search(r'"content":"([\d.,KMB]+) videos"', page)
    rows = list(posts.values())
    for r in rows:                                                          # a feed entry that is a Short keeps its exact date
        if r["kind"] == "short":
            r["url"] = f"https://www.youtube.com/shorts/{r['id']}"
    head = {"channel": "youtube", "handle": base.split("/")[-1], "pulled": str(TODAY), "followers": subs.group(1) if subs else None, "total_posts": total.group(1) if total else None}
    write_json(os.path.join(d, "content/youtube/posts.json"), {**head, "source": base + "/videos and the channel feed",
                                                                "note": "dates are exact for the newest 15 uploads (the feed); older ones are YouTube's rounded age ('2mo ago')",
                                                                "posts": [r for r in rows if r["kind"] == "video"]})
    if any(r["kind"] == "short" for r in rows):                             # a different format: ranked on its own, never against long videos
        write_json(os.path.join(d, "content/youtube-shorts/posts.json"), {**head, "source": base + "/shorts",
                                                                           "note": "the Shorts tab gives views but no dates, so none can be set aside as under 7 days old", "posts": [r for r in rows if r["kind"] == "short"]})
    kinds = Counter(r["kind"] for r in rows)
    print(f"  {base.split('/')[-1]}: {subs.group(1) if subs else '?'} subscribers, {total.group(1) if total else '?'} videos; read {kinds.get('video', 0)} videos and {kinds.get('short', 0)} Shorts, {exact_n} with exact dates")


def cmd_x(args):
    h, d = args[0].strip().lstrip("@").split("/")[-1], out_dir(args)
    page = get(f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{h}", timeout=30)
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', page or "", re.S)
    try:
        entries = json.loads(m.group(1))["props"]["pageProps"]["timeline"]["entries"]
    except Exception:
        print(f"  X's public timeline for @{h} did not load (it limits how often it answers): try again in a few minutes, else note X as 'not read'")
        return
    rows, user = [], {}
    for e in entries:
        t = (e.get("content") or {}).get("tweet")
        if not t:
            continue
        u = t.get("user") or {}
        mine = u.get("screen_name", "").lower() == h.lower()
        if mine:
            user = u
        media = (t.get("extended_entities") or {}).get("media") or []
        day, _ = when(t.get("created_at"))
        text = t.get("full_text") or t.get("text") or ""
        repost = text.startswith("RT @") or bool(t.get("retweeted_status")) or not mine
        rows.append({"id": t.get("id_str"), "url": f"https://x.com/{u.get('screen_name', h)}/status/{t.get('id_str')}", "kind": "repost" if repost else ("reply" if t.get("in_reply_to_status_id_str") or text.startswith("@") else "post"),
                     "text": text, "date": str(day) if day else "", "date_exact": True, "likes": t.get("favorite_count"), "reposts": t.get("retweet_count"), "replies": t.get("reply_count"),
                     "quotes": t.get("quote_count"), "media": media[0].get("type") if media else "none", "image": media[0].get("media_url_https") if media else ""})
    bio = " ".join(str(user.get(k) or "") for k in ("name", "description")).strip()
    site = " ".join(u.get("expanded_url", "") for u in ((user.get("entities") or {}).get("url") or {}).get("urls", []))
    write_json(os.path.join(d, f"content/x-{h.lower()}/posts.json"), {"channel": "x", "handle": h, "pulled": str(TODAY), "followers": user.get("followers_count"), "bio": bio, "bio_link": site,
                                                                        "source": "X's public embed timeline (about the newest 20 posts, plus the pinned one)",
                                                                        "note": "this feed carries no view counts: posts are ranked on likes + reposts + replies + quotes", "posts": rows})
    own = [r for r in rows if r["kind"] == "post"]
    print(f"  @{h} bio: {bio[:160]!r} link: {site or 'none'}  (count the account only if this ties it to the company)")
    print(f"  @{h}: {user.get('followers_count', '?')} followers; read {len(rows)} entries, {len(own)} own posts, from {min((r['date'] for r in rows if r['date']), default='?')} to {max((r['date'] for r in rows if r['date']), default='?')}")


# ---------------------------------------------------------------- rows: a saved context.dev answer -> posts.json

def first(o, *names):
    for n in names:
        v = o
        for part in n.split("."):
            v = v.get(part) if isinstance(v, dict) else None
        if v not in (None, "", [], {}):
            return v
    return None


def cmd_rows(args):
    """Claude Code saves a long tool answer to a file and says where. This reads the posts out of it, so no number or image link is retyped."""
    ch, src, d = args[0].lower(), args[1], out_dir(args)
    text = open(src, errors="replace").read()
    try:
        doc = json.loads(text)
        if isinstance(doc, list):                                           # a list of text blocks
            doc = json.loads("".join(b.get("text", "") for b in doc if isinstance(b, dict)))
    except Exception:
        sys.exit(f"{src} is not a saved context.dev answer (JSON). Write the rows by hand in the shape the skill gives.")
    lists = []
    for key in ("latest_posts", "videos", "posts"):
        for found in walk(doc, key, []):
            if isinstance(found, list) and found and isinstance(found[0], dict):
                lists.append(found)
    if not lists:
        sys.exit("no list of posts in that answer (looked for latest_posts, videos, posts)")
    raw = max(lists, key=len)
    data = next((x for x in walk(doc, "data", []) if isinstance(x, dict) and ("follower_count" in x or "biography" in x)), {})
    handle = opt(args, "--handle") or data.get("username") or ""
    posts = []
    for r in raw:
        secs = first(r, "video_duration_seconds")
        kind = {"image": "photo", "text": "self"}.get(str(first(r, "type") or "post"), str(first(r, "type") or "post"))
        body = first(r, "caption", "body", "text") or ""
        imgs = r.get("images") or []
        owner = first(r, "owner.username", "author.username", "author")
        posts.append({"id": str(first(r, "shortcode", "id") or ""), "url": first(r, "url") or "", "date": str(first(r, "posted_at", "created_at", "date") or "")[:10], "kind": kind,
                      "title": first(r, "title") or str(body).split("\n")[0][:120], "text": str(body)[:200],
                      "image": first(r, "thumbnail_url") or (imgs[0].get("url") if imgs and isinstance(imgs[0], dict) else "") or (r.get("image_urls") or [""])[0],
                      "views": first(r, "view_count"), "likes": first(r, "like_count"), "comments": first(r, "comment_count"), "shares": first(r, "share_count"), "saves": first(r, "save_count"),
                      "score": first(r, "score"), "subreddit": first(r, "subreddit") or "", "length": f"{round(float(secs))}s" if secs else "", "owner": owner if isinstance(owner, str) else "",
                      "pinned": bool(r.get("is_pinned")), "paid": bool(r.get("is_paid_partnership") or r.get("is_ad") or r.get("sponsors"))})
    name = opt(args, "--as") or ch
    write_json(os.path.join(d, f"content/{name}/posts.json"), {"channel": ch, "handle": handle, "pulled": str(TODAY), "followers": data.get("follower_count"), "bio": data.get("biography"),
                                                                "source": doc.get("url") if isinstance(doc, dict) else "", "posts": posts})
    others = Counter(p["owner"] for p in posts if p["owner"] and handle and p["owner"].lower() != handle.lower())
    print(f"  {name}: {len(posts)} posts from {src.split('/')[-1]}" + (f"; {data.get('follower_count')} followers" if data.get("follower_count") else "")
          + (f"; {sum(others.values())} are other accounts' posts ({', '.join(others)}): collabs or tags, keep them but count them apart" if others and ch != "reddit" else ""))
    print("  first row: " + json.dumps({k: v for k, v in posts[0].items() if k != "image"}, ensure_ascii=False)[:300])


# ---------------------------------------------------------------- rank: engagement, bands, images, contact sheets

def engagement(ch, r, have_views):
    g = lambda k: num(r.get(k)) or 0
    if ch in ("youtube", "tiktok") or (ch == "x" and have_views):
        return g("views"), "views"
    if ch == "x":
        return g("likes") + g("reposts") + g("replies") + g("quotes"), "likes + reposts + replies + quotes"
    if ch == "reddit":
        return g("score"), "score"
    if ch == "linkedin":
        return g("likes") + g("comments"), "reactions + comments"
    if ch == "instagram":
        return g("likes") + g("comments"), "likes + comments"
    return (g("views"), "views") if have_views else (g("likes") + g("comments"), "likes + comments")


def font(size):
    from PIL import ImageFont
    for p in ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/SFNS.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


def short(n):
    n = float(n or 0)
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.1f}K" if n >= 1e4 else f"{n:,.0f}"


def sheet(path, top, bottom, unit, n_top, n_bottom):
    from PIL import Image, ImageDraw
    tw, pad, lab = 230, 10, 34
    size = {"TOP": n_top, "BOTTOM": n_bottom}
    rows = [("TOP", top), ("BOTTOM", bottom)]
    rows = [(n, [r for r in rs if r.get("_img")]) for n, rs in rows]
    rows = [(n, rs) for n, rs in rows if rs]
    if not rows:
        return None
    cols = min(8, max(len(rs) for _, rs in rows))
    tiles = {}
    for _, rs in rows:
        for r in rs[:16]:
            try:
                im = Image.open(r["_img"]).convert("RGB")
                im.thumbnail((tw, 330))
                tiles[r["id"]] = im
            except Exception:
                pass
    W = pad + cols * (tw + pad)
    lines = [(n, size[n], [rs[i:i + cols] for i in range(0, min(len(rs), 16), cols)]) for n, rs in rows]
    tall = lambda chunk: max([tiles[r["id"]].height for r in chunk if r["id"] in tiles] or [40])
    H = pad + sum(30 + sum(tall(c) + lab + pad for c in chunks) for _, _, chunks in lines)
    img = Image.new("RGB", (W, H), (255, 255, 255))
    dr = ImageDraw.Draw(img)
    f1, f2 = font(18), font(13)
    y = pad
    for name, total, chunks in lines:
        shown = sum(len(c) for c in chunks)
        dr.text((pad, y), f"{name}: {total} posts" + (f" ({shown} shown)" if shown < total else ""), font=f1, fill=(20, 20, 20) if name == "TOP" else (150, 60, 50))
        y += 30
        for chunk in chunks:
            th = tall(chunk)
            for i, r in enumerate(chunk):
                x = pad + i * (tw + pad)
                im = tiles.get(r["id"])
                if im:
                    img.paste(im, (x + (tw - im.width) // 2, y + th - im.height))
                dr.text((x, y + th + 4), f"#{r['rank']}  {short(r['engagement'])} {unit.split(' ')[0]}", font=f2, fill=(30, 30, 30))
                dr.text((x, y + th + 19), (r.get("title") or r.get("text") or "").replace("\n", " ")[:34], font=f2, fill=(110, 110, 110))
            y += th + lab + pad
    img.save(path, quality=88)
    return path


def cmd_rank(args):
    d = args[0]
    base = os.path.join(d, "content")
    if not os.path.isdir(base):
        sys.exit(f"nothing in {base}: pull a channel first")
    try:
        from PIL import Image
    except ImportError:
        Image = None
        print("  Pillow is missing (pip3 install pillow): ranking only, no thumbnails or contact sheets")
    summary = []
    for name in sorted(os.listdir(base)):
        f = os.path.join(base, name, "posts.json")
        doc = read_json(f)
        if not doc:
            continue
        ch = (doc.get("channel") or name.split("-")[0]).lower()
        pulled, _ = when(doc.get("pulled"))
        pulled = pulled or TODAY
        posts = [p for p in doc.get("posts", []) if p.get("kind") not in ("repost", "reply")]
        have_views = sum(1 for p in posts if num(p.get("views")) is not None) >= 0.8 * max(1, len(posts))
        unit = "?"
        for p in posts:
            p["id"] = str(p.get("id") or p.get("url") or id(p))
            p["engagement"], unit = engagement(ch, p, have_views)
            day, exact = when(p.get("date"), pulled)
            p["age_days"] = (pulled - day).days if day else ""
            p["date"] = str(day) if day else ""
            p["settled"] = p["age_days"] == "" or p["age_days"] >= 7
            p["spread_per_day"] = round(p["engagement"] / max(1, p["age_days"]), 2) if p["age_days"] != "" else ""
        settled = sorted((p for p in posts if p["settled"]), key=lambda p: -p["engagement"])
        n = len(settled)
        if n >= 20:
            nt, nb, rule = math.ceil(n / 4), n // 2, "top quarter vs bottom half"
        elif n >= 12:
            nt, nb, rule = math.ceil(n / 3), n // 3, "small sample: top third vs bottom third"
        else:
            nt, nb, rule = 0, 0, "too few posts to call a pattern"
        for i, p in enumerate(settled):
            p["rank"] = i + 1
            p["band"] = "top" if i < nt else "bottom" if i >= n - nb else "middle"
        for p in posts:
            if not p["settled"]:
                p["rank"], p["band"] = "", "under 7 days old"
        sp = sorted((p["spread_per_day"] for p in settled if p["spread_per_day"] != ""), reverse=True)
        cut = sp[max(0, math.ceil(len(sp) / 4) - 1)] if len(sp) >= 8 else None
        for p in posts:
            p["fast_spreader"] = bool(cut is not None and p["spread_per_day"] != "" and p["spread_per_day"] >= cut and p["settled"])
        top = [p for p in settled if p["band"] == "top"] or settled[:5]
        bottom = [p for p in settled if p["band"] == "bottom"][-5:] if nb else []
        got = miss = 0
        if Image:
            os.makedirs(os.path.join(base, name, "img"), exist_ok=True)
            for tag, group in (("top", top), ("bottom", bottom)):
                for p in group:
                    dst = os.path.join(base, name, "img", f"{tag}-{p['rank']:02d}-{re.sub(r'[^A-Za-z0-9_-]', '', p['id'])[:24]}.jpg")
                    if not os.path.exists(dst) and p.get("image"):
                        b = get(p["image"], raw=True, timeout=25, tries=1)
                        try:
                            im = Image.open(io.BytesIO(b)).convert("RGB")
                            im.thumbnail((720, 720))
                            im.save(dst, quality=88)
                        except Exception:
                            pass
                    if os.path.exists(dst):
                        p["_img"] = dst
                        p["image_file"] = os.path.relpath(dst, d)
                        got += 1
                    else:
                        p["image_file"] = "not read"
                        miss += 1
            sheet(os.path.join(base, name, "sheet.jpg"), top, bottom, unit, len(top), nb or len(bottom))
        cols = ["rank", "band", "engagement", "date", "age_days", "spread_per_day", "fast_spreader", "kind", "title", "text", "views", "likes", "comments", "shares", "saves", "reposts",
                "replies", "quotes", "score", "length", "media", "subreddit", "owner", "pinned", "paid", "url", "image_file"]
        for p in posts:
            for k in ("title", "text"):
                if p.get(k):
                    p[k] = str(p[k]).replace("\n", " ")[:300]
        write_csv(os.path.join(base, name, "posts.csv"), sorted(posts, key=lambda p: (p["rank"] == "", p["rank"] or 0)), cols)
        dates = sorted(p["date"] for p in posts if p["date"])
        kinds = Counter(p.get("kind") or "post" for p in posts)
        s = {"channel": name, "ranked_on": unit, "posts": len(posts), "settled": n, "rule": rule, "top": nt, "bottom": nb, "from": dates[0] if dates else "", "to": dates[-1] if dates else "",
             "kinds": dict(kinds), "median": sorted(p["engagement"] for p in settled)[n // 2] if n else 0, "best": settled[0]["engagement"] if n else 0,
             "images_read": got, "images_not_read": miss, "followers": doc.get("followers")}
        summary.append(s)
        print(f"  {name:<22} {len(posts):>3} posts ({n} over 7 days old), {s['from']} to {s['to']}; ranked on {unit}; {rule}"
              + (f"; {nt} top / {nb} bottom" if nt else "") + f"; median {short(s['median'])}, best {short(s['best'])}; {got} images read" + (f", {miss} not read" if miss else ""))
    write_json(os.path.join(base, "summary.json"), summary)


# ---------------------------------------------------------------- ads

def cmd_ads(args):
    d = args[0]
    base = os.path.join(d, "ads")
    keep = [k.strip().lower() for k in (opt(args, "--advertiser") or "").split("|") if k.strip()]      # exact names, "A|B": a library search also returns namesakes
    allrows, summary = [], []
    for name in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        if not name.endswith(".json"):
            continue
        doc = read_json(os.path.join(base, name))
        net = doc.get("network") or name[:-5]
        pulled, _ = when(doc.get("pulled"))
        pulled = pulled or TODAY
        ads = doc.get("ads") or []
        mine = [a for a in ads if not keep or (a.get("advertiser") or "").strip().lower() in keep]
        for a in mine:
            day, _ = when(a.get("started"), pulled)
            a["network"], a["started"], a["days_running"] = net, str(day) if day else "", (pulled - day).days if day else ""
            allrows.append(a)
        runs = [a["days_running"] for a in mine if a["days_running"] != ""]
        clean = [re.sub(r"\s+", " ", (a.get("text") or a.get("headline") or "")).strip() for a in mine]
        texts = Counter(t[:160] for t in clean)
        tails = Counter(t.split(", ", 1)[1][:120] for t in clean if ", " in t[:60])     # "Visa, every off-brand deck..." / "Cisco, every off-brand deck..."
        if tails and tails.most_common(1)[0][1] >= 3 and tails.most_common(1)[0][1] > texts.most_common(1)[0][1]:
            tail, n = tails.most_common(1)[0]
            texts = Counter({"<a different name each time>, " + tail: n, **{t[:160]: c for t, c in Counter(t for t in clean if tail not in t).items()}})
        texts.pop("", None)
        oldest = max(mine, key=lambda a: a["days_running"] if a["days_running"] != "" else -1, default=None)
        summary.append({"network": net, "total_shown_by_library": doc.get("total") or "", "ads_read": len(ads), "from_this_advertiser": len(mine), "with_start_date": len(runs),
                        "running_60_days_plus": sum(1 for r in runs if r >= 60), "longest_run_days": max(runs) if runs else "", "oldest_started": oldest["started"] if oldest and runs else "",
                        "distinct_messages": len(texts), "most_repeated_message": (texts.most_common(1)[0][0] + f" (x{texts.most_common(1)[0][1]})") if texts else "",
                        "calls_to_action": ", ".join(f"{k} x{v}" for k, v in Counter(a.get("cta") for a in mine if a.get("cta")).most_common(3)), "library_url": doc.get("source") or ""})
    if not summary:
        sys.exit(f"nothing in {base}: save each ad library as ads/<network>.json first")
    write_csv(os.path.join(base, "ads.csv"), allrows, ["network", "advertiser", "started", "days_running", "format", "headline", "text", "cta", "landing", "id", "url"])
    write_csv(os.path.join(base, "summary.csv"), summary)
    for s in summary:
        print(f"  {s['network']:<10} library shows {s['total_shown_by_library'] or '?'}; read {s['ads_read']}, {s['from_this_advertiser']} from this advertiser; "
              + (f"{s['running_60_days_plus']} running 60+ days, longest {s['longest_run_days']} days (since {s['oldest_started']}); " if s["with_start_date"] else "no start dates on this library's list; ")
              + f"{s['distinct_messages']} distinct messages")


# ---------------------------------------------------------------- curve: monthly series and the inflection

SERIES = [("traffic", "estimated monthly visits (supplied)"), ("brand_search", "Google searches for the brand name (supplied)"), ("wikipedia", "Wikipedia page views (people looking the company up)"),
          ("reviews", "new reviews"), ("news", "news articles naming the company"), ("wayback", "days the Wayback Machine saved the homepage")]


def steps(vals):
    """Every month where the next three months all stay above the average of the three before: (index, before avg, after avg)."""
    out = []
    for i in range(3, len(vals) - 2):
        b, a = sum(vals[i - 3:i]) / 3, sum(vals[i:i + 3]) / 3
        if a > 0 and min(vals[i:i + 3]) > b:
            out.append((i, b, a))
    return out


def inflection(vals):
    """The take-off: the first month the three-month level at least triples and reaches a tenth of the series' peak.
    With no take-off, the largest sustained step up in absolute terms. -> (index, step, before, after, kind) or None."""
    st = steps(vals)
    if not st:
        return None
    peak = max(vals)
    for i, b, a in st:
        if a >= 3 * max(b, 1e-9) and a >= 0.1 * peak:
            return (i, a - b, b, a, "take-off")
    i, b, a = max(st, key=lambda x: x[2] - x[1])
    return (i, a - b, b, a, "largest step up")


def later_steps(vals, after_i):
    """Up to three further step ups after the take-off, at least six months apart, largest first."""
    picked = []
    for i, b, a in sorted((x for x in steps(vals) if x[0] >= after_i + 6), key=lambda x: x[1] - x[2]):
        if all(abs(i - j) >= 6 for j, _, _ in picked):
            picked.append((i, b, a))
        if len(picked) == 3:
            break
    return sorted(picked)


def load_series(d):
    out = {}
    for name, label in SERIES:
        f = os.path.join(d, "site/wayback.csv") if name == "wayback" else os.path.join(d, f"curve/{name}.csv")
        rows = read_csv(f)
        if rows:
            out[name] = {r["month"]: float(r["value"] or 0) for r in rows if r.get("month")}
    news = read_json(os.path.join(d, "news.json"))
    if news and "news" not in out:
        c = Counter()
        for a in news.get("articles", news if isinstance(news, list) else []):
            day, _ = when(a.get("date") or a.get("published_at"))
            if day:
                c[month(day)] += 1
        if c:
            out["news"] = dict(c)
    for f in sorted(os.listdir(os.path.join(d, "curve"))) if os.path.isdir(os.path.join(d, "curve")) else []:
        n = f[:-4]
        if f.endswith(".csv") and n not in out and n != "monthly":
            rows = read_csv(os.path.join(d, "curve", f))
            if rows and "month" in rows[0] and "value" in rows[0]:
                out[n] = {r["month"]: float(r["value"] or 0) for r in rows}
    return out


def usable(s):
    """Enough to read a step from: 8 months with something in them and 40 counted in all."""
    return sum(1 for v in s.values() if v) >= 8 and sum(s.values()) >= 40


def primary(series):
    for name, _ in SERIES:
        if name in series and usable(series[name]) and name != "wayback":       # how often an archive saved a page is context, never a growth curve
            return name
    for name in series:
        if name not in dict(SERIES) and usable(series[name]):
            return name
    return None


def cmd_curve(args):
    d = args[0]
    series = load_series(d)
    if not series:
        sys.exit("no monthly series yet: run wiki or wayback, or save one as curve/<name>.csv with the columns month,value")
    lo = max(min(min(s) for s in series.values()), f"{TODAY.year - 5}-{TODAY.month:02d}")
    ms = [m for m in months_between(lo, month(TODAY)) if m < month(TODAY)]
    labels = dict(SERIES)
    for n in series:
        own = read_json(os.path.join(d, f"curve/{n}.json")) or {}
        if own.get("label"):
            labels[n] = own["label"]
    rows, info = [], {}
    for m in ms:
        rows.append({"month": m, **{n: (s.get(m, "") if n != "news" else s.get(m, 0)) for n, s in series.items()}})
    for n, s in series.items():
        span = [m for m in ms if m >= min(s)]
        vals = [s.get(m, 0) for m in span]
        inf = inflection(vals)
        info[n] = {"label": labels.get(n, n), "months": len(span), "from": span[0] if span else "", "latest": vals[-1] if vals else 0}
        if inf:
            i, step, b, a, kind = inf
            info[n].update({"inflection": span[i], "kind": kind, "before_avg": round(b, 1), "after_avg": round(a, 1), "times": round(a / b, 2) if b else None,
                            "later_steps": [{"month": span[j], "before_avg": round(b2, 1), "after_avg": round(a2, 1)} for j, b2, a2 in later_steps(vals, i)]})
        for r in rows:
            j = span.index(r["month"]) if r["month"] in span else -1
            r[n + "_growth_pct"] = round(100 * (vals[j] - vals[j - 1]) / vals[j - 1], 1) if j > 0 and vals[j - 1] else ""
    p = primary(series)
    info["_primary"] = p
    write_csv(os.path.join(d, "curve/monthly.csv"), rows)
    write_json(os.path.join(d, "curve/curve.json"), info)
    for n, i in info.items():
        if n.startswith("_"):
            continue
        thin = "" if usable(series[n]) else "  [too thin to read a step from]"
        print(f"  {'*' if n == p else ' '} {n:<12} {i['label']}: {i['months']} months from {i['from']}; "
              + (f"{i['kind']} in {i['inflection']} ({short(i['before_avg'])} a month before -> {short(i['after_avg'])} after" + (f", x{i['times']}" if i.get("times") else "") + ")"
                 + ("; later steps: " + ", ".join(f"{x['month']} ({short(x['before_avg'])} -> {short(x['after_avg'])})" for x in i["later_steps"]) if i.get("later_steps") else "")
                 if i.get("inflection") else "no sustained step up") + thin)
    if p:
        print("  * = the series the moves are lined up against. None of these is traffic unless you supplied curve/traffic.csv: name the series when you quote it.")
    else:
        print("  no series is strong enough to call a curve. Say 'no curve': date the moves, list the reported numbers (users, revenue, raises) from the news, and skip the lift sums.")


# ---------------------------------------------------------------- moves vs growth

def spearman(a, b):
    def ranks(v):
        o = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
                j += 1
            for k in range(i, j + 1):
                r[o[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    ra, rb = ranks(a), ranks(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return round(sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / den, 2) if den else None


def cmd_moves(args):
    d = args[0]
    moves = read_json(os.path.join(d, "moves.json"))
    series = load_series(d)
    p = primary(series)
    if not moves:
        sys.exit("needs moves.json: a list of {date, channel, move, link, reach}")
    if not p:
        rows = []
        for mv in moves:
            day, _ = when(mv.get("date"))
            if day:
                rows.append({**mv, "date": str(day)})
        rows.sort(key=lambda r: r["date"])
        write_csv(os.path.join(d, "moves-vs-growth.csv"), rows, ["date", "channel", "move", "reach", "link"])
        print(f"  {len(rows)} dated moves written in date order. No monthly series is strong enough to measure a lift against: none is claimed.")
        return
    s = series[p]
    label = (read_json(os.path.join(d, f"curve/{p}.json")) or {}).get("label") or dict(SERIES).get(p, p)
    ms = [m for m in months_between(min(s), max(s)) if m < month(TODAY)]
    vals = [s.get(m, 0) for m in ms]
    growth = {ms[i]: (100 * (vals[i] - vals[i - 1]) / vals[i - 1] if vals[i - 1] else None) for i in range(1, len(ms))}

    def g(m, offs):
        if m not in ms:
            return None
        i = ms.index(m)
        xs = [growth.get(ms[i + o]) for o in offs if 0 <= i + o < len(ms)]
        xs = [x for x in xs if x is not None]
        return sum(xs) / len(xs) if xs else None
    rows = []
    for mv in moves:
        day, _ = when(mv.get("date"))
        if day:
            rows.append({**mv, "date": str(day), "month": month(day), "_day": day})
    rows.sort(key=lambda r: r["_day"])
    cid = 0
    for i, r in enumerate(rows):
        if i == 0 or (r["_day"] - rows[i - 1]["_day"]).days > 31:
            cid += 1
        r["cluster"] = cid
    size = Counter(r["cluster"] for r in rows)
    first = {}
    for r in rows:
        first.setdefault(r["cluster"], r["month"])
    for r in rows:
        m = first[r["cluster"]]
        b, a = g(m, (-2, -1)), g(m, (0, 1, 2))
        r["growth_before_pct"] = round(b, 1) if b is not None else ""
        r["growth_after_pct"] = round(a, 1) if a is not None else ""
        r["lift_pts"] = round(a - b, 1) if a is not None and b is not None else ""
        r["cluster_size"] = size[r["cluster"]]
        r["measured_on"] = label
    write_csv(os.path.join(d, "moves-vs-growth.csv"), rows, ["date", "channel", "move", "reach", "cluster", "cluster_size", "growth_before_pct", "growth_after_pct", "lift_pts", "measured_on", "link"])
    seen, tops = set(), []
    for r in sorted((r for r in rows if r["lift_pts"] != ""), key=lambda r: -r["lift_pts"]):
        if r["cluster"] not in seen:
            seen.add(r["cluster"])
            tops.append(r)
    print(f"  {len(rows)} dated moves in {cid} clusters, lined up against {label} ({len(ms)} months, {ms[0]} to {ms[-1]})")
    for r in tops[:3]:
        names = "; ".join(x["move"][:50] for x in rows if x["cluster"] == r["cluster"])[:150]
        print(f"  lift {r['lift_pts']:+} pts ({r['growth_before_pct']}% a month before -> {r['growth_after_pct']}% after) from {first[r['cluster']]}: {names}")
    chans = defaultdict(Counter)
    for r in rows:
        chans[r.get("channel") or "?"][r["month"]] += 1
    corr = []
    for ch, c in chans.items():
        if len(ms) < 12 or sum(c.values()) < 5:
            corr.append({"channel": ch, "moves": sum(c.values()), "note": "under 12 months or under 5 moves: no correlation called"})
            continue
        row = {"channel": ch, "moves": sum(c.values()), "months": len(ms) - 1}
        for lag in (0, 1, 2):
            pairs = [(c.get(ms[i], 0), growth.get(ms[i + lag])) for i in range(1, len(ms) - lag) if growth.get(ms[i + lag]) is not None]
            row[f"spearman_lag{lag}"] = spearman([x for x, _ in pairs], [y for _, y in pairs]) if len(pairs) >= 12 else ""
        corr.append(row)
        print(f"  {ch}: {row['moves']} moves; rank correlation with growth the same month {row['spearman_lag0']}, a month later {row['spearman_lag1']}, two months later {row['spearman_lag2']}")
    write_csv(os.path.join(d, "moves-by-channel.csv"), corr, ["channel", "moves", "months", "spearman_lag0", "spearman_lag1", "spearman_lag2", "note"])
    print("  a lift is what the numbers did around a move. It does not show the move caused it: monthly data, overlapping moves, other causes.")


# ---------------------------------------------------------------- report: playbook.md -> one-file playbook.html

CSS = """
:root{--bg:#fff;--fg:#16181d;--mut:#667085;--line:#e4e7ec;--soft:#f6f7f9;--acc:#2563eb;--seen:#0f7b4f;--inf:#b4540a}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0e1014;--fg:#e8eaee;--mut:#98a2b3;--line:#262a33;--soft:#161a21;--acc:#7aa7ff;--seen:#4fd1a1;--inf:#f0a45d}}
:root[data-theme=dark]{--bg:#0e1014;--fg:#e8eaee;--mut:#98a2b3;--line:#262a33;--soft:#161a21;--acc:#7aa7ff;--seen:#4fd1a1;--inf:#f0a45d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
main{max-width:920px;margin:0 auto;padding:40px 16px 96px}h1{font-size:34px;line-height:1.15;margin:0 0 8px;letter-spacing:-.02em}
h2{font-size:23px;margin:52px 0 12px;padding-top:20px;border-top:1px solid var(--line);letter-spacing:-.01em}h3{font-size:18px;margin:30px 0 8px}
p,li{max-width:74ch}a{color:var(--acc);text-underline-offset:2px}code{font:13.5px ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--soft);padding:1px 5px;border-radius:4px}
.tw{overflow-x:auto;margin:14px 0}table{border-collapse:collapse;width:100%;font-size:14.5px}th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--mut);font-weight:600;font-size:12.5px;text-transform:uppercase;letter-spacing:.04em}
pre{background:var(--soft);border:1px solid var(--line);border-radius:10px;padding:14px 16px;overflow-x:auto;font:13.5px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap}
.prompt{position:relative;margin:12px 0}.prompt button{position:absolute;top:8px;right:8px;font:600 12.5px -apple-system,sans-serif;background:var(--acc);color:#fff;border:0;border-radius:7px;padding:6px 10px;cursor:pointer}
.prompt pre{padding-top:44px}blockquote{margin:14px 0;padding:2px 16px;border-left:3px solid var(--line);color:var(--mut)}
figure{margin:18px 0}figure img,figure svg{max-width:100%;height:auto;border:1px solid var(--line);border-radius:10px;background:#fff}figcaption{color:var(--mut);font-size:13.5px;margin-top:6px}
.seen{color:var(--seen);font-weight:700;font-size:12px;letter-spacing:.05em}.inf{color:var(--inf);font-weight:700;font-size:12px;letter-spacing:.05em}
.top{color:var(--mut);font-size:14px;margin-bottom:26px}hr{border:0;border-top:1px solid var(--line);margin:32px 0}
"""


def chart(d):
    info = read_json(os.path.join(d, "curve/curve.json"))
    rows = read_csv(os.path.join(d, "curve/monthly.csv"))
    p = (info or {}).get("_primary")
    if not info or not rows or not p:
        mv = read_csv(os.path.join(d, "moves-vs-growth.csv"))
        if not mv:
            return ""
        cell = lambda x: (f'<a href="{html.escape(x["link"])}">{html.escape(x["move"])}</a>' if x.get("link") else html.escape(x["move"]))
        return ('<p><em>No public monthly series was strong enough to draw a curve, so the moves are listed by date and no lift is claimed.</em></p><div class="tw"><table>'
                "<tr><th>Date</th><th>Channel</th><th>Move</th><th>Reach</th></tr>"
                + "".join(f"<tr><td>{html.escape(x['date'])}</td><td>{html.escape(x.get('channel', ''))}</td><td>{cell(x)}</td><td>{html.escape(str(x.get('reach', '')))}</td></tr>" for x in mv)
                + "</table></div>")
    pts = [(r["month"], float(r[p])) for r in rows if r.get(p) not in ("", None)]
    if len(pts) < 3:
        return ""
    W, H, L, R, T, B = 880, 330, 54, 16, 18, 44
    mx = max(v for _, v in pts) or 1
    X = lambda i: L + i * (W - L - R) / (len(pts) - 1)
    Y = lambda v: T + (H - T - B) * (1 - v / mx)
    path = " ".join(f"{'M' if i == 0 else 'L'}{X(i):.1f},{Y(v):.1f}" for i, (_, v) in enumerate(pts))
    s = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" font-family="-apple-system,Helvetica,Arial,sans-serif">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>']
    for k in range(5):
        v = mx * k / 4
        s.append(f'<line x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#e4e7ec"/><text x="{L - 8}" y="{Y(v) + 4:.1f}" font-size="11" fill="#667085" text-anchor="end">{short(v)}</text>')
    step = max(1, len(pts) // 9)
    for i in range(0, len(pts), step):
        s.append(f'<text x="{X(i):.1f}" y="{H - B + 18}" font-size="11" fill="#667085" text-anchor="middle">{pts[i][0]}</text>')
    inf = info.get(p, {}).get("inflection")
    idx = {m: i for i, (m, _) in enumerate(pts)}
    if inf in idx:
        s.append(f'<line x1="{X(idx[inf]):.1f}" x2="{X(idx[inf]):.1f}" y1="{T}" y2="{H - B}" stroke="#2563eb" stroke-dasharray="4 4"/>'
                 f'<text x="{X(idx[inf]) + 6:.1f}" y="{T + 12}" font-size="11.5" fill="#2563eb">{info[p].get("kind", "step up")}: {inf}</text>')
    s.append(f'<path d="{path}" fill="none" stroke="#16181d" stroke-width="2"/>')
    legend = []
    moves = read_csv(os.path.join(d, "moves-vs-growth.csv"))
    seen, k = {}, 0
    for mv in moves:
        m = mv["date"][:7]
        if m not in idx or mv["cluster"] in seen:
            continue
        k += 1
        seen[mv["cluster"]] = k
        i = idx[m]
        s.append(f'<circle cx="{X(i):.1f}" cy="{Y(pts[i][1]):.1f}" r="9" fill="#2563eb"/><text x="{X(i):.1f}" y="{Y(pts[i][1]) + 4:.1f}" font-size="10.5" fill="#fff" text-anchor="middle" font-weight="700">{k}</text>')
        group = [x for x in moves if x["cluster"] == mv["cluster"]]
        legend.append(f"<tr><td>{k}</td><td>{html.escape(mv['date'][:7])}</td><td>" + "<br>".join(
            (f'<a href="{html.escape(x["link"])}">{html.escape(x["move"])}</a>' if x.get("link") else html.escape(x["move"])) + f' <span style="color:var(--mut)">({html.escape(x["channel"])})</span>' for x in group)
            + f"</td><td>{html.escape(str(mv['growth_before_pct']))}% → {html.escape(str(mv['growth_after_pct']))}%</td><td>{html.escape(str(mv['lift_pts']))}</td></tr>")
    s.append("</svg>")
    out = f'<figure>{"".join(s)}<figcaption>{html.escape(info[p]["label"])}, by month. Not traffic unless the label says so.</figcaption></figure>'
    if legend:
        out += ('<div class="tw"><table><tr><th>#</th><th>Month</th><th>Moves (within a month of each other count as one)</th><th>Growth a month, before → after</th><th>Lift (points)</th></tr>'
                + "".join(legend) + "</table></div>")
    return out


def cmd_report(args):
    d = args[0]
    src = args[1] if len(args) > 1 and not args[1].startswith("-") else os.path.join(d, "playbook.md")
    if not os.path.exists(src):
        sys.exit(f"write {src} first")
    md = open(src).read()
    prompts = []

    def stash(m):
        prompts.append(m.group(1).strip("\n"))
        return f"\n\nPROMPTBLOCK{len(prompts) - 1}END\n\n"
    md = re.sub(r"```prompt\n(.*?)```", stash, md, flags=re.S)
    try:
        import markdown
        body = markdown.markdown(md, extensions=["tables", "fenced_code", "sane_lists"])
    except ImportError:
        print("  the 'markdown' package is missing (pip3 install markdown): the report keeps the text unformatted")
        body = "<pre>" + html.escape(md) + "</pre>"
    body = body.replace("<table>", '<div class="tw"><table>').replace("</table>", "</table></div>")
    body = re.sub(r"\bSEEN\b", '<span class="seen">SEEN</span>', body)
    body = re.sub(r"\bINFERRED\b", '<span class="inf">INFERRED</span>', body)

    def put_prompt(m):
        t = html.escape(prompts[int(m.group(1))])
        return f'<div class="prompt"><button onclick="copyP(this)">Copy the prompt</button><pre>{t}</pre></div>'
    body = re.sub(r"<p>PROMPTBLOCK(\d+)END</p>", put_prompt, body)

    def put_sheet(m):
        ch = m.group(1).strip()
        f = os.path.join(d, "content", ch, "sheet.jpg")
        if not os.path.exists(f):
            return f"<p><em>No contact sheet for {html.escape(ch)}: its images were not read.</em></p>"
        b = base64.b64encode(open(f, "rb").read()).decode()
        return f'<figure><img alt="{html.escape(ch)}: top and bottom posts" src="data:image/jpeg;base64,{b}"><figcaption>{html.escape(ch)}: the top posts above, the bottom ones below, as pulled.</figcaption></figure>'
    body = re.sub(r"<p>\[\[sheet:([^\]]+)\]\]</p>", put_sheet, body)
    body = body.replace("<p>[[curve]]</p>", chart(d))
    title = (re.search(r"^# (.+)$", md, re.M) or [None, "Growth playbook"])[1]
    page = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>'
            f"<style>{CSS}</style></head><body><main>{body}</main><script>function copyP(b){{navigator.clipboard.writeText(b.nextElementSibling.innerText).then(()=>{{"
            "const t=b.textContent;b.textContent='Copied';setTimeout(()=>b.textContent=t,1400)})}</script></body></html>")
    dst = os.path.splitext(src)[0] + ".html"
    with open(dst, "w") as f:
        f.write(page)
    print(f"  {dst} ({os.path.getsize(dst) / 1024:.0f} KB, one file, {len(prompts)} prompts with a copy button)")


# ---------------------------------------------------------------- setup

def cmd_setup(args):
    ok = True
    for mod, why, fix in (("PIL", "thumbnails and contact sheets", "pip3 install pillow"), ("markdown", "the HTML report", "pip3 install markdown")):
        try:
            __import__(mod)
            print(f"ok  {mod}: {why}")
        except ImportError:
            ok = False
            print(f"!!  {mod} is missing ({why}). Fix: {fix}")
    print("ok  Python " + sys.version.split()[0])
    print("context.dev does the scraping: check that its tools (web-scrape, web-search, get-news-search, get-usage) are connected, then call get-usage.")
    return ok


CMDS = {"setup": cmd_setup, "rows": cmd_rows, "site": cmd_site, "wayback": cmd_wayback, "wiki": cmd_wiki, "youtube": cmd_youtube, "x": cmd_x, "rank": cmd_rank,
        "ads": cmd_ads, "curve": cmd_curve, "moves": cmd_moves, "report": cmd_report}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS or (sys.argv[1] != "setup" and len(sys.argv) < 3):
        sys.exit(__doc__)
    CMDS[sys.argv[1]](sys.argv[2:])
