# reverse-growth

Give Claude a company. Get back how it grows: when it took off, what it does on each channel, what its best posts have
in common, and ten plays to copy, each with a prompt ready to paste.

It runs on [context.dev](https://link.context.dev/keeran-jagadesan) (referral link: Keeran may earn a commission;
code `KEERAN25OFF` takes 25% off the first 6 months of a paid plan). The free plan's 1,000 credits a month cover
six or more full teardowns.

## What it reads

| | Source |
|---|---|
| Site: page families, sign-up flow, pricing, tools it loads | sitemaps, context.dev `web-map` and `web-scrape` |
| Company: funding rounds, headcount, news | context.dev `company-search`, `get-news-search` |
| Ads: Meta, Google, LinkedIn | each network's public ad library, read by context.dev |
| Their posts: Instagram, TikTok, LinkedIn, Reddit | context.dev's parsers |
| Their posts: YouTube, X | YouTube's channel page and feed, X's public embed timeline |
| What people say: Reddit, G2, app stores | context.dev's parsers |
| When it grew | brand searches from OpenSEO if connected, Wikipedia page views, news per month, the Wayback Machine |

It can't see traffic, keyword rankings or backlinks. Connect OpenSEO for those.

## Install

Copy this folder into `~/.claude/skills/` (or your project's `.claude/skills/`), then in Claude Code:

```
/reverse-growth how does gamma.app grow?
```

Needs Python 3.9+, `pip3 install pillow markdown`, and the context.dev connector
(`claude mcp add --transport http context https://mcp.context.dev/mcp`). The skill walks you through it.

## What you get

`growth/<company>/playbook.html`: one file, light and dark. The curve with each move pinned on it, a contact sheet of
each channel's best and worst posts side by side, ten plays with a copy button on every prompt, and a method section
listing what was read, what was blocked and what is a guess. Plus every table as a CSV.

Credit: the idea and step order follow [rea-growth](https://github.com/superdesigndev/treg) by Superdesign. See `NOTICE`.
