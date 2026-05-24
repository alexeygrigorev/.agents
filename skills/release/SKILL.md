---
name: release
description: Release the current package to PyPI and GitHub by bumping the version, tagging, and letting CI publish. Use when the user wants to ship the current project.
allowed-tools: Bash(git *), Bash(gh *), Bash(uv *), Bash(make *), Bash(curl *), Bash(grep *), Bash(sed *)
---

# Release

These projects publish to PyPI through a CI workflow at `.github/workflows/publish.yml` that fires on `v*` tag pushes. The releaser's job is to bump the version, push a tag, and write release notes. CI does the build and upload.

If `.github/workflows/publish.yml` does **not** exist, use the `setup-pypi-ci` skill first to install it. Do not fall back to local `hatch publish` / `twine upload`.

## Steps

1. **Identify the version file.** It's `<pkg>/__version__.py` for hatch projects (`grep '^\[tool.hatch.version\]' -A1 pyproject.toml` to confirm).
2. **Check what's on PyPI right now:**
   ```bash
   curl -s https://pypi.org/pypi/<pkg-name>/json | python3 -c "import json,sys; print(json.load(sys.stdin)['info']['version'])"
   ```
3. **Bump the version** in `__version__.py`. Default to a patch bump unless the user says otherwise. Make sure the new version is greater than what's on PyPI — local files sometimes drift behind.
4. **Commit any pending implementation changes** if they aren't committed yet.
5. **Commit the version bump.** Message: `Bump to X.Y.Z`.
6. **Push** to the default branch.
7. **Tag and push:** `git tag vX.Y.Z && git push origin vX.Y.Z`. If the project has a `make release` target, use it — it derives the version from the file and tags automatically.
8. **Watch the workflow:**
   ```bash
   gh run watch $(gh run list --workflow=publish.yml --limit 1 --json databaseId -q '.[0].databaseId') --exit-status
   ```
9. **Verify on PyPI:**
   ```bash
   curl -s https://pypi.org/pypi/<pkg-name>/json | python3 -c "import json,sys; print(json.load(sys.stdin)['info']['version'])"
   ```
10. **Create the GitHub release with real notes** (see below).

## Release notes

Don't just paste commit messages. Inspect the actual changes:

```bash
LAST=$(git tag --sort=-v:refname | head -n 2 | tail -n 1)
git log $LAST..HEAD --oneline
git diff $LAST..HEAD --stat
```

Read key diffs and summarize:

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
pip install <pkg-name>==X.Y.Z
\`\`\`
EOF
)"
```

## Tag convention

Always use `v` prefix: `v0.1.0`, not `0.1.0`. The publish workflow's tag filter is `v*` and the version-check step strips the leading `v` before comparing against the package version.

## When CI fails

Common causes:

- **Version-mismatch error from workflow** — the tag and `__version__.py` don't match. Fix the file or retag.
- **`invalid-publisher` from PyPI** — someone configured Trusted Publishing instead of an API token. Confirm `PYPI_API_TOKEN` is set as a repo secret (`gh secret list`).
- **Build hook needs npm/node** (e.g. Jupyter labextension). The labextension files should be committed and `skip-if-exists` should kick in. If CI tries to build them, commit the prebuilt artifacts.

If CI uploaded but you need to fix release notes, edit on GitHub or `gh release edit vX.Y.Z --notes "..."`.

## Don't

- Don't run `hatch publish`, `uv publish`, `twine upload`, or any local publish command. The token in `~/.pypirc` is only for emergency manual recovery.
- Don't delete a PyPI version and re-upload — PyPI doesn't allow re-uploading a yanked version. Bump and re-release instead.
- Don't tag without first verifying the version in `__version__.py` matches what you want to publish.
