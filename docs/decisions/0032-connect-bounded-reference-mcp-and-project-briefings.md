# 0032: Bounded reference MCP and refreshed project briefings

Date: 2026-10-14
Status: accepted

## Decision

Connect the existing dethrottled bridge through an SSH loopback tunnel and the
official MCP Python SDK. Keep credentials on szbox. Limit access to declared
reference work, approved hosts, read tools and explicit execution budgets.
Retain reference packets and exact structured-review inputs as local artifacts.
Brief Qwen from versioned project documents at invocation.

## Rationale

The direct tailnet route timed out. Existing SSH access reaches Caddy's local
authentication-injecting gateway without changing a server allowlist or binding.
Live schemas avoid unsupported backend arguments. Search host filtering is
necessary because site-restricted queries returned unrelated results.

The existing pinned Qwen service and review abstraction already work. A second
runner or a Modelfile cannot provide live project memory or trustworthy tool
execution. Controller-managed retrieval and refreshed context address those
needs without an untested autonomous loop.

## Consequences

The tunnel needs the WSL user service manager and existing SSH configuration.
Client timeouts cannot guarantee backend cancellation, and requested-host
validation cannot guarantee redirect restrictions. Rights review remains
mandatory. Review text is not numeric evidence or experiment state. This
integration is not a Phase 4 measurement endpoint or Phase 6 target barrier.
See `docs/WEBENGINE.md` for operational details and limitations.
