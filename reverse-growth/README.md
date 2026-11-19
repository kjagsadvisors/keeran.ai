# reverse-growth

Give Claude a company. Get back how it grows: when it took off, what it does on each channel, what its best posts have
in common, and ten plays to copy, each with a prompt ready to paste.

## Set it up in one paste

1. **Make a free context.dev account:** https://link.context.dev/keeran-jagadesan. It does the scraping. The free plan
   gives you 1,000 credits a month with no card, and a full run used 99 on my test, so the free plan is enough for
   now. If you upgrade later, code `KEERAN25OFF` takes 25% off your first 6 months. (That's my referral link: I may
   earn a commission.)
2. **Paste this into Claude Code** (the Code tab in the Claude desktop app works):

   ```
   Set up the reverse-growth skill from https://github.com/kjagsadvisors/keeran.ai for me.

   1. Download the repo to a temporary folder and copy its reverse-growth folder to ~/.claude/skills/reverse-growth.
   2. Read its SKILL.md and take me through the Onboarding section, one step at a time. Run the commands yourself where you can.
   3. If I need to restart Claude, tell me, and I'll paste this prompt again.
   4. Once context.dev is connected, ask me for the company I want to reverse engineer (and my own company, if I want the plays fitted to it), then run the skill. Use its defaults for everything else.
   ```

   Claude downloads the skill, checks your setup and connects context.dev with you. You sign in to context.dev once.
   If it asks you to restart, restart and paste the same prompt again.
3. **Name a company.** After the first time, this is all you type:

   ```
   /reverse-growth how does gamma.app grow?
   ```

The same steps, with what it found on a real company: https://keeranai.com/reverse-growth

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

## Install by hand

Copy this folder into `~/.claude/skills/` (or your project's `.claude/skills/`). It needs Python 3.9+,
`python3 -m pip install --user pillow markdown`, and the context.dev connector
(`claude mcp add --transport http context https://mcp.context.dev/mcp`, then `/mcp` to sign in, then restart).

## What you get

`growth/<company>/playbook.html`: one file, light and dark. The curve with each move pinned on it, a contact sheet of
each channel's best and worst posts side by side, ten plays with a copy button on every prompt, and a method section
listing what was read, what was blocked and what is a guess. Plus every table as a CSV.

Credit: the idea and step order follow [rea-growth](https://github.com/superdesigndev/treg) by Superdesign. See `NOTICE`.
