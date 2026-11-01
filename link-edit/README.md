# link-edit, a Claude Code skill

Paste a link, get the edit. You film yourself talking. Claude scrapes the real assets with
[context.dev](https://link.context.dev/keeran-jagadesan), cuts you out of the clip on your Mac, and renders a finished
9:16 effect with the asset behind or around you. You never go looking for a logo, a screenshot or a font.

| Command | What you get |
|---|---|
| `/logo-wall nvidia.com` | Their real logo and color, in a wall behind you |
| `/site-spin apple.com` | Their real pages, orbiting your head |
| `/news-hit claude ultra` | The real headline with the key words highlighted, and you in front of it |
| `/price-tag claude.com/pricing` | Live prices hanging on strings around you |
| `/brand-caps vercel.com` | Captions in their exact font, colors and button style |

- **Real assets, not lookalikes**: the logo, pages, prices and fonts are pulled live from the site you name.
- **Any length of take**: cut yourself out once, then point each effect at the second you want it.
- **Your own audio stays**: each clip comes back with your voice on it, ready to drop into your edit.

## Install

**The easy way:** paste the repo link into Claude Code and say "set up the link-edit skill":

```
https://github.com/kjagsadvisors/keeran.ai
```

**By hand:**

1. Copy the `link-edit` folder into `~/.claude/skills/`.
2. Copy `commands/*.md` to `~/.claude/commands/`.
3. Install the tools once (Mac):
   ```bash
   xcode-select --install
   brew install node ffmpeg
   pip3 install numpy pillow
   cd ~/.claude/skills/link-edit/fx && npm install
   ```

## Connect context.dev

The skill can't run without it, because that's where every asset comes from.

1. Make your account with [this link](https://link.context.dev/keeran-jagadesan). The free plan is enough to start: you
   get 1,000 credits a month, and two full reels took about 65.
2. Upgrading? Code **KEERAN25OFF** gets you a discount on a paid plan.
3. Connect it:
   ```bash
   claude mcp add --transport http context https://mcp.context.dev/mcp
   ```
   Then open `/mcp` in Claude Code and sign in to `context`.

That's my referral link, so I may earn something when you sign up or upgrade through it.

## Use it

```
/logo-wall nvidia.com my-clip.mov
```

Hold your phone so your head sits in the lower half of the frame. That headroom is where the effect goes.

Needs a Mac and Google Chrome. Use assets you have the right to use: other companies' logos, pages and headlines are
fine to talk about on your own page, not to run in a paid ad.
