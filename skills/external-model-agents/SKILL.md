---
name: external-model-agents
description: Use only when the user explicitly mentions external agents and asks to invoke Claude Code, Codex CLI, Grok, or Google Antigravity CLI non-interactively for delegated work. Do not use for generic subagents, Luna agents, or the built-in subagent tool.
---

# External Model Agents

Claude Code, Codex, Grok, and Google Antigravity CLI (`agy`) are peers. Any one can call the others as an ordinary background process. They do not inherit the caller's conversation or agent context.

## Activation boundary

Use this skill only when the user explicitly mentions external agents (or explicitly invokes this skill) and wants an external model CLI used for the work. A request for generic “agents,” “subagents,” or “Luna agents” alone does not activate this skill; use the built-in subagent tools instead.

## Never start an interactive session

Use only these non-interactive forms:

```bash
claude -p "your prompt"
codex exec "your prompt"
grok -p "your prompt"
agy -p "your prompt"
```

Plain `claude`, plain `codex`, plain `agy`, and Grok without `-p/--single` open interactive interfaces. Never use those forms for delegated work: an interactive process does not exit on its own and can strand the background job forever.

## Run safely

- Run every peer CLI in the background with an explicit timeout, then read its output file. Prefer the caller's background-process option when it has one; otherwise use shell backgrounding.
- Choose the timeout deliberately. A real 30-minute run of this kind was killed with a zero-byte output file and no work to recover; long implementation or review work may need a much more generous limit.
- Ask the peer to write its deliverable incrementally to a named file and print only a short final summary. A kill then preserves partial work, and the caller avoids reading an expensive long stdout transcript. Give the peer write permission to the deliverable location.
- Brief the peer like a fresh agent: give the repository path, task, known facts, exclusions, constraints, expected deliverable path, and ownership of other agents' work.
- Explicitly tell it to read applicable `AGENTS.md` and `CLAUDE.md` files. It has not read them merely because the caller has.

## CLI reference

### Claude Code

```bash
timeout 60m claude \
  -p \
  --model sonnet \
  --effort medium \
  --permission-mode auto \
  --output-format text \
  "your prompt" \
  > /tmp/claude-agent.out 2>&1 &
```

`-p/--print` prints a response and exits. `--output-format` accepts `text`, `json`, or `stream-json`; `--json-schema` constrains structured output. Use `--permission-mode` plus `--allowed-tools`, `--disallowed-tools`, or `--tools` to bound tool access. Available permission modes are `acceptEdits`, `auto`, `bypassPermissions`, `manual`, `dontAsk`, and `plan`. `--no-session-persistence` prevents saving a print-mode session. Reserve `--dangerously-skip-permissions` for an externally isolated sandbox where bypassing checks is deliberate.

### Codex

```bash
timeout 60m codex exec \
  -c model=gpt-5.6-sol \
  -c model_reasoning_effort=medium \
  --sandbox read-only \
  -o /tmp/codex-agent.out \
  "your prompt" \
  > /tmp/codex-agent.log 2>&1 &
```

`exec` is the non-interactive subcommand. Set model and reasoning effort together with `-c key=value` overrides; `-m/--model` is also available for the model, but reasoning effort has no dedicated flag. Use `--sandbox read-only` for analysis that needs no model-written artifact and `--sandbox workspace-write` when the task must edit or save incremental output. `-o FILE` writes the final message to a file; `--json` emits JSONL events; `--skip-git-repo-check` permits work outside a Git repository.

### Grok

```bash
timeout 60m grok \
  -m grok-4.6 \
  --effort medium \
  --permission-mode auto \
  -p "your prompt" \
  > /tmp/grok-agent.out 2>&1 &
```

`-p/--single` supplies a single-turn prompt, prints the response, and exits. Choose the model with `-m/--model`, reasoning depth with `--reasoning-effort` or `--effort`, and non-interactive tool handling with `--permission-mode auto`. `--output-format` accepts `plain`, `json`, `streaming-json`, or `streaming-messages-json`; `--json-schema` constrains the response and implies JSON output.

### Google Antigravity CLI

Use `agy`, Google's current terminal agent, for Google subscription-backed external agents. Authenticate once in an interactive `agy` session before delegation; headless runs use saved credentials and fail if authentication is missing. See the [official authentication guide](https://www.antigravity.google/docs/cli/install/).

Run from the assigned repository or isolated worktree; `--add-dir` adds workspace access rather than changing the working directory. Use the executable directly, since non-interactive shells generally do not expand the `asp` alias.

```bash
(
  cd /repo || exit 1
  exec timeout 60m env -u GEMINI_API_KEY -u GOOGLE_API_KEY agy \
    --dangerously-skip-permissions \
    --effort high \
    --print-timeout 0 \
    --output-format json \
    -p "Read AGENTS.md and CLAUDE.md. Implement X; another agent owns Y. Write progress incrementally to /repo/.tmp/agy-work.md; print a short final summary."
) > /tmp/agy-agent.json 2> /tmp/agy-agent.log &
agy_pid=$!
```

