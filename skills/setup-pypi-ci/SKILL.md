---
name: setup-pypi-ci
description: Add the standardized CI publish workflow (`.github/workflows/publish.yml` + `make release`) to an existing Python project so PyPI releases happen on tag push. Use when a project still publishes via a local script (`publish.py`, `hatch publish`, `twine upload`) or has no automated publish at all.
---

# Setup PyPI CI

Migrate an existing Python project to the standardized CI-based publish flow. After this skill runs, releasing means: bump version → commit → push → `make release`. CI handles build + upload.

## Preconditions

- Project is a hatch-based Python package (`pyproject.toml` has `build-backend = "hatchling.build"` and `[tool.hatch.version]` pointing to `<pkg>/__version__.py`).
- Repo is on GitHub and `gh` is authenticated.
- User has a PyPI API token in `~/.pypirc` (or will provide one).

If the project uses a different build backend, adapt the build step — the version-check and publish steps stay the same.

## Steps

### 1. Add the publish workflow

Create `.github/workflows/publish.yml`:

```yaml
name: Publish

on:
  push:
    tags:
      - "v*"
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: astral-sh/setup-uv@v6
      - run: uv build
      - name: Verify version matches tag
        if: startsWith(github.ref, 'refs/tags/v')
        run: |
          TAG="${GITHUB_REF#refs/tags/v}"
          if ! ls dist/ | grep -qE -- "-${TAG}(-|\.)"; then
            echo "::error::dist/ contents do not match tag v${TAG}"
            ls dist/
            exit 1
          fi
      - uses: actions/upload-artifact@v5
        with:
          name: dist
          path: dist/*

  publish-pypi:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v5
        with:
          name: dist
          path: dist
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}
```

### 2. Set the PyPI token secret

Reuse the user's global token, or have them generate a project-scoped one on pypi.org:

```bash
PYPI_TOKEN=$(grep "^password" ~/.pypirc | head -1 | sed 's/password = //')
gh secret set PYPI_API_TOKEN --body "$PYPI_TOKEN"
gh secret list   # confirm
```

### 3. Replace the local publish path in the Makefile

Remove `publish` and `publish-test` targets (the ones that call `hatch publish` / `twine upload`). Keep `publish-build` (useful for local testing) and `publish-clean`. Add a `release` target that tags from `__version__.py`:

```makefile
.PHONY: publish-build publish-clean release

publish-build:
	uv run hatch build

publish-clean:
	rm -r dist/

# Release: tag the current version and push to trigger CI publish.
# CI workflow: .github/workflows/publish.yml (on tag push v*)
release:
	@VERSION=$$(grep -E "^__version__" <pkg>/__version__.py | sed -E "s/.*['\"]([^'\"]+)['\"].*/\1/"); \
	echo "Releasing v$$VERSION"; \
	git tag "v$$VERSION"; \
	git push origin "v$$VERSION"
```

For projects with the package under `src/<pkg>/`, point the path at `src/<pkg>/__version__.py`.

### 4. Delete legacy publish scripts

Common offenders:

- `publish.py` (at repo root or `scripts/publish.py`)
- `release.sh`, `publish.sh`

Remove them. Their logic is now in the workflow + `make release`.

### 5. Reconcile drift between local and PyPI

It's common for `__version__.py` to lag behind what's actually on PyPI (someone published manually without bumping the local file). Before tagging:

```bash
LOCAL=$(grep '^__version__' <pkg>/__version__.py | sed -E "s/.*['\"]([^'\"]+).*/\1/")
PYPI=$(curl -s https://pypi.org/pypi/<pkg-name>/json | python3 -c "import json,sys; print(json.load(sys.stdin)['info']['version'])")
echo "local: $LOCAL, pypi: $PYPI"
```

If local ≤ pypi, bump local above pypi before tagging.

### 6. Commit, push, and do a verification release

```bash
git add .github/workflows/publish.yml Makefile <pkg>/__version__.py
git rm publish.py 2>/dev/null
git commit -m "Switch to CI-based publish on tag push"
git push
make release   # or: git tag vX.Y.Z && git push origin vX.Y.Z
gh run watch $(gh run list --workflow=publish.yml --limit 1 --json databaseId -q '.[0].databaseId') --exit-status
curl -s https://pypi.org/pypi/<pkg-name>/json | python3 -c "import json,sys; print(json.load(sys.stdin)['info']['version'])"
```

Then write release notes with `gh release create vX.Y.Z --title "vX.Y.Z" --notes "..."` — see the `release` skill.

## Notes

- Tags must use the `v` prefix (`v0.1.0`). The workflow strips it before comparing against the package version.
- The build job runs `uv build`, which uses the project's declared `build-backend` (usually hatchling). No separate hatch install needed in CI.
- For Jupyter-builder / npm-based extensions: commit the prebuilt files so the `skip-if-exists` build hook short-circuits in CI. Don't make CI run `jlpm` / `npm install`.
- Don't try to use Trusted Publishing (OIDC) unless you've configured a trusted publisher on PyPI for this exact repo + workflow path + environment. Until then, stick with the API token.
