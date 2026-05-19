# Releasing `agent-handshake-protocol`

Manual release SOP. Automation is a future concern; the goal here is repeatability without ambiguity.

V1 distribution is **tagged GitHub releases**. PyPI publish is a future candidate (see the PRD Out-of-scope and the appendix at the bottom of this file). Consumers install via `git+https://github.com/MennoAf/agent-handshake-protocol.git@v<VERSION>` URLs from their `pyproject.toml`.

## Pre-release checklist

- [ ] `pyproject.toml` `version` matches the intended release (e.g. `0.1.0`).
- [ ] `git status` is clean.
- [ ] `uv run pytest tests/ -q` exits 0.
- [ ] `CHANGELOG.md` (if present) reflects the changes since the last tag.
- [ ] `main` is pushed to `origin`. Tag will be cut against that commit.

## Release steps (V1 — GitHub-tag distribution)

1. **Tag the release:**

   ```
   git tag -a v<VERSION> -m "Release <VERSION>"
   git push origin v<VERSION>
   ```

   Verify the tag is visible on the remote:

   ```
   git ls-remote --tags origin v<VERSION> | grep -q refs/tags/v<VERSION>
   ```

2. **Verify install from a clean venv:**

   ```
   uv venv /tmp/ahp-smoke
   /tmp/ahp-smoke/bin/uv pip install "agent-handshake-protocol @ git+https://github.com/MennoAf/agent-handshake-protocol.git@v<VERSION>"
   /tmp/ahp-smoke/bin/python -c "from agent_handshake_protocol import CommitIntent, SoWPeerTier, __version__; assert __version__ == '<VERSION>'"
   ```

   All three lines must exit 0.

3. **(Optional) Create a GitHub Release entry** at `https://github.com/MennoAf/agent-handshake-protocol/releases/new?tag=v<VERSION>` with the changelog summary. The git tag IS the release contract; the GitHub Release entry is just human-facing surface.

## Post-release

- [ ] Bump `version` in `pyproject.toml` to the next dev marker (e.g. `0.1.1.dev0`) — keeps `__version__` honest in development between releases.
- [ ] Open a PR in each downstream consumer (Mentarchy, agent_builder) bumping the `tag = "v<VERSION>"` value in their `[tool.uv.sources]` block.

## Rollback

Tags on GitHub *can* be deleted and re-cut, but downstream consumers who pinned the tag will see their lockfile resolve to a different commit on next `uv sync` — which is exactly the same trust failure PyPI version burns prevent. So treat tags as immutable in practice:

1. If a release ships broken, do NOT delete-and-retag `v<VERSION>`. Cut `v<VERSION>+1` with the fix.
2. Optional: edit the GitHub Release entry for `v<VERSION>` to mark it as "yanked / see v<VERSION>+1" so humans don't pin to it.

If you absolutely must delete a tag (e.g. it leaked a secret), notify every known consumer before deleting `origin`'s tag — lockfile divergence will silently confuse anyone who already pinned it.

## Appendix — PyPI publish (deferred until V2 candidate triggers)

PyPI is not used for V1. Re-enable this section when (a) a non-friendly third-party adopter needs `pip install agent-handshake-protocol` without a git-source override, or (b) a CI environment cannot reach GitHub from its package-resolution path.

Pre-conditions when bringing PyPI up:

- [ ] You hold a PyPI API token for the `agent-handshake-protocol` project (stored outside the repo).

Steps:

1. **Build wheels + sdist:**

   ```
   rm -rf dist/
   uv build
   ```

2. **Publish to PyPI:**

   ```
   uv publish --token "$PYPI_TOKEN"
   ```

   (Or use `UV_PUBLISH_TOKEN` env var, or `~/.pypirc`. Never commit the token.)

3. **Verify install from a clean venv against PyPI:**

   ```
   uv venv /tmp/ahp-smoke-pypi
   /tmp/ahp-smoke-pypi/bin/uv pip install agent-handshake-protocol==<VERSION>
   /tmp/ahp-smoke-pypi/bin/python -c "from agent_handshake_protocol import CommitIntent, SoWPeerTier, __version__; assert __version__ == '<VERSION>'"
   ```

PyPI rollback constraints (do not allow re-uploading the same version after deletion — the version string is permanently burned) still apply if PyPI ever becomes the primary distribution.
