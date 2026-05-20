"""Self-contained tests for the protocol package.

These verify the package can stand alone with only pydantic as a runtime
dependency — no Mentarchy / Wick imports. Integration tests that compose
these blocks into framework-specific containers (e.g., Mentarchy's
DoctrineLedgerEntry) live with their owning framework.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Literal

import pytest
from pydantic import ValidationError

from agent_handshake_protocol import (
    CommitIntent,
    CommitResult,
    CommitVerdict,
    DigestConfidence,
    InboundDigest,
    InterchangeBlock,
    InterchangeBlockRegistry,
    RejectionReason,
    SoWPeerTier,
    register_interchange_block,
    resolve_interchange_blocks,
)

# The mutable registry that ``register_interchange_block`` writes to.
# Public ``InterchangeBlockRegistry`` is a read-only ``MappingProxyType``
# view; tests that need to clear/restore state must work against the
# underlying dict. This import is the only sanctioned mutation path
# outside the decorator itself.
from agent_handshake_protocol.contracts import _REGISTRY


@pytest.fixture(autouse=True)
def _isolate_registry():
    """Snapshot the registry around each test so test-registered blocks don't leak."""
    snapshot = dict(_REGISTRY)
    yield
    _REGISTRY.clear()
    _REGISTRY.update(snapshot)


class TestEnumWireFormat:
    """Wire values are part of the protocol — exact strings matter."""

    def test_sow_peer_tier_values(self):
        assert SoWPeerTier.AGENT.value == "agent"
        assert SoWPeerTier.SKILL.value == "skill"
        assert SoWPeerTier.MANUAL.value == "manual"

    def test_commit_verdict_values(self):
        assert CommitVerdict.COMMITTED.value == "COMMITTED"
        assert CommitVerdict.REJECTED.value == "REJECTED"

    def test_rejection_reason_eight_values(self):
        assert {r.value for r in RejectionReason} == {
            "SOW_STALE",
            "SOW_HASH_MISMATCH",
            "CLAIM_EXPIRED",
            "CLAIM_NOT_HELD",
            "SECRET_DETECTED",
            "SCOPE_VIOLATION",
            "PUSH_CONFLICT_UNRESOLVED",
            "TIER_MISMATCH",
        }

    def test_digest_confidence_four_levels(self):
        assert {c.value for c in DigestConfidence} == {
            "CLEAN",
            "FLAGGED_UNTRUSTED",
            "SUSPICIOUS",
            "NO_OP",
        }


class TestRegistry:
    def test_three_handshake_blocks_register_at_import(self):
        assert InterchangeBlockRegistry["commit-intent"] is CommitIntent
        assert InterchangeBlockRegistry["commit-result"] is CommitResult
        assert InterchangeBlockRegistry["inbound-digest"] is InboundDigest

    def test_register_duplicate_type_raises(self):
        with pytest.raises(ValueError, match="already registered"):

            @register_interchange_block
            class FakeCommitIntent(InterchangeBlock):
                type: Literal["commit-intent"] = "commit-intent"

    def test_register_idempotent_for_same_class(self):
        @register_interchange_block
        class CustomBlock(InterchangeBlock):
            type: Literal["custom-block"] = "custom-block"

        register_interchange_block(CustomBlock)  # no raise
        assert InterchangeBlockRegistry["custom-block"] is CustomBlock


