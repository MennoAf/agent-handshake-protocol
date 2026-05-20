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

## Postel posture: receive liberal, send conservative

The protocol's wire boundary follows the robustness principle on both sides — and the asymmetry matters.

### Receive (be liberal)

`InterchangeBlock` is configured with `extra="ignore"`. Unknown fields on inbound blocks are **dropped, not rejected**. This lets a newer peer extend a block type (e.g. add `audit_token` to `CommitIntent`) without breaking an older consumer that doesn't yet know about the new field. The older consumer simply ignores what it can't interpret and processes the fields it does know.

Silent drops would be the failure mode here, so every drop is observable: a `model_validator(mode="before")` on `InterchangeBlock` emits a `WARNING` to the `agent_handshake_protocol.contracts` logger naming the model and the dropped field names. Consumers configure their logging stack however they want — file, stdout, structured JSON, error tracker. The point is that schema drift between peers does not vanish without a trace.

If a consumer wants strict rejection instead of tolerant ignore (e.g. for a security-sensitive boundary where unknown keys should hard-fail), they can subclass the relevant block and set `model_config = ConfigDict(extra="forbid")` on the subclass. The protocol itself does not impose strict mode by default.

### Send (be conservative)

The wrap serializer on `InterchangeBlock` iterates `type(self).model_fields` — the **declared** field set of the concrete subclass — when building the output dict. Undeclared instance attributes (anything a subclass might stash via `__setattr__` or via a `ConfigDict(extra="allow")` override) cannot leak onto the wire by construction. The send side emits exactly what the subclass's Pydantic schema declared, no more.

This asymmetry is intentional: if peers also-be-liberal on send, schema drift compounds across hops. If peers be-conservative-on-send, the wire format stays clean even when the codebase gets messy.

## Abstract base — extension contract

`InterchangeBlock` is an **abstract base**. Direct instantiation is rejected at runtime:

```python
InterchangeBlock(type="commit-intent")          # raises ValueError
InterchangeBlock.model_validate({"type": "x"})  # raises ValueError
```

Use a concrete subclass, or define your own. The required pattern for a new block type:

```python
from typing import Literal
from agent_handshake_protocol import InterchangeBlock, register_interchange_block

@register_interchange_block
class MyBlock(InterchangeBlock):
    type: Literal["my-block"] = "my-block"
    payload: str
    severity: int
```

A subclass that omits a non-empty Literal default on `type` is rejected at class-definition time (`TypeError` from `__init_subclass__`). This catches the common "I forgot to declare the type string" mistake before the class can ever be instantiated or registered. See [`examples/custom_block.py`](../examples/custom_block.py) for the worked example.

Third-party adopters are first-class extenders — the protocol expects subclasses outside the Diplomat vocabulary. The substrate is designed to carry them. See [`README.md`](../README.md) "Substrate vs vocabulary" for the framing.

## Firewall doctrine — cross-install context

A common failure mode when two agent installs work on the same repository is **context bleed**: peer A's free-form handoff prose (a Weft handoff, a session note, a planning doc) gets ingested by peer B's agent, which then can't distinguish "things peer A wants me to act on" from "things peer A wrote for their own agent's context." Confused scope is the symptom; conflated trust boundaries is the cause.

The protocol's design prevents this at the wire layer. Agents do **not** read peer-side prose directly. They read structured `InterchangeBlock` instances — specifically `InboundDigest` for peer-state summaries — that have already been classified by the Diplomat agent on the peer's side:

- `InboundDigest.confidence` (`CLEAN` / `FLAGGED_UNTRUSTED` / `SUSPICIOUS` / `NO_OP`) — trust classification of the source content.
- `InboundDigest.operator_action_required: bool` — explicit "this needs action" vs "FYI only" signal.
- `InboundDigest.summary` (max 1000 chars) — the classified, bounded summary that the consuming agent reads **instead of** the raw peer-side prose.

The contract is: raw `.handshake/v0/` artifacts and raw peer-side handoff prose are read **only** by Diplomat. The consuming agent sees only the structured digest. This package provides the vocabulary to express the result of that classification (the `InboundDigest` block, the `DigestConfidence` enum, the action-required bool). The classification logic itself lives in the Diplomat agent (Mentarchy V1 / agent_builder v0), not in this package.

**Practical consequence:** if your agent appears to "get confused by another agent's context," the bug is on the Diplomat side, not the protocol side. Either Diplomat isn't running between the two installs, or it is running but the classification pipeline isn't producing the right digest. The protocol guarantees the boundary has a clean vocabulary; it does not guarantee that consumers route inbound peer prose through it.

A future protocol version may extend the vocabulary to carry finer granularity ("here are 3 things to do + 2 FYIs"). That is a V2 candidate; the V1 contract is single-bool + single-summary.

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
