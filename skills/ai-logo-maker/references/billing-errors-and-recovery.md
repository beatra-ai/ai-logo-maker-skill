# Billing, errors, and recovery

Every generation tool consumes Beatra credits and creates an asynchronous task.
Use one logical request identity across transport uncertainty so recovery cannot
accidentally create or charge a duplicate task.

## Submit a billable request

1. Assemble the final generation arguments.
2. Generate one opaque `client_request_id`.
3. Submit exactly once.
4. Store both `client_request_id` and the returned `task_id`.
5. Poll with `beatra.tasks.get`; do not resubmit while the task is queued or
   running.

The prepaid amount accepted with the request can be an estimate. A successful
task is settled against authoritative measured usage. Read the terminal
`usage` and `billing` fields, and report net credits as
`billing.net_charged_credits`. Do not promise that the initial estimate
is the final charge.

## Run a batch

When one request becomes many paid calls (a list of items, a loop, or a
script):

1. Before the first paid call, price the whole batch from the live prices
   (`beatra.models.list`, or `beatra.social.tools.get` for social data) and
   tell the user the estimated total.
2. Let the first `insufficient_balance` stop the whole batch. Do not go on to
   the next item; report which items finished and which did not.
3. Resume only the unfinished items, and only after the user says they have
   topped up. A refused item keeps its `client_request_id` and arguments.

## Recover an uncertain response

- If no response arrived, make an identical retry with the same
  `client_request_id` and exactly the same generation arguments.
- If any prompt, input artifact, model, output setting, or other generation
  argument changes, treat it as new work and use a new `client_request_id`.
- If the task ID was lost, use `beatra.tasks.list` before considering a retry.
- If remote execution failed, report the terminal error. Start changed or newly
  requested work only with a new request ID.

## Handle structured failures

- HTTP 401 authentication failure: do not replay the paid call automatically.
  Run `python3 scripts/authorize.py` and follow its output
  until it prints `Beatra is ready`, then recover with the original request
  identity and unchanged arguments.
- Timeout, DNS/TLS, HTTP 429, HTTP 5xx, or another transport failure: preserve
  the credential. If delivery of a paid call is uncertain, retry only with the
  same `client_request_id` and exactly the same arguments after connectivity
  recovers.
- Insufficient scope: explain that the active connection lacks required access;
  run `python3 scripts/authorize.py --force` only after the
  user explicitly chooses to reconnect the full Beatra authorization. Never ask
  for a media-specific grant.
- Insufficient balance (error code `insufficient_balance`): relay the returned
  message to the user — it already carries the facts that matter: nothing was
  charged, the top-up link, credits take effect immediately, and the same
  request can be retried as-is. Translate into the user's language but keep
  the URL exactly as returned. Stop all remaining paid work, including the
  rest of a batch, and do not retry until the user says they have topped up.
  A successful task can also leave a negative balance when actual measured
  usage exceeded the estimate; the output remains valid, but new billable
  work must wait for a top-up.
- After that refusal, `scripts/mcp_client.py` holds further calls to the same
  tool on this computer: it answers them with the same message and sends
  nothing (`details.local_hold`). Its `details.agent_note` names the balance
  check that lifts the hold once the user says they have topped up. If the user
  chose a cheaper request instead, run that cheaper call once with
  `--recheck-balance`. Never put `--recheck-balance` in a loop or script.
- Idempotency conflict: the request identity was reused with different
  arguments. Do not retry it. Keep the original task if it exists, or use a new
  `client_request_id` only for user-approved changed work.
- Rate or concurrency limit: honor the returned retry delay, then retry the
  exact same arguments with the same request identity. Do not create a
  replacement task.
- Validation failure or model incompatibility: call `beatra.models.list` for current
  constraints, correct the invalid arguments, and use a new
  `client_request_id` because the generation inputs changed.
- Upload expiration, MIME mismatch, or byte-length mismatch: request a fresh
  grant and upload the unchanged file again. Never reuse a consumed or expired
  grant.
- Remote execution failure: preserve the Beatra error code and task ID;
  report only the failure classification and billing/refund fields returned by
  Beatra. Do not infer a different cause or promise a refund that is not shown.

Never expose authentication tokens, complete private prompts, or sensitive
input content while explaining recovery.
