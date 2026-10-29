# hormozi-lead-magnet, a Claude Code skill

It makes a finished lead magnet for your business: a page that works, the post that gives it away, and a plan for
testing its name.

**It's built on the lead magnet method from Alex Hormozi's *$100M Leads*:**
1. Pick one narrow problem your buyer has, and solve it completely, for free. Solving it should reveal the next
   problem, the one your paid offer solves.
2. Solve it one of three ways:
   - reveal a problem they didn't know they had;
   - give a sample or trial;
   - do one step of a multi-step process.
3. Name it for the result, not the method, and test the name, because he says it moves demand more than anything inside.
4. End with one clear next step and a real reason to take it now.

`reference-breakdown.md` walks through his two lead magnet lessons step by step. `hormozi-lead-magnet-research.md`
covers everything else he's said about lead magnets across 281.9 hours of his videos. Both have timestamped links.
This skill isn't affiliated with or endorsed by Alex Hormozi.

## How it works

1. **Claude asks you eight questions.** For example: what you sell, who it's for (and who it isn't), what you always
   find wrong when you first look at a customer's situation, and how many new customers you can take on.
2. **It suggests a type and five names**, using his four naming formulas. You pick.
3. **It builds one self-contained page from your answers.** Your words, your checks, your proof. The page is one of:
   - **Assessment:** questions → a score → the specific problems their answers reveal → your next step.
   - **Guide:** numbered steps with checklists. It also saves as a PDF.
   - **Free service claim:** what they get, what it's worth, your limit, and a qualifying form.
4. **It's restyled to your brand.** Give it your website: it measures your colours, fonts, logo and button shape, and
   the page comes out looking like your own site, not a template.
5. **You get the post that gives it away**, plus a cheap way to test the name before you spend anything on it.

The page runs on any host (Netlify Drop, Vercel, GitHub Pages, your own site). Point the form at your email tool, CRM
or a Zapier/Make webhook, and a qualifying question sends qualified and unqualified leads to different next steps.

## Install

1. Put the `hormozi-lead-magnet` folder in `~/.claude/skills/`.
2. You need Python 3 and Google Chrome (for restyling to your site, the PDF and screenshots).
3. In Claude Code, say "make me a lead magnet" (or run `/hormozi-lead-magnet`).

Start from `examples/skeleton/magnet.json` to see the structure:

```bash
python3 magnet.py check examples/skeleton
python3 magnet.py build examples/skeleton    # -> examples/skeleton/out/index.html
```

Only real proof: every result, number and quote on your lead magnet has to be yours.
