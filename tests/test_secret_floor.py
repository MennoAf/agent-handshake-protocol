"""Tests for the canonical secret-scan floor.

These lock the floor as the single source of truth shared by every Diplomat
tier: the exact pattern-name set (a wire-visible contract), that every
historical v0 and v1 pattern still fires, and that the scan helpers are
leak-safe (names only, never matched content).
"""

from __future__ import annotations

from agent_handshake_protocol import SECRET_FLOOR_PATTERNS, contains_secret, scan_text

# A real secret of each kind the floor must catch, keyed by the pattern name
# that should fire. Values are synthetic but structurally valid.
SAMPLES: dict[str, str] = {
    "ssh_private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\nabc",
    "aws_access_key": "AKIAIOSFODNN7EXAMPLE",
    "aws_secret_key": 'aws_secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"',
    "anthropic_key": "sk-ant-api03-" + "a" * 40,
    "openai_key_legacy": "sk-" + "a" * 24 + "T3BlbkFJ" + "b" * 24,
    "openai_key_new": "sk-proj-" + "a" * 32,
    "github_token": "ghp_" + "a" * 36,
    "generic_credential": "password = hunter2hunter2",
}


def test_pattern_name_set_is_the_contract() -> None:
    """The floor is exactly the union set. Add-don't-rename: this guards drift."""
    assert set(SECRET_FLOOR_PATTERNS) == {
        "ssh_private_key",
        "aws_access_key",
        "aws_secret_key",
        "anthropic_key",
        "openai_key_legacy",
        "openai_key_new",
        "github_token",
        "generic_credential",
    }


def test_every_sample_fires_its_pattern() -> None:
    for expected_name, sample in SAMPLES.items():
        hits = scan_text(sample)
        assert expected_name in hits, f"{expected_name} did not fire on its sample"


def test_v0_only_patterns_present() -> None:
    """Patterns the v1 code historically lacked must now fire (no coverage lost)."""
    # PGP/bare private keys (v1 only enumerated RSA/OPENSSH/EC/DSA).
    assert contains_secret("-----BEGIN PGP PRIVATE KEY-----")
    assert contains_secret("-----BEGIN PRIVATE KEY-----")
    # Generic credential catch-all (v1 had none).
    assert contains_secret("api_key: abcd1234efgh")
    assert contains_secret("SECRET=supersecretvalue")


def test_v1_only_patterns_present() -> None:
    """Patterns the v0 docs historically lacked must now fire (no coverage lost)."""
    # AWS secret key + ghs_ server token (v0 docs had neither).
    assert contains_secret('aws "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"')
    assert contains_secret("ghs_" + "z" * 36)


def test_clean_text_has_no_hits() -> None:
    for benign in [
        "Refactor the digest summarizer to lock Haiku 4.5",
        "files_changed: src/app.py, docs/readme.md",
        "the password reset flow needs a test",  # prose, no assignment -> no hit
        "",
    ]:
        assert scan_text(benign) == [], f"false positive on: {benign!r}"


def test_scan_is_leak_safe_returns_names_only() -> None:
    secret = "AKIAIOSFODNN7EXAMPLE"
    hits = scan_text(secret)
    assert hits == ["aws_access_key"]
    assert secret not in "".join(hits)


def test_non_str_input_is_empty() -> None:
    assert scan_text(None) == []  # type: ignore[arg-type]
    assert scan_text(12345) == []  # type: ignore[arg-type]
    assert contains_secret(None) is False  # type: ignore[arg-type]
