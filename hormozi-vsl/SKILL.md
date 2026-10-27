---
name: hormozi-vsl
description: Write and make a finished video sales letter (VSL) for any offer, Hormozi-style. Intro = Promise, Pain, Proof, Plan, Pic → Unique Thing → Objections through the belief-breaking formula → one CTA. Lines come from the owner's own answers, never a script Claude writes. Made with the launch-video skill's engine and voice module, in either of two looks: on-screen (kinetic type plus real proof, no camera) or on camera (the owner filmed on their phone, cut line by line with proof in between). Covers the framework, the intake, scene mapping, pacing, voice, phone footage, A/B versions and testing. Use when someone wants a VSL, video sales letter, sales video, Hormozi VSL, landing-page video, "a video that sells my offer", an objection-handling video, or "turn my sales pitch into a video".
---

# Hormozi-style VSL

A VSL is your sales conversation, recorded once and played to everyone who lands on your page. This skill takes an
offer that doesn't have one yet and ends with a finished VSL: lines in the owner's own words, put in the order
Hormozi teaches, rendered to MP4. The engine, the scene types, the voice module and the render come from the
**launch-video** skill (`../launch-video/`). Read its SKILL.md and `reference/plan.md` first; this skill only adds what's
different for a VSL.

Two looks, same script:
- **On-screen:** the voice, kinetic type that lands word by word, and real proof between the lines. No camera needed.
- **On camera:** the owner records the whole script on their phone. The footage plays line by line, with proof shots cut in (§5b).

