# Logo craft

## Design for the smallest size first

A logo that fails at favicon size is not finished. Every concept must stay
recognizable at 32 × 32 pixels. Build the prompt around:

- **one strong silhouette** — the overall shape should be identifiable as a
  single mass even when detail is lost;
- **one to three colors** — fewer colors survive scaling; gradients and texture
  break down at small sizes;
- **high contrast** — the mark must separate from its background at any size;
- **no fine detail** — hairlines, thin strokes, and small text disappear;
- **generous safe area** — keep the focal element centered with margin so
  circular and rounded crops do not clip it.

Include these constraints directly in the generation prompt. For example:
"bold simple geometric shape, strong silhouette, maximum three solid colors,
high contrast, no gradients, no fine detail, scalable to small sizes."

## Brand color discipline

Put exact brand colors in the prompt as hex codes such as `#1655E0`. Omit
`palette` unless the user asked for a 3–10 color board with weights. Then each
entry is `{"color":"#1655E0","weight":0.5}`. Never `r` / `g` / `b`. All
weights must sum to exactly `1.0000`.

When the user does not provide colors, let the model choose and review the
result for appropriateness to the industry and personality cue.

## Canvas and output

- Default canvas for generation: square `1:1` at `2K` tier. This single master
  works as an app icon (1024 × 1024), can be cropped to a favicon, and serves
  as a social avatar.
- For transform with references: use `source` to inherit the last reference's
  ratio, or set an explicit `1:1` when the user wants a square master.
- For edit: the default is `source`, which inherits the base image's ratio.
- A different ratio (horizontal for a website header, vertical for a banner)
  is a separate paid request with its own confirmation and `client_request_id`.

## Negative space and composition

Strong logos use negative space deliberately. When building the prompt:

- favor centered or slightly asymmetric balance over cluttered layouts;
- keep text (the brand name) to one placement, one size, one treatment;
- separate the symbol from the wordmark so each can be used independently;
- avoid decorative backgrounds that compete with the mark.

## Title treatment

When the brand name should appear inside the generated logo:

- quote the exact short name in the prompt;
- request one placement and one typographic treatment;
- do not add secondary text, taglines, or urls inside the image;
- generated typography is approximate; review legibility after delivery and
  advise the user that precise typesetting may require downstream adjustment.

When the user wants a text-free symbol mark, state that explicitly in the
prompt: "no text, no letters, no typography."

For wordmarks where the brand name IS the logo, typeface character is the
entire design. Guide the prompt with these distinctions:

- **geometric sans-serif** (clean, modern, tech) — uniform stroke weight,
  circular or geometric letterforms; works at small sizes but can feel cold;
- **humanist sans-serif** (warm, approachable, editorial) — varying stroke
  weight inspired by handwriting; friendly but less precise at tiny sizes;
- **serif** (classic, premium, editorial) — added stroke terminals convey
  tradition and authority; risk of terminal detail disappearing below 32px;
- **monospace** (technical, developer, retro) — equal-width characters;
  distinctive but can feel rigid for non-tech brands;
- **script / hand-drawn** (artisanal, personal, craft) — flowing or irregular
  strokes; high personality but low scalability and legibility at small sizes.

For any wordmark, specify the weight (light, regular, bold, black) and letter
spacing (tight, normal, wide) in the prompt. Bold and tight spacing improve
small-size legibility; light and wide spacing suit display-only contexts.

## Monochrome test

After generation, evaluate whether the logo would hold up in a single color
(pure black or pure white). If the concept relies on color contrast alone and
would disappear in monochrome, note this in the review and suggest
simplification. This is the most reliable predictor of scalability.
