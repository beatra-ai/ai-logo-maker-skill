# Brand brief and routing

## Start from the user's actual starting point

A logo request arrives in one of three shapes. Identify which one before
choosing a tool.

| Starting point | What is enough to start | Route |
| --- | --- | --- |
| No source image | Brand or project name plus one industry or style cue | `beatra.images.generate` |
| One to four visual references | Ordered references plus a clear logo goal | `beatra.images.transform` |
| Accepted draft | The draft plus the requested change | `beatra.images.edit` |

A brand name alone with no industry or style cue is enough to propose a
default direction and include it in the single paid-call confirmation. Do not
interview the user before generating when a reasonable default exists.

## Extract the brand brief

Collect what is already known and fill gaps only when they materially change
the result.

- **Brand or project name.** The name that appears in or accompanies the mark.
  Reuse it exactly as given.
- **Industry or personality cue.** One descriptor is enough: tech, food,
  finance, health, education, fashion, gaming, legal, artisanal. If the user
  says "modern coffee shop," the industry is coffee and the personality is
  modern.
- **Style direction.** Minimal, bold, playful, elegant, geometric, hand-drawn,
  retro, futuristic. If absent, infer from the industry cue and include the
  inferred direction in the confirmation.
- **Logo type.** When the user names a type, use it. When absent, choose based
  on the brand name length and industry.

## Logo type guidance

Different logo types need different prompt structures.

- **Wordmark** — the brand name rendered as the logo (Google, Coca-Cola). Best
  when the name is short and distinctive. Prompt should emphasize typography
  style, letter spacing, and color.
- **Lettermark / monogram** — initials or a shortened form (IBM, HBO). Best
  when the brand name is long. Prompt should emphasize letter geometry and
  negative space.
- **Pictorial mark** — a recognizable symbol or icon (Apple, Twitter bird).
  Best when the brand has a strong visual association. Prompt should emphasize
  the symbol, its silhouette, and simplicity.
- **Abstract mark** — a non-literal geometric form (Nike swoosh, Pepsi circle).
  Best for brands that want a unique ownable shape. Prompt should emphasize
  motion, balance, and form.
- **Emblem** — text enclosed inside a symbol shape (Starbucks, Harley-Davidson).
  Best for traditional or premium brands. Prompt should emphasize the badge or
  seal container.
- **Combination mark** — text plus symbol side by side (Adidas, Lacoste). Best
  for new brands that need both a symbol and name recognition. Prompt should
  describe both elements and their spatial relationship.
- **Mascot** — a character illustration (KFC Colonel, Michelin Man). Best for
  family-friendly or sports brands. Prompt should emphasize the character
  personality.

## One visual hook

Every logo concept should distill to one memorable visual idea. Before
generating, identify the single strongest element: a shape, a letterform, an
animal, an object, a gesture. Keep supporting details subordinate to that one
hook so it survives at small sizes.

## Defaults that avoid unnecessary questions

- Canvas: square `1:1` for the master logo (the most versatile single output).
- Count: if they name 1–4, that is `count`. If they name more than 4, still one
  call, `count=4`. If they only name styles or say nothing, `count=2`. A style
  list is not several calls. Do not fire `count=1` four times.
- Model: `auto`.
- Style: infer from industry when absent; state the inference in the
  confirmation.
- Brand colors: put hex codes in the prompt. Omit `palette` unless they asked
  for a 3–10 color board with weights.

## Visual access

Local files enter the workflow through `beatra.assets.upload`. Upload makes the
bytes available to the remote tool; it does not itself inspect the image.
Review only visual facts the host can actually see. When the host cannot view
an image, state that visual verification was not possible and proceed on the
user's declared intent.
