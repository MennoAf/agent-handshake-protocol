"""Portable wire-protocol types for cross-agent INTERCHANGE communication.

Pydantic v2 models for the polymorphic InterchangeBlock primitive plus the
Diplomat commit/digest vocabulary. No framework coupling — depends only on
pydantic. Any agent that wants to speak the handshake protocol imports from
here.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_serializer
from pydantic_core import PydanticUndefined

# ---------------------------------------------------------------------------
# Interchange Block Base Class + Registry
# ---------------------------------------------------------------------------


class InterchangeBlock(BaseModel):
    """Base class for polymorphic interchange blocks.

    Concrete subclasses narrow ``type`` to a string literal and register
    themselves via ``@register_interchange_block`` decorator. Extra fields
    are forbidden at the trust boundary — unknown keys raise a ValidationError
    rather than being silently stripped.
    """

    model_config = ConfigDict(extra="forbid")

    type: str
    schema_version: int = 1

    @model_serializer(mode="wrap")
    def _serialize_with_subclass_fields(self, handler: Any) -> dict[str, Any]:
        """Include all concrete subclass fields when serializing.

        Pydantic v2 serializes ``list[InterchangeBlock]`` using the base-class
        schema, which drops subclass-only fields. The wrap serializer patches
        the output dict with any field that the base handler omitted — so
        round-trip through ``model_dump()`` / ``model_validate()`` is lossless.
        """
        base_dict = handler(self)
        for field_name in type(self).model_fields:
            if field_name not in base_dict:
                base_dict[field_name] = getattr(self, field_name)
        return base_dict


InterchangeBlockRegistry: dict[str, type[InterchangeBlock]] = {}


def register_interchange_block(
    cls: type[InterchangeBlock],
) -> type[InterchangeBlock]:
    """Decorator to register an InterchangeBlock subclass.

    Reads the ``type`` literal default from the class and stores it in the
    registry for polymorphic deserialization. Raises ValueError if the type
    is already registered to a different class (idempotent re-registration
    of the same class is allowed).

    Args:
        cls: The InterchangeBlock subclass to register.

    Returns:
        The class itself, allowing use as a decorator.

    Raises:
        ValueError: If the type string is already registered to a different class.
    """
    type_str = cls.model_fields["type"].default
    if type_str is None or type_str is PydanticUndefined:
        raise ValueError(
            f"{cls.__name__}: 'type' field has no Literal default value"
        )

    existing = InterchangeBlockRegistry.get(type_str)
    if existing is not None and existing is not cls:
        raise ValueError(
            f"Type '{type_str}' already registered to {existing.__name__}; "
            f"cannot register {cls.__name__}"
        )

    InterchangeBlockRegistry[type_str] = cls
    return cls


def resolve_interchange_blocks(v: object) -> object:
    """Deserialize raw dicts into their concrete InterchangeBlock subclasses.

    Looks up each dict's ``type`` key in the registry and parses through
    the matching subclass so subclass-specific fields are preserved.

    Args:
        v: The value to resolve. If not a list, returned unchanged.

    Returns:
        The resolved list of InterchangeBlock instances, or the input unchanged.

    Raises:
        ValueError: If a block is missing the 'type' field or has an unknown type.
    """
    if not isinstance(v, list):
        return v
    out = []
    for item in v:
        if isinstance(item, InterchangeBlock):
            out.append(item)
            continue
        if not isinstance(item, dict):
            # Let Pydantic surface the type error downstream.
            out.append(item)
            continue
        type_str = item.get("type")
        if type_str is None:
            raise ValueError("interchange block missing 'type' field")
        subclass = InterchangeBlockRegistry.get(type_str)
        if subclass is None:
            raise ValueError(f"unknown interchange block type: {type_str!r}")
        out.append(subclass.model_validate(item))
    return out


# ---------------------------------------------------------------------------
# Diplomat handshake vocabulary — CommitIntent / CommitResult / InboundDigest
# ---------------------------------------------------------------------------


class SoWPeerTier(StrEnum):
    """Peer install trust tier, declared per identity in the SoW.

    Diplomat reads peer tier on every operation to decide between
    PARANOID (asymmetric) and SYMMETRIC code paths. Default if
    unspecified in the SoW is ``skill`` — conservative.
    """

    AGENT = "agent"
    SKILL = "skill"
    MANUAL = "manual"


class CommitVerdict(StrEnum):
    """Outcome of a CommitIntent processed by Diplomat."""

    COMMITTED = "COMMITTED"
    REJECTED = "REJECTED"


class RejectionReason(StrEnum):
    """The eight rejection reasons Diplomat can emit on a rejected commit.

    Mirrored from PRD §V1 INTERCHANGE schemas (commit-result block) plus
    TIER_MISMATCH (PRD §Tier downgrade detection). Methodist's deterministic
    checkers emit values from this vocabulary when they resolve the outcome
    inline.
    """

    SOW_STALE = "SOW_STALE"
    SOW_HASH_MISMATCH = "SOW_HASH_MISMATCH"
    CLAIM_EXPIRED = "CLAIM_EXPIRED"
    CLAIM_NOT_HELD = "CLAIM_NOT_HELD"
    SECRET_DETECTED = "SECRET_DETECTED"
    SCOPE_VIOLATION = "SCOPE_VIOLATION"
    PUSH_CONFLICT_UNRESOLVED = "PUSH_CONFLICT_UNRESOLVED"
    TIER_MISMATCH = "TIER_MISMATCH"


class DigestConfidence(StrEnum):
    """Confidence flag on an inbound digest.

    ``NO_OP`` is the heuristic-gate output emitted when no semantic content
    has changed since the last digest (cost gate per Pinch).
    """

    CLEAN = "CLEAN"
    FLAGGED_UNTRUSTED = "FLAGGED_UNTRUSTED"
    SUSPICIOUS = "SUSPICIOUS"
    NO_OP = "NO_OP"


@register_interchange_block
class CommitIntent(InterchangeBlock):
    """Coding agent → Diplomat: a request to commit + push.

    Per PRD §V1 Outbound, Diplomat runs SoW check, secret scan, and scope
    check against this block before performing the commit. Diplomat does
    NOT semantically verify that the diff matches ``intent`` in V1 — that
    is the V2 semantic-diff-verification feature.
    """

    type: Literal["commit-intent"] = "commit-intent"
    intent: str = Field(max_length=500)
    files_changed: list[str]
    claim_id: str
    scope_assertion: str


@register_interchange_block
class CommitResult(InterchangeBlock):
    """Diplomat → coding agent: outcome of a CommitIntent.

    On ``COMMITTED``, ``commit_sha`` is populated and the rejection fields
    are ``None``. On ``REJECTED``, ``rejection_reason`` + ``rejection_detail``
    + ``recovery_action`` are populated and ``commit_sha`` is ``None``.

    For ``SECRET_DETECTED`` rejections, ``rejection_detail`` carries the
    pattern that matched but never the matched content (PRD §V1 INTERCHANGE
    schemas commit-result block).
    """

    type: Literal["commit-result"] = "commit-result"
    verdict: CommitVerdict
    consumes: str
    commit_sha: str | None = None
    rejection_reason: RejectionReason | None = None
    rejection_detail: str | None = None
    recovery_action: str | None = None


@register_interchange_block
class InboundDigest(InterchangeBlock):
    """Diplomat → coding agent: structured summary of peer-side changes.

    The coding agent never reads ``.handshake/v0/*`` directly; this block
    is the only structured inbound state surface for handshake artifacts
    (PRD §V1 Inbound). ``operator_action_required`` is true when
    ``confidence == SUSPICIOUS``.
    """

    type: Literal["inbound-digest"] = "inbound-digest"
    confidence: DigestConfidence
    since_digest: datetime
    files_changed: list[str]
    claim_changes: list[str] = Field(default_factory=list)
    sow_amendments: list[str] = Field(default_factory=list)
    summary: str = Field(max_length=1000)
    operator_action_required: bool = False
