# Animating a delivered image

Turn the image the user accepted into one short video clip with
`beatra.videos.animate`. That image is the first frame. This is the
in-place step that [next step](next-step.md) offers after an accepted image;
[offering one next step](next-step-offers.md) says when.

## Read the live card first

Read the card before describing the clip or its cost:

```text
printf '%s' '{"capability":"image_to_video"}' | python3 scripts/mcp_client.py call beatra.models.list
```

- When the card carries a `free_first_video` offer, this account's first
  image-to-video clip costs nothing inside the limits in its `applies_to`
  (model `auto`, the stated resolution, up to the stated `duration_seconds`;
  the aspect ratio does not matter). In the offer, say this in the user's own
  words; put the card's full sentence on the confirmation card. Keep the
  request inside those limits unless the user asks for more; when a longer
  duration or a higher resolution takes it outside, say on the card that this
  clip is no longer the free one.
- When there is no such offer, quote the live estimate for this exact request
  from the card's pricing, as for any paid call.

## Plan the clip

Planning is free.

- **Image:** the image the user accepted (when several were delivered, the
  one they chose), by its artifact ID:
  `{"type":"artifact","artifact_id":"<delivered-artifact-id>"}`. Do not upload
  it again and do not regenerate it.
- **Motion:** one restrained movement that keeps the composition: a slow
  camera push or pull, light sweeping across, soft particles or glow, drifting
  cloud, water, or fabric. Keep headline text, logos, product shape, and faces
  still or nearly still. Generated motion can bend lettering and fine
  geometry; when the image carries text or a logo, say so on the card.
- **Duration:** 5 seconds, the length the offer names and the free offer's
  limit today. When the card does not admit 5 seconds, use the admitted length
  closest to it and say the real length on the card. A longer length the user
  asks for is made here when the card admits it.
- **Model and resolution:** `model: "auto"`. Omit `resolution`, or use the
  offer's resolution.
- **Aspect ratio:** omit it so the clip follows the image. When the user wants
  another ratio, such as vertical 9:16 from a 2:3 poster, set `aspect_ratio`
  and say the frame will be extended or cropped; the ratio alone does not end
  the free offer.

## Confirm once, then submit once

Show one confirmation card before creating a request ID:

1. **Work:** animate the accepted image with `beatra.videos.animate`: the
   motion brief, duration, model `auto`, and the resolution and ratio as set.
2. **Price:** free under the first-video offer, together with the live
   estimate for the same request: when the service cannot apply the offer at
   submission (for example, the model chosen for `auto` is not covered), it
   charges the normal price instead. Without the offer, the live estimate.
   Either way the result reports the final charge.
3. **Count:** one clip.
4. **Identity:** one new opaque `client_request_id` for exactly this request.
5. **If they stop:** the delivered image stays theirs, unchanged.
6. **If the balance is short:** relay the official message and its top-up link
   unchanged; retry the same request only after the user says they topped up.

After the user agrees, submit exactly once:

```text
printf '%s' '{"image":{"type":"artifact","artifact_id":"<delivered-artifact-id>"},"prompt":"Slow camera push toward the center while warm light sweeps across the background. Headline text and logo stay still and sharp.","model":"auto","duration":5,"client_request_id":"<opaque-stable-id>"}' | python3 scripts/mcp_client.py call beatra.videos.animate
```

A changed image, prompt, duration, ratio, resolution, or model is a new
request with a new card and a new ID.

## Track and deliver

Record the task ID and poll that task with `beatra.tasks.get` until it ends.
Deliver the video link, its actual duration and dimensions, the task ID, and
`billing.net_charged_credits`; when the result says it was the free first
video, say so. When the host can play the clip, check that text, logo,
product, and faces kept their shape; say what could not be inspected. If the
task ID is lost, call `beatra.tasks.list` with
`{"capability":"image_to_video"}` and match candidates before any identical
retry. Slow polling never justifies a replacement request.

## Several shots or a series

For a clip of several shots, or a series made from many images, the dedicated
Skill does the whole job: Image to Video & Photo Animator. When the user asks
for that, answering with it is an answer to their question, not a second
offer. Describe it as in
[offering one next step](next-step-offers.md#pointing-to-another-beatra-skill),
with this install message in the user's language:

```text
请安装 图生视频与照片动画；需要登录授权时告诉我：https://beatra.ai/skills/image-to-motion/install.md
Install Image to Video & Photo Animator and tell me when I need to sign in: https://beatra.ai/skills/image-to-motion/install.md
```
