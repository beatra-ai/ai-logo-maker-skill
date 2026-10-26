# AI Logo Maker Skill

English | [简体中文](./README.zh-CN.md) | [日本語](./README.ja.md)

> 👉 See also [AI Poster Maker Skill](https://github.com/beatra-ai/ai-poster-maker-skill)

Turn a brand name, industry, or reference image into logo concepts and a scalable brand mark, from inside Claude Code, Cursor, Codex, Windsurf, Cline, or OpenClaw.

> [!IMPORTANT]
> Rendering needs a [Beatra](https://beatra.ai?utm_source=github&utm_medium=flagship&utm_campaign=ai-logo-maker-skill) account and uses credits. The skill itself is free to install.

| Question | Answer |
| --- | --- |
| **What it does** | Turn a brand name, industry, or reference image into a professional AI logo, brand mark, or app icon with multi-concept exploration, precise brand colors, and scalable composition. |
| **Models** | Qwen Image 2.0 Fast, Qwen Image 3.0, Qwen Image 3.0 Pro, GPT Image 2.5 Flare, GPT Image 2.5 Sunburst, GPT Image 2, Wan Image 2.7 Fast, Qwen Image 2.0 Pro, Wan Image 2.7 Pro, MiniMax Image 01 Live, Wan 2.7, Wan 3.0 Video, MiniMax H3, Seedance 2.0 Mini, HappyHorse 1.1, Seedance 2.0 Fast, Seedance 2.0, Wan 3.0 Video Prime, Seedance 2.5 |
| **Requirements** | Python 3.10+ and an agent that loads `SKILL.md` |
| **Cost** | Free to install. Each render uses credits on your Beatra account, and paid steps run only when you ask for that exact render or approve its card. |
| **Works with** | Claude Code, Cursor, Codex, Windsurf, Cline, OpenClaw |

<p align="center"><img src="assets/hero.webp" width="800" alt="Three logo directions for a fictional specialty coffee roaster, Brightmoss: a bean-and-leaf combination mark, a B lettermark with a coffee-drop cutout, and a sun-over-cup emblem. AI-generated with Beatra."></p>

*Three logo directions for a fictional specialty coffee roaster, Brightmoss: a bean-and-leaf combination mark, a B lettermark with a coffee-drop cutout, and a sun-over-cup emblem. AI-generated with Beatra.*

| Skill | Entry point | Version |
| --- | --- | --- |
| [`ai-logo-maker`](skills/ai-logo-maker) | [SKILL.md](skills/ai-logo-maker/SKILL.md) | 0.2.9 |

This repository is published automatically from [beatra-ai/beatra-skills](https://github.com/beatra-ai/beatra-skills/tree/main/skills/ai-logo-maker). Report issues there.

## Install

With the [`skills`](https://skills.sh) CLI:

```bash
npx skills add beatra-ai/ai-logo-maker-skill
```

With the GitHub CLI:

```bash
gh skill install beatra-ai/ai-logo-maker-skill ai-logo-maker
```

Or clone this repository and copy `skills/ai-logo-maker` into `~/.claude/skills/` for Claude Code,
`~/.cursor/skills/` for Cursor, `~/.agents/skills/` for Codex, `~/.codeium/windsurf/skills/` for Windsurf,
`~/.cline/skills/` for Cline, or `~/.openclaw/skills/` for OpenClaw.

Or paste this into your agent:

```text
Install the ai-logo-maker skill from https://github.com/beatra-ai/ai-logo-maker-skill (folder skills/ai-logo-maker), then follow its SKILL.md to connect my Beatra account.
```

## Examples

<p align="center"><img src="assets/demo-2.webp" width="800" alt="The chosen Brightmoss bean-and-leaf direction refined into an app icon and a horizontal wordmark lockup. AI-generated with Beatra."></p>

*The chosen Brightmoss bean-and-leaf direction refined into an app icon and a horizontal wordmark lockup. AI-generated with Beatra.*

Ask your agent:

```text
Take the approved Brightmoss bean-and-leaf logo and turn it into an app icon on a deep forest green rounded square plus a horizontal wordmark lockup, both on the same warm cream background.
```

Prompt:

```text
Refine this accepted Brightmoss logo into a two-part brand presentation on one flat warm cream background (#F4EEE2). Left: an app icon, a solid rounded square in deep forest green (#1F4D3A) with the same coffee-bean-and-leaf symbol from the image centered inside in cream, generous padding, no text in the icon. Right: a horizontal lockup, the same green bean-and-leaf symbol placed to the left of the exact word "Brightmoss" in the same bold humanist sans-serif lettering, forest green, vertically centered with the symbol. Keep the symbol shape and the wordmark letterforms identical to the source. Flat vector, maximum two colors, no gradients, no shadows, no mockup, no tagline, no other text.
```

## Technical Specifications & Output Limits

As of 2026-10-18. Live list: https://docs.beatra.ai/en/docs/models

- **Uploads** — up to 100 MB per file; the per-model input limits below also apply
- **Text to image** — 10 models (Qwen Image 2.0 Fast, Qwen Image 3.0, Qwen Image 3.0 Pro, GPT Image 2.5 Flare, GPT Image 2.5 Sunburst, GPT Image 2, Wan Image 2.7 Fast, Qwen Image 2.0 Pro, Wan Image 2.7 Pro, MiniMax Image 01 Live); PNG; up to 4 images per request; canvas up to 16.8 MP
  - 16.8 MP (4K tier): Wan Image 2.7 Pro (up to 4 images per request); GPT Image 2.5 Flare, GPT Image 2.5 Sunburst, GPT Image 2 (1 image per request)
- **Image to image** — 10 models (Qwen Image 2.0 Fast, Qwen Image 3.0, Qwen Image 3.0 Pro, Wan Image 2.7 Fast, Qwen Image 2.0 Pro, Wan Image 2.7 Pro, GPT Image 2.5 Flare, GPT Image 2.5 Sunburst, GPT Image 2, MiniMax Image 01 Live); PNG; up to 4 images per request; canvas up to 16.8 MP
  - 16.8 MP (4K tier): GPT Image 2.5 Flare, GPT Image 2.5 Sunburst, GPT Image 2 (1 image per request)
  - Input images: up to 4 per request, 10–20 MB each; BMP, GIF, JPEG, PNG, TIFF, WEBP
- **Image editing** — 6 models (Qwen Image 2.0 Fast, Qwen Image 3.0, Qwen Image 3.0 Pro, Wan Image 2.7 Fast, Qwen Image 2.0 Pro, Wan Image 2.7 Pro); PNG; up to 4 images per request; canvas up to 4.2 MP
  - 4.2 MP (2K tier): Qwen Image 2.0 Fast, Qwen Image 3.0, Qwen Image 3.0 Pro, Wan Image 2.7 Fast, Qwen Image 2.0 Pro, Wan Image 2.7 Pro (up to 4 images per request)
  - Input images: up to 4 per request, 10–20 MB each; BMP, GIF, JPEG, PNG, TIFF, WEBP
- **Image to video** — 9 models (Wan 2.7, Wan 3.0 Video, MiniMax H3, Seedance 2.0 Mini, HappyHorse 1.1, Seedance 2.0 Fast, Seedance 2.0, Wan 3.0 Video Prime, Seedance 2.5); 480p to 4K; 2–30 s; aspect ratios 16:9, 1:1, 21:9, 3:4, 4:3, 9:16; MOV, MP4
  - 4K: Seedance 2.0, up to 15 s
  - 30 s: Wan 3.0 Video, Wan 3.0 Video Prime, Seedance 2.5, up to 1080p
  - Native audio: Wan 2.7, MiniMax H3

## Why use Beatra instead of calling model APIs directly

- **One account for every model this skill uses** — Text to image 10; Image to image 10; Image editing 6; Image to video 9 (Qwen Image 2.0 Fast, Qwen Image 3.0, Qwen Image 3.0 Pro, GPT Image 2.5 Flare, GPT Image 2.5 Sunburst, GPT Image 2, Wan Image 2.7 Fast, Qwen Image 2.0 Pro, Wan Image 2.7 Pro, MiniMax Image 01 Live, Wan 2.7, Wan 3.0 Video, MiniMax H3, Seedance 2.0 Mini, HappyHorse 1.1, Seedance 2.0 Fast, Seedance 2.0, Wan 3.0 Video Prime, Seedance 2.5) (as of 2026-10-18), behind one Beatra sign-in; no keys from individual model providers to manage.
- **You decide what gets paid for** — Paid renders run only when you ask for that exact render or approve its card, which shows the live credit estimate.
- **Direction before rendering** — the skill plans, directs, and reviews the work, then renders it on Beatra.
- **Files you can verify** — every file under `skills/` matches the release archive on cdn.beatra.ai byte for byte, checked by SHA-256 before each push.
- **Updates you control** — no self-updater; update with the tool you installed it with.
- **Runs in your agent** — Claude Code, Cursor, Codex, Windsurf, Cline, OpenClaw.

## What you get

- **Explore before you commit** — Generate multiple logo concepts from one brand brief, compare directions side by side, then refine the strongest. Professional logo design starts with options.
- **Built for every size** — Every concept is composed for favicon clarity, app icon precision, and social avatar impact. Strong silhouettes and limited palettes that stay recognizable from 16 pixels to billboard.
- **Your exact brand colors** — Lock precise brand colors with hex values and weighted palettes, so the logo carries your identity rather than a random color choice.

## Use cases

- **New business and startup logos** — Go from a company name and industry to a professional brand identity, with multiple concepts to compare before choosing a direction.
- **App icons and product marks** — Create square icons ready for app stores, favicons, software dashboards, and product launches—with safe-area margin built in.
- **Brand refresh from existing assets** — Transform sketches, mood boards, or an existing logo into a polished modern mark while preserving the original direction.
- **Social media and content branding** — Build profile avatars, watermarks, and a consistent visual identity that carries across platforms and content formats.

## FAQ

### What logo styles can I create?

Wordmarks, lettermarks, pictorial marks, abstract marks, monograms, emblems, and combination marks. Share the brand name, industry, and the feeling you want, and the best style for the context is recommended.

### Will my logo work as a tiny favicon?

Every concept is composed for small-size legibility with strong silhouettes, high contrast, and minimal detail. Review the result at thumbnail size before finalizing.

### Can I match my existing brand colors?

Yes. Provide hex color values and the logo generation uses them as the palette foundation, with precise weighted color control.

### Can I refine a logo I already have?

Yes. Upload the existing logo or sketch, describe what to change, and the refinement preserves the overall direction while adjusting specific elements.

## Updates and security

Since the 2026-10 release, this skill contains no self-updater: it runs only the
files you installed and never replaces them on its own. Update it with the tool
you installed it with — `npx skills update ai-logo-maker` or `gh skill update ai-logo-maker`.
Details: `references/updates-and-security.md` inside the skill.

## License

[MIT-0](LICENSE) — free to use, modify, and redistribute, including
commercially. No attribution required. Same terms as these skills carry on
ClawHub.

## Links

- Website — https://beatra.ai?utm_source=github&utm_medium=flagship&utm_campaign=ai-logo-maker-skill
- Docs — https://docs.beatra.ai?utm_source=github&utm_medium=flagship&utm_campaign=ai-logo-maker-skill
- Console — https://console.beatra.ai
- For AI agents — https://beatra.ai/llms.txt (index) · https://beatra.ai/llms-full.txt (every skill in one file)
