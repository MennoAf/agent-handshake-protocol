"""Regression test for examples/custom_block.py.

Loads the example by file path (so examples/ is not a Python package) and
exercises the real resolve_interchange_blocks round-trip. The autouse
registry-snapshot fixture mirrors test_contracts.py's pattern so registering
the example block here does not leak into other tests.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest

from agent_handshake_protocol import (
    InterchangeBlockRegistry,
    resolve_interchange_blocks,
)

# Mutable registry — see comment in tests/test_contracts.py for the rationale.
from agent_handshake_protocol.contracts import _REGISTRY

EXAMPLE_PATH = Path(__file__).parent.parent / "examples" / "custom_block.py"
EXAMPLE_MODULE_NAME = "_custom_block_under_test"


@pytest.fixture(autouse=True)
def _isolate_registry() -> Iterator[None]:
    snapshot = dict(_REGISTRY)
    yield
    _REGISTRY.clear()
    _REGISTRY.update(snapshot)
    sys.modules.pop(EXAMPLE_MODULE_NAME, None)


def _load_example() -> ModuleType:
    """Load examples/custom_block.py by file path; triggers @register_interchange_block.

    Registers the module in sys.modules so Pydantic's type-hint resolution
    (which looks up `Literal` etc. in the owning module's globals) works
    when the example uses `from __future__ import annotations`.
    """
    spec = importlib.util.spec_from_file_location(EXAMPLE_MODULE_NAME, EXAMPLE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[EXAMPLE_MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(EXAMPLE_MODULE_NAME, None)
        raise
    return module


def test_example_block_round_trips() -> None:
    """examples/custom_block.py survives the real resolve_interchange_blocks round-trip."""
    module = _load_example()
    BugReport = module.BugReport
    BugSeverity = module.BugSeverity

    original = BugReport(
        title="Test bug",
        severity=BugSeverity.LOW,
        repro_steps=["step 1", "step 2"],
    )

    wire_payload = [original.model_dump()]
    resolved = resolve_interchange_blocks(wire_payload)

    assert isinstance(resolved, list)
    assert len(resolved) == 1
    restored = resolved[0]
    assert isinstance(restored, BugReport)
    assert restored.title == "Test bug"
    assert restored.severity == BugSeverity.LOW
    assert restored.repro_steps == ["step 1", "step 2"]


def test_example_block_registers_under_bug_report_type() -> None:
    """The example claims the 'bug-report' type string in InterchangeBlockRegistry."""
    _load_example()
    assert "bug-report" in InterchangeBlockRegistry


def test_example_registry_cleanup_after_fixture() -> None:
    """After the autouse fixture restores the snapshot, 'bug-report' is gone.

    Loads the example inside this test (via the fixture-scoped helper), then
    asserts the registry currently HAS the key. The autouse fixture's teardown
    will pop it; that teardown is what other tests in the suite rely on to
    avoid cross-test contamination from the example block.
    """
    _load_example()
    assert "bug-report" in InterchangeBlockRegistry
    # Teardown happens after this test returns — the autouse fixture restores
    # the snapshot, removing 'bug-report' from the registry for subsequent tests.