class TestCommitIntent:
    def test_round_trip_preserves_all_fields(self):
        block = CommitIntent(
            intent="Refactor the ledger writer",
            files_changed=["a.py", "b.py"],
            claim_id="claim-001",
            scope_assertion="within scope",
        )
        restored = CommitIntent.model_validate(block.model_dump())
        assert restored == block
        assert restored.type == "commit-intent"
        assert restored.schema_version == 1

    def test_intent_max_length_enforced(self):
        with pytest.raises(ValidationError):
            CommitIntent(
                intent="x" * 501,
                files_changed=["a.py"],
                claim_id="c1",
                scope_assertion="ok",
            )

    def test_extra_fields_logged_and_dropped(self, caplog):
        """Receive-policy: unknown fields are WARN-logged and dropped, not rejected.

        Forward-compat posture (Postel): older consumers should tolerate newer
        peers adding fields without crashing. Pydantic ``extra="ignore"`` does
        the drop; the model_validator(mode="before") emits the WARNING so the
        drift is observable (no silent loss).
        """
        with caplog.at_level(logging.WARNING, logger="agent_handshake_protocol.contracts"):
            block = CommitIntent.model_validate(
                {
                    "type": "commit-intent",
                    "intent": "x",
                    "files_changed": ["a.py"],
                    "claim_id": "c1",
                    "scope_assertion": "ok",
                    "unexpected": "kaboom",
                    "another_extra": 42,
                }
            )
        assert block.intent == "x"
        assert not hasattr(block, "unexpected")
        assert not hasattr(block, "another_extra")
        assert "Dropping unknown fields on CommitIntent" in caplog.text
        assert "unexpected" in caplog.text
        assert "another_extra" in caplog.text


class TestCommitResult:
    def test_committed_round_trip(self):
        block = CommitResult(
            verdict=CommitVerdict.COMMITTED,
            consumes="commit-intent#claim-001",
            commit_sha="a" * 40,
        )
        restored = CommitResult.model_validate(block.model_dump())
        assert restored == block

    def test_rejected_round_trip(self):
        block = CommitResult(
            verdict=CommitVerdict.REJECTED,
            consumes="commit-intent#claim-001",
            rejection_reason=RejectionReason.SCOPE_VIOLATION,
            rejection_detail="b.py outside claim scope",
            recovery_action="split into separate claim",
        )
        restored = CommitResult.model_validate(block.model_dump())
        assert restored == block
        assert restored.rejection_reason is RejectionReason.SCOPE_VIOLATION


class TestInboundDigest:
    def test_round_trip_preserves_all_fields(self):
        block = InboundDigest(
            confidence=DigestConfidence.CLEAN,
            since_digest=datetime(2026, 5, 13, tzinfo=UTC),
            files_changed=["docs/peer-notes.md"],
            claim_changes=["peer claimed: c-001"],
            sow_amendments=[],
            summary="peer updated notes",
            operator_action_required=False,
        )
        restored = InboundDigest.model_validate(block.model_dump())
        assert restored == block

    def test_summary_max_length_enforced(self):
        with pytest.raises(ValidationError):
            InboundDigest(
                confidence=DigestConfidence.CLEAN,
                since_digest=datetime(2026, 5, 13, tzinfo=UTC),
                files_changed=[],
                summary="x" * 1001,
            )


class TestConsumerFallbackContract:
    """Document the protocol's contract with consumers around unknown enum values.

    Per docs/COMPATIBILITY.md: this package raises ValueError on unknown enum
    values (the strict-at-the-boundary stance). Consumers are expected to
    wrap construction in try/except and default-fall-back. This test
    pins that contract in code so consumers can rely on it.
    """

    def test_unknown_peer_tier_string_raises_for_consumers_to_handle(self):
        with pytest.raises(ValueError):
            SoWPeerTier("delegate")

    def test_unknown_rejection_reason_string_raises_for_consumers_to_handle(self):
        with pytest.raises(ValueError):
            RejectionReason("BIKESHED_VIOLATION")

    def test_unknown_digest_confidence_string_raises_for_consumers_to_handle(self):
        with pytest.raises(ValueError):
            DigestConfidence("VIBES")


class TestVersionExport:
    def test_version_is_a_string(self):
        from agent_handshake_protocol import __version__

        assert isinstance(__version__, str)
        assert __version__  # non-empty


