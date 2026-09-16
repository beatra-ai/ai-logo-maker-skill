# Review and recovery

## Before the paid boundary

Present one final direction. Freeze the prompt, ordered references, canvas,
brand colors, logo type, count, model, and controls in a single confirmation.
After approval, create one stable opaque `client_request_id` for that exact
logical request and submit once. Any change—prompt, reference or order, canvas,
colors, model, count, or control—is new paid work with a new confirmation and
a new ID.

## Monitor and recover

After receiving a `task_id`, poll only that task with `beatra.tasks.get`. Use
bounded backoff: first poll around 2 seconds, increasing toward 5 and 10
seconds, maximum 15 seconds. Honor `deadline_at`. Stop active polling after 30
minutes and report the task ID and status.

- **Lost create response:** if the response to the original submission is
  genuinely unknown (network failure, timeout, process exit), retry the exact
  same parameters with the same `client_request_id`. The server treats this as
  idempotent recovery.
- **Lost task ID:** call `beatra.tasks.list` to find candidates, then verify
  the selected one with `beatra.tasks.get`. Match by capability, input, and
  timing. If the match is ambiguous, do not submit a replacement.
- **Slow task:** a queued or running task never authorizes a replacement. Keep
  polling or report the task ID for later resumption.
- **Authorization failure:** do not auto-retry. Preserve the credential and
  direct the user to rerun `scripts/authorize.py`. The original
  `client_request_id` remains valid for idempotent recovery once authorization
  is restored.
- **Connection failure:** preserve the credential and the original
  `client_request_id`. Retry only the exact same parameters.

If a generate, transform, or edit call returns insufficient credits: give the
user the tool message in full. Do not change the URL. You may translate the
other words. Do not replace it with your own top-up copy. Point the user to
pay using that message.

Use `beatra.tasks.cancel` only when the user asks. If cancellation returns
`409`, the task continues—do not promise a stop or refund, and keep tracking
the original task. See the shared
[billing, errors, and recovery](billing-errors-and-recovery.md)
for the full structured-failure reference.

## Review only what is visible

When the result is visible, review in this order:

1. **Scalability** — is the mark still recognizable at thumbnail size? Does the
   silhouette hold up?
2. **Brand-color accuracy** — do the colors match the user's palette values?
3. **Silhouette strength** — does the mark read as one strong shape, or does it
   fragment into competing details?
4. **Safe-area margin** — would a circular or rounded crop clip the focal
   element?
5. **Monochrome potential** — would the logo survive in a single color?
6. **Type legibility** — if the brand name appears in the image, is it
   readable?

If the host cannot view the artifact, state that visual verification was not
possible and deliver the result links for the user to review.

## Deliver

Present every returned image in order. Include the artifact links, observed
dimensions, task ID, and `billing.net_charged_credits`. Do not infer credits
from image count or elapsed time.

Offer at most one focused, unexecuted revision. When the user accepts a
concept but wants changes, describe the revision as a new `beatra.images.edit`
request with the accepted image as `images[0]`.

## Logo deliverable variants

A complete logo delivery typically includes several variants of the same mark.
After the primary square logo is accepted, advise the user that common variants
are available as separate focused requests:

- **horizontal lockup** — symbol and brand name side by side for website
  headers and email signatures (wider aspect ratio such as 3:1 or 4:1);
- **icon-only mark** — the symbol without text for favicons and app icons;
- **monochrome version** — single-color (black or white) for stamps, embossing,
  and low-ink contexts;
- **dark-background variant** — reversed colors for dark themes and overlays.

Each variant is a distinct paid request with its own confirmation and
`client_request_id`. Do not promise that a variant will be identical to the
primary mark in every proportion—review each result independently.

When the primary use needs a different ratio or a dark-background variant,
advise that it is a separate focused request.
