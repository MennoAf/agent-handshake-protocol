"""Portable wire-protocol types for cross-agent INTERCHANGE communication.

Pydantic v2 models for the polymorphic InterchangeBlock primitive plus the
Diplomat commit/digest vocabulary. No framework coupling — depends only on
pydantic. Any agent that wants to speak the handshake protocol imports from
here.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator
from pydantic_core import PydanticUndefined

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Interchange Block Base Class + Registry
# ---------------------------------------------------------------------------


class InterchangeBlock(BaseModel):
    """Abstract base class for polymorphic interchange blocks.

    Concrete subclasses narrow ``type`` to a string literal default (e.g.
    ``type: Literal["my-block"] = "my-block"``) and register themselves via
    the ``@register_interchange_block`` decorator. Direct instantiation of
    ``InterchangeBlock`` itself is rejected — use a subclass.

    Receive-policy posture (Postel): the base class is configured with
    ``extra="ignore"`` so that newer peers can add fields without breaking
    older consumers. A ``model_validator(mode="before")`` captures unknown
    keys and logs them at WARNING level via the ``agent_handshake_protocol``
    logger before Pydantic strips them — silent drops are the failure mode
    this avoids. See ``docs/COMPATIBILITY.md`` for the full receive/send
    policy and the firewall doctrine.
    """

    model_config = ConfigDict(extra="ignore")

    type: str
    schema_version: int = Field(default=1, ge=1, le=65535)

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        # Force subclasses to declare a non-empty Literal default on `type`.
        # The decorator that registers blocks reads model_fields["type"].default,
        # so a subclass that forgets to override `type` would silently inherit
        # the base's open `str` declaration and become un-registerable.
        #
        # Uses Pydantic's hook (not Python's __init_subclass__) because Pydantic
        # populates model_fields AFTER __init_subclass__ runs in the metaclass
        # chain — so at __init_subclass__ time the subclass's narrowed `type`
        # default is not yet visible.
        super().__pydantic_init_subclass__(**kwargs)
        type_field = cls.model_fields.get("type")
        if type_field is None:
            return
        default = type_field.default
        if default is PydanticUndefined or default is None or default == "":
            raise TypeError(
                f"InterchangeBlock subclass {cls.__name__!r} must declare "
                f"`type` with a non-empty Literal default, e.g. "
                f'`type: Literal["my-block"] = "my-block"`. '
                f"Got default={default!r}."
            )

    @model_validator(mode="before")
    @classmethod
    def _warn_on_unknown_fields(cls, data: Any) -> Any:
        """Log a WARNING when a peer sends fields this consumer doesn't know.

        Pydantic ``extra="ignore"`` silently drops unknown keys, which makes
        schema drift between peers invisible. This validator runs first,
        compares input keys against declared fields, and emits a single
        WARNING per validation call with the model name and the dropped
        field names. Pydantic then performs the actual drop.
        """
        if isinstance(data, dict):
            declared = set(cls.model_fields.keys())
            extras = sorted(set(data.keys()) - declared)
            if extras:
                logger.warning(
                    "Dropping unknown fields on %s: %s",
                    cls.__name__,
                    extras,
                )
        return data

    @model_validator(mode="after")
    def _block_direct_base_instantiation(self) -> InterchangeBlock:
        """Refuse to construct a bare InterchangeBlock (abstract-base guard).

        Without this guard, ``InterchangeBlock.model_validate({"type": "x"})``
        returns a degenerate object that passes type checks but carries none
        of any concrete subclass's fields. Subclasses bypass this guard
        because ``type(self)`` differs from ``InterchangeBlock``.
        """
        if type(self) is InterchangeBlock:
            raise ValueError(
                "InterchangeBlock is abstract; instantiate a concrete subclass "
                "(CommitIntent, CommitResult, InboundDigest, or your own "
                "@register_interchange_block subclass — see examples/custom_block.py)."
            )
        return self

    @model_serializer(mode="wrap")
    def _serialize_with_subclass_fields(self, handler: Any) -> dict[str, Any]:
        """Include all concrete-subclass declared fields when serializing.

        Pydantic v2 serializes ``list[InterchangeBlock]`` using the base-class
        schema, which drops subclass-only fields. This wrap serializer patches
        the output dict with any field that the base handler omitted — so
        round-trip through ``model_dump()`` / ``model_validate()`` is lossless.

        Audit note (2026-05-19): the loop iterates ``type(self).model_fields``
        — Pydantic's *declared* fields registry — not ``__dict__`` or ``dir()``.
        Undeclared instance attributes therefore cannot leak onto the wire;
        the send-side posture is conservative by construction.
        """
        base_dict: dict[str, Any] = handler(self)
        for field_name in type(self).model_fields:
            if field_name not in base_dict:
                base_dict[field_name] = getattr(self, field_name)
        return base_dict


# Module-private mutable registry. Mutated only by ``register_interchange_block``.
# Tests that need to reset/restore registry state import this name directly
# (it's the only sanctioned mutation path outside the decorator). The public
# read-only view is exported as ``InterchangeBlockRegistry`` below.
_REGISTRY: dict[str, type[InterchangeBlock]] = {}

InterchangeBlockRegistry: Mapping[str, type[InterchangeBlock]] = MappingProxyType(_REGISTRY)
"""Public, read-only view of the registered InterchangeBlock subclasses.

Introspection (``"commit-intent" in InterchangeBlockRegistry``, ``.keys()``,
``.items()``, iteration) is supported. Direct mutation raises ``TypeError``
— all registration must go through ``@register_interchange_block``. This
closes the registry-hijack vector (audit 2026-05-19, Sieve MEDIUM)."""


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

    existing = _REGISTRY.get(type_str)
    if existing is not None and existing is not cls:
        raise ValueError(
            f"Type '{type_str}' already registered to {existing.__name__}; "
            f"cannot register {cls.__name__}"
        )

    _REGISTRY[type_str] = cls
    return cls


def resolve_interchange_blocks(v: object) -> list[InterchangeBlock] | object:
    """Deserialize raw dicts into their concrete InterchangeBlock subclasses.

    Looks up each dict's ``type`` key in the registry and parses through
    the matching subclass so subclass-specific fields are preserved.

    Args:
        v: The value to resolve. If not a list, returned unchanged.

    Returns:
        When ``v`` is a list, a ``list[InterchangeBlock]`` of resolved blocks
        (every element is a concrete InterchangeBlock subclass instance).
        Otherwise, ``v`` returned unchanged.

    Raises:
        ValueError: If a block dict is missing the 'type' field or has an
            unknown type string.
        TypeError: If the list contains an item that is neither a dict nor
            an existing InterchangeBlock instance. The error message includes
            the item's index and observed type. Strict on purpose: the input
            should be wire-shaped data, not an arbitrary mixed list.
    """
    if not isinstance(v, list):
        return v
    out: list[InterchangeBlock] = []
    for idx, item in enumerate(v):
        if isinstance(item, InterchangeBlock):
            out.append(item)
            continue
        if not isinstance(item, dict):
            raise TypeError(
                f"resolve_interchange_blocks: item at index {idx} is "
                f"{type(item).__name__}, expected dict or InterchangeBlock"
            )
        type_str = item.get("type")
        if type_str is None:
            raise ValueError("interchange block missing 'type' field")
        subclass = _REGISTRY.get(type_str)
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