`--dangerously-skip-permissions` auto-approves tool calls, including shell commands and file writes; use it when bypass is authorized for the task, as in this workspace. Otherwise omit it and configure scoped `permissions.allow` rules. Headless tools that need an approval they cannot obtain can be denied while the process still exits successfully, so inspect stderr and verify the requested deliverable.

On the installed version, `--print-timeout 0` waits until the turn finishes; the outer timeout still bounds the process. Check `agy --help` when upgrading. Choose a model from `agy models` and pass `--model MODEL_SLUG` when the user requests one. Do not substitute a model silently. `--effort` accepts `low`, `medium`, `high`, and `max` on the installed version.

Capture stdout and stderr separately: stdout holds the JSON result, while stderr holds diagnostics. After the background process completes, inspect the exit code, result `status`, `error`, and `response`, then read the incremental deliverable. To resume a particular run, use `agy --conversation CONVERSATION_ID -p "Follow-up"`; use `-c` only when the most recent conversation is unambiguous.

For progress events use `--output-format stream-json`. For a persistent multi-turn headless session, use `--input-format stream-json --output-format stream-json`, omit `-p`, and send one NDJSON message per turn:

```json
{"event":"user","message":{"content":"Your prompt"}}
```

Read events as they arrive, wait for the current turn's `result` before sending the next prompt, and close stdin when finished. CLI-handled slash commands such as `/model` and `/usage` must be separate `agy -p /model` calls, not messages in this stream. See the [official headless guide](https://www.antigravity.google/docs/cli/headless/).

For browserless CI, an API key is a separate authentication option: set `modelProvider` to `gemini` in `~/.gemini/antigravity-cli/settings.json` and export `GEMINI_API_KEY`. Setting the key alone does not select that provider. For this user's subscription-backed runs, use saved Google sign-in and strip ambient `GEMINI_API_KEY` and `GOOGLE_API_KEY` rather than changing provider settings.

## Preserve repository contracts

Peer output remains subject to the caller's repository rules and task scope.

- Public URLs must not change.
- Do not re-pin content-authority digests merely to make a failing test pass. A deliberate re-pin is legitimate only when the underlying authority intentionally changed and the reason is stated.
- Keep PII out of Git, logs, prompts, and reports.
- In a shared worktree, stage and commit explicit paths only. Never use `git add -A` or `git commit -a` while other agents may share the index.

## Peer composition examples

Each example is non-interactive, bounded by a timeout, runs in the background, and captures stdout. Replace paths, models, and prompts for the task.

### Claude calling Codex or Grok

```bash
timeout 60m codex exec -c model=gpt-5.6-sol -c model_reasoning_effort=medium \
  -C /repo --sandbox workspace-write -o /repo/.tmp/codex-final.md \
  "Read CLAUDE.md and AGENTS.md. Review X; Y is known, Z is out of scope, and another agent owns W. Write findings incrementally to /repo/.tmp/codex-review.md; print only a short summary." \
  > /tmp/codex-run.log 2>&1 &

timeout 60m grok --cwd /repo -m grok-4.6 --effort medium --permission-mode auto \
  -p "Read CLAUDE.md and AGENTS.md. Review X; Y is known, Z is out of scope, and another agent owns W. Write findings incrementally to /repo/.tmp/grok-review.md; print only a short summary." \
  > /tmp/grok-result.txt 2>&1 &
```

### Codex calling Claude or Grok

```bash
timeout 60m claude -p --add-dir /repo --model sonnet --effort medium --permission-mode auto \
  --output-format text \
  "Work in /repo. Read CLAUDE.md and AGENTS.md. Implement X; Y is known, Z is out of scope, and another agent owns W. Write progress incrementally to /repo/.tmp/claude-work.md; print only a short summary." \
  > /tmp/claude-result.txt 2>&1 &

timeout 60m grok --cwd /repo -m grok-4.6 --effort medium --permission-mode auto \
  -p "Read CLAUDE.md and AGENTS.md. Implement X; Y is known, Z is out of scope, and another agent owns W. Write progress incrementally to /repo/.tmp/grok-work.md; print only a short summary." \
  > /tmp/grok-result.txt 2>&1 &
```

### Grok calling Claude or Codex

```bash
timeout 60m claude -p --add-dir /repo --model sonnet --effort medium --permission-mode auto \
  --output-format text \
  "Work in /repo. Read CLAUDE.md and AGENTS.md. Analyze X; Y is known, Z is out of scope, and another agent owns W. Write findings incrementally to /repo/.tmp/claude-analysis.md; print only a short summary." \
  > /tmp/claude-result.txt 2>&1 &

timeout 60m codex exec -c model=gpt-5.6-sol -c model_reasoning_effort=medium \
  -C /repo --sandbox workspace-write -o /repo/.tmp/codex-final.md \
  "Read CLAUDE.md and AGENTS.md. Analyze X; Y is known, Z is out of scope, and another agent owns W. Write findings incrementally to /repo/.tmp/codex-analysis.md; print only a short summary." \
  > /tmp/codex-run.log 2>&1 &
```

After launch, use the caller's background-job mechanism to monitor completion. On completion or timeout, read the requested deliverable first, then the short captured summary or diagnostic log.
