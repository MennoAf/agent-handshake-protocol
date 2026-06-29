"""Canonical hardcoded secret-scan floor shared by every Diplomat tier.

This is the single source of truth for the secret patterns that *both* the v0
handshake skill/CLI and the v1 Diplomat agent enforce on outbound text and
peer-supplied inbound text. The doctrine is that an SoW may *tighten* this
floor but can never loosen it — so the floor lives here, in the shared
wire-protocol package, where every tier imports the exact same patterns and
the two sides can never drift apart.

History: before this module existed the floor was duplicated three times — as
prose in ``diplomat/SKILL.md``, as code in the v0 CLI, and as code in the v1
agent's Methodist checker. The three copies drifted: the v0 docs carried a
generic credential catch-all and a PGP-capable private-key pattern the v1 code
lacked, while the v1 code carried AWS-secret-key, ``ghs_`` and OpenAI-legacy
patterns the v0 docs lacked. This module is the *union* of those sets, so no
real secret that any tier historically caught is lost.

Leak-safety: the scan helpers return only *pattern names*, never the matched
content. Callers that surface a hit to a human must keep it that way.

Design note — the ``sk-`` family uses the precise key shapes (Anthropic
``sk-ant-…``, OpenAI legacy ``…T3BlbkFJ…``, OpenAI ``sk-proj-…``) rather than a
broad ``sk-[A-Za-z0-9]{32,}`` catch-all. The broad form matched any ``sk-``
followed by 32 alphanumerics (a false-positive magnet in diffs and base64
blobs); the precise set covers every real current key format without the noise.
"""

from __future__ import annotations

import re

# Broadened from the v1 enumeration (RSA/OPENSSH/EC/DSA) to the v0 ``[A-Z ]*``
# form so it also catches PGP and bare PKCS#8 ``-----BEGIN PRIVATE KEY-----``.
SSH_PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
AWS_ACCESS_KEY = re.compile(r"AKIA[0-9A-Z]{16}")
AWS_SECRET_KEY = re.compile(r"(?i)aws[^'\"]*['\"][0-9a-zA-Z/+=]{40}['\"]")
ANTHROPIC_KEY = re.compile(r"sk-ant-(?:api|admin)\d{2}-[A-Za-z0-9_-]{32,}")
OPENAI_KEY_LEGACY = re.compile(r"sk-[A-Za-z0-9]{20,}T3BlbkFJ[A-Za-z0-9]{20,}")
OPENAI_KEY_NEW = re.compile(r"sk-proj-[A-Za-z0-9_-]{20,}")
GITHUB_TOKEN = re.compile(r"gh[ps]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{48,}")
# Generic credential catch-all from the v0 floor: a credential-ish key, an
# assignment, then 8+ non-space characters.
GENERIC_CREDENTIAL = re.compile(
    r"(?i)(?:password|secret|token|api[_-]?key)\s*[:=]\s*\S{8,}"
)

# Insertion order is the scan order. Pattern names are part of the contract —
# they appear in CommitResult.rejection_detail and Methodist violation details —
# so renaming a key is a wire-visible change. Add, don't rename.
SECRET_FLOOR_PATTERNS: dict[str, re.Pattern[str]] = {
    "ssh_private_key": SSH_PRIVATE_KEY,
    "aws_access_key": AWS_ACCESS_KEY,
    "aws_secret_key": AWS_SECRET_KEY,
    "anthropic_key": ANTHROPIC_KEY,
    "openai_key_legacy": OPENAI_KEY_LEGACY,
    "openai_key_new": OPENAI_KEY_NEW,
    "github_token": GITHUB_TOKEN,
    "generic_credential": GENERIC_CREDENTIAL,
}


def scan_text(text: str) -> list[str]:
    """Return the names of every floor pattern that matches ``text``.

    Leak-safe: returns pattern *names* only, never the matched content. Returns
    an empty list for non-``str`` input so callers can scan heterogeneous
    fields without pre-checking types.
    """
    if not isinstance(text, str):
        return []
    return [name for name, pattern in SECRET_FLOOR_PATTERNS.items() if pattern.search(text)]


def contains_secret(text: str) -> bool:
    """True if ``text`` matches any floor pattern. Leak-safe convenience wrapper."""
    return bool(scan_text(text))