class TestResolveInterchangeBlocks:
    def test_resolves_dicts_to_concrete_subclasses(self):
        raw = [
            {
                "type": "commit-intent",
                "intent": "x",
                "files_changed": ["a.py"],
                "claim_id": "c1",
                "scope_assertion": "ok",
            }
        ]
        out = resolve_interchange_blocks(raw)
        assert isinstance(out[0], CommitIntent)
        assert out[0].intent == "x"

    def test_passes_through_already_resolved_blocks(self):
        block = CommitIntent(
            intent="x",
            files_changed=["a.py"],
            claim_id="c1",
            scope_assertion="ok",
        )
        out = resolve_interchange_blocks([block])
        assert out[0] is block

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="unknown interchange block type"):
            resolve_interchange_blocks([{"type": "nope"}])

    def test_missing_type_raises(self):
        with pytest.raises(ValueError, match="missing 'type' field"):
            resolve_interchange_blocks([{"intent": "x"}])

    def test_non_list_passes_through(self):
        assert resolve_interchange_blocks("not a list") == "not a list"
        assert resolve_interchange_blocks(None) is None

    def test_non_dict_item_raises_type_error_with_index(self):
        """Strict contract: non-dict, non-InterchangeBlock items are a caller bug."""
        valid = {
            "type": "commit-intent",
            "intent": "x",
            "files_changed": ["a.py"],
            "claim_id": "c1",
            "scope_assertion": "ok",
        }
        with pytest.raises(TypeError, match="index 1"):
            resolve_interchange_blocks([valid, "not a dict", valid])
        with pytest.raises(TypeError, match="index 0"):
            resolve_interchange_blocks([42, valid])


class TestAbstractBase:
    """Direct instantiation of InterchangeBlock is rejected (abstract-base posture)."""

    def test_direct_construction_raises(self):
        with pytest.raises(ValueError, match="abstract"):
            InterchangeBlock(type="commit-intent")

    def test_direct_model_validate_raises(self):
        with pytest.raises(ValueError, match="abstract"):
            InterchangeBlock.model_validate({"type": "commit-intent"})

    def test_concrete_subclass_still_constructs(self):
        # Subclasses bypass the guard because type(self) is not InterchangeBlock.
        block = CommitIntent(
            intent="x",
            files_changed=["a.py"],
            claim_id="c1",
            scope_assertion="ok",
        )
        assert isinstance(block, InterchangeBlock)
        assert isinstance(block, CommitIntent)

    def test_subclass_without_type_default_raises_at_class_definition(self):
        """__init_subclass__ rejects a subclass that forgets to declare a type default."""
        with pytest.raises(TypeError, match="must declare `type`"):

            class _ForgotToOverride(InterchangeBlock):
                pass

    def test_subclass_with_empty_type_default_raises_at_class_definition(self):
        with pytest.raises(TypeError, match="must declare `type`"):

            class _EmptyType(InterchangeBlock):
                type: Literal[""] = ""


class TestRegistryImmutability:
    """The public InterchangeBlockRegistry view rejects mutation."""

    def test_setitem_raises_type_error(self):
        with pytest.raises(TypeError):
            InterchangeBlockRegistry["sneaky"] = CommitIntent  # type: ignore[index]

    def test_delitem_raises_type_error(self):
        with pytest.raises(TypeError):
            del InterchangeBlockRegistry["commit-intent"]  # type: ignore[attr-defined]

    def test_reads_still_work(self):
        # Read-only does not mean opaque — introspection paths are first-class.
        assert "commit-intent" in InterchangeBlockRegistry
        assert InterchangeBlockRegistry["commit-intent"] is CommitIntent
        assert set(InterchangeBlockRegistry.keys()) >= {
            "commit-intent",
            "commit-result",
            "inbound-digest",
        }


class TestSchemaVersionBounds:
    """schema_version is bounded to a sane positive range."""

    def _intent_kwargs(self, **overrides):
        base = dict(
            intent="x",
            files_changed=["a.py"],
            claim_id="c1",
            scope_assertion="ok",
        )
        base.update(overrides)
        return base

    def test_schema_version_zero_rejected(self):
        with pytest.raises(ValidationError):
            CommitIntent(**self._intent_kwargs(schema_version=0))

    def test_schema_version_above_max_rejected(self):
        with pytest.raises(ValidationError):
            CommitIntent(**self._intent_kwargs(schema_version=70000))

    def test_schema_version_at_floor_accepted(self):
        block = CommitIntent(**self._intent_kwargs(schema_version=1))
        assert block.schema_version == 1

    def test_schema_version_at_ceiling_accepted(self):
        block = CommitIntent(**self._intent_kwargs(schema_version=65535))
        assert block.schema_version == 65535
