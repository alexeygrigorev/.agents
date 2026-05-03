# AI Assistant Dotfiles

Bootstrap and configure [Claude Code](https://docs.anthropic.com/en/docs/claude-code), [Codex](https://developers.openai.com/codex), and [OpenCode](https://opencode.ai/) from one shared repo.

This repo is the single source of truth for shared skills, aliases, wrappers, and reproducible assistant settings. Clone it once, then configure one assistant target or all of them.

## Install

Requires [git](https://git-scm.com/) and either `python3` or [uv](https://docs.astral.sh/uv/).

**One-liner** (clones and configures all targets):

```bash
curl -sSL https://raw.githubusercontent.com/alexeygrigorev/.claude/main/installer.sh | bash
source ~/.bashrc
```

**Already cloned?** Run configure directly:

```bash
./configure.sh
source ~/.bashrc
```

Configure only selected targets:

```bash
./configure.sh claude
./configure.sh codex
./configure.sh opencode
./configure.sh claude codex
./configure.sh all
```

Use `--yes` to update `~/.bashrc` without prompting:

```bash
./configure.sh --yes all
```

## What It Does

- `claude`: symlinks `skills/` into `~/.claude`, then merges `config/claude/settings.json` into `~/.claude/settings.json`
- `codex`: syncs `config/codex/settings.json` into `~/.codex/config.toml`, then symlinks shared skills into `~/.codex/skills`
- `opencode`: symlinks `skills/` into `~/.config/opencode`
- all targets: install CLI wrappers from `bin/` into `~/bin`
- all targets: add a `source` line to `~/.bashrc` pointing to this repo's `.bashrc`

Since `.bashrc` is sourced from the repo, pulling updates is enough to get new aliases and functions. Re-run `./configure.sh` when target settings or symlinks change.

## Structure

```text
.claude/
├── config/
│   ├── claude/settings.json
│   └── codex/settings.json
├── skills/            # Shared skills
├── scripts/           # Setup scripts
├── .bashrc            # Shell aliases and functions
├── installer.sh       # One-liner: clone/update repo and configure
└── configure.sh       # Local setup for claude/codex/opencode/all
```

## Skills

Skills are shared across Claude Code, Codex, and OpenCode where supported.

| Skill | Description |
|-------|-------------|
| `create-github-repo` | Create a new GitHub repo with `gh` and push the current project |
| `fetch-loom` | Download Loom transcripts and videos |
| `fetch-youtube` | Fetch YouTube video transcripts for analysis or summarization |
| `init-library` | Scaffold a new Python library with modern tooling |
| `jina-reader` | Fetch clean readable content from URLs using Jina Reader |
| `release` | Release to PyPI and GitHub with version bumping and release notes |

## Bash Aliases

Available after sourcing `.bashrc`:

| Alias | Command |
|-------|---------|
| `c` | `claude` |
| `cc` | `claude -c` |
| `csp` | `claude --dangerously-skip-permissions` |
| `ccsp` | `claude -c --dangerously-skip-permissions` |
| `cy` | `codex --dangerously-bypass-approvals-and-sandbox` |

### Functions

- `claude_init` - copy the shared `CLAUDE.md` template into the current directory
- `codex_sync_config` - sync repo-managed Codex settings into `~/.codex/config.toml`
- `codex_sync_skills` - sync shared skills into `~/.codex/skills`

## Adding New Assets

- Skills: create a folder in `skills/` with a `SKILL.md` frontmatter file and any supporting scripts
- Claude settings: edit `config/claude/settings.json`
- Codex settings: edit `config/codex/settings.json`
