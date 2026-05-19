# agent-handshake-protocol

Portable wire-protocol types for the agent-handshake / Diplomat ecosystem.

Pydantic v2 models for the cross-agent INTERCHANGE block primitive plus the
Diplomat commit/digest vocabulary. No framework coupling — depends only on
`pydantic`. Importable from any Python 3.12+ project.

## Substrate vs vocabulary

The package ships two distinct things that can be adopted together or independently.

**Substrate** — the reusable primitive, not specific to any one agent vocabulary:

- `InterchangeBlock` — base class for polymorphic interchange blocks.
  Round-trip-lossless via a wrap serializer; trust-boundary
  `extra="forbid"` (unknown keys raise rather than being silently
  stripped); reserves a `schema_version: int = 1` field for future dispatch.
- `InterchangeBlockRegistry`, `register_interchange_block`,
  `resolve_interchange_blocks` — registry + helpers for polymorphic
  deserialization.

**Diplomat vocabulary** — the specific block types and enums Diplomat speaks
on top of the substrate:

- Blocks: `CommitIntent`, `CommitResult`, `InboundDigest`.
- Enums: `SoWPeerTier`, `CommitVerdict`, `RejectionReason`, `DigestConfidence`.

Adopters who want to register their own block types against the
`InterchangeBlock` substrate — and ignore the Diplomat vocabulary entirely —
can do so. See [`examples/custom_block.py`](examples/custom_block.py) for a
non-Diplomat adopter: a `BugReport` block with its own enum, registered via
`@register_interchange_block`, round-tripped through the real
`resolve_interchange_blocks`. The example imports only substrate exports;
that negative is the mechanical proof the substrate is independently usable.

A future package split is documented in
[`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md) under "Future package split".
If the substrate ever moves into its own package, the import path
`from agent_handshake_protocol import InterchangeBlock` stays stable via
re-export — the migration is invisible at the import-statement level.

## Consumers

**Full Diplomat vocabulary:**

- V0 Diplomat *skill* (sibling repo `agent_handshake`).
- V1 Wick-resident Diplomat *agent* (Mentarchy monorepo).

**Substrate only** (registers its own block vocabulary against `InterchangeBlock`):

- Any agent that wants the substrate without the Diplomat handshake —
  start from [`examples/custom_block.py`](examples/custom_block.py).

## Install

V1 is distributed via tagged GitHub releases. PyPI is a future candidate
(see `docs/diplomat-v1-compat-prd.md` Out of scope) but is not the V1
mechanism — there is no PyPI artifact to install today.

Direct install pinned to a release tag:

```
pip install "agent-handshake-protocol @ git+https://github.com/MennoAf/agent-handshake-protocol.git@v0.1.0"
# or
uv add "agent-handshake-protocol @ git+https://github.com/MennoAf/agent-handshake-protocol.git@v0.1.0"
```

As a `pyproject.toml` dependency (the form Mentarchy and `agent_builder` use):

```toml
[project]
dependencies = [
  "agent-handshake-protocol",
]

[tool.uv.sources]
agent-handshake-protocol = { git = "https://github.com/MennoAf/agent-handshake-protocol.git", tag = "v0.1.0" }
```

Pin to a release tag, not a branch — see [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md)
for the version policy (patches are additive; minor bumps may break wire format).

From a sibling checkout (editable; useful when developing against an unreleased
revision):

```toml
[tool.uv.sources]
agent-handshake-protocol = { path = "../agent-handshake-protocol", editable = true }
```
