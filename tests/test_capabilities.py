"""Tests for the SoW capability / protocol-version negotiation vocabulary.

These lock the ``Capability`` value set as a wire-visible contract (add, never
rename), the ``parse_capabilities`` Postel posture (drop + warn on unknown,
never raise), and that the module is re-exported from the package root.
"""

from __future__ import annotations

import logging

import pytest

from agent_handshake_protocol import (
    PROTOCOL_VERSION,
    Capability,
    parse_capabilities,
)


def test_protocol_version_is_a_literal_string() -> None:
    """A literal, not derived from importlib.metadata — negotiation can't depend
    on the distribution being resolvable at runtime."""
    assert isinstance(PROTOCOL_VERSION, str)
    assert PROTOCOL_VERSION == "0.4.0"


def test_capability_value_set_is_the_contract() -> None:
    """Add-don't-rename: this guards drift in the announced vocabulary."""
    assert {c.value for c in Capability} == {
        "commit-interchange",
        "inbound-digest",
        "ephemeral-scope",
        "tier-negotiation",
        "capability-negotiation",
    }


def test_capability_values_are_kebab_case() -> None:
    for cap in Capability:
        assert cap.value == cap.value.lower()
        assert " " not in cap.value
        assert "_" not in cap.value


def test_parse_known_capabilities_round_trips() -> None:
    raw = ["commit-interchange", "inbound-digest"]
    assert parse_capabilities(raw) == [
        Capability.COMMIT_INTERCHANGE,
        Capability.INBOUND_DIGEST,
    ]


def test_parse_preserves_order_and_dedupes() -> None:
    raw = ["inbound-digest", "commit-interchange", "inbound-digest"]
    assert parse_capabilities(raw) == [
        Capability.INBOUND_DIGEST,
        Capability.COMMIT_INTERCHANGE,
    ]


def test_parse_drops_and_warns_on_unknown(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Postel: a newer peer's unknown capability is dropped, not raised, and the
    drop is observable in logs."""
    with caplog.at_level(logging.WARNING, logger="agent_handshake_protocol.capabilities"):
        result = parse_capabilities(["inbound-digest", "warp-drive"])
    assert result == [Capability.INBOUND_DIGEST]
    assert any("warp-drive" in rec.message for rec in caplog.records)


def test_parse_none_is_empty() -> None:
    assert parse_capabilities(None) == []


def test_parse_non_list_warns_and_returns_empty(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="agent_handshake_protocol.capabilities"):
        assert parse_capabilities("inbound-digest") == []
    assert any("must be a list" in rec.message for rec in caplog.records)


def test_parse_empty_list_is_empty() -> None:
    assert parse_capabilities([]) == []
