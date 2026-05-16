"""Portable wire-protocol types for the agent-handshake / Diplomat ecosystem."""

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

__all__ = [
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
