---
name: init-library
description: Initialize a new Python library with modern tooling, packaging, tests, and optional CLI support. Use when the user wants to scaffold a new Python package.
allowed-tools: Bash(uv *), Bash(git *), Bash(make *), Bash(mkdir *), Bash(touch *), Bash(ls *)
---

# Init Library

Initialize a new Python library with modern tooling.

## Ask the User

Before starting, ask:

1. Library name
2. Short description
3. Runtime dependencies
4. Whether the package should install a CLI executable

## Target Structure

```text
<library_name>/
├── <library_name>/
│   ├── __init__.py
│   ├── cli.py
│   └── __version__.py
├── tests/
│   └── __init__.py
├── .github/
│   └── workflows/
│       ├── test.yml
│       └── publish.yml
├── Makefile
├── pyproject.toml
├── README.md
├── .gitignore
├── .python-version
└── uv.lock
```

## Build Configuration

Use this `pyproject.toml` shape:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "<library_name>"
description = "<description>"
readme = "README.md"
license = {text = "WTFPL"}
requires-python = ">=3.10"
dynamic = ["version"]

dependencies = [
    # Add runtime dependencies here
]

authors = [
    {name = "<your-name>", email = "<your-email>"}
]

[dependency-groups]
dev = [
    "hatch",
    "pytest",
    "pytest-cov",
    "ruff",
]

[tool.hatch.build.targets.wheel]
packages = ["<library_name>"]

[tool.hatch.version]
path = "<library_name>/__version__.py"

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py310"
```

If the package should expose a CLI, add:

```toml
[project.scripts]
<library_name> = "<library_name>.cli:main"
```

## Default Files

`__version__.py`:

```python
__version__ = "0.0.1"
```

`cli.py` template when a CLI is requested:

```python
import argparse


def main():
    parser = argparse.ArgumentParser(description="<description>")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()
    print("Hello from <library_name>!")


if __name__ == "__main__":
    main()
```

`Makefile`:

```makefile
.PHONY: test setup shell coverage publish-build publish-clean release

test:
	uv run pytest

setup:
	uv sync --dev

shell:
	uv shell

coverage:
	uv run pytest --cov=<library_name> --cov-report=term-missing

publish-build:
	uv run hatch build

publish-clean:
	rm -r dist/

# Release: tag the current version and push to trigger CI publish.
# CI workflow: .github/workflows/publish.yml (on tag push v*)
release:
	@VERSION=$$(grep -E "^__version__" <library_name>/__version__.py | sed -E "s/.*['\"]([^'\"]+)['\"].*/\1/"); \
	echo "Releasing v$$VERSION"; \
	git tag "v$$VERSION"; \
	git push origin "v$$VERSION"
```

`.github/workflows/publish.yml`:

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

After the repo is on GitHub, set the PyPI token secret once:

```bash
PYPI_TOKEN=$(grep "^password" ~/.pypirc | head -1 | sed 's/password = //')
gh secret set PYPI_API_TOKEN --body "$PYPI_TOKEN"
```

Releasing then becomes: bump `__version__.py`, commit, push, and `make release` (or `git tag vX.Y.Z && git push origin vX.Y.Z`). See the `release` skill for the full flow including GitHub release notes.

`.python-version`:

```text
3.13
```

## After Creating Files

Run:

```bash
uv sync --dev
```

Then verify the scaffold with at least one basic test run path, and keep the generated project consistent with the user's answers.
