"""Portable wire-protocol types for the agent-handshake / Diplomat ecosystem."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from agent_handshake_protocol.contracts import (
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

try:
    __version__: str = _pkg_version("agent-handshake-protocol")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = [
    "__version__",
    "CommitIntent",
    "CommitResult",
    "CommitVerdict",
    "DigestConfidence",
    "InboundDigest",
    "InterchangeBlock",
    "InterchangeBlockRegistry",
    "RejectionReason",
    "SoWPeerTier",
    "register_interchange_block",
    "resolve_interchange_blocks",
]
