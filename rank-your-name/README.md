# rank-your-name, a Claude Code skill

Makes you the top result when someone Googles your name, and the person AI assistants name when asked who you are.

I built it while trying to beat Wikipedia for my own first name, "keeran". The write-up is here: [I'm trying to be the only Keeran on Google](https://medium.com/@keeranjagadesan/im-trying-to-be-the-only-keeran-on-google-ef00e951db50).

## What it does

- Checks where every version of your name ranks today, and whether Google already shows a knowledge panel for you
- Asks ChatGPT, Perplexity, Gemini and Claude "Who is <you>?" and shows what they cite instead of you
- Sorts your backlinks into real ones and junk
- Connects Google Search Console and requests indexing
- Fixes your site so Google knows your short name and every profile is yours
- Lines up your profiles (Crunchbase, Product Hunt, Medium, YouTube, GitHub), checking with you before it changes any of them
- Finds link and press targets, and explains the real path to a Wikipedia article
- Sets up a weekly rank check for your name

## Install

It runs on [OpenSEO](https://keeranai.com/go/openseo) for the search data. The AI-answer check needs a paid plan.

1. Connect OpenSEO to Claude (Customize → Connectors → OpenSEO).
2. Copy the `rank-your-name` folder into `~/.claude/skills/`.
3. Ask Claude: "rank my name", and give it your name, your site and your profiles.

Or paste this repo's link into Claude and say "set up the rank-your-name skill".

*I work with OpenSEO, and the link above is my referral link.*
