# MCP connection

All Beatra Skill packages use one connection path:

```text
scripts/mcp_client.py -> https://mcp.beatra.ai/mcp
```

The host follows this computer's network route, described below.

They share the one full-scope Device Token stored in
`~/.beatra/credentials.json`. Installing or switching packages must not trigger
another authorization when that credential is already valid. Do not add,
enable, trust, or configure a host Beatra Connector. Never print or move the
token into command arguments, environment variables, logs, chat, or another
package directory.

The bundled client performs MCP `initialize`, retains `MCP-Session-Id` when the
server returns one, sends `notifications/initialized`, and then uses
`tools/list` or `tools/call`. Its `verify` command runs the non-billable
`beatra.tasks.list` operation. It supplies the private `Authorization: Bearer`
header on every request without exposing its value.

Source attribution: every `tools/call` may carry two optional string
arguments, `source_package_slug` (this package's slug) and `source_platform`
(the agent environment, for example `claude-code` or `codex`). The bundled
client adds them automatically. They are telemetry only: missing values never
block a call, and the server treats them as `unknown`.

## Network route

Beatra serves two networks: the international hosts, and the mainland China
hosts `mcp.beatra.cn`, `api.beatra.cn`, `www.beatra.cn`, `cdn.beatra.cn` and
`console.beatra.cn`. The saved credential works on both. Packages of the
mainland China (`cn`) channel always use the mainland hosts and cannot change
network (`network` shows `"policy":"cn"`). Other packages choose once a day,
before their first command: the client asks Beatra which network suits this computer,
in a small request that carries no credential and no installation identity,
and records the answer in `~/.beatra/network.json`. Approval pages, console and
top-up links, uploads, and result downloads then follow the chosen network.

```text
python3 scripts/mcp_client.py network
python3 scripts/mcp_client.py network --use auto
```

`network` shows the current choice. Only when the user asks for a specific
network, run `network --use cn` (mainland China) or `network --use ai`
(international): it first checks that Beatra answers on that network and
refuses otherwise; packages of the `cn` channel refuse `--use`. If commands start failing to connect after a network was
chosen this way, run `network --use auto`. A request that failed is never
resent on the other network; the next command decides again unless a network was chosen with
`network --use`.

On the mainland China network the approval page offers WeChat, phone and email
sign-in. If the user cannot find their sign-in method, or wants to sign in with
Google, run `python3 scripts/authorize.py --approval-link ai`: it shows the same
approval on Beatra's international site, and the network does not change;
`--approval-link auto` goes back. When you give the user a console or top-up
link on the mainland network, remind them to sign in the way they did before
(phone, email, or the same WeChat): scanning with a different WeChat creates a
separate account. If credits do not appear after a top-up, first check that
they signed in to the same account.
