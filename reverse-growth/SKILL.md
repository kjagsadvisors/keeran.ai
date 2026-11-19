---
name: reverse-growth
description: Reverse engineer how any company grows, on context.dev. Give it a company and get a playbook - when it took off, what it did on each channel (site and sign-up flow, ads on Meta, Google and LinkedIn, its own posts on YouTube, TikTok, Instagram, X, LinkedIn and Reddit, who talks about it, reviews, hiring), what its best posts have in common, and ten plays to copy, each with a ready prompt. Use when someone asks "how did X grow", "how does X get users", "teardown of X's marketing", "reverse engineer X's growth", "what content works for X", "what ads is X running", or wants to copy what a competitor or a company they admire does on each channel.
---

# reverse-growth

A company in, a playbook out: when it grew, which moves lined up with that, how its content is made on each channel
and what wins there, and ten plays the user can copy, each with a prompt ready to paste.

context.dev does the scraping (pages, ad libraries, social feeds, reviews, news, search). `growth.py`, next to this
file, reads the open feeds that need no scraper, does every sum, ranks the posts, builds the contact sheets and writes
the report: `python3 <skill>/growth.py ...`.

## Onboarding (first run, and any time context.dev isn't connected)

1. Run `python3 <skill>/growth.py setup`. For each `!!` line, show the fix and offer to run it.
2. Look at your own tools for context.dev's (`web-scrape`, `web-search`, `get-news-search`, `get-usage`, under a server
   called `context` or a connector named Context.dev). If they're there, go to step 4.
3. Walk them through it, in this order, with these exact links:
   - "First, make a free context.dev account: **https://link.context.dev/keeran-jagadesan**. The free plan gives you
     1,000 credits a month. A full teardown uses about 100 to 150."
   - "If you ever upgrade, code **KEERAN25OFF** takes 25% off your first 6 months."
   - "That's Keeran's referral link, so he may earn a commission if you sign up or upgrade through it."
   - Connect it. In Claude Code, offer to run this for them (ask first):
     ```bash
     claude mcp add --transport http context https://mcp.context.dev/mcp
     ```
     then tell them to type `/mcp`, pick `context` and sign in with the account they just made. In the Claude app:
     Settings > Connectors > Add custom connector, URL `https://mcp.context.dev/mcp`.
   - Either way a new connector only shows up in a new session: tell them to restart Claude and come back to this.
   Always use the link above, never the bare context.dev address, and always say it's a referral link.
4. Call `get-usage` (free). Tell them their credits and keep the number: the bill at the end is this number minus
   the one after. The free plan's 1,000 credits a month cover several full runs.

## Modes

| Mode | When | Steps | Delivers |
|---|---|---|---|
| **full** (default) | "how does TARGET grow", "teardown", "what should I copy" | 0-12 | `playbook.md`, `playbook.html`, the CSVs |
| **content** | only titles, thumbnails, covers, captions, "what content works" | 0, 1 (handles only), 7, 13 | `content.md`, `content.html`, the CSVs |

## Rules

- Every finding is **SEEN** (a call result or an image shows it: link it) or **INFERRED** (reasoned from what was seen:
  say from what). Nothing seen means "not seen". Never fill a gap with a guess.
- Public pages only. Make no accounts, fill no forms, contact no one, sign in nowhere.
- A site that refuses the script or context.dev is listed as blocked. Don't work around a refusal.
- The script does every sum. Every number in the report comes from a call result or the script's output, with the
  date it was read.
- No traffic numbers exist here unless the user supplies them. The curve is built from named stand-ins (step 3) and
  is always called by its name ("Wikipedia page views"), never "traffic" or "growth".
- Keep context.dev's answers out of the main conversation: a social feed or an ad library can run to tens of
  thousands of words. Run each pull in a subagent that saves only the rows listed below and returns the count. With
  no subagents, pull one channel at a time and write the rows before the next call.
- Claude Code saves a long tool answer to a file and tells you the path. When it does, never retype it: `growth.py
  rows <channel> <that file> -o <dir>` reads the posts out of it, and `growth.py site ... --urls <that file>` reads a
  site map out of it. Retype rows only when the answer came back inline, and then copy every number exactly.
