# Compatibility Policy

This document describes the version-pinning policy consumers of `agent-handshake-protocol` should use, and the forward-compatibility contract this package follows.

## Version pinning for consumers

V1 is distributed via tagged GitHub releases (see README `Install` section).
PyPI distribution is a future candidate, not the V1 mechanism.

Until the package reaches `1.0`, the supported pin is **tag-based, one minor series at a time**. In `pyproject.toml`:

```toml
[project]
dependencies = [
  "agent-handshake-protocol",
]

[tool.uv.sources]
agent-handshake-protocol = { git = "https://github.com/MennoAf/agent-handshake-protocol.git", tag = "v0.1.0" }
```

Bump the `tag` field to pick up patch releases within the `0.1.x` minor series after reviewing the changelog. Do not pin to a branch (`main`, `master`); branches move and are not part of the release contract. If/when PyPI distribution lands, the equivalent pin becomes `agent-handshake-protocol = ">=0.1,<0.2"` and the `[tool.uv.sources]` override drops; the version-compatibility rules below apply identically to both forms.

Patch releases (`0.1.0` → `0.1.1` → `0.1.2`) are always additive. They may:

- Add new `InterchangeBlock` subclasses to the registry.
- Add new `RejectionReason`, `DigestConfidence`, or `SoWPeerTier` enum values.
- Add new optional fields to existing block types (with defaults).

They will never:

- Remove fields from existing block types.
- Remove enum values.
- Rename anything in the public API (anything imported via `from agent_handshake_protocol import ...`).
- Change wire-format string values for existing enums.

Minor-version bumps (`0.1.x` → `0.2.0`) may break the above. Read the changelog before upgrading across a minor bump.

## Forward-compatibility contract for consumers

Patch releases are always additive — but additive changes still require consumers to handle the new surface gracefully. Specifically:

**Consumers must default-fall-back rather than raise on unknown values.** When parsing a `SoWPeerTier`, `RejectionReason`, or `DigestConfidence` value from a wire artifact (SoW file, INTERCHANGE block, persisted ledger entry), an unrecognized string must NOT crash the consumer. The expected pattern (used by Diplomat in `agents/diplomat/diplomat/inbound.py:_peer_tier_from_sow`):

```python
def parse_tier(raw: str | None) -> SoWPeerTier:
    if raw is None:
        return SoWPeerTier.SKILL  # conservative default
    try:
        return SoWPeerTier(raw)
    except ValueError:
        return SoWPeerTier.SKILL  # forward-compat: unknown tier → conservative
```

Reasons consumers see an unknown value at runtime:

- Peer install is running a newer version of the protocol package than this consumer.
- Wire artifact (SoW, ledger) was written by a newer version and is now being read by an older one.
- Manual edit of a wire artifact introduced a typo.

In every case, conservative default + operator-visible signal (log, warning, or `TIER_MISMATCH`-style annotation) is preferred over hard failure.

## Schema-version field on `InterchangeBlock`

Every `InterchangeBlock` carries a `schema_version: int = 1` field. This is reserved for future use — V1 sets it to `1` and no consumer should branch on it yet. When the protocol introduces breaking changes within a block type, `schema_version` will increment, and consumers will be expected to dispatch on it. Until then, treat it as a constant.

## Future package split

The package today bundles two distinct concerns:

- **Substrate** — `InterchangeBlock`, `InterchangeBlockRegistry`, `register_interchange_block`, `resolve_interchange_blocks`, plus the trust-boundary contract (`extra="forbid"`) and the `schema_version` policy. Reusable by any agent vocabulary.
- **Diplomat vocabulary** — `CommitIntent`, `CommitResult`, `InboundDigest`, and the four StrEnums (`SoWPeerTier`, `CommitVerdict`, `RejectionReason`, `DigestConfidence`). Specific to the Diplomat handshake.

If cross-vendor adoption of the substrate materializes, the substrate may move into a separate `interchange-protocol` package down the line and `agent-handshake-protocol` will depend on it. **No schedule or trigger is committed here** — the split happens if and when a real non-Diplomat adopter shows up and the bundled distribution causes friction.

If the split happens, the substrate imports remain stable via re-export. That is, `from agent_handshake_protocol import InterchangeBlock` (and the other substrate exports: `InterchangeBlockRegistry`, `register_interchange_block`, `resolve_interchange_blocks`) will continue to resolve to the same class objects — `agent_handshake_protocol` will re-export them from the new `interchange-protocol` package.

Consumers who want to import the substrate directly from the (future) `interchange-protocol` package can do so once it exists; consumers who keep importing from `agent_handshake_protocol` see no change. The migration is invisible at the import-statement level, by design.

This is a forward-looking commitment, not a planned action. The current package layout — substrate and vocabulary co-located in `agent_handshake_protocol` — is the V1 baseline.

## Where to file changes

- New block types or enum values: open an issue or PR on the public repo (D1 from `docs/diplomat-v1-compat-prd.md`).
- Field removals or renames: not acceptable in `0.x` patches. File for `0.2.0` or higher.
- Wire-format string changes: never acceptable in `0.x`. The wire format is the public contract.
