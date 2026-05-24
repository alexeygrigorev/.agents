---
name: setup-pypi-ci
description: Add the standardized CI publish workflow (`.github/workflows/publish.yml` + `make release`) to an existing Python project so PyPI releases happen on tag push. Use when a project still publishes via a local script (`publish.py`, `hatch publish`, `twine upload`) or has no automated publish at all.
---

# Setup PyPI CI

After this skill: release = bump version → commit → push → `make release`. CI builds and uploads.

## Steps

1. Copy `publish.yml` to `.github/workflows/publish.yml`.
2. Merge the targets from `Makefile` into the project's Makefile. Replace `<pkg>` with the actual package directory (use `src/<pkg>` if applicable).
3. Set the PyPI token secret:
   ```bash
   PYPI_TOKEN=$(grep "^password" ~/.pypirc | head -1 | sed 's/password = //')
   gh secret set PYPI_API_TOKEN --body "$PYPI_TOKEN"
   ```
4. Commit and push.

Use the `release` skill to cut the first version.
