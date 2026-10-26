# Installation and authentication

Use this reference when Beatra is newly installed, unavailable, or needs its
authorization recovered. This flow is owned by the Skill and works the same way
in any agent that can run Python 3.10 or newer and make HTTPS requests. The
helpers use only the Python standard library; do not install packages for them.

## Keep one private local identity

The Skill uses two user-only files:

- `~/.beatra/installation.json` contains one stable, non-secret installation
  reference.
- `~/.beatra/credentials.json` contains the single Device Token.

On POSIX systems the directory must be mode `0700` and both files mode `0600`.
On Windows the current user must be the only principal granted access through
the file ACL. Never copy the Device Token into conversation context, stdout,
stderr, a command argument, an environment variable, a log, a backup, a diff,
or another file. A completed authorization leaves the token only in
`~/.beatra/credentials.json`.

## Ensure Beatra is ready

From the installed `beatra` Skill directory, run:

```text
python3 scripts/authorize.py
```

Use `python` instead when that is the local Python 3.10+ command. Always run this
idempotent helper after installing or replacing a Beatra Skill and when
recovering its connection. It validates the candidate credential with one
non-billable live MCP request. A valid credential becomes Ready without opening
the browser, so installing another Beatra package does not require a second
approval.

When no valid credential exists, or the live MCP endpoint definitively returns
HTTP 401, the helper:

1. reuses or creates `~/.beatra/installation.json`;
2. continues an approval that is already open on this computer, or requests a
   new Device Authorization from Beatra. When the user already selected Allow
   on this computer and nothing collected it, Beatra connects at once — no
   second approval;
3. prints the HTTPS approval link at once and opens it in the user's browser
   (only once for each approval). The URL fragment carries the approval code,
   so the page verifies the code by itself;
4. waits while it checks every few seconds whether the user selected Allow,
   and keeps checking through brief network failures. One run waits up to
   about 15 minutes; an approval page stays open for up to an hour;
5. atomically saves the returned Device Token to
   `~/.beatra/credentials.json` without printing an HTTP response body;
6. validates the new credential with the same non-billable MCP request and
   prints `Beatra is ready` only after it succeeds.

### Wait for Allow

The user usually needs a minute or more to sign in or create an account before
selecting Allow. The helper waits for it: leave it running. If your host moves
the command to the background, let it keep running and do not start a second
one.

Act on how each run ends:

- `Beatra is ready` — the connection works; continue with the user's request.
- `BEATRA_AUTH_PENDING` (exit status 3) — the run ended before the user selected
  Allow: the approval page had not been opened yet, the run's wait ran out, or
  the run was stopped. Show the approval link to the user as described below if
  you have not already, and again if the link is different. Run the same command
  at most twice in one turn; it continues the same approval, so the user
  approves only once. When it is still pending after that, deliver what needs
  no connection (below) and stop. When the message says Beatra could not be
  reached, tell the user the connection is being retried instead of asking them
  to approve again.
- `BEATRA_AUTH_IN_PROGRESS` (exit status 3) — another run on this computer is
  starting an approval right now. Run the same command again in a moment; it
  continues that approval.
- `Beatra authorization stopped (access_denied)` — the user declined on the
  approval page. A decline is often a mis-click: if the user still wants to
  connect, run the same command again and it opens a new approval page.
- `Beatra authorization stopped (expired_token)` — the approval page expired
  before the user selected Allow. Tell the user; if they still want to
  connect, run the same command again and share the new approval link.

A run stopped by a timeout or an interrupted tool call counts as one of the
two runs in the turn: run the same command again once, since it continues the
approval that is already open, and after a second stop deliver what needs no
connection and stop.

An approval does not depend on a run being active when the user selects Allow.
Beatra keeps it, and every Beatra command collects it first: when the user
writes again after approving, run the helper once (or go on with their
request) and the connection completes without a second approval. So if the
user interrupts to ask something else, stop the helper and answer them; and if
they do not want to connect now, stop waiting — the link stays valid for a
while.

