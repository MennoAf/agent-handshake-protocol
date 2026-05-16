# agent-handshake-protocol

Portable wire-protocol types for the agent-handshake / Diplomat ecosystem.

Pydantic v2 models for the cross-agent INTERCHANGE block primitive plus the
Diplomat commit/digest vocabulary. No framework coupling — depends only on
`pydantic`. Importable from any Python 3.12+ project.

## What's in here

- `InterchangeBlock` — base class for polymorphic interchange blocks
  (round-trip-lossless via wrap serializer; subclasses register via
  `@register_interchange_block`).
- `InterchangeBlockRegistry`, `register_interchange_block`,
  `_resolve_interchange_blocks` — registry + helper for polymorphic
  deserialization.
- Diplomat enums: `SoWPeerTier`, `CommitVerdict`, `RejectionReason`,
  `DigestConfidence`.
- Diplomat blocks: `CommitIntent`, `CommitResult`, `InboundDigest`.

## Consumers

- The V0 Diplomat *skill* (sibling repo `agent_handshake`).
- The V1 Wick-resident Diplomat *agent* (Mentarchy monorepo).
- Any third-party agent that wants to speak the same wire protocol.

## Install (editable, from a sibling checkout)

```toml
[tool.uv.sources]
agent-handshake-protocol = { path = "../agent-handshake-protocol", editable = true }
```
