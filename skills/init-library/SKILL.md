---
name: init-library
description: Initialize a new Python library with modern tooling, packaging, tests, and optional CLI support. Use when the user wants to scaffold a new Python package.
---

# Init Library

## Ask the user

1. Library name
2. Short description
3. Runtime dependencies
4. Whether the package should install a CLI executable

## Scaffold

Create:

```text
<library_name>/
├── <library_name>/__init__.py
├── <library_name>/__version__.py        # __version__ = "0.0.1"
├── <library_name>/cli.py                # only if CLI requested — see cli.py
├── tests/__init__.py
├── pyproject.toml                       # see pyproject.toml
├── Makefile                             # see Makefile
├── README.md
├── .gitignore
├── .python-version                      # 3.13
└── uv.lock
```

Substitute `<library_name>` and `<description>` throughout. If no CLI was requested, drop `cli.py` and the `[project.scripts]` block in `pyproject.toml`.

Then run `uv sync --dev` and confirm `uv run pytest` works on an empty test.

## Publish setup

After the repo is on GitHub, run the `setup-pypi-ci` skill to add the CI publish workflow and `make release` target.
