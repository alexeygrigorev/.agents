---
name: release
description: Release the current project to its package registry and GitHub by bumping the version, pushing a tag, and letting CI publish. Works for any project (Python/PyPI, Rust/crates.io, Node/npm, etc.) that has a CI publish workflow keyed off `v*` tags.
allowed-tools: Bash(git *), Bash(gh *), Bash(make *), Bash(curl *), Bash(grep *), Bash(sed *)
---

# Release

Releasing means: bump the version, push a `v*` tag, write release notes. CI does the build and upload to whatever registry the project targets.

Required precondition: `.github/workflows/publish.yml` exists and triggers on `push: tags: ['v*']`. If it doesn't, install it first (for Python: use the `setup-pypi-ci` skill; for other ecosystems: model it on an existing project's workflow). Do not fall back to running a local publish command.

## Steps

1. Find the version source of truth. Common patterns:
   - Python (hatch): `<pkg>/__version__.py` — path in `[tool.hatch.version]` in `pyproject.toml`.
   - Python (static): `version =` in `pyproject.toml`.
   - Rust: `version =` in `Cargo.toml`.
   - Node: `"version":` in `package.json`.
   If the project has a `make release` target, it already knows the path.
2. Check the registry's current version. Examples:
   - PyPI: `curl -s https://pypi.org/pypi/<name>/json | python3 -c "import json,sys; print(json.load(sys.stdin)['info']['version'])"`
   - crates.io: `curl -s https://crates.io/api/v1/crates/<name> | python3 -c "import json,sys; print(json.load(sys.stdin)['crate']['max_version'])"`
   - npm: `npm view <name> version`
3. Bump the version in the source-of-truth file. Default to a patch bump unless the user says otherwise. The new version must be greater than what's on the registry — local files sometimes drift behind.
4. Commit pending implementation changes if any are still uncommitted.
5. Commit the version bump with message `Bump to X.Y.Z`.
6. Push to the default branch.
7. Tag and push: `git tag vX.Y.Z && git push origin vX.Y.Z`. If `make release` exists, prefer it — it derives the version from the file and tags automatically.
8. Watch the workflow:
   ```bash
   gh run watch $(gh run list --workflow=publish.yml --limit 1 --json databaseId -q '.[0].databaseId') --exit-status
   ```
9. Verify on the registry with the same command from step 2.
10. Create the GitHub release with real notes (see below).

## Release notes

Don't paste commit messages verbatim. Inspect the actual changes:

```bash
LAST=$(git tag --sort=-v:refname | head -n 2 | tail -n 1)
git log $LAST..HEAD --oneline
git diff $LAST..HEAD --stat
```

Read the meaningful diffs and summarize under headings like:

- new features
- bug fixes
- breaking changes
- infrastructure / publish changes

Then create the release:

```bash
gh release create vX.Y.Z --title "vX.Y.Z" --notes "$(cat <<'EOF'
## What's changed

- ...

## Install

\`\`\`
<ecosystem-appropriate install line>
\`\`\`
EOF
)"
```

Install-line examples: `pip install <name>==X.Y.Z`, `cargo add <name>@X.Y.Z`, `npm install <name>@X.Y.Z`.

## Tag convention

Always use the `v` prefix: `v0.1.0`, not `0.1.0`. The standard publish workflow's tag filter is `v*` and its version-check step strips the leading `v` before comparing against the source-of-truth version.

## When CI fails

- Version-mismatch error — the tag and the version file disagree. Fix one or retag.
- Auth failure from the registry — confirm the publish credential is set as a repo secret (`gh secret list`). For PyPI: `PYPI_API_TOKEN`. For crates.io: `CARGO_REGISTRY_TOKEN`. For npm: `NPM_TOKEN`.
- Build hook needs external tooling (npm/node for a Python labextension, system libs for a Rust crate). Prebuilt artifacts should be committed, or the workflow needs the toolchain installed before build.

If CI succeeded but the release notes are wrong, `gh release edit vX.Y.Z --notes "..."`.

## Don't

- Don't run a local publish command (`hatch publish`, `uv publish`, `twine upload`, `cargo publish`, `npm publish`, etc.). CI is the only path. Local tokens exist for emergency recovery only.
- Don't tag before verifying the source-of-truth version matches what you want to publish.
- Don't try to delete and re-upload a version on a public registry — most registries forbid it. Bump and re-release.
