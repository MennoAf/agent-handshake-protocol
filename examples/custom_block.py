"""Example: a non-Diplomat InterchangeBlock subclass.

Demonstrates that the InterchangeBlock substrate (base class + registry +
register/resolve helpers + extra="forbid" trust boundary + schema_version
policy) is independently usable for any agent vocabulary, not just the
Diplomat handshake.

This file imports ONLY substrate exports from agent_handshake_protocol. If
a Diplomat-vocabulary import ever appears here, the substrate-independence
contract has broken — the test in tests/test_examples.py asserts this with
a negative grep in the PRD done_when (docs/diplomat-v1-compat-prd.md §D6).

Run:
    uv run python examples/custom_block.py
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from agent_handshake_protocol import (
    InterchangeBlock,
    register_interchange_block,
    resolve_interchange_blocks,
)


class BugSeverity(StrEnum):
    LOW = "low"
    HIGH = "high"
    CRITICAL = "critical"


@register_interchange_block
class BugReport(InterchangeBlock):
    """Toy block — a third-party vocabulary the substrate carries unchanged."""

    type: Literal["bug-report"] = "bug-report"
    title: str
    severity: BugSeverity
    repro_steps: list[str]


def main() -> None:
    original = BugReport(
        title="Login button does nothing on Safari 17",
        severity=BugSeverity.HIGH,
        repro_steps=[
            "open /login on Safari 17",
            "click 'Sign in'",
            "observe: no navigation, no console error",
        ],
    )

    wire_payload = [original.model_dump()]
    resolved = resolve_interchange_blocks(wire_payload)

    # resolve_interchange_blocks returns `object` statically; narrow to list,
    # then narrow each block to its concrete subclass before reading fields.
    assert isinstance(resolved, list)
    assert len(resolved) == 1
    restored = resolved[0]
    assert isinstance(restored, BugReport)
    assert restored.title == original.title
    assert restored.severity == BugSeverity.HIGH
    assert restored.repro_steps == original.repro_steps

    print(f"Round-trip OK: {restored.title!r} ({restored.severity})")


if __name__ == "__main__":
    main()
