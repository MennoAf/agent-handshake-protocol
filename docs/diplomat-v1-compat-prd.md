---
title: "agent-handshake-protocol — Diplomat V1 Compatibility & Distribution PRD"
project: agent-handshake-protocol
target_consumers:
  - Mentarchy (Diplomat V1 agent + Methodist checkers + shared contracts)
  - agent_builder (Diplomat v0 skill, CLI, daemon — consumed by Brandon's Finch install)
upstream:
  - "Mentarchy `documents/diplomat-v1-prd.md` — canonical Diplomat V1 PRD (status: SHIP IT)"
  - "Mentarchy commit 6537fdd — original contract extraction from `shared/contracts.py`"
  - "agent_builder commit f9877af (I1) — re-export shim in `agent_builder/handshake/contracts.py`"
authors: ["Jason Bauman"]
status: IN_PROGRESS
last_updated: 2026-05-19
v0_predecessor: "Contracts inline in Mentarchy `shared/contracts.py` (pre-6537fdd)"
---

# agent-handshake-protocol — Diplomat V1 Compatibility & Distribution PRD

## Problem

`agent-handshake-protocol` is the canonical home of the cross-install wire-protocol types Diplomat V1 speaks: `InterchangeBlock` (with its polymorphic registry), `CommitIntent`, `CommitResult`, `InboundDigest`, plus the enums `SoWPeerTier`, `CommitVerdict`, `RejectionReason`, `DigestConfidence`. Two consumers depend on it today:

1. **Mentarchy** imports directly (`from agent_handshake_protocol import ...`) and composes the types into `DoctrineLedgerEntry`, `CouncilInput`, and the Diplomat handlers (`agents/diplomat/diplomat/{outbound,inbound}.py`).
2. **agent_builder** (the `agent_handshake` sibling repo — Brandon's v0 Diplomat skill, CLI, and daemon) re-exports the contracts via a thin shim at `agent_builder/handshake/contracts.py` so its own consumers can import a stable local path.

The contracts themselves are structurally complete for Diplomat V1. Every type Diplomat needs already exists with the right field shape (audited 2026-05-19 against `agents/diplomat/diplomat/outbound.py:19-29` and `inbound.py:21-25`). **The blocking gap is distribution**, not type definitions:

- The repo has no git remote. The package is published nowhere.
- Both consumers depend on a sibling-path override (`[tool.uv.sources]` with `path = "../../agent-handshake-protocol"`, editable).
- Any external install — Brandon's Finch install consuming `agent-builder` from PyPI, an AIO Cleanroom CI runner installing Mentarchy, anyone running the v0 Diplomat skill outside Jason's filesystem — cannot resolve `agent-handshake-protocol>=0.1.0` because nothing on PyPI or any reachable git remote exposes it.

This PRD locks the V1 surface (no field changes) and ships the distribution + version-discipline pieces that unblock external installs. Mentarchy's Diplomat V1 PRD (§Asymmetric Peer Handling, §V2 Standalone Compatibility Seams) already depends on these primitives being importable from outside Jason's machine; this PRD is the upstream half of that contract.

## Non-Goals (V1)

- **Not adding fields** to `CommitIntent`, `CommitResult`, `InboundDigest`, or any enum. The audit confirmed Diplomat V1's full needs are met by the existing 0.1.0 surface. Any field additions are V2 and must go through a separate spec.
- **Not defining the `SoW` dataclass here.** SoW lives in `agent_builder.handshake.sow`, not in this package. This package contributes only the `SoWPeerTier` enum that the SoW dict shape references. See the companion `agent_builder` PRD for SoW work.
- **Not building a release automation system.** First publish is manual + documented. Automation is a follow-up if pain warrants.
- **Not bumping to 1.0.** V1 ships under 0.1.x; the 1.0 cut waits until Diplomat V1's first 30 days of dual-install operation produce no contract-shape regrets (mirrors §Validation Criteria Claim 4 in the Diplomat V1 PRD).
- **Not handling federation / N>2 parties.** The protocol stays 1:1; matches the Diplomat V1 non-goal.
- **Not splitting the package.** D6 names the substrate as reusable but keeps it inside `agent-handshake-protocol`. A separate `interchange-protocol` package is a V2 candidate gated on observed friction from a real non-Diplomat adopter — the `docs/COMPATIBILITY.md` "Future package split" section documents the split-on-demand contract so adopters know the migration path will be invisible at the import-statement level.

## What's already there (audit, 2026-05-19)

| Diplomat V1 needs | Present in 0.1.0? | Source |
| --- | --- | --- |
| `InterchangeBlock` polymorphic base + registry | ✅ | `contracts.py:23-89` |
| `resolve_interchange_blocks` deserializer | ✅ | `contracts.py:92-125` |
| `SoWPeerTier` enum (AGENT / SKILL / MANUAL) | ✅ | `contracts.py:133-144` |
| `CommitVerdict` (COMMITTED / REJECTED) | ✅ | `contracts.py:146-151` |
| `RejectionReason` × 8 (incl. TIER_MISMATCH) | ✅ | `contracts.py:153-169` |
| `DigestConfidence` × 4 (incl. NO_OP) | ✅ | `contracts.py:172-182` |
| `CommitIntent` with `claim_id` + `scope_assertion` + `files_changed` | ✅ | `contracts.py:185-199` |
| `CommitResult` with optional `commit_sha` + rejection fields | ✅ | `contracts.py:202-221` |
| `InboundDigest` with `confidence` + `operator_action_required` | ✅ | `contracts.py:224-241` |
| `extra="forbid"` at the trust boundary | ✅ | `InterchangeBlock.model_config` |
| Lossless subclass-field round-trip | ✅ | `_serialize_with_subclass_fields` wrap serializer |
| Tests pass (`tests/test_contracts.py`) | ✅ | Verified locally |

No type-shape work is required to support Diplomat V1.

## Constraints Touched (Gate A catalog)

Enforced bounds and validators that live in or near the modified components. None are modified by this PRD; all are explicitly OUT OF SCOPE here. Future field-shape PRDs must catalog them in scope.

| Constraint | Location | Status |
| --- | --- | --- |
| `CommitIntent.intent` `max_length=500` | `agent_handshake_protocol/contracts.py:196` | OUT OF SCOPE — V1 field shape locked. |
| `InboundDigest.summary` `max_length=1000` | `agent_handshake_protocol/contracts.py:240` | OUT OF SCOPE — V1 field shape locked. (Diplomat truncates to 1000 at emit time, see `agents/diplomat/diplomat/inbound.py:197`.) |
| `InterchangeBlock` `extra="forbid"` (trust-boundary unknown-key rejection) | `contracts.py:32` | OUT OF SCOPE — load-bearing for V1 trust boundary; do not loosen. |
| `requires-python = ">=3.12"` | `pyproject.toml:5` | NAMED — D2 verifies the published wheel installs against 3.12+. Not modified. |
| Pydantic v2 dep floor (`pydantic>=2.7`) | `pyproject.toml:8` | OUT OF SCOPE — bumped only on demonstrated need. |

## Required work

### D1 — Publish git remote

**Status (2026-05-19): PENDING — operator action.** Decision made: `MennoAf/agent-handshake-protocol`. Commands in §Execution Hand-off.

Create a public GitHub repo and push the current `main`. The repo lives under `MennoAf/agent-handshake-protocol` (same org as `agent-builder`, keeps the Diplomat ecosystem co-located).

**Done when:**
- `git remote get-url origin` prints the chosen GitHub URL.
- `git push -u origin main` exits 0.
- `curl -s https://raw.githubusercontent.com/{owner}/agent-handshake-protocol/main/README.md | diff - README.md` exits 0 (content-identical, not just visually similar).

### D2 — Tagged GitHub release as V1 distribution

**Status (2026-05-19): PENDING — operator action.** Distribution mechanism for V1 is a tagged GitHub release at `MennoAf/agent-handshake-protocol@v0.1.0`. PyPI publishing is deferred to V2-candidates (see "Out of scope") — there is no PyPI artifact in V1.

Tag `v0.1.0` on `main` and push the tag. Consumers install via `git+https://...@v0.1.0` URLs from their `pyproject.toml`. No PyPI account, no `uv build`+`uv publish` step, no wheel hosting — uv/pip resolves the tag's source tree directly and builds locally per consumer install.

The `dist/agent_handshake_protocol-0.1.0-py3-none-any.whl` + sdist artifacts built locally during D4/D5 prep remain on disk and are unused for V1 distribution. They survive as a head-start for a future PyPI publish (V2-candidate) but are not part of V1's done_when.

**Done when:**

- Tag `v0.1.0` exists on `origin` and points at the same commit as `origin/main`:
  ```
  git fetch --tags origin
  git rev-parse v0.1.0 == git rev-parse origin/main    # exits 0
  ```
- A fresh `/tmp/ahp-smoke` venv installs the package from the GitHub tag and the import smoke passes:
  ```
  uv venv /tmp/ahp-smoke
  /tmp/ahp-smoke/bin/uv pip install "agent-handshake-protocol @ git+https://github.com/MennoAf/agent-handshake-protocol.git@v0.1.0"
  /tmp/ahp-smoke/bin/python -c "from agent_handshake_protocol import CommitIntent, SoWPeerTier, __version__; assert CommitIntent.__module__ == 'agent_handshake_protocol.contracts'; assert SoWPeerTier.AGENT.value == 'agent'; assert __version__ == '0.1.0'"
  ```
- The smoke is run from a directory that does NOT contain any `[tool.uv.sources]` override pointing at a local sibling checkout (verified by `! rg 'agent-handshake-protocol' /tmp/ahp-smoke/**/pyproject.toml 2>/dev/null | rg 'path ='`).

### D3 — Repoint consumer overrides at the GitHub tag (downstream coordination)

**Status (2026-05-19): DEFERRED — gated on D2.** Not run until the D2 GitHub-tag install smoke confirms `v0.1.0` is reachable from a fresh clone. Operator pings Claude after D2 verifies; both consumer pyprojects are updated in a single short pass.

This step is not done in this repo, but it is the goal that justifies D1+D2. Once `v0.1.0` is tagged on `origin/main`:

- **Mentarchy** flips its `[tool.uv.sources]` entry for `agent-handshake-protocol` from `{ path = "../agent-handshake-protocol", editable = true }` to `{ git = "https://github.com/MennoAf/agent-handshake-protocol.git", tag = "v0.1.0" }`.
- **agent_builder** does the same at `pyproject.toml:29-30` — replaces the path override with a tag-pinned git source.

The `[tool.uv.sources]` block stays in each consumer's pyproject for V1; the override no longer points at a local sibling but at the public GitHub tag. PyPI distribution (V2 candidate) is what would let consumers drop the `[tool.uv.sources]` entry entirely.

Both updates land in their own repos but are tracked here because they are the visible deliverable of this PRD. See companion `agent_builder` PRD §A5 for the agent_builder side.

**Done when:**
- For each consumer pyproject.toml, the `[tool.uv.sources]` entry for `agent-handshake-protocol` is a tag-pinned git source (not a path override). Verified for each:
  ```
  rg -A2 'agent-handshake-protocol' /Users/jasonbauman/Documents/code_projects/Personal/Mentarchy/pyproject.toml | rg 'git = "https://github.com/MennoAf/agent-handshake-protocol' && rg -A2 'agent-handshake-protocol' /Users/jasonbauman/Documents/code_projects/Personal/Mentarchy/pyproject.toml | rg 'tag = "v0\.'
  rg -A2 'agent-handshake-protocol' /Users/jasonbauman/Documents/code_projects/Personal/agent_handshake/agent_builder/pyproject.toml | rg 'git = "https://github.com/MennoAf/agent-handshake-protocol' && rg -A2 'agent-handshake-protocol' /Users/jasonbauman/Documents/code_projects/Personal/agent_handshake/agent_builder/pyproject.toml | rg 'tag = "v0\.'
  ```
  All four `rg` calls exit 0.
- Neither consumer pyproject still references the local path override:
  ```
  ! rg -A2 'agent-handshake-protocol' /Users/jasonbauman/Documents/code_projects/Personal/Mentarchy/pyproject.toml | rg 'path = "\.\./agent-handshake-protocol'
  ! rg -A2 'agent-handshake-protocol' /Users/jasonbauman/Documents/code_projects/Personal/agent_handshake/agent_builder/pyproject.toml | rg 'path = "\.\./agent-handshake-protocol'
  ```
- Both consumer suites exit 0 against the GitHub-tag-resolved version:
  ```
  cd /Users/jasonbauman/Documents/code_projects/Personal/Mentarchy && uv sync && uv run pytest -q
  cd /Users/jasonbauman/Documents/code_projects/Personal/agent_handshake/agent_builder && uv sync && uv run pytest -q
  ```

### D4 — Export `__version__` and add a compatibility note

**Status (2026-05-19): DONE (uncommitted).** `__version__` exported from `agent_handshake_protocol/__init__.py` via `importlib.metadata.version("agent-handshake-protocol")` with `PackageNotFoundError` fallback to `"0.0.0+unknown"`. `docs/COMPATIBILITY.md` landed with the three required policy headers (verified by D4 done_when grep chain).

Add a `__version__: str` constant at the package root (`agent_handshake_protocol/__init__.py`), sourced from `importlib.metadata.version("agent-handshake-protocol")`. Add a short `docs/COMPATIBILITY.md` documenting the version-pinning policy consumers should use:

- Minor-version compatibility (`>=0.1,<0.2`) is the supported pin until 1.0.
- Patch releases (0.1.x) are always additive — no field removals, no enum-value removals.
- New enum values may appear in patches; consumers must default-default-fall-back rather than raise on unknown values (Diplomat already does this — see `inbound.py:_peer_tier_from_sow` for the canonical pattern).

**Done when:**
- `python -c "from agent_handshake_protocol import __version__; assert __version__ == '0.1.0'"` exits 0.
- `docs/COMPATIBILITY.md` exists AND `grep -q "Minor-version compatibility" docs/COMPATIBILITY.md && grep -q "Patch releases are always additive" docs/COMPATIBILITY.md && grep -q "default-fall-back rather than raise on unknown values" docs/COMPATIBILITY.md` exits 0.

### D5 — Test coverage for the V1 surface (gap-fill)

**Status (2026-05-19): DONE (uncommitted).** Existing suite already covered two of the three originally scoped tests (`TestRegistry::test_three_handshake_blocks_register_at_import`, `TestEnumWireFormat::test_rejection_reason_eight_values`). Added `TestConsumerFallbackContract` (3 tests pinning the strict-at-boundary contract for `SoWPeerTier`, `RejectionReason`, `DigestConfidence`) + `TestVersionExport` (1 test). Full suite: 23/23 green.

Existing `tests/test_contracts.py` covers the polymorphic round-trip. Add three focused tests so any future field change forces a deliberate test update:

- `test_all_diplomat_v1_block_types_register_themselves` — asserts `CommitIntent`, `CommitResult`, `InboundDigest` are all present in `InterchangeBlockRegistry` after import (regression guard against accidentally dropping the `@register_interchange_block` decorator).
- `test_rejection_reason_enum_is_locked` — asserts the eight current `RejectionReason` values are present and no others. New rejections are intentional additions, not accidental ones.
- `test_unknown_peer_tier_string_handled_by_consumers` — documents (in a comment) that the package itself does not silently fall back; consumers (Diplomat) are expected to wrap `SoWPeerTier(value)` in try/except. The test exercises the explicit `ValueError` so the contract is visible.

**Done when:**
- All three tests are runnable and exit 0:
  ```
  uv run pytest tests/test_contracts.py::test_all_diplomat_v1_block_types_register_themselves tests/test_contracts.py::test_rejection_reason_enum_is_locked tests/test_contracts.py::test_unknown_peer_tier_string_handled_by_consumers -q
  ```
- The full suite exits 0: `uv run pytest tests/ -q` from the package root.
- Substrate note: tests are pure-Python type / registry assertions. No external substrate is involved; the stub-vs-live question does not apply.

### D6 — Position substrate as independently usable

**Status (2026-05-19): PROPOSED — execution pending.** Added after Mentarchy's V1 agent surfaced the use case ("integrate the contracts.py idea into their own workflow without dealing with the specific agents"). Audit pass: SOLID after revision (chat history this session). Three deliverables land in the same uncommitted batch as D4/D5, before D1+D2 ship.

Reframes the package's outward positioning so the `InterchangeBlock` primitive can be adopted by third parties without committing to the Diplomat vocabulary. Three deliverables:

1. **README.md "Substrate vs vocabulary" section.** Names which exports are reusable substrate (`InterchangeBlock`, `InterchangeBlockRegistry`, `register_interchange_block`, `resolve_interchange_blocks`, the `extra="forbid"` + `schema_version` policy) vs which are Diplomat-specific vocabulary (`CommitIntent`, `CommitResult`, `InboundDigest`, the four StrEnums). States explicitly that adopters who don't want Diplomat can register their own blocks against the substrate. Also updates the install snippet to show the PyPI form (`uv add agent-handshake-protocol` or equivalent).

2. **`examples/custom_block.py` toy.** ~40 lines: a non-Diplomat `InterchangeBlock` subclass with its own enum, `@register_interchange_block`, and a round-trip through `resolve_interchange_blocks`. **Load-bearing constraint:** the file MUST NOT import any Diplomat vocabulary (`CommitIntent`, `CommitResult`, `InboundDigest`, `SoWPeerTier`, `CommitVerdict`, `RejectionReason`, `DigestConfidence`). That negative is the mechanical proof of substrate independence. Regression-guarded by `tests/test_examples.py`, which exercises the real `resolve_interchange_blocks` round-trip and pops the example block from `InterchangeBlockRegistry` in teardown so it does not contaminate other test sessions.

3. **`docs/COMPATIBILITY.md` "Future package split" section.** Documents the forward-looking contract: if cross-vendor adoption of the substrate materializes, the substrate may move into a separate `interchange-protocol` package, and the import path `from agent_handshake_protocol import InterchangeBlock` (plus the other substrate exports) will remain stable via re-export. Forward-looking commitment, not a planned action — package-naming question for V1 was decided as: keep `agent-handshake-protocol`, treat substrate-independence as a documentation claim rather than a branding one.

**Done when:**

1. README substrate-vs-vocabulary framing:
   ```
   grep -q "Substrate vs vocabulary" README.md
   grep -qE "InterchangeBlock.*substrate|substrate.*InterchangeBlock" README.md
   grep -qE "Diplomat (vocabulary|blocks)" README.md
   ```
   All three exit 0.

2. `examples/custom_block.py` is a substrate-only adopter:
   ```
   uv run python examples/custom_block.py     # exits 0
   ! grep -qE "CommitIntent|CommitResult|InboundDigest|SoWPeerTier|CommitVerdict|RejectionReason|DigestConfidence" examples/custom_block.py
   ```
   (the negative grep MUST exit 1 — i.e., no Diplomat imports.)

3. `tests/test_examples.py` exercises the substrate via real round-trip and cleans up:
   ```
   uv run pytest tests/test_examples.py -q    # exits 0
   grep -q "resolve_interchange_blocks" tests/test_examples.py
   grep -qE "model_dump|model_validate" tests/test_examples.py
   grep -qE "InterchangeBlockRegistry\.pop|del InterchangeBlockRegistry|fixture" tests/test_examples.py
   ```

4. `docs/COMPATIBILITY.md` split-on-demand commitment:
   ```
   grep -q "Future package split" docs/COMPATIBILITY.md
   grep -q "stable via re-export" docs/COMPATIBILITY.md
   grep -q "from agent_handshake_protocol import InterchangeBlock" docs/COMPATIBILITY.md
   ```

5. README install snippet shows the GitHub-tag install form:
   ```
   grep -qE "git\+https://github\.com/MennoAf/agent-handshake-protocol" README.md
   ```

6. Full suite remains green:
   ```
   uv run pytest tests/ -q    # exits 0
   ```

**Substrate note:** D6 is pure documentation + example-file work. No external substrate involvement. The example uses the real registry and real `resolve_interchange_blocks` function (not mocks); the test's pytest gate exercises real Pydantic round-trip serialization.

## Acceptance criteria (rollup)

Each item is a runnable assertion (or a pointer to one defined in §Required work):

1. `git remote get-url origin` prints a non-empty GitHub URL (D1).
2. Tag `v0.1.0` exists on `origin` pointing at `origin/main` AND the D2 clean-venv `git+https://...@v0.1.0` install smoke exits 0 (D2).
3. Both consumer pyprojects' `[tool.uv.sources]` entries for `agent-handshake-protocol` are tag-pinned git sources (not path overrides), AND both consumer test suites pass against the tag-resolved version (D3).
4. `python -c "from agent_handshake_protocol import __version__; assert __version__ == '0.1.0'"` exits 0 (D4).
5. `[ -f docs/COMPATIBILITY.md ] && [ -f docs/RELEASING.md ]` exits 0 AND the D4 `grep -q` chain for the COMPATIBILITY policy headers exits 0 (D2 + D4).
6. `uv run pytest tests/ -q` exits 0 (covers the three new D5 tests + the existing suite + the new D6 example test).
7. D6 grep + run chain exits 0 across all sub-clauses: README "Substrate vs vocabulary" section landed, `examples/custom_block.py` runs cleanly with no Diplomat-vocabulary imports, `tests/test_examples.py` exercises the real `resolve_interchange_blocks` round-trip and cleans up the registry, `docs/COMPATIBILITY.md` "Future package split" section landed with the re-export commitment, README install snippet shows the GitHub-tag install form (`git+https://github.com/MennoAf/agent-handshake-protocol`).

## Rollout sequence

1. **D4 + D5 + D6** (version export + tests + substrate-independence framing) land in this repo as one uncommitted prep batch.
2. **D1** (push remote to `MennoAf/agent-handshake-protocol`) — unblocks D2.
3. **D2** (tag `v0.1.0` on `origin/main`) — unblocks D3. README install snippet already shows the GitHub-tag form (no flip required).
4. **D3** (consumer pin updates to git+tag) — lands in Mentarchy + agent_builder *after* D2 verifies, in two separate commits (one per consumer repo), with passing test suites.

Total expected work: low-single-digit hours, gated only by the GitHub repo decision (§Open Questions Q1) and PyPI account access.

## Test plan

- **Unit tests** in this repo: the three new D5 tests, the three new D6 example tests, plus existing round-trip coverage.
- **Integration smoke (manual, post-tag):** create a fresh `/tmp/ahp-smoke`, `uv venv && uv pip install "agent-handshake-protocol @ git+https://github.com/MennoAf/agent-handshake-protocol.git@v0.1.0"`, run `python -c "from agent_handshake_protocol import CommitIntent, SoWPeerTier, __version__; ..."` and verify no import errors AND `__version__ == "0.1.0"`.
- **Consumer regression:** after D3 lands, run `pytest` in both Mentarchy and agent_builder against the GitHub-tag-resolved version. All current passing tests must remain passing — this is the load-bearing verification that the path-source-to-git-tag swap is observably a no-op.

## Pre-D2 Decisions (resolved 2026-05-19)

1. **License: MIT.** ✅ `LICENSE` file landed at repo root; `pyproject.toml` declares `license = "MIT"` + `license-files = ["LICENSE"]` + `authors = [{ name = "Jason Bauman" }]`. `uv build` verified to accept the declaration (dist/ wheel + sdist built locally; unused for V1 GitHub-tag distribution but kept for the V2 PyPI candidate).
2. **Repo home: `MennoAf/agent-handshake-protocol`.** Co-located with `agent-builder` for ecosystem visual unity. To be created via `gh repo create` in the Execution Hand-off step below.
3. **V1 distribution: tagged GitHub releases, not PyPI.** PyPI publish is deferred to V2 candidates (no account setup, no token management, no registry contract for V1). Consumers pin via `[tool.uv.sources]` with a tag-pinned git source. PyPI moves from "operator action" to "open if external adoption pressure materializes" — see "Out of scope (explicit V2 candidates)."

## Execution Hand-off (2026-05-19)

Snapshot of what's prepped in this repo and the exact commands remaining for the operator. Each command should be run from the operator's shell (Claude Code's `Bash(git push*)` deny rule blocks the agent from doing it directly; same logic applies to credentialed `uv publish` and `gh repo create` steps).

### State at hand-off

In `~/Documents/code_projects/Personal/agent-handshake-protocol/`:

| Artifact | State |
| --- | --- |
| `LICENSE` (MIT) | landed, uncommitted |
| `pyproject.toml` (license + authors metadata) | edited, uncommitted |
| `agent_handshake_protocol/__init__.py` (`__version__` export) | edited, uncommitted |
| `docs/COMPATIBILITY.md` | landed, uncommitted |
| `docs/RELEASING.md` | landed, uncommitted |
| `tests/test_contracts.py` (TestConsumerFallbackContract + TestVersionExport) | edited, uncommitted |
| `README.md` (Substrate-vs-vocabulary section + PyPI install form) | pending — D6 |
| `examples/custom_block.py` (non-Diplomat InterchangeBlock adopter) | pending — D6 |
| `tests/test_examples.py` (substrate round-trip + registry cleanup) | pending — D6 |
| `docs/COMPATIBILITY.md` (Future package split section) | pending — D6 |
| `dist/agent_handshake_protocol-0.1.0-{whl,tar.gz}` | built locally, ready to publish (rebuild after D6 lands) |
| Test suite | 23/23 green (rerun after D6 adds tests/test_examples.py) |
| Git remote | none configured |

In `~/Documents/code_projects/Personal/agent_handshake/agent_builder/`:

| Artifact | State |
| --- | --- |
| Commit `f9877af` (I1 re-export shim) | local-only, not yet on `origin/main` |

### Operator commands

**Step 1 — Commit the protocol-repo prep, create the GitHub repo, push:**

```
cd ~/Documents/code_projects/Personal/agent-handshake-protocol
git add LICENSE pyproject.toml agent_handshake_protocol/__init__.py docs/ tests/test_contracts.py tests/test_examples.py examples/ README.md
git status   # review
git commit -m "Add license, version export, compat + release docs, consumer-fallback tests, substrate-independence framing (D6)"
gh repo create MennoAf/agent-handshake-protocol --public --source=. --remote=origin --push
```

If `gh repo create` doesn't have org-write permissions for `MennoAf`, fall back to manual: create the empty repo on github.com, then:

```
git remote add origin git@github.com:MennoAf/agent-handshake-protocol.git
git push -u origin main
```

Acceptance gates from D1 — both should exit 0 after this step:

```
git remote get-url origin
curl -s https://raw.githubusercontent.com/MennoAf/agent-handshake-protocol/main/README.md | diff - README.md
```

**Step 2 — Tag v0.1.0 and push:**

```
cd ~/Documents/code_projects/Personal/agent-handshake-protocol
git tag -a v0.1.0 -m "Release 0.1.0 (GitHub-tag distribution; PyPI deferred)"
git push origin v0.1.0
```

Then the D2 acceptance smoke (clean-venv install from the GitHub tag):

```
uv venv /tmp/ahp-smoke
/tmp/ahp-smoke/bin/uv pip install "agent-handshake-protocol @ git+https://github.com/MennoAf/agent-handshake-protocol.git@v0.1.0"
/tmp/ahp-smoke/bin/python -c "from agent_handshake_protocol import CommitIntent, SoWPeerTier, __version__; assert CommitIntent.__module__ == 'agent_handshake_protocol.contracts'; assert SoWPeerTier.AGENT.value == 'agent'; assert __version__ == '0.1.0'"
```

All three must exit 0. Tag visibility check: `git ls-remote --tags origin v0.1.0 | grep -q refs/tags/v0.1.0`.

**Step 3 — Push the agent_builder I1 commit (covers companion PRD §A4):**

```
cd ~/Documents/code_projects/Personal/agent_handshake/agent_builder
git push origin main
git merge-base --is-ancestor f9877af origin/main   # must exit 0
```

**Step 4 — Hand off back to Claude for D3 / A5:**

Once Step 2's clean-venv smoke succeeds, return to Claude and the path-override drop in both consumer pyprojects happens in a single short pass (Mentarchy + agent_builder + a green pytest run each).

### What Claude has NOT done (and why)

- **Git commits in this repo.** Per the global "only commit when explicitly requested" rule. The `git add` + `git commit` line above is staged so the operator can review the diff first.
- **Git push, gh repo create, git push --tags.** Credential-bearing or remote-mutating; outside Claude Code's auto-mode safety envelope here.
- **D3 / A5 (repointing `[tool.uv.sources]` overrides at the git tag).** Deferred deliberately so the GitHub-tag install is observably working before consumers depend on it.

## Out of scope (explicit V2 candidates)

- **PyPI publish.** V1 ships via tagged GitHub releases (see D2). PyPI becomes worth doing when (a) a non-friendly third-party adopter wants to `pip install agent-handshake-protocol` without configuring a git source override, or (b) a CI environment cannot reach GitHub from its package-resolution path. Until then, the GitHub tag IS the release artifact. `docs/RELEASING.md` carries the V1 GitHub-tag SOP up top with the PyPI SOP preserved as an appendix to re-enable later. The locally-built `dist/agent_handshake_protocol-0.1.0-{whl,tar.gz}` artifacts are kept on disk as a head-start for that PyPI bring-up.
- **`SoWPeerTierMap` typed alias** (`dict[str, SoWPeerTier]`). Mild ergonomics win for consumers; not load-bearing. Defer until a second consumer beyond Mentarchy needs the same Pydantic-validated SoW shape.
- **JSON Schema export** of every InterchangeBlock for external (non-Python) consumers. Useful if a non-Python peer install ever materializes; out of scope while both installs are Python.
- **Wheel signing / sigstore.** Worth doing if external trust becomes a concern; manual GitHub-tag distribution is the V1 baseline.
- **CI on the public GitHub.** Once D1 lands, a GitHub Actions workflow running `pytest` on push would be cheap insurance — but it is not gating Diplomat V1.

---

**Cross-reference:** companion PRD at `agent_handshake/agent_builder/docs/diplomat-v1-compat-prd.md` covers the SoW `peer_tier` field, CLI `--peer-tier` flag, and `commit_and_push` retry widening — the actual shape changes Diplomat V1 needs in the runtime layer.
