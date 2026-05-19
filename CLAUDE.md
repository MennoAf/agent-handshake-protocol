# agent-handshake-protocol — Claude session notes

## Identity & task queue

- **Loom project:** `agent-handshake-protocol` (id `47836951-70c9-4ad9-a3f7-88aeefebc69b`)
- **Loom agent name:** `handshake_protocol` (registered as worker)
- Working-dir auto-resolves to this project — `loom_status()` / `loom_inbox()` will scope here without an explicit `project_id`.
- If a session lands in `loom-loop` instead, the working-dir attribute on the project record is missing or wrong; fix the project record, don't override per-call.

## What this repo is

Portable Pydantic v2 wire-protocol types for the agent-handshake / Diplomat ecosystem. No framework coupling — `pydantic` is the only runtime dep. Importable from any Python 3.12+ project.

## Consumers (don't break their wire format)

- V0 Diplomat **skill** — sibling repo `agent_handshake`
- V1 Wick-resident Diplomat **agent** — Mentarchy monorepo
- Third-party agents speaking the same protocol

Changes to `InterchangeBlock`, the registry helpers, or the Diplomat enums/blocks (`CommitIntent`, `CommitResult`, `InboundDigest`, `SoWPeerTier`, `CommitVerdict`, `RejectionReason`, `DigestConfidence`) are wire-protocol changes — treat them as breaking unless additive and backward-compatible on deserialize.

## Conventions

- Package manager: `uv` (see `pyproject.toml`, `uv.lock`).
- Python ≥ 3.12.
- Tests under `tests/`; run with `uv run pytest`.
