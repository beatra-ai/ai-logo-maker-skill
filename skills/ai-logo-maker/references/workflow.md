# Workflow

## Build one logo brief

Translate the brand name, industry cue, style direction, and logo type into a
single coherent prompt. Keep the prompt focused on the visual result, not on
process language. Include scalability constraints directly.

Example prompt structure:

> Professional logo for [brand name], [industry] industry, [style direction]
> [logo type]. Bold simple silhouette, maximum three solid colors, high
> contrast, no gradients, no fine detail, centered composition with generous
> safe area, recognizable at small sizes.

## Prepare the selected route

### Generate without references

Use `beatra.images.generate` when there are no source images.

```json
{
  "prompt": "Professional logo for Lumen, a tech startup, minimalist abstract mark. Bold geometric shape suggesting a light beam, deep blue #0E4D92 and electric cyan #00C4FF, white background, strong silhouette, no text, no gradients, scalable to favicon.",
  "model": "auto",
  "count": 2,
  "canvas": {
    "type": "preset",
    "tier": "2K",
    "aspect": "1:1"
  },
  "client_request_id": "lumen-logo-explore-001"
}
```

### Transform with ordered references

Use `beatra.images.transform` with one to four ordered references. Upload local
files through the bundled client helpers first, then reference the returned
artifact IDs. Label each image's role explicitly in the prompt so the model
understands which reference guides what.

```json
{
  "prompt": "Professional logo for Lumen. Image 1 is a hand-drawn sketch whose geometric outline and arrow motif should anchor the composition. Image 2 guides only the color palette (deep blue #0E4D92 and electric cyan #00C4FF). Refine into a clean mark with strong silhouette, white background, centered, scalable to favicon.",
  "model": "auto",
  "count": 1,
  "canvas": {
    "type": "preset",
    "tier": "2K",
    "aspect": "1:1"
  },
  "images": [
    {"type": "artifact", "artifact_id": "<sketch-artifact-id>"},
    {"type": "artifact", "artifact_id": "<color-reference-artifact-id>"}
  ],
  "client_request_id": "lumen-logo-from-sketch-001"
}
```

When more than one reference is supplied, their order matters. The last image
anchors the output ratio when canvas aspect is `source`.

### Edit an accepted draft

Use `beatra.images.edit` with the draft as `images[0]`. Later entries are
optional references. Use at most two normalized `edit_regions` for targeted
work; omit regions for a whole-image adjustment.

```json
{
  "prompt": "Simplify the logo mark, reduce to two colors, strengthen the silhouette for small-size clarity, keep the overall composition.",
  "model": "auto",
  "count": 1,
  "images": [
    {"type": "artifact", "artifact_id": "<accepted-draft-artifact-id>"}
  ],
  "edit_regions": [
    {
      "image_index": 0,
      "x": 0.2,
      "y": 0.15,
      "width": 0.6,
      "height": 0.5
    }
  ],
  "client_request_id": "lumen-logo-refine-001"
}
```

## Apply brand colors and model controls

### Colors

Put hex codes in the prompt. Omit `palette`. Send `palette` only if they asked
for a 3–10 color board with weights. Then copy this shape. Never `r` / `g` /
`b`. Weights must sum to exactly `1.0000`.

```json
"palette": [
  {"color": "#1655E0", "weight": 0.5},
  {"color": "#00B872", "weight": 0.3},
  {"color": "#00C2D1", "weight": 0.2}
]
```

### Model and count

Keep `model=auto` unless the user explicitly requests a concrete model. How
many images this generate call: if they name 1–4, that is `count`. If they
name more than 4, still one call, `count=4`. If they only name styles or say
nothing, `count=2`. A style list is not several calls. Do not fire `count=1`
four times to make two or four options. Keep `count=1` for transform and edit
unless they name 1–4. Call `beatra.models.list` with the relevant capability
(`text_to_image`, `image_to_image`, or `image_edit`) only when the user asks
about model availability, compatibility, or price.

When the user asks how many credits remain, call `beatra.wallet.get`. When they
ask what was charged, call `beatra.wallet.ledger`. Both are read-only. Do not
invent an account-balance or top-up tool. Do not make `wallet.get` a required
step before every paid submit.

## Confirm, submit once, and monitor

Present one final confirmation card containing the complete prompt, ordered
references, canvas, brand colors, logo type, count, and model. After approval,
create one stable opaque `client_request_id` and submit once. Record the
returned `task_id` and poll with `beatra.tasks.get`.

A changed prompt, reference set or order, canvas, colors, model, count, or
control value is new paid work requiring a new confirmation and a new
`client_request_id`.