- Brand names are shared. A search for "Gamma" returns a music label and a telecom too. Check that each news item,
  Reddit post and ad is about TARGET, drop the rest, and say how many were dropped.
- After each step tell the user in three lines: what was found, what the next step checks, credits used so far. Stop
  when the cap would be passed.
- Never copy the target's identity: no logo, name, slogans, footage or images in anything made for the user. The
  thumbnails are downloaded for study only.

## 0 · Setup

The target's domain is the only thing you must have. Ask one question: which company, and (optional) the user's own
company and stage (pre-launch, early revenue, scaling) if they want the plays fitted to it. Use the defaults for the
rest and say what they are: full mode, a cap of 200 credits. With no company of their own, write the plays as
patterns anyone can use. With no target, `web-search` "fastest growing <category> startups <year>", propose
three, let them pick. Work in `growth/<target>/` (called `<dir>` below).

## 1 · The site (about 10 credits)

```bash
python3 <skill>/growth.py site TARGET -o <dir>
```
It reads the sitemaps and groups every URL into page families (templates, use cases, integrations, compare pages,
blog, docs, user-made pages), counting each page once however many languages it is in. Then it reads the homepage
for the analytics, ad pixels, chat, testing and affiliate tools it loads, and opens any Google Tag Manager container
the page names, which lists the pixels inside. It prints the social accounts the homepage links.

If the site refuses the script, don't work around it. Use context.dev:
- `web-map` `{domain, maxLinks: 300}`. Two things flood the list: user-made pages (thousands under one folder) and
  language copies of the same page. Note the flood, then call again with `excludeUrlRegex` for it, for example
  `"/docs/"`. Then `growth.py site TARGET -o <dir> --urls <file>`, where the file is the saved answer or any text
  file with the URLs in it. The counts are of context.dev's sample, not the whole site: say so.
