# agent-handshake-protocol — Claude session notes

## Identity & task queue

- **Loom project:** `agent-handshake-protocol` (id `47836951-70c9-4ad9-a3f7-88aeefebc69b`)
- **Loom agent name:** `handshake_protocol` (registered as worker)
- The global Loom MCP server is pinned at startup to `loom-loop` (its `app.project_id` is process-global; `loom_switch_project` mutates the shared context and would affect every other session). Until session-bound project scoping lands in Loom, **always pass `project_id="47836951-70c9-4ad9-a3f7-88aeefebc69b"` explicitly** on `loom_status`, `loom_inbox`, `loom_create`, etc. when working in this repo. Do **not** call `loom_switch_project` — it has global side effects.
- Tracked enhancement: feature request sent to `warp` in `loom-loop` to add per-session project binding so cwd→project resolution works as originally intended.

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
