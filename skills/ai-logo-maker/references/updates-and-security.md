# Updates and security

Since the October 2026 releases, Beatra Skill packages contain no self-updater.
Earlier releases could replace their own files from Beatra's CDN; that code has
been removed. Updates now come only from the store or tool you installed the
Skill from.

## What runs

Every operation runs one of the bundled scripts: `scripts/mcp_client.py`,
`scripts/authorize.py`, or `scripts/uninstall.py`. They use only the Python
standard library. `scripts/authorize.py` opens the Beatra approval page in
this computer's web browser when approval is still needed. They never
download, write, or execute other code, and the files of this installed Skill
stay exactly as installed.

## Where requests go

Requests use HTTPS and follow this computer's network route, described in
[MCP connection](mcp-connection.md): the international hosts, or the mainland
China hosts `mcp.beatra.cn`, `api.beatra.cn`, and `www.beatra.cn`. When you
choose to upload a local file, it goes only to the one-time upload address
Beatra issues for that upload. Choosing the network, or retrying the version
list once, may send a small request to the other network.

## What is stored on this computer

These files are written under `~/.beatra/`. On POSIX that directory is mode
0700. Nothing is written inside the installed Skill directory.

- `credentials.json` (POSIX mode 0600), written by `scripts/authorize.py`: the device credential.
- `installation.json` (POSIX mode 0600), written by `scripts/authorize.py`: the stable installation reference.
- `host.json`, written by `scripts/authorize.py`: the agent environment, and a device name when one is known.
- `network.json` (POSIX mode 0600), written by `scripts/mcp_client.py`: this computer's network route.
- `skills.json` (POSIX mode 0600), written by `scripts/authorize.py` and `scripts/mcp_client.py`: which Beatra skills are installed here, with the slug, agent environment, install path, and time.
- `pending_authorization.json` (POSIX mode 0600), written by `scripts/authorize.py`: an approval that is still open. Removed when that approval is collected or discarded.
- `.authorize.lock` (POSIX mode 0600), written by `scripts/authorize.py` while authorization is in progress, then removed.
- `balance-holds.json` (POSIX mode 0600), written by `scripts/mcp_client.py`: a local record after a tool is refused for insufficient credits. Removed when no such record remains.

`scripts/mcp_client.py` also keeps one directory per installation under
`~/.beatra/updates/`. Its name is the first 24 hexadecimal characters of the
SHA-256 of the resolved installation path, and on POSIX the directory is mode
0700. The files inside it are POSIX mode 0600:

- `state.json`: the time of the last version check.
- `registration.json`: the cache of the last installation registration.
- `source.json`: where this copy was installed from, when that is known.

Replacing one of these files writes a temporary file in the same directory and
then renames it over the old file.

When `scripts/uninstall.py` decides this is the last Beatra skill on the
computer, it first asks Beatra to revoke the device credential when one is
stored. If Beatra refuses, it changes nothing so the run can be repeated.
Otherwise it unlinks exactly these names in `~/.beatra/`: `credentials.json`,
`installation.json`, `host.json`, `skills.json`, `registrations.json`,
`network.json`, `balance-holds.json`, `pending_authorization.json`, and
`.authorize.lock`. It then removes `~/.beatra/` only when that directory is
empty. It does not remove `~/.beatra/updates/` or anything inside it. These
scripts do not create `registrations.json`; uninstall still unlinks that name
if it is present. The script never deletes the installed Skill directory. It
names that directory in `delete_next` for the caller to delete. If another
skill remains, or the inventory cannot prove this is the last one, it leaves
`~/.beatra/` unchanged.

## What is reported

Beyond the requests a command makes, the only report is the installation
registration described in [installation registration](installation-registration.md).
No prompts, file contents, file paths, or tool-call details are sent with it.
Each tool call itself names this package and the agent environment (for example
`claude-code`), as source attribution in [MCP connection](mcp-connection.md)
describes, so a task can be traced to the Skill that made it.

## Version notice

At most once every 24 hours, before an ordinary command, the bundled client
reads Beatra's public version list for this package
(`/skills/<package>/sources.json` on the site host of the current network). It
works out from local records which store or tool installed this copy. When that
place offers a newer version, it prints one line on standard error with the
command that updates it there. It never installs anything. If the check fails,
nothing is printed and the command runs as usual. A copy with no such record
gets no notice.

| Installed with | Update with |
| --- | --- |
| ClawHub CLI | `clawhub update <package> --workdir <dir> --dir <skills-dir>` (add `--force` if it reports local changes) |
| SkillHub CLI | `skillhub install <package> --force --dir <skills-dir>` |
| GitHub CLI | `gh skill update <package>`, run in the project directory for a project install |
| skills CLI (GitHub or ModelScope) | `npx skills update <package> -p -y`, run in the project directory; or `npx skills update <package> -g -y` for a global install |
| WorkBuddy | Update the Skill in WorkBuddy |
| Beatra website (English packages) | Reinstall from the package's install page |

## Check by hand

    python3 scripts/mcp_client.py update --check

It reports what the store or tool you installed from offers now. It installs
nothing and leaves the Skill's files unchanged. If `python3` is not the local
Python command, use the available Python 3.10+ command.