- The stack: `web-scrape` the homepage with `formats.parse` and custom rules
  `{"scripts": {"selector": "script[src]", "type": "list", "output": "@src"}, "frames": {"selector": "iframe", "type":
  "list", "output": "@src"}, "hints": {"selector": "link[rel=preconnect],link[rel=dns-prefetch]", "type": "list",
  "output": "@href"}, "links": {"selector": "a[href]", "type": "list", "output": "@href"}}`. Save all four lists, one
  address per line, to `<dir>/site/home.txt` (leave out the site's own code bundles) and add `--html
  <dir>/site/home.txt` to the command above.

Then, with context.dev:
- `brand-retrieve-unified` `{type: "by_domain", domain}`: official social accounts, app store links, careers and
  pricing pages, colours. An account counts if the site links it, its bio links back to the site, or an official
  account's bio points to it. For a doubtful TikTok handle, parser `tiktok-profile` shows the bio (1 credit).
- `web-scrape` `formats.markdown`, `responseMode: "compact"` on: home, pricing, the sign-up page, the affiliate /
  partner / referral page, the changelog. Compact mode stops at 4,000 characters: for a fact further down the page
  use `formats.highlights` with a `highlightsParams.query` naming it. Write `<dir>/site/notes.md`: sign-up method
  (SSO, email, card up front?), waitlist or invite codes, what is free, trial length and how it ends, plans and
  prices, the first thing a new user is told to do, and every place a non-user meets the product (shared outputs,
  public pages, embeds, badges, invites). A page that isn't in the map is "not seen": don't guess its address.
- The founders: the about page, else `web-search` "TARGET founder". Their X handles go to step 7.

A pixel in the page or the tag manager is SEEN. What they run on it is INFERRED. Content mode: handles only, then
step 7.

## 2 · Company, money, news (about 6 credits)

- `company-search` `{query: "TARGET domain + what it does"}`: founding year, headcount, funding rounds with dates,
  revenue range. Label revenue "reported".
- `get-news-search` `{domain, sortBy: "newest", limit: 30}`, up to 4 pages (it may end sooner). Keep only
  `match.level: "primary"`, then drop same-named companies, repeats of one story and items with no date. Once more
  with `filterBy.articleType: ["press_release"]` for the company's own announcements. Save `<dir>/news.json`:
  `{"pulled": "YYYY-MM-DD", "articles": [{"date", "title", "source", "url", "type"}]}`.
- From those headlines, list every number the company has reported (users, revenue, valuation) with its date.
- The integrations and partners pages from step 1's families: who they plug into and who sends them users.

## 3 · When it grew (free)

No scraper sells this, so the curve comes from dated public counts. Run what applies:
```bash
python3 <skill>/growth.py wiki TARGET -o <dir>            # monthly Wikipedia page views, if it has an article
python3 <skill>/growth.py wayback TARGET -o <dir>         # the day each family's example page was first saved
python3 <skill>/growth.py curve <dir>                     # lines them up and marks the take-off
```
`curve` uses the strongest series it has, in this order: traffic or brand searches the user supplied, Wikipedia page
views, reviews, news a month. A series needs 8 months with something in them and 40 counted in all.
It marks the **take-off** (the first month the three-month level at least triples and reaches a tenth of the peak),
or failing that the largest sustained step up, plus up to three later steps. Wayback saves are context, never the
curve.

The best series is brand searches. If OpenSEO is connected, call its `get_keyword_metrics` for the two or three ways
people type the brand ("TARGET ai", "TARGET app"), add them up per month, and save `<dir>/curve/brand_search.csv`
(columns `month,value`, months as `YYYY-MM`) with `<dir>/curve/brand_search.json` `{"label": "US Google searches a
month for ...", "source": "OpenSEO"}`. Any other monthly series works the same way as `curve/<name>.csv`.

Line up step 2's launches and raises against the take-off. If `curve` says no series is strong enough, say "no
curve": date the moves, list the reported numbers, and claim no lift.

## 4 · Search and AI answers (about 15 credits, plus 40 for the AI answers)

- Step 1's families show the search play: thousands of pages in one family is a template filled from data, and a
  handful of pages in dozens of languages is keyword pages translated. Read the top page of the three largest
  families (`web-scrape`, markdown): the search it answers, hand-written or templated, how it sends the reader to
  the product. No families from step 1: skip this and say so.
- Three buyer questions: "best <category> tool" ("best AI presentation maker"), "TARGET alternatives", and the job in
  the buyer's words ("make a pitch deck with AI"). `web-search` `{query, numResults: 10, responseMode: "compact"}`.
  A result's position is its place in the list. Record TARGET's position, which of its pages ranks, and what the
  others are: a competitor's own page, a press release, a list or review, Reddit, YouTube.
- Optional, 13 credits a question: the same questions to `web-answers` `{task, mode: "fast", json_format:
  {"brands_in_order": [""], "sources": [""]}}`: the order brands are named. It usually cites one page. Call it
  "context.dev's web answer", not ChatGPT.
- Rankings, search volumes and backlinks are not available here. If the user has OpenSEO connected, run
  `/reverse-engineer-seo` and `/reverse-engineer-geo` on TARGET and fold their findings into this step.

## 5 · Ads (about 10 credits)

Each library is a public page. `web-scrape` it with `formats.json` and a JSON Schema, `sharedParams: {waitFor:
6000}`, `responseMode: "compact"`:

| Network | URL (URL-encode the brand) | Schema fields |
|---|---|---|
| Meta | `https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=US&q=<brand>&search_type=keyword_unordered&media_type=all` | `result_count_text`, `ads[]`: advertiser, library_id, started_running, primary_text, headline, cta, landing_domain |
| Google | `https://adstransparency.google.com/?region=US&domain=TARGET` | `ads_count_text`, `advertisers[]`, `ads[]`: advertiser, format, link |
| LinkedIn | `https://www.linkedin.com/ad-library/search?accountOwner=<brand>` | `result_count_text`, `ads[]`: advertiser, format, text, detail_url |

Add `"instructions": "Only what is visible on the page. Do not invent."` to every schema. Save each as
`<dir>/ads/<network>.json`: `{"network", "pulled", "source": <the URL>, "total": <the count text>, "ads":
[{"advertiser", "id", "started", "format", "headline", "text", "cta", "landing", "url"}]}`. Keep the target's ads in
full and cut other advertisers' text to 200 characters. Then:
```bash
python3 <skill>/growth.py ads <dir> --advertiser "Exact Name|Other exact name"
```
A library search also returns namesakes, so pass the advertiser names exactly as each library shows them (they
differ: a page name on Meta, a legal name on Google). The count text is the library's total for the search,
namesakes included: say so. Meta lists the most-shown ads first and gives start dates, so only Meta can show which
ads have run 60 days or more (a kept ad is a winning ad). Google's and LinkedIn's lists have no dates or run
lengths: say "not seen". The script groups ads that share a template with a changing name ("Visa, every off-brand
deck...", "Cisco, every off-brand deck...") as one message: that pattern is an ad per target account. Per network
report: ads read, the message repeated most, the offer, the button, and the landing page (read it with
`web-scrape`). Other advertisers running ads to TARGET's domain are worth a line (INFERRED: affiliates or
resellers). No ads found is SEEN "no ads on this network". TikTok's ad library only covers Europe: skip it.

## 6 · Who talks about it (about 10 credits)

- Reddit: `web-scrape` `https://www.reddit.com/search/?q=%22TARGET%22&sort=top&t=year` with `formats.parse`,
  `parseParams: {type: "prebuilt", parser: "reddit-search", limit: 25}`. The answer carries every post's full text,
  so Claude Code saves it to a file: `growth.py rows reddit <that file> -o <dir> --handle "search: TARGET"`. It may
  return fewer than 25. Drop the posts that aren't about TARGET and say how many.
- YouTube and X: `web-search` `{query: "TARGET review OR tutorial", includeDomains: ["youtube.com"]}` and
  `{query: "TARGET", includeDomains: ["x.com"], freshness: "last_year"}`. Results rarely carry view counts: list
  them, don't rank them against Reddit scores.
- Reviews: find the G2 page with one `web-search` (slugs vary), then `web-scrape` it with parser `g2-reviews` (the 25
  newest; add `?filters[nps_score][]=1&filters[nps_score][]=2` for the unhappy ones, often only a handful), and
  `app-store` / `google-play` on the app links for rating and rating count. Tally what people like, dislike and use
  it for, with role and company size. The tally is by hand: call it approximate.
- Label each item founder or team, creator (#ad, "sponsored" or "#publicidad" means paid), affiliate (a tracked
  link), user, or press. Note every contest, hackathon, waitlist or invite-code drop. Save `<dir>/mentions.md` and
  `<dir>/reviews.md`.

## 7 · Their own content, channel by channel (about 5 credits; image reads are free)

Step 6 is what others say. This is what TARGET publishes and how it's made. Run it for every handle from step 1.

**Pull.**

| Channel | How | You get |
|---|---|---|
| YouTube | `growth.py youtube @handle -o <dir>` | newest 30 videos and 48 Shorts: title, views, age, length, thumbnail. Shorts go to their own folder and are ranked apart. |
| X | `growth.py x handle -o <dir>` (brand and each founder) | newest ~20 posts: text, likes, reposts, replies, media. It prints the bio: check it's theirs. If X answers "too many requests", wait five minutes and try once more, then call it "not read". |
| Instagram | `web-scrape` `https://www.instagram.com/handle/`, parser `instagram-profile` | followers, newest 12 posts, pinned ones included |
| TikTok | `web-scrape` `https://www.tiktok.com/@handle`, parser `tiktok-feed` | 15 videos: plays, saves, shares, cover. Check the newest date: the feed can be months old. |
| LinkedIn | `web-scrape` `https://www.linkedin.com/company/slug/`, `formats.json`, schema `followers`, `posts[]`: text_first_lines, age, reactions, comments, media, url | followers, the newest public posts (about 6) |
| Reddit | step 6's rows, or the brand's own account with parser `reddit-user` | title, subreddit, score |

If Claude Code saved the answer to a file: `growth.py rows instagram <file> -o <dir>` (or `tiktok`, `reddit`).
Otherwise write `<dir>/content/<channel>/posts.json` by hand:
```json
{"channel": "instagram", "handle": "name", "pulled": "YYYY-MM-DD", "followers": 12345, "source": "<url>",
 "posts": [{"id": "", "url": "", "date": "", "kind": "reel|carousel|photo|video|post", "title": "", "text": "first 200 characters",
            "image": "<cover or thumbnail URL, whole>", "views": null, "likes": null, "comments": null, "shares": null,
            "saves": null, "score": null, "length": "", "subreddit": "", "owner": "", "pinned": false, "paid": false}]}
```
Where the parsers keep things (under `parsed.data`): Instagram `follower_count`, `latest_posts[]` with `shortcode`
(id), `type` ("image" is a photo), `posted_at`, `caption`, `like_count`, `comment_count`, `view_count`,
`video_duration_seconds`, `thumbnail_url`, `owner.username`, `is_pinned`, `is_paid_partnership`. TikTok `videos[]`
with `id`, `type`, `posted_at`, `caption`, `view_count`, `like_count`, `comment_count`, `share_count`, `save_count`,
`video_duration_seconds`, `thumbnail_url`, `author.username`, `is_ad`. `date` can be exact or the page's own "3w" /
"22h". Use null for a number the feed doesn't give. Social image links expire within hours, so rank straight away.

A profile's feed includes other accounts' posts it was added to as collaborator. Keep them, with their `owner`: a
creator's post beating the brand's own is a finding. Count them apart from the brand's own posts.

**Rank.**
```bash
python3 <skill>/growth.py rank <dir>
```
Per channel: engagement (views on YouTube and TikTok; likes + comments on Instagram; likes + reposts + replies +
quotes on X, whose public feed has no view counts; reactions + comments on LinkedIn; score on Reddit), posts under 7
days old set aside, then the bands.
20 or more settled posts: top quarter against bottom half. 12 to 19: top third against bottom third, called a small
sample. Under 12: no pattern is called. It downloads the cover of every top post and five bottom ones and builds
`content/<channel>/sheet.jpg`. Never compare across channels.

**Look.** Open each `sheet.jpg`, then the single images where the sheet is too small to read. An image that did not
download is "not read". Never describe one from its caption.

**Read** each image and title against its channel's list. What the image shows is SEEN. Why it might work is INFERRED.
- **YouTube.** Title: length, a number or money, first person, a question, the promise. Thumbnail: a face and its
  expression, words on it (count them), product or result shown, before/after, main colour, logo. Do title and
  thumbnail repeat or add to each other? Shorts against long videos.
- **TikTok.** Cover frame and words on it, the first line, format (talking head, screen recording, slideshow, skit,
  green screen), sound, length.
- **Instagram.** The mix of reels, carousels and photos, and which wins. Cover or first slide: headline size, words,
  template. The line before "more". The grid as a whole: colours, type, where the logo sits.
- **X.** The first line, length, thread or single, media (none, screenshot, chart, video, meme). Founder against
  brand account. Do numbers (revenue, users) drive the best posts?
- **LinkedIn.** The two lines before "see more", format, people or product in the image, company page against staff.
- **Reddit.** Title pattern, subreddits, whether the account says who it works for.

**Write up**, per channel:
- **Pattern.** Three to five traits the top band shares and the bottom band lacks, each counted ("8 of 9 top
  thumbnails show a face, 2 of 12 bottom ones").
- **House style.** What repeats in every post: colours (name them, read the hex off the image), lettering, templates,
  series.
- **Formulas.** The two or three fill-in templates behind the top titles, covers or hooks, one real example each.

## 8 · Loops (about 8 credits)

- Step 1's notes list where a non-user meets the product. Find it in the wild: `web-search`
  `site:TARGET/<the folder of user-made public pages>`, and `"Made with TARGET" -site:TARGET` (or "Powered by",
  "Built with"). If the second search returns guides to removing the badge, that is the finding: people see it
  enough to want it gone.
- Read three user-made pages with `web-scrape`, `formats.highlights`, query "made with, badge, footer, sign up": the
  badge sits at the bottom, past where compact mode stops. Record what it says, where it links, whether the link
  carries a referral code, and what the viewer is asked to do.
- Which plan removes the badge (step 1's pricing notes) is part of the loop.
- `growth.py wayback TARGET -o <dir> --pages <one early user-made page or the folder's index>` gives a date it existed
  by. A whole folder can't be dated this way: say "not seen" if no single page stands for it.

## 9 · What is next (about 2 credits)

`web-scrape` the careers page (`formats.json`, schema `openings[]`: title, team, location; save `<dir>/jobs.json`). Growth, SEO, paid,
lifecycle, community, devrel, partnerships, sales, content, design, video and country roles each name the channel
being scaled next.

## 10 · Moves against the curve (free)

Write `<dir>/moves.json`: one row per dated move from steps 2 and 5-8, `[{"date", "channel", "move", "link",
"reach"}]`: launch, raise, founder or brand post, creator video, ad start, loop first seen, new page family, new
content format. Then:
```bash
python3 <skill>/growth.py moves <dir>
```
Moves under a month apart are one cluster, and the cluster gets the credit, never one move in it. For each: growth
a month in the two months before against the month of and the two after. Per channel, a rank correlation with
growth 0, 1 and 2 months later, only with 12 months of curve and 5 moves. Each lift is SEEN as numbers. That the
move caused it is INFERRED: monthly data, overlapping moves, other causes. Say which series the lift was measured on.
With no curve from step 3 it lists the moves by date and claims no lift.

## 11 · The path (no calls)

One row per stage, each cell SEEN or INFERRED with links: **Get noticed** (founder posts, press, ads, search, AI
answers, own content) → **Sign up** (method, card, waitlist, partner links) → **First win** (the first action) →
**Pay** (plans, how the trial ends, free limits) → **Share** (what reaches non-users).

## 12 · The playbook

Write `<dir>/playbook.md`, in plain words, in this order:
1. `# How TARGET grows` and three lines: the one-sentence answer, the date, what was and wasn't read.
2. **The curve**: put `[[curve]]` on its own line (the chart goes there, or a dated list of the moves when there is
   no curve), then the take-off, the later steps, the moves around each, and the numbers the company has reported.
3. **The path** (step 11's table).
4. **By channel**: for each, the moves, the pattern, house style and formulas from step 7, what worked (the number,
   SEEN) and what didn't. Put `[[sheet:<channel folder>]]` on its own line for the contact sheet.
5. **Ten plays**, ordered by evidence, timing (started before the step up), lift and fit for the user's stage. Each:
   the play in one line, the evidence (SEEN or INFERRED, linked), effort (a day, a week, a quarter), time to a first
   result and the number to watch, cost to try, and the prompt in a fenced block tagged `prompt` (it gets a copy
   button). The prompt starts the play for the user's company: the pages to build, posts to make, lists to find. At
   least one play per channel where step 7 found a pattern, carrying that channel's formula.
6. **Skip these**: two or three plays that look good but the evidence doesn't support.
7. **14 days**: day by day for the channels worth using, and the one number to check on day 14.
8. **Method**: what was called, what was blocked, images not read, the date of every count, credits used (`get-usage`
   now against the start), every INFERRED reading, and that this has no tie to TARGET.
```bash
python3 <skill>/growth.py report <dir>
```
writes `playbook.html`: one file, light and dark, the chart with each move pinned, contact sheets inline, a copy
button on every prompt. End by naming the first play to run this week.

## 13 · Content report (content mode)

`<dir>/content.md`: per channel the sample and dates, pattern, house style, formulas, top five posts linked, and its
`[[sheet:...]]`; then the shared style across channels and where one channel breaks it; then, for the user's company,
five ready titles or covers per channel from the formulas and one prompt that makes the first post.
`growth.py report <dir> <dir>/content.md`.

## Keep watching (optional, ask first)

context.dev can watch the target: `create-monitor` on the pricing page (plan or price changes), the sitemap (new page
families), the careers page (new growth roles), or a search for the brand. Monitors cost credits on every run and
keep running until deleted: say so, and create one only on the user's yes.

## What it costs

Measured on the test run (gamma.app, full mode, all steps): 99 credits. A page read, a parser or a JSON extraction
is 1 to 2 credits, a `web-search` 1 to 4, a `web-answers` about 13. `get-usage`'s `credits_used` can lag a few
minutes behind: bill from `credits_remaining`.

## What this can't see

Traffic, keyword rankings, search volumes and backlinks (connect OpenSEO for those), anything behind a login, ad
run dates on Google and LinkedIn, TikTok ads outside Europe, X view counts, and posts older than each feed's public
window (about 12 on Instagram, 15 on TikTok, 20 on X, 6 on LinkedIn, 30 on YouTube). Say so in the method notes.
