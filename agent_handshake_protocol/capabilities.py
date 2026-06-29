"""Capability + protocol-version negotiation vocabulary for the SoW.

The Statement of Work already declares a per-identity *trust* tier
(``peer_tier``). This module adds the parallel *capability* axis: what each
party can actually DO, announced per identity, plus the protocol version each
party speaks. Both are **advisory** in this release — a peer reads them to
detect version skew or a missing feature, but nothing *gates* on them yet.
Gating on a declared capability is a deliberate follow-on; landing the
negotiation substrate first means no code depends on the new fields before
they are observed in the wild.

Single source of truth: the ``Capability`` vocabulary and the
``parse_capabilities`` coercion live here, in the shared wire-protocol package,
so the v0 handshake skill/CLI and the v1 Diplomat agent can never drift on what
a capability string means — the same doctrine that moved the secret floor into
``secret_floor``.
"""

from __future__ import annotations

import logging
from enum import StrEnum

logger = logging.getLogger(__name__)

# The protocol-contract version each party announces in the SoW. Distinct from
# the SoW *document* version (``version: 1``) and from the package distribution
# ``__version__``: this is the wire/negotiation contract level. Bump it when the
# negotiated vocabulary changes. A literal (not derived from importlib.metadata)
# so negotiation never depends on the distribution being resolvable at runtime.
PROTOCOL_VERSION = "0.4.0"


class Capability(StrEnum):
    """A capability a SoW party announces it supports.

    Values are kebab-case and, where a capability corresponds to an
    ``InterchangeBlock``, match that block's ``type`` string (e.g.
    ``inbound-digest``). Capability names are part of the contract once
    shipped — additive only, never rename (the same rule the secret-floor
    pattern names follow, since they surface to peers and operators).

    The initial set names the real differentiators between tiers:
      - ``commit-interchange`` — speaks the CommitIntent/CommitResult vocabulary.
      - ``inbound-digest`` — emits/consumes structured InboundDigest blocks
        (the v1 agent does; a heuristic v0 skill may not).
      - ``ephemeral-scope`` — supports per-branch declared scope for EXTERNAL
        mode (V1.5).
      - ``tier-negotiation`` — honours ``peer_tier`` and runs tier-downgrade
        detection.
      - ``capability-negotiation`` — reads/writes this very capability surface.
    """

    COMMIT_INTERCHANGE = "commit-interchange"
    INBOUND_DIGEST = "inbound-digest"
    EPHEMERAL_SCOPE = "ephemeral-scope"
    TIER_NEGOTIATION = "tier-negotiation"
    CAPABILITY_NEGOTIATION = "capability-negotiation"


def parse_capabilities(raw: object) -> list[Capability]:
    """Coerce a raw announced-capability list into known ``Capability`` values.

    Postel posture: liberal on receive. Unknown capability strings — a newer
    peer announcing a feature this build does not model — are **dropped** and
    logged at WARNING, neither retained nor raised. Capabilities are advisory
    this release, so a capability we do not understand is one we simply cannot
    act on; surfacing it in logs keeps the drift observable (the same
    warn-on-drop posture as ``InterchangeBlock``'s receive policy). Non-list
    input, or non-string entries, are treated as "nothing announced" with a
    warning rather than an exception — a malformed peer artifact must never
    take Diplomat down.

    Order is preserved and duplicates are collapsed.
    """
    if raw is None:
        return []
    if not isinstance(raw, list):
        logger.warning(
            "capabilities must be a list; got %s", type(raw).__name__
        )
        return []
    known: list[Capability] = []
    unknown: list[str] = []
    for item in raw:
        try:
            cap = Capability(item)
        except ValueError:
            unknown.append(str(item))
            continue
        if cap not in known:
            known.append(cap)
    if unknown:
        logger.warning(
            "dropping unknown capabilities: %s", sorted(set(unknown))
        )
    return known
