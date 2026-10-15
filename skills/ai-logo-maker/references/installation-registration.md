# Installation registration

On first use, and again when the version, agent environment, channel, network
route, install source or installation reference changes or 24 hours pass, the
bundled client makes one best-effort, non-billable
`beatra.installations.register` call for this package. It is the only reporting call
the Skill makes, it does not replace Device Authorization, it never asks for
narrower package scopes, and its failure never blocks the user's requested
task. It records:

- the package, its version, the agent environment (`platform`), and the
  stable installation reference;
- the distribution channel and locale fixed when the package was built;
- the network route this computer uses and why (see the MCP connection
  reference);
- where this copy was installed from, when known: a source file Beatra adds to
  copies it hands to a store or its website, a store client's own record in
  the Skill directory, or the agent's `install-source --guess`;
- coarse runtime facts: operating system and version, processor architecture,
  Python version, interface language, and time-zone offset.

It never sends user names, file paths, environment variables, prompts, or tool
details. Beatra uses these fields to understand which stores and networks
people install from, as its privacy policy describes, and clears the runtime
facts when the account is deleted.

A per-installation cache in `~/.beatra/updates/` suppresses another
registration until the version, agent environment, channel, network route, install
source or installation reference changes, or 24 hours pass. An unknown but well-formed package
slug is accepted and recorded as unrecognized, so package release never
depends on a synchronized backend registry deployment.

The `platform` field is the real agent environment, resolved once per process
from environment signatures (or `~/.beatra/host.json`, written at
authorization time) — never detected per request. When authorizing manually,
pass `--platform <environment-name>` to `scripts/authorize.py` if automatic
detection cannot identify the host.
