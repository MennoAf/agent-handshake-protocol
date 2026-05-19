# agent-handshake-protocol

Open wire-protocol types for cross-install agent coordination. MIT-licensed.

When two agent installs work on the same git repository — different councils,
different runtimes, possibly different vendors — they need a shared vocabulary
to negotiate work claims, sign off on operating rules, and exchange digests of
each other's commits. This package defines that vocabulary as portable
Pydantic v2 models. It depends only on `pydantic` and is importable from any
Python 3.12+ project.

The package ships two layers — a generic interchange substrate and the
Diplomat-specific block vocabulary. Adopters can take both, or take only the
substrate and define their own block types on top.

## Substrate vs vocabulary

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

## Why open

Cross-install coordination only works if both peers speak the same protocol.
That makes this package a network-effect dependency: it's useful to you in
proportion to how many other installs adopt it. The protocol is MIT-licensed
and versioned (see [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md)) so any
adopter can pin a release and rely on the wire format staying stable for the
lifetime of that minor version. Issues and proposals welcome on the GitHub
repo.

## Reference implementations

Two installs use this package today and serve as worked examples of the wire:

- **v0 Diplomat skill** — a portable council skill that wraps a CLI and a small
  daemon. Lives in the sibling repo
  [`agent_handshake`](https://github.com/MennoAf/agent-builder) (the
  `agent_builder` package). Designed to be loaded into any council framework
  and run end-to-end on a developer machine. Speaks the full Diplomat
  vocabulary.

- **v1 Diplomat agent** — a broker-token-scoped agent embedded in the
  Mentarchy monorepo (private). Speaks the same vocabulary on the wire; the
  difference is operational (broker-enforced capability isolation, telemetry
  into a Doctrine Ledger).

Both installs interoperate over the same `.handshake/v0/` folder in the shared
repo because the wire types are defined here, once. New adopters writing their
own Diplomat-class agent should target this package's contracts directly — no
need to fork either reference.

## Adopting without the Diplomat vocabulary

If you want only the `InterchangeBlock` substrate (because you're designing a
different inter-agent protocol entirely), register your own block types
against it and skip everything in `agent_handshake_protocol.diplomat.*`.
[`examples/custom_block.py`](examples/custom_block.py) is the worked example.

## Install

V1 is distributed via tagged GitHub releases. PyPI is a future goal (see
[`docs/diplomat-v1-compat-prd.md`](docs/diplomat-v1-compat-prd.md) — D3 in the
companion PRD defers PyPI to V2). The GitHub tag IS the V1 distribution
channel; there is no PyPI artifact today, and clean installs resolve directly
from the tag.

Direct install pinned to a release tag:

```bash
pip install "agent-handshake-protocol @ git+https://github.com/MennoAf/agent-handshake-protocol.git@v0.1.0"
# or
uv add "agent-handshake-protocol @ git+https://github.com/MennoAf/agent-handshake-protocol.git@v0.1.0"
```

As a `pyproject.toml` dependency (the form the reference implementations use):

```toml
[project]
dependencies = [
  "agent-handshake-protocol @ git+https://github.com/MennoAf/agent-handshake-protocol.git@v0.1.0",
]

[tool.hatch.metadata]
# Required for hatch-built projects: hatch refuses PEP 508 direct references
# (`pkg @ git+...`) by default. Other build backends (setuptools, flit, poetry)
# do not need this.
allow-direct-references = true
```

The PEP 508 git URL is the canonical cross-tool way to express "depend on this
exact git ref" and lands in the built wheel's `Requires-Dist` metadata — so
your package is itself installable via `pip install`, `uv pip install`, or
`uv add` from anywhere, with the transitive `agent-handshake-protocol` resolved
correctly from the GitHub tag.

Always pin to a release tag, not a branch — see
[`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md) for the version policy
(patches are additive; minor bumps may break wire format).

**uv-only alternative.** If your project is uv-managed and not distributed as
a wheel, the older `[tool.uv.sources]` form also works (uv consumes it during
`uv sync`):

```toml
[project]
dependencies = ["agent-handshake-protocol"]

[tool.uv.sources]
agent-handshake-protocol = { git = "https://github.com/MennoAf/agent-handshake-protocol.git", tag = "v0.1.0" }
```

Note this `[tool.uv.sources]` form does NOT carry into a built wheel's
`Requires-Dist`, so it only works for projects adopters consume via `uv sync`
on a clone — not via `pip install` or any remote install. Prefer the PEP 508
form above unless you have a specific reason.

**Sibling-path checkout** (editable; useful when developing against an
unreleased revision of this package):

```toml
[tool.uv.sources]
agent-handshake-protocol = { path = "../agent-handshake-protocol", editable = true }
```

## Compatibility

See [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md) for the full versioning
policy. Short version: patch bumps are additive and safe; minor bumps may
change the wire format; major bumps may change import paths.

## License

[MIT](LICENSE). Copyright (c) 2026 Jason Bauman.
