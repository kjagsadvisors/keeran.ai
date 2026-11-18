---
name: rank-your-name
description: Makes a person the top result when someone Googles their name, and the person AI assistants name when asked who they are. Uses OpenSEO to check where the name ranks today, whether Google already shows a knowledge panel, what ChatGPT, Perplexity, Gemini and Claude say, and whether the person's site has any real backlinks. Then it fixes the site, lines up the profiles, finds link and press targets, and sets up weekly tracking. Use when someone says "I want to be #1 when you Google my name", "rank for my name", "own my name on Google", "personal brand SEO", "get a knowledge panel", or "why doesn't AI know who I am".
license: MIT
---

# Rank your name

Make one person the answer to a search for their name, on Google and in AI assistants. Built from a real run on the name "Keeran" (keeranai.com). Needs the OpenSEO MCP server connected (https://openseo.so). The AI-answer check needs a paid OpenSEO plan.

If OpenSEO isn't connected, say so and stop. Don't guess rankings.

## Inputs

- The person's name as people search it: the short name ("keeran"), the full name ("keeran jagadesan"), and any handle or brand ("keeran ai", "keeran.ai").
- Their site, if they have one, and their main profiles (Instagram, X, LinkedIn, YouTube, GitHub).
- What they do in one line. This is what search results and AI answers should say about them.
- A `projectId` from `list_projects`. Create one for their site with `create_project` if there is none.

Ask the person which profiles they want left exactly as they are before you plan any profile changes. In the run this skill comes from, the person kept their last name on Instagram and kept X linking to Instagram. Their call, every time.

## Steps

1. **Baseline the name.** Call `get_serp_results` for every name variant, plus the bare short name on `device: "mobile"` with `depth: 20`. Send at most 5 keywords per call, because the responses are large. Quote `bestPosition` as the rank and note `seenIn`, since results that appear in only 1 of 3 reads are weak. For each query, record who holds #1, the person's best result, and whether a `knowledge_graph` item appears. A knowledge panel on any variant means Google already treats them as a person, and the job is spreading it to the short name.
2. **Ask the AI assistants.** Call `explore_prompt` with "Who is <short name>?", `models: ["chat_gpt", "perplexity", "gemini", "claude"]`, and `highlightBrand` set to the full name. Record which models name the person and what each one cites instead. Wikipedia name pages, baby-name sites and other people's profiles are the usual answers. Tell the user it uses a small amount of credit first.
3. **Check the backlinks.** Call `get_backlinks_overview` for the site, then `get_backlinks_profile` with `hideSpam: false`, `sortField: "domainRank"` and `pageSize: 50`. Sort the referring pages into real links (a person or publication chose to link) and junk (site-worth calculators, link shorteners, "report/12345" stats pages, scraped directories). A recently bought domain often carries junk from its previous owner. Don't disavow it; Google ignores it. Count the real ones. That number is usually the actual gap.
4. **Connect Search Console.** Call `list_search_console_sites`. If the site isn't listed, it was never verified. Walk the user through adding it as a Domain property and adding the TXT record at their DNS host, or do it in their browser if they ask. Then call `set_search_console_site`. New properties show no data for a day or two. Use URL inspection to request indexing for the home page and the About page, and submit the sitemap.
5. **Fix the site.** On the home page, the `Person` structured data gets `name` (full name), `givenName`, `familyName`, `alternateName` (short name and handle), and `sameAs` (every profile, the Google Search profile first if they have one). Add a `WebSite` block whose `name` is the short name, so Google can label the site with it in results. Add an About page that says, in plain sentences, who they are, what they make, and links every profile. AI assistants cite pages like this. Keep the visible copy in the person's voice, and put changes on a branch for their review if the site deploys on push.
6. **Line up the profiles.** One line everywhere: "<Full name> (<short name>) · <what they do> · <site>". Create the profiles that rank for people's names and don't exist yet: Crunchbase person page, Product Hunt maker profile, Medium, YouTube description, GitHub profile and repo homepage. Show each new profile before saving. Change an existing profile only after the person says yes to that profile. If the short-name handle is taken (it often is), use the full name; it's better for search anyway.
7. **Find real links.** Use `get_serp_results` on queries where their work fits a list: "<their field> creators to follow", "best <thing they make>", "<their tool category> directory", "<topic> podcast". Keep pages that name and link people: directories with submission forms, roundups, partner and customer pages of brands they've worked with, podcast show notes. Note the contact path only if you found it on the page. Draft the asks and leave sending to the person.
8. **Plan the press trail.** Only people with their own Wikipedia article appear on a name's Wikipedia page, and an article needs significant coverage in several independent, reliable sources. Writing your own is a conflict of interest and gets deleted. So the plan is press first: profiles and interviews in independent outlets, then a Wikidata entry and an Articles for Creation submission by someone else once three or more exist.
9. **Track it.** Create a rank tracker with `create_rank_tracker` (it starts as manual, so it costs nothing), add the name variants with `add_rank_tracking_keywords`, get the price from `estimate_rank_tracker_cost`, and only after the user approves it, run the first check with `run_rank_tracker`. Weekly scheduling is set in the OpenSEO app under the tracker's Configure button. Set the project's `brandName` to the short name with `update_project_context` so later AI visibility runs count mentions correctly.

## Output

A report, saved with the `seo-report` skill if it's available, in this order:

- **Where you stand:** three bullets with the knowledge panel status, the bare-name rank, the AI answer count (for example "0 of 4 name you"), and real backlinks against junk.
- **Rankings table:** each name variant with the person's best result and who holds #1.
- **AI answers table:** each assistant, whether it names them, and what it cites instead.
- **The plan:** the site fixes, the profile list, the link targets with their angle, and the press trail. Each item has an owner (you or Claude) and whether it's done.
- **What we left alone:** every profile the person chose to keep as is, so nobody "fixes" it later.
- **Tracking:** the tracker, its schedule, and when to rerun the AI question (monthly).

## Guardrails

- Never pay for links or buy link packages.
- Never write, or offer to write, a Wikipedia article about the user.
- Never send outreach, submit forms or save profile changes without the person's yes for that one action.
- Don't put follower counts or other private stats on public profiles unless the person asks.
- If the person is paid by a tool they mention in public posts (OpenSEO included), the post discloses it.
- Bare first names are contested and personalized by country and login. Check results logged out, say how long this takes (weeks to months), and don't promise #1.
