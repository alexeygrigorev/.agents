---
name: release
description: Release the current project to its package registry and GitHub by bumping the version, pushing a tag, and letting CI publish. Works for any project (Python/PyPI, Rust/crates.io, Node/npm, etc.) that has a CI publish workflow keyed off `v*` tags.
---

# Release

Requires `.github/workflows/publish.yml` that triggers on `v*` tag push. For Python, install it with the `setup-pypi-ci` skill if missing.

## Steps

1. Bump the version in the source-of-truth file (e.g. `<pkg>/__version__.py`, `Cargo.toml`, `package.json`). Default to a patch bump. Make sure it's greater than what's currently on the registry.
2. Commit: `Bump to X.Y.Z`. Push to the default branch.
3. Tag and push: `git tag vX.Y.Z && git push origin vX.Y.Z` (or `make release` if available).
4. Watch the workflow:
   ```bash
   gh run watch $(gh run list --workflow=publish.yml --limit 1 --json databaseId -q '.[0].databaseId') --exit-status
   ```
5. Write the GitHub release notes: inspect `git log <prev-tag>..HEAD --oneline` and the diff, summarize the meaningful changes, then `gh release create vX.Y.Z --title "vX.Y.Z" --notes "..."` (or `gh release edit` if CI already opened one). Include an install line for the ecosystem.
