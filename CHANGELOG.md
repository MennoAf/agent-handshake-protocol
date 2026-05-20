# Changelog

All notable changes to `agent-handshake-protocol`. The format loosely follows [Keep a Changelog](https://keepachangelog.com/) and the project adheres to [Semantic Versioning](https://semver.org/) with the patch-additivity guarantees documented in [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md).

## [Unreleased]

### Changed (breaking on receive semantics, additive on wire)

- **`InterchangeBlock` is now an abstract base.** Direct instantiation (`InterchangeBlock(type="x")` or `InterchangeBlock.model_validate(...)`) raises `ValueError`. Subclasses are still the supported extension path — see `docs/COMPATIBILITY.md` "Abstract base — extension contract." Existing concrete subclasses (`CommitIntent`, `CommitResult`, `InboundDigest`) are unaffected; consumers who only construct via these subclasses see no behavior change.
- **Receive policy: `extra="forbid"` → `extra="ignore"`** with WARN-on-drop. Unknown fields on inbound blocks are now dropped (instead of raising `ValidationError`) and logged at `WARNING` level via the `agent_handshake_protocol.contracts` logger. This makes the protocol forward-compatible: newer peers can add fields without breaking older consumers, while schema drift remains observable in logs. The receive doctrine is now codified in `docs/COMPATIBILITY.md` "Postel posture."
- **`resolve_interchange_blocks` strictness.** Non-dict, non-`InterchangeBlock` items in the input list now raise `TypeError` with the offending index and observed type. Previously these were silently passed through, violating the implicit `list[InterchangeBlock]` contract. The return type is now declared as `list[InterchangeBlock] | object` so static checkers can rely on it. Callers that intentionally mixed raw values into the list must now pre-filter.
- **`InterchangeBlockRegistry` is now a read-only `MappingProxyType`.** Introspection (`in`, `.keys()`, `.items()`, iteration) works as before. Direct mutation (`InterchangeBlockRegistry["x"] = Y`) now raises `TypeError`. All registration must go through `@register_interchange_block`. Tests that need to mutate the underlying dict for isolation should import the module-private `_REGISTRY` name.

### Added

- **`schema_version` bounds.** `schema_version: int = Field(ge=1, le=65535)`. Values outside this range raise `ValidationError`. The field is still a forward-compat reservation; no dispatch branches on it yet.
- **`__init_subclass__` guard on `InterchangeBlock`.** Subclasses that omit a non-empty Literal default on `type` are rejected at class-definition time with a `TypeError` explaining the required pattern. Catches the "I forgot to declare the type string" mistake before the class can be instantiated or registered.
- **`py.typed` marker** (PEP 561). Downstream type checkers now pick up the type hints in `agent_handshake_protocol`. Required for a typed library.
- **GitHub Actions CI** (`.github/workflows/test.yml`). Runs `pytest`, `ruff check`, and `mypy` on push and pull request against Python 3.12 and 3.13.
- **`CHANGELOG.md`** (this file). Referenced from `docs/RELEASING.md` and `pyproject.toml` `[project.urls]`.
- **`[project.urls]`** block in `pyproject.toml` — homepage, repository, issues, changelog.
- **`docs/COMPATIBILITY.md` doctrine sections**: "Postel posture: receive liberal, send conservative," "Abstract base — extension contract," "Firewall doctrine — cross-install context." The firewall section codifies that agents read structured digests, not raw peer-side prose — preventing the cross-install context-bleed failure mode.

### Audit notes (2026-05-19)

A Finch council audit (Goonsquad / Repo Eval / Sieve deep / Ghost) drove the changes above. Two notes worth recording for future readers:

- **Wrap serializer was already correct.** Ghost's CRITICAL finding suggested the `@model_serializer(mode="wrap")` at `contracts.py:_serialize_with_subclass_fields` was leaking undeclared instance attributes onto the wire. On audit-grade review, the loop already iterated `type(self).model_fields` (Pydantic's declared field set), so undeclared attrs cannot reach the wire by construction. No change was needed to the serializer body; a comment was added noting the audit pass. The actual root cause of the round-trip-asymmetry concern Ghost was reaching for was `extra="forbid"` on receive, which is addressed above.
- **The wire format itself is unchanged.** All built-in blocks (`CommitIntent`, `CommitResult`, `InboundDigest`) emit and accept the same JSON shape they did before. Consumers running v0.1.0 against a peer running this version (and vice versa) are interoperable. The behavioral changes above affect how the receive side handles *unexpected* input — they do not change the bytes for expected input.

## [0.1.0] — 2026-05-19

Initial release. Substrate + Diplomat V1 vocabulary, distributed via tagged GitHub release. See [`docs/diplomat-v1-compat-prd.md`](docs/diplomat-v1-compat-prd.md) for the V1 distribution PRD.

### Included

- `InterchangeBlock` polymorphic base + `InterchangeBlockRegistry` + `register_interchange_block` decorator + `resolve_interchange_blocks` deserializer.
- Diplomat vocabulary: `CommitIntent`, `CommitResult`, `InboundDigest` blocks; `SoWPeerTier`, `CommitVerdict`, `RejectionReason`, `DigestConfidence` enums.
- `__version__` exported from `importlib.metadata`.
- `docs/COMPATIBILITY.md` (version policy), `docs/RELEASING.md` (manual SOP).
- `examples/custom_block.py` (non-Diplomat substrate adopter) + `tests/test_examples.py`.
