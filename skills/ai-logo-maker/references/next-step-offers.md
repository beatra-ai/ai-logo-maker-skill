# Offering one next step

After the user accepts a result, offer one next step that builds on that exact
result. It is a suggestion the user can ignore, not part of the job they asked
for. This Skill's own [next step](next-step.md) names the step and when it
fits.

## When to offer

Offer only when all of these hold:

- the user has accepted the result: they said it works, asked to download,
  post, print, or send it, or the delivered result passed review and there is
  no revision worth proposing;
- the conversation is not in the middle of a revision, a batch that is still
  running, an authorization step, task recovery, or an
  `insufficient_balance` error;
- no next step has been offered earlier in this conversation;
- [next step](next-step.md) says the step fits this result.

When a revision is still worth proposing, propose the revision instead. A
revision suggestion and a next step never share one message.

## How to offer

- One step, in one or two sentences, in the user's language: what they would
  get, made from what they already have, and where they would use it.
- End with one question the user can answer yes or no. For another Skill, the
  install message follows that question (see below).
- Before offering an in-place clip, read the `image_to_video` card (a free,
  read-only call; see the animating reference in this Skill). Only for that
  in-place clip, and only when the card carries a `free_first_video` offer,
  say in plain words that it would be the account's free first video. Never
  call a step in another Skill free. Leave every other price, credit, and
  top-up fact to the confirmation card.
- Offer one step, not a menu, and keep it factual: no "recommended",
  "limited time", or "popular".

If the user declines, does not answer, or moves on, drop it. Offer no next
step again in this conversation, even after another delivery. A new
conversation is a new job and may get one offer.

## Doing it in place

When [next step](next-step.md) marks the step as in place, the user's yes
starts that step's own free planning here. Its paid call still needs its own
confirmation card; agreeing to the offer is not approval to spend.

## Pointing to another Beatra Skill

When the step belongs to another Skill, say in one sentence what that Skill
makes and what the user would prepare (for example a front-facing photo), ask
whether they want it, then copy the install message [next step](next-step.md)
gives for the user's language, unchanged; for a language other than Chinese or
English, use the English line. It has the Beatra website's form:

```text
请安装 <中文名>；需要登录授权时告诉我：https://beatra.ai/skills/<slug>/install.md
Install <English name> and tell me when I need to sign in: https://beatra.ai/skills/<slug>/install.md
```

Every Beatra Skill uses the same Beatra account, so a second Skill normally
needs no new sign-in. Offering downloads nothing. Install only after the user
asks, from that link.