#### Deliver while the approval is pending

When the approval is still pending at the end of a turn, finish and deliver
everything in the request that needs no connection, in the format the user
asked for — the Skill's root names it for each kind of work: the prepared
text, prompt, lyrics, shot list, or selection criteria. Say in one line that
the paid step continues on their next message after Allow, because the next
Beatra command collects the approval. Do not fill the gap with another tool or
service, and do not name voices, models, prices, or results that no live call
returned.

When telling the user what to do:

- present the approval page as a link and say the only decision on it is
  selecting Allow;
- never quote, display, or read out the approval code. It travels inside the
  link fragment, the approval page does not show it, and the user never types
  or compares it — a code surfaced in conversation is noise, not a step;
- say prominently that a signed-out browser lands on Beatra sign-in first:
  the user signs in or creates their account there, and the approval page
  continues automatically after sign-in;
- say once that the connection continues automatically after Allow — never
  ask the user to confirm in chat that they approved.
- on the mainland China network, follow the sign-in and console-link guidance
  in [MCP connection](mcp-connection.md#network-route).

The helper opens no local listener and requires no inbound connection. One
approval covers image, video, music, speech, upload, model, and task tools.

HTTP 403 or insufficient scope does not prove the credential is invalid. Keep
the credential and run `python3 scripts/authorize.py --force`
only when the user explicitly wants to reconnect or switch accounts. A timeout,
DNS/TLS failure, HTTP 429, or HTTP 5xx is transient: keep the credential, do
not start Device Authorization, and retry after connectivity recovers.

### Record where this Skill was installed from

After this Skill first connects, if this conversation shows how this
Skill was installed — for example an install command or link that names a
store or site — record it once:

```text
python3 scripts/mcp_client.py install-source --guess <source>
```

Use one of `website`, `github`, `skillhub`, `skillatlas`, `modelscope`,
`workbuddy`, `clawhub`, or `other`. If the conversation does not show it,
skip this and do not ask the user. If the command is not recognized, skip it.

## Use the bundled MCP client

Every Beatra Skill tool runs through the bundled `scripts/mcp_client.py`, which
connects to `https://mcp.beatra.ai/mcp`. Do not add, enable, trust, or configure
a host Beatra Connector. The bundled client reads the shared credential file
and never accepts the token through argv or the environment:

```text
python3 scripts/mcp_client.py verify
python3 scripts/mcp_client.py tools
python3 scripts/mcp_client.py call beatra.tasks.list
```

The host follows this computer's network route; see [MCP connection](mcp-connection.md).

For `call`, provide the tool arguments as one JSON object on stdin. Do not put
user content or credentials in the command arguments. The authorization helper
already performs this verification. Run the explicit `verify` command only for
diagnostics; it invokes `beatra.tasks.list` with `{}` and is non-billable.

The direct client follows the Streamable HTTP sequence:

1. send `initialize` with the MCP protocol version and client information;
2. retain an `MCP-Session-Id` response header when the server provides one;
3. send the `notifications/initialized` notification;
4. use `tools/list` for discovery and `tools/call` for execution;
5. include the protocol version, optional session ID, and Device Token bearer
   header on every request.

## Recover or revoke access

The single Device Token has a sliding 15-day idle lifetime. Every accepted MCP
use extends that idle deadline without user action. If Beatra returns HTTP 401
after the token was idle too long or was revoked, run
`python3 scripts/authorize.py` and act on its output as
described above; the helper replaces and validates the credential. Do not start another
authorization for a media-type change and do not delete a credential because of
a transient connection failure.

The user can revoke a connected agent from the Beatra Console at any time.
Revocation immediately invalidates the credential. Rerun Device Authorization
only when the user wants to reconnect that installation.

After first installing or replacing the Skill, start a new agent session when
the host discovers Skills only at session startup.
