# AI Assistant Dotfiles

Bootstrap and configure [Claude Code](https://docs.anthropic.com/en/docs/claude-code), [Codex](https://developers.openai.com/codex), and [OpenCode](https://opencode.ai/) from one shared repo.

This repo is the single source of truth for shared skills, aliases, wrappers, and reproducible assistant settings. Clone it once, then configure one assistant target or all of them.

## Install

Requires [git](https://git-scm.com/) and either `python3` or [uv](https://docs.astral.sh/uv/).

**One-liner** (clones and configures all targets):

```bash
curl -sSL https://raw.githubusercontent.com/alexeygrigorev/.agents/main/installer.sh | bash
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

### zlaude (Z.AI-routed Claude)

`zlaude` is an opt-in target that sets up a **separate** Claude Code profile under
`~/.zlaude` routed to [Z.AI](https://z.ai/) (GLM models) via `ANTHROPIC_BASE_URL`.
It is **not** part of `all` because it prompts for an API key:

```bash
./configure.sh zlaude
```

Every run prompts at the terminal for your Z.AI API key (get one at
<https://z.ai/manage-apikey/apikey-list>) — it is never read from `.env` or the
environment. The key is written only into `~/.zlaude/settings.json`. Leaving the
prompt blank aborts before anything is created, so no partial profile is left
behind.

The profile gets the same skills, attribution-removal, hooks, and permissions as
the `claude` target, plus a Z.AI env block (auth token, base URL, and earlier
auto-compaction at ~128k tokens). Use it via the `z` / `zc` / `zsp` aliases
(mirroring `c` / `cc` / `csp`), which set `CLAUDE_CONFIG_DIR=~/.zlaude`.

### zodex (Z.AI-routed Codex)

`zodex` is an opt-in target that sets up a **separate** Codex profile under
`~/.zodex` routed to Z.AI through the
[`zai-codex-proxy`](https://github.com/alexeygrigorev/zai-codex-proxy)
Responses-to-Chat bridge on `127.0.0.1:18765`:

```bash
./configure.sh zodex
```

It writes Codex config to `~/.zodex/config.toml`, proxy config to
`~/.zodex/codex-proxy/config.json`, and the Z.AI key to `~/.zodex/zai.env` with
private file permissions. Use it via `zodex`; use `zy` for the same profile with
Codex's bypass/yolo flag. The startup script checks whether the proxy is already
running, checks the latest
[`zai-codex-proxy` release](https://github.com/alexeygrigorev/zai-codex-proxy/releases/latest),
downloads it into `~/.zodex/bin` when the local binary is missing or older, and
starts the latest binary when no proxy is already running. If a proxy is already
serving requests, the script updates the binary on disk but leaves the running
process alone so active zodex sessions are not disconnected. Set
`ZODEX_PROXY_RESTART_ON_UPDATE=1` to force an immediate restart after an update.

#### zodex Subagents

Subagents require two separate pieces to work with Z.AI:

- Codex must expose the collaboration tools. The zodex profile enables
  `[features.multi_agent_v2]` in `~/.zodex/config.toml`, with
  `max_concurrent_threads_per_session = 16`, so Codex sends plain tools such as
  `spawn_agent`, `wait_agent`, `send_message`, and `list_agents`.
- Z.AI only accepts Chat Completions-style `function` tools. `zai-codex-proxy`
  keeps Codex's Responses API interface, preserves namespace tool metadata
  internally, flattens namespace children into Z.AI-compatible function tools,
  and maps function-call results back into the Responses API shape Codex expects.
- Codex multi-agent v2 sends task payloads as Responses `agent_message` items
  whose text is carried in `content[].encrypted_content`. Z.AI cannot interpret
  that shape directly. `zai-codex-proxy` normalizes both `agent_message` and
  `agentMessage` into ordinary chat text using the `Message Type: NEW_TASK`
  envelope expected by Codex's subagent prompt.

Do not solve this by forking Codex. The Codex source is useful for checking the
wire protocol and dispatcher behavior, but the compatibility layer lives in the
proxy and the feature flags live in the zodex profile.

Quick verification:

```bash
zodex exec --skip-git-repo-check \
  "Spawn exactly one subagent with task_name tiny_math and message: compute 2+2 and reply with exactly 4. Then wait for it. After it completes, reply exactly: FINAL_SUBAGENT_OK"
```

Expected result: `FINAL_SUBAGENT_OK`. If Codex says no subagent tools are
available, check `~/.zodex/config.toml` for `[features.multi_agent_v2]`. If Z.AI
rejects tools, check the latest
[`zai-codex-proxy` release](https://github.com/alexeygrigorev/zai-codex-proxy/releases).

For a stronger smoke test, run the same profile in a clean directory and ask it
to spawn five subagents, one each for Python, Rust, JavaScript, Haskell, and Go,
with each subagent appending a haiku to a shared file. This verifies parallel
spawn, task delivery, child tool use, wait, and final aggregation.

## What It Does

- `claude`: symlinks `skills/` into `~/.claude`, then merges `config/claude/settings.json` into `~/.claude/settings.json`
- `codex`: syncs `config/codex/settings.json` into `~/.codex/config.toml`, then symlinks shared skills into `~/.codex/skills`
- `zodex`: writes `~/.zodex/config.toml` with multi-agent v2 enabled, stores the Z.AI key in `~/.zodex/zai.env`, configures the local proxy, then syncs shared skills into `~/.zodex/skills`
- `opencode`: symlinks `skills/` into `~/.config/opencode`
- `zlaude` (opt-in): prompts for a Z.AI key, then symlinks `skills/` into `~/.zlaude` and writes `~/.zlaude/settings.json` (shared settings + Z.AI env block)
- all targets: install CLI wrappers from `bin/` into `~/bin`
- all targets: add a `source` line to `~/.bashrc` pointing to this repo's `.bashrc`

Since `.bashrc` is sourced from the repo, pulling updates is enough to get new aliases and functions. Re-run `./configure.sh` when target settings or symlinks change.

## Structure

```text
.agents/
├── config/
│   ├── claude/settings.json
│   └── codex/settings.json
├── skills/            # Shared skills
├── scripts/           # Setup scripts
├── .bashrc            # Shell aliases and functions
├── installer.sh       # One-liner: clone/update repo and configure
└── configure.sh       # Local setup for claude/codex/opencode/zlaude/zodex/all
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
| `stylint` | Run and fix prose style checks for docs, lessons, workshops, and agent-written text |

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