**References in this folder:**
- `reference-breakdown.md`: frame-by-frame breakdown of [Hormozi, "How to script a VSL"](https://www.youtube.com/watch?v=Lm_PEN6PH-M), including the flip-chart pages, timings and what he says in each block.
- `hormozi-vsl-research.md`: what he teaches about VSLs, hooks, offers, proof, CTAs and testing across his other videos and books, with sources and a tag on every claim saying where it came from.
- `examples/skeleton/plan.json`: the VSL structure as a launch-video plan, with placeholders instead of lines.

**Borrow the framework, not the identity.** Never use Hormozi's name, face, catchphrases, Acquisition.com branding or
his examples in a client's video.

## 1. The framework

From his flip chart (`reference-breakdown.md`):

```
INTRO (≤ 90 s)     UNIQUE THING (60–90 s, 3 min max)    OBJECTIONS 1–5 (each)    CTA
Promise            the named process:                   What they think          one action,
Pain               "here's how our thing works"         Why that's wrong         and what
Proof                                                   What's actually right    happens next
Plan                                                    Proof
Pic (road map)
```

| Block | Beat | Job |
|-------|------|-----|
| Intro | **Promise** | What they'll get from watching: "In this video I'll show you how we take X and make it Y." |
| | **Pain** | The situation they're in now, in their words. Be specific about the pain and more measured about the promise. |
| | **Proof** | It's been done for people like them: "this one, and this one, and this one." Real results only. |
| | **Plan** | How the video is laid out: "our N-step process, then the questions everyone asks." |
| | **Pic** | A visual road map, so they know where they are and how long they're in for. |
| Unique thing | **Named method** | The process end to end, as *your* way, with a name. |
| Objections | **× 3–5** | Each false belief that stops the sale, broken in four moves: what they think → why it's wrong → what's actually right → proof. |
| CTA | **One action** | Exactly what to do, a reason to do it now, and what happens after. |

**Where it sits.** Default: **the landing page**, above the fold, with the CTA button directly under the video. In
Hormozi's example the same video is also texted between a quote request and the appointment, to pre-frame the visit.
It's the same video wherever it goes, and mostly only the CTA changes. A later VSL in the same funnel (after a call, at renewal) swaps in different examples and the objections people have *at that stage*.

**Warm traffic only.** He says a VSL → book-a-call funnel is a warm motion. Cold traffic doesn't convert through a short VSL, so send cold traffic to a lead magnet or paid workshop first. Also from him: you "basically never sell less with a VSL".

**Make two versions:** same script, different examples. That's the first A/B test.

### Which VSL to build

| Situation | Structure |
|-----------|-----------|
| Lead → appointment or sales call (local service, high-ticket) | The framework above. Answer the common FAQs and deal-killers in the VSL so the call is for closing (his example: "your spouse needs to be there"). |
| Well-understood service (dentist, chiropractor) | His second structure: who, what, where, when, why, how ("what to expect"), then the biggest objections through the four moves, then a stack of before/afters and testimonials. |
| No call: they buy from the page (low-ticket, courses, communities) | The long form in `hormozi-vsl-research.md` §1: call-out → bridge story → credibility → offer → FAQ → 5+ proof stories → price anchor → concerns → next steps → best/worst-case close → guarantee + real urgency. |
| Group or launch funnel | Five short videos: opportunity → 3 belief-breaking stories (the vehicle, other people, themselves) → CTA. One `launches/` project each. |

### Rules for every line

These are Hormozi's rules; sources are in `hormozi-vsl-research.md`.

- **The first 3–5 seconds decide it.** Open on the call-out and the promise.
  - Say who it's for and who it's *not* for.
  - Use a specific moment, not a category: "the yard you close the blinds on", not "an ugly yard".
  - A lead who just requested a quote is most aware, so go straight to the promise.
- **Rule of One:** one big idea for the whole video. Every proof and objection reinforces it.
- **Third-grade reading level:** short sentences, small words.
- **Proof beats promise.** A **damaging admission** (one true flaw, "but", then the claim) buys trust.
- **Show, don't tell.** Every claim gets something on screen. He criticised all-talking-head sales videos; show each part as it's named, like an unboxing.
- **Real scarcity and urgency only,** with a reason why. A service business's capacity is real; say it.
- **CTA: clear, not clever.** One action. End on a P.S. card: a one-line recap or "who this isn't for".

### More rules from the full corpus

From 551 videos and 281.9 hours of his transcripts; sources in `hormozi-vsl-research.md` §8.

- **The first 60 seconds.** He says people meander for 1–2 minutes and lose about 40% of the audience. Open fast:
  - proof first, from someone just like the viewer;
  - then the promise;
  - then the plan for the rest of the video.
  On the flip chart he writes Promise first, but in other videos he lists proof first. Either order works; never meander.
- **Old way vs. our new way.** State the big idea as the contrast, and say why you exist.
- **One offer.** He deletes the downsell from a VSL on camera. The VSL sells the main thing only.
- **Price.** Put the price (or a range) in only when you have more demand than your sales team can handle, as friction that protects their time. With spare capacity, leave it out.
- **FAQ in their words.** Use the exact questions prospects ask on calls: "A lot of people ask this. Here's how we answer it."
- **Lead magnet inside.** If the page offers a free thing, tease it early and deliver it about a third of the way in.
- **Check they watched.** Confirm it in reminders, or with an engagement CTA ("text me your event date"). Open the call with "did you watch the video?"
- **Proof stack.** One proof per avatar up front (3–4), then before/afters and testimonials near the end. His dental VSL is "basically a ton of testimonials."
- **Improve it from the drop-off graph.** Expand the parts where engagement spikes and fix the drop-offs, starting with the opening. If a recorded VSL won't convert, deliver it live a few times to tighten it.

## 2. Intake: start from the owner's words

**Don't write the VSL for them.** A script written to be read sounds read. In the reference, Hormozi *talks each beat
out* the way the owner would on a sales call. Do the same:

1. **Brief, in one message** (launch-video §1, plus the VSL questions, plus: on-screen or on camera?). Ask them to answer the way they'd say it to a customer:
   - **Promise:** what do people get when you're done?
   - **Pain:** what do customers say on the first call? What are they embarrassed or worried about?
   - **Proof:** which 3 jobs would you show first? Send photos, screenshots, real numbers and reviews (with permission).
   - **Method:** walk me through what you do, step by step. What do you call it?
   - **Objections:** the 3–5 things people say that stop them buying. For each one: what do they think, why is it wrong, what's actually true, and which job proves it?
   - **CTA:** after watching, what's the one thing they should do? What happens after they do it?
   - **Format** (16:9 or 9:16), **voice** and **brand link**, as in launch-video.
2. **Or a riff:** have them record each block unscripted (`vo.py import` a phone take, or a voice memo), transcribe it, and edit from the transcript.
3. **Edit, don't rewrite.** Cut filler, keep their phrasing, and split into launch-video lines: one idea per line, about 9 words max.
4. **Show them the lines** (`python3 ../launch-video/vo.py script launches/<name>`) before building scenes. If a line doesn't sound like them, it goes.
5. **Check every claim.** Counters, stats, reviews and before/afters must be real. Never invent proof, testimonials or results. If a beat needs a fact you don't have, ask.

## 3. Scenes: how each VSL beat maps to launch-video

Projects live in `launches/<name>/` like any launch. Start from `examples/skeleton/plan.json`. Put real proof in
`assets/` (job photos, screenshots, review screenshots), and pull the brand with `../launch-video/brand.py` if
they have a site.

| VSL beat | Scene | Notes |
|----------|-------|-------|
| Hook / Promise | `text`, `bg: dark` | Pill on the outcome: "how we turn a [yard you hide] into one you show off." |
| Pain | `text`, `mode: type`, `bg: dark` | Typed reads like their own thought. One specific moment per line. |
| Proof (intro) | `cards`, `layout: row` or `fan`, `bg: light` | 3 real job photos, `label` = the street or client type, one landing per "this one". |
| Plan / Pic (road map) | `chips`, `bg: light` | `["How it works", "→", "Your questions", "→", "Next step"]`, one chip per block, lit as it's named. |
| Section marker | `text`, short | "[Part 2:] what people worry about." This is the road map callback at the top of each block. |
| Method reveal | `hero` → `logo` | "Meet" → the company lockup. `logo` always shows `brand.name`, so put the method's name in `tagline` ("The Lone Oak *Method*"). Or follow "Meet" with a `text`, `mode: letters`, `size: xl`, `bg: glow` carrying the name. The riser and boom land on the reveal. |
| Each method step | `ui`, `frame: none` (photo) or `browser` (software); or `cards` | One step per scene. `cam` keys zoom to the detail that the line names, and `focus` lifts it. |
| Process overview | `chips` | The steps as a flow: `["Design", "→", "Prep", "→", "Build", "→", "Walkthrough"]`. |
| Objection: what they think | `text`, `bg: dark` | The belief in serif italic: "A lot of people think _dead grass means starting over._" |
| Why it's wrong / what's right | `text` | "It doesn't. We [resod it] in two days." Pill on the truth. |
| Objection proof | `ui` photo (before) → `ui` photo (after), or `cards` | Add a real counter: "Same yard, {48} hours later." |
| Social proof | `ui` + `toasts` | Real reviews only, in their exact words, with permission (`title` = name/stars, `body` = the review). |
| Numbers | `chips` or `{from..to}` counters | Real numbers only: jobs done, years, review count. |
| CTA | `text`, `bg: glow` | Pill on the action ("Text us at [555 0100]"), `sub` = URL or what happens next. |
| P.S. | last `text`, `hold` 2–3 s | One-line recap, or "who this isn't for". |

**Backgrounds follow the launch rhythm:** dark for the hook, pain and each objection's belief; light for proof and the
process; glow for the method reveal and CTA. The flip from dark to light *is* the turn from problem to proof.

**No real UI?** Most service businesses have photos, not software. Use `ui` with `frame: "none"` for photos, and `cam`
keys (`{"at": 1.2, "to": [x, y, w, h], "fill": 0.6}`) to zoom into what the line names. Coordinates are fractions of the
photo: open it and check.

## 4. Pacing and length

| Block | Duration | Lines (~9 words, ~3.5 s each) |
|-------|----------|-------------------------------|
| Hook / Promise | 5–10 s | 1–3 |
| Rest of intro (Pain, Proof, Plan, Pic) | 60–80 s | 15–22 |
| Unique thing | 60–90 s (180 s max) | 15–25 |
| Each objection (× 3–5) | 30–60 s | 8–15 |
| CTA + P.S. | 15–30 s | 4–8 |
| **Total** | **~5–7 min** | **~70–120 scenes** |

- Keep launch-video's line rules: one idea per line, a new visual every 1.5–4 s.
- Speak at the **standard pace (~2.5 words/s)**, slightly slower than a 40 s launch (2.6 w/s). A VSL is a conversation.
- **Hormozi's own number: "five to seven minutes. Doesn't need to be long."** He said this in two separate videos (`hormozi-vsl-research.md` §8).
- **Music:** the synth bed is tuned for 30–60 s launches with one drop. For a VSL use `"music": false` or a licensed, quiet bed (`{"file": …, "gain": 0.12}`). Set `music.drop` on the method reveal if it has one.
- **SFX** come from the scenes automatically. Over 100 scenes that's a lot of pops and whooshes, so lower `mix.sfx` to about 0.3.

## 5. Voice

The owner's own voice is the strongest proof the video has. Record it rather than using TTS, unless they insist.

```bash
python3 ../launch-video/vo.py say      launches/<name>   # free draft voice, for timing and the board
python3 ../launch-video/vo.py record   launches/<name>   # teleprompter, one take per line: give them the command, they run it
python3 ../launch-video/vo.py auphonic launches/<name>   # master the takes (one production; free plan adds a jingle)
```

For the launch-video voice protocol, put this in the plan: `"vo": {"lead": 0.04, "pre": 0.06, "post": 0.18, "hold": 0.45, "level": -17, "denoise_db": 12}`.

A VSL is 70–120 lines, so recording is a real session. Split it by block with `--line N` retakes, and re-run
`auphonic` after any re-record. For a riff, `vo.py import` a long take instead. Fish Audio and ElevenLabs work too
(`vo.py fish` / `eleven`); state the character count first (around 4,000–7,000 for a VSL).

## 5b. On camera: record it on your phone

Same lines and plan, with the owner on screen for the lines that need a face (promise, the method, the CTA) and
proof shots everywhere else.

1. **Film the whole script in one take**, reading the lines in order with a short pause between them.
   - Landscape for 16:9, portrait for 9:16.
   - Phone at eye level, a window in front of you, a quiet room.
   - Mess-ups are fine: pause, then say the line again.
2. **Prep the file** (HEVC → H.264, full resolution): `python3 ../launch-video/screen.py ~/Downloads/IMG_1234.MOV launches/<name>/assets/phone.mp4`
3. **Voice from the same take:** `python3 ../launch-video/vo.py import launches/<name> launches/<name>/assets/phone.mp4`, then `vo.py auphonic` (optional) and `vo.py build`.
4. **Mark face scenes** in `plan.json` with `"face": true`. Keep proof scenes (`cards`, `ui` photos, `chips`, counters) as they are.
5. **Sync:** `python3 face.py launches/<name> launches/<name>/assets/phone.mp4`.
   - Each face scene becomes a `ui` scene with `frame: none` playing the footage from the second its first word is spoken.
   - The voice is the same take, so the lips match. Tested to within one frame.
   - Re-run it after any timeline change.
6. Board, render and check as usual (§6).

`ui` plays footage muted. The sound comes from the voice track, which is what keeps Auphonic mastering and the timeline
in charge. A retake recorded with `vo.py record --line N` won't match the footage, so re-film that line instead and
`vo.py import` again.

## 6. Build, render, check

```bash
node ../launch-video/engine/render.mjs launches/<name> --board      # one frame per scene: read it, fix layout
node ../launch-video/engine/render.mjs launches/<name> --draft      # half size, 15 fps
node ../launch-video/engine/render.mjs launches/<name>              # out/<name>.mp4 (1080p30) + out/<name>-review.mp4
```

- **Before showing anything, read the board yourself.** On a 100-scene board, check each block's first scene, every photo crop, and every pill.
- **After the render, pull strips around every block change** (launch-video §6). Look for captions that run ahead of or behind the voice, crops that miss what the line names, and text collisions.
- **Version B:** copy the project and swap the `assets/` photos and objection proof, keeping the lines. Clips are cached by text, so the voice is reused and nothing is re-recorded.

## 7. Deliver and test

- **Deliver:** `out/<name>.mp4`, the lines, and the plan for version B.
  - Pre-appointment: text the link right after booking, with a short line from the rep.
  - Landing page: put it above the fold with the CTA button directly under it.
- **Test one thing a week**, starting with the hook and the first 3 lines. Keep the body, rotate the opening.
- **Track:**
  - how many leads watch, and how far they get;
  - show rate;
  - first-visit close rate, compared with before the VSL went out.

  Show rate is often the bigger lever.

## Pitfalls

- **Skipping the Pic.** Without the road map, viewers don't know how long they're in for, and they leave.
- **Objections without the fourth move.** Proof is what breaks the belief. No photo or number for an objection? Find one or drop it.
- **Generic proof.** Show people like the viewer (same kind of house, same problem), not a highlight reel.
- **Launch-length habits.** One pill per line still applies, but don't hero-reveal more than once. The method reveal is the only "Meet" moment.
- **Lines over ~9 words.** They wrap and shrink. Split them.
- **More than one CTA.** One action, then what happens next.
- **Lines that sound written.** If the owner wouldn't say it on a sales call, cut it. No production jargon in spoken lines ("beats", "framework", "road map", "Part one:"). Those are words for building the video, not things a person says to a customer.
- **Selling the format instead of the outcome.** "No face", "made in code" and "same engine as…" are how the video gets made, not why anyone buys. Lead with what the viewer gets. Production details belong in proof only if they answer a real objection.
- **Skipping the intake.** Claude drafting the lines itself, even "just as a draft", is the failure this skill exists to prevent. Ask the questions in §2 first, even when the product is your own.
- **Fake or inflated claims.** Never fabricate testimonials, reviews, results or before/afters. Blur any person in a photo who hasn't agreed to be shown.
