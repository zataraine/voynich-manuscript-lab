# Bounded web reference access

Verified on 2026-10-14. The dethrottled MCP bridge (historically called
vestigia) is an optional reference source, not an experiment engine or a
decipherment model. The pinned local Qwen runtime is unchanged.

## Connection

The configured route is:

```text
WSL localhost:18185 -> SSH nocturne-szbox -> szbox localhost:18185
  -> Caddy injects authentication and Host -> localhost:18184/mcp
```

The WSL tailnet connection timed out during setup. SSH forwarding therefore
uses existing pinned SSH credentials without copying the MCP token, changing
Caddy's allowlist, or exposing the bridge's loopback listener.

The installed user service is `voynich-webengine-tunnel.service`; its tracked
template is `config/services/voynich-webengine-tunnel.service`. It requires the
existing `nocturne-szbox` SSH alias and host key. It is enabled for the user
default target and restarts failed connections. WSL and its user service
manager must be running; this does not start Windows or WSL remotely.

```bash
systemctl --user status voynich-webengine-tunnel.service
systemctl --user restart voynich-webengine-tunnel.service
systemctl --user stop voynich-webengine-tunnel.service
```

## Policy and budgets

`manuscript_lab.webengine` uses the official Python MCP SDK, intentionally
locked through `pyproject.toml` and `uv.lock`, with `httpx` as a direct dependency.
It discovers live tool schemas and capabilities rather than guessing backend
fields. MCP bridge arguments are validated against their advertised schemas;
backend `optional_fields` are not automatically added to bridge calls.

`config/webengine.yaml` allows only search, fetch, corpus search/statistics,
and diagnostics. Browser driving and combined search/fetch/research tools are
not enabled. Jobs accept only declared reference, metadata or research-note
content, not manuscript transcription or corpus content. This declaration is
not an automatic semantic classifier or the Phase 6 validation barrier.

Limits are six tool calls including capabilities discovery, 120 seconds per
MCP session, 30 seconds per call, 128 KiB per normalized response, five search
results, two fetch URLs and 6,000 characters requested per fetch. These are
client limits; timeout does not guarantee cancellation inside the engine. The
separate Qwen review uses the existing local-AI timeout and output settings.

Fetches require approved reference hosts, HTTP(S), no embedded credentials and
no explicit port. Search results are filtered to those hosts before review.
Approved hosts cover ACL Anthology, arXiv, GitHub and MCP documentation; the
restricted manuscript viewer is not included. Requested-host checks do not
prove that the engine cannot follow cross-host redirects. Source rights and
the source catalog still require review before acquisition. Capability claims
are server advertisements, not proof of offline execution or rights compliance.

## Use

Choose a new output path for every invocation; existing artifacts are refused.

```bash
./scripts/run python -m manuscript_lab.webengine capabilities \
  --output artifacts/references/mcp-capabilities-001.json
./scripts/run python -m manuscript_lab.webengine search \
  --query 'site:aclanthology.org Voynich entropy' \
  --output artifacts/references/search-001.json
./scripts/run python -m manuscript_lab.webengine fetch \
  --url https://aclanthology.org/W11-1511/ --review \
  --output artifacts/references/review-001.json
```

Packets retain effective arguments, timestamp, schema/capability/response
hashes, code provenance, configuration hash and environment-lock hash. Search
packets retain the pre-filter response hash and exclusion count, not excluded
text. A hash alone cannot reconstruct that discarded response.

`--review` stores the exact Qwen input, including versioned snapshots of the
README, mechanism estimand and Phase 4 acceptance audit. Fetched material is
framed as untrusted evidence. The review uses the existing structured local-AI
interface; it is a reference-intake review, not an experiment or a claim.
A landing page or snippet does not establish a full paper's findings.

The controller selects retrieval calls; Qwen does not yet choose or execute
autonomous MCP calls. Native tool loops would require a separate bounded
controller and evaluation. Project briefings refresh at invocation rather
than relying on model memory or a stale hard-coded persona.

## Verification

Live checks discovered twelve bridge tools, fetched an ACL reference, exercised
search and completed a schema-bound Qwen review. Search returned unrelated
news despite a `site:` query; the approved-host filter excluded it. Local
diagnostic artifacts are under `artifacts/diagnostics/webengine-*20261014.json`
and are intentionally not published. Unit tests cover policy, budgets,
schema validation, response formats, provenance and briefing snapshots.
This plumbing changes no manuscript result and completes no research phase.
