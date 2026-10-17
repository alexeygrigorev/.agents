---
name: aplexer
description: >-
  Use when the user wants to see what coding-agent sessions are running in
  aplexer on a remote machine, start a new agent session there (e.g. to fix a
  bug or a failing CI run), send instructions to a running session, read what a
  session did, or stop one.
---
# aplexer: manage remote coding-agent sessions

## Hetzner: use the Hub for orchestration

Alexey's 17 October 2026 instruction replaces psc/native starts for ordinary
Hetzner orchestration with the deployed Hub at **https://hub.dtcdev.click**.
The workers.dev hostname remains an alias. Use native aplexer commands below
for diagnostics/recovery or explicitly authorized native operations. Win35 is
expected offline through 31 October; do not route work there meanwhile.

For a new human CLI installation (Google allowlist/device approval):

```bash
curl -fsSL https://hub.dtcdev.click/cli/install.sh | sh
hub auth login
hub auth status
hub sessions list
hub sessions tree
hub sessions list --json
```

Use the caller's existing authorized profile; do not copy host keys or another
person's human credentials. Agents need their own permitted Hub authority.
The unified list includes Hub headless and externally started native sessions.
Native aliases are exact `workspace_basename:tag`, for example
`dataops:batching`. Reused/ambiguous names return409; use the listed Hub UUID.
A Hub-created session's UUID can differ from its `binding.native_id`.

Start sub-sessions through the Hub and pass the coordinator's **Hub session
UUID** as `--parent`. The coordinator must supply this value and an authorized
profile; do not guess it from a native tag or borrow a human login. Parent
existence/ownership checks can refuse an unauthorized edge. External sessions
honestly retain unknown/external ancestry. For example:

```bash
hub sessions start --machine MACHINE_ID --workspace /absolute/trusted/repo \
  --engine ENGINE --headless --brief-file /local/task.txt --name child-task \
  --parent PARENT_HUB_UUID --key UNIQUE_START_KEY --wait --timeout 180
# Choose --interactive instead of --headless/--brief-file for an empty terminal.
hub sessions send SESSION_UUID --body-file /local/message.txt \
  --key UNIQUE_SEND_KEY --wait --timeout 90
hub sessions capture SESSION_UUID --screen --key UNIQUE_CAPTURE_KEY --wait
hub sessions stop SESSION_UUID --key UNIQUE_STOP_KEY --wait --timeout 90
```

The local brief/message files are uploaded by the CLI; workspace paths must
be registered on the selected host. Keep engine/model quota admission and
resource limits from the project policy. Never launch Grok workers under the
current shared-limit hold. Inspect wait results: `acked` with a correlated
`delivered` acknowledgement proves receipt, not task completion; `recorded`
and `transported` alone do not. Stop requires confirmed terminal state. Retain
keys and reuse identical payloads after uncertain responses. Read/list access
does not authorize sending to or stopping somebody else's live session.

The 17 October acceptance covered all34 then-current native UUIDs, both named
external sessions, an owned external receiver's name-based send/capture/stop,
and the authenticated sessions dashboard. Actual Google-account approval
still belongs to the human; do not describe bootstrap-admin tests as theirs.


aplexer is a session manager for long-running agent sessions (claude, codex, gemini, antigravity, grok, opencode, shell, ...) on a remote Linux machine. Each session has its own background worker (not tmux) and is addressed as `WORKSPACE:TAG`. PocketShell is the user's phone/desktop app that drives the same sessions. Use the `a` command (PocketShell wrapper around the `aplexer` binary; same subcommands).

## Setup
- Run everything over non-interactive SSH: `ssh <host> '<command>'`. Get the SSH alias for the machine from memory (ask the user if unknown). Use your own SSH key, never the user's.
- Over SSH, always address sessions with the full `WORKSPACE:TAG` form (e.g. `/home/user/git/repo:mytag`). Re-check the workspace in `a list --json` first, because a session's workspace follows its shell's current directory.
- Commands are quoted twice (local + remote shell). For any non-trivial prompt, write it to a file and use `--stdin` or a prompt file. Join multi-line prompts into one line, since a newline can submit early.

## Delegate, don't investigate
The agent in the session does the work; you relay and check in lightly. Keep your own work minimal (no long babysitting runs, no self-investigation) to save quota. Your main job is deciding which project to start it in.
- Pick the project: first check `projects.md` in this skill's folder (`/home/box/agent-data/workflows/aplexer/projects.md`), a map of the main repos, their URLs, deploy workflows, and name/agent aliases; update it when you discover a new project or something changes. Match the request to a repo checkout on the remote machine. List them with `ssh <host> 'ls ~/git'` and confirm with `git -C ~/git/DIR remote get-url origin` (e.g. `[org/repo]` in a notice maps to the checkout whose origin is `org/repo`). Skip worktree dirs (`*-wt-*`). Use the user's recent context (the product they've been working on) to resolve vague asks. Ask only if two projects fit equally well.
- When the user asks for coding work, or forwards a CI failure notice (e.g. `[org/repo] Run failed: <workflow> - main (<sha>)`), start a session in that repo right away. Don't diagnose it yourself first: give the agent the repo, the run name/link or SHA, the user's words, and the rules below, and let it find the root cause.
- Relay the user's instructions faithfully (quote their words), add only context the agent can't get itself, and ask it to use subagents for multi-part work.
- If the user has granted a standing go-ahead for this kind of work, don't ask before starting.

## Safety
- Existing sessions are the user's live work. Reading (list, status, capture, transcript) is always fine. Sending input to, or killing, a session the user did not name needs their go-ahead.
- Never pick paid options in agent menus (e.g. "switch to usage credits" when a quota is hit). Press Esc and report the limit instead.
- Agents start with their skip-permissions flag by default, so they act unattended. Use `--no-skip-permissions` if the user wants approvals.

## Check what's running
```bash
ssh <host> 'a list'            # grouped by workspace; --all includes exited
ssh <host> 'a list --json'     # tag, workspace, engine, state, reported_state (working/waiting/idle), last_activity_ms, id
ssh <host> 'a status WS:TAG --json'
```
Summarize for the user: per session, the repo, the agent, whether it's working, waiting for input, or idle, and when it was last active. `reported_state` needs the agent's status hooks (`a init`); if missing, read the screen instead. A `broken` session's worker died (`a prune` cleans those up, only with the user's OK).

## Read what a session did
```bash
ssh <host> 'a capture WS:TAG --screen --plain'   # current screen, plain text (best quick look)
ssh <host> 'a transcript WS:TAG --last 20'       # parsed conversation and tool calls (--json, --kind tool_call); empty for some engines (e.g. antigravity), use capture then
ssh <host> 'a handoff WS:TAG'                    # transcript + screen + workspace bundle
```

## Start a new session
1. Pick workspace (repo dir or worktree), a short unique tag, and engine (`a engines` lists them; `a profiles` lists named profiles, use with `--profile`). If the user names an agent by a nickname, map it to the closest profile (e.g. a `z...` name to a `zcodex`/`zlaude` profile) and say which you used. The built-in engines already add each agent's skip-permissions flag (e.g. `antigravity` runs `agy --dangerously-skip-permissions`), so prefer `--engine X` / `--profile X` over a custom command. Check `pocketshell usage` for that agent's quota first.
2. Without an initial prompt (simplest, then send one):
   ```bash
   ssh <host> 'a --json start --workspace ~/git/REPO --tag NAME --engine claude'
   ```
   With an initial prompt, the full agent command goes after `--` and replaces the default, so repeat the binary path (from `~/.config/aplexer/config.toml`) and the skip flag yourself:
   ```bash
   ssh <host> 'a --json start --workspace ~/git/REPO --tag NAME --engine claude -- /path/to/claude --dangerously-skip-permissions "PROMPT"'
   ```
   Options: `--fresh` (auto-suffix if the tag is taken), `--cwd`, `--env K=V`, `--memory 12G`.
3. Wait 5 to 20 seconds, then check the screen with `capture --screen --plain`.
4. Agents ask "Do you trust this folder?" in any new directory and ignore input until answered. Approve it (for Claude: Down then Enter):
   ```bash
   ssh <host> 'a send WS:TAG --hex 1b5b42; sleep 1; a send WS:TAG "" --enter'
   ```
5. Send the task. `a send --enter` waits for the input box itself (see "Send an instruction"); a capture first is only needed to spot dialogs or errors.

## Coding tasks: git workflow (user's standing preference)
When you start an agent to fix or build something in a repo, the result goes straight to main, not to a pull request:
1. Create a dedicated worktree from a fresh `origin/main` before starting, and start the session in it, so shared checkouts (which may have uncommitted work and other agents) are untouched. Use a new tag/worktree name per session, and when several sessions edit the same repo, tell each to rebase often:
   ```bash
   ssh <host> 'cd ~/git/REPO && git fetch origin && git worktree add ../REPO-wt-TAG -b TAG origin/main'
   ```
2. Put these rules in the task prompt: work only in this worktree; run the relevant tests; commit; then rebase on the latest `origin/main`, re-run tests, and push to main (`git push origin HEAD:main`); do NOT open a pull request. For big tasks, ship in increments (one commit + push per area). If the push is rejected because main moved, fetch, rebase, re-test, and push again. Don't deploy by hand, change cloud resources or secrets, or enable/disable workflows unless the user asked; the repo's normal deploy-on-push is fine.
3. After the push lands, clean up: remove the worktree (`git worktree remove ../REPO-wt-TAG`), delete the local branch (`git branch -D TAG`) and any remote branch (`git push origin --delete TAG`), and kill the session. Also remove any extra worktrees/branches the agent created for its subagents. Only clean up what you created.
4. Check CI on main after each push, and compare any failures with the previous main run so you only report what the change introduced. For a CI-failure task, re-run the failing workflow (e.g. `gh workflow run`) after deploy and confirm it's green.
5. Keep supervision light, because supervising costs the assistant's own quota: put the whole task (including push, CI check, and cleanup rules) in the agent's prompt, confirm it started, then end. Check back only at milestones or from a scheduled routine, not every minute or two. When you do check, approve agent prompts (except paid or account ones) and nudge it if it's idle, looping, or concluded "nothing to change" while the user's complaint is clearly unaddressed.

## Unfinished work: restart automatically
If a session dies, is killed, or stops before finishing its task, don't ask the user: when you next look (a routine run or the user's next message, not a dedicated watcher), check `a list --json` and `git log origin/main` to see what already shipped, then restart a fresh session (new tag and worktree from latest `origin/main`) with the remaining work. If your own background worker is interrupted, don't re-dispatch it; the session keeps running on its own. Note restarts in your report.

## Keep assistant usage cheap
- Start sessions and report once; no long-running executors that watch sessions.
- Routine checks: a couple of quick inline ssh reads; spin up a worker only when something needs fixing; stay silent when nothing changed.
- No overnight work unless the user asked for it.

## Engine quirks
- codex-based profiles running non-OpenAI models (e.g. `zcodex`) may try a `Write` tool that doesn't exist ("unsupported call: Write"). Tell them up front to edit files with `apply_patch` or the shell.
- antigravity's transcript is empty; use `capture --screen --plain`.
- Sending while the agent is busy queues the prompt (`delivery.queued: true`). If a queued message isn't picked up after the turn ends, press Esc (`--hex 1b`) and resend.

## Send an instruction
```bash
ssh <host> 'a send WS:TAG "do X" --enter'                 # --enter submits
ssh <host> 'a send WS:TAG --stdin --enter' < prompt.txt   # longer prompts, no quoting trouble
ssh <host> 'a send WS:TAG --hex 1b'                       # Esc (interrupt / close a menu)
```
`--enter` acknowledges the delivery (aplexer >= 0.1.16, see the aplexer README "Delivery acknowledgement"): it waits for a booting agent's input box, checks the text landed and was submitted (pressing Enter again or resending dropped text), then waits up to `--wait-ack` seconds (default 10) for the agent to start working. Read the exit code:
- `0`: delivered and working (or `unverified`: the screen could not be read, e.g. a trust dialog or a non-agent session, so check it yourself).
- `3`: submitted, but the agent stayed idle. Read the screen: a slash command, a quota or error message, or a menu.
- `1`: failed. The text never showed in the input box, or stayed stuck there after 3 Enter presses. The error says which; capture the screen before retrying.

Use `a --json send ... --enter` for the full verdict (`delivery.status`, `working_evidence`, `queued`, `sends`, `enter_presses`). Sending right after `a start` is safe: the readiness wait covers the boot (OpenCode needs ~7s). Trust dialogs are not answered for you (step 4 above). If the quota or error check matters, still read the screen or transcript after the agent has had time to reply.

## Stop a session
```bash
ssh <host> 'a kill WS:TAG --signal TERM --grace-ms 10000'   # gentle; plain `a kill` = SIGHUP then SIGKILL after 2s
```
Only stop sessions the user asked to stop, or ones you created yourself.

## Report back
Per task: what changed (user-facing, short), commit SHAs on main, CI/deploy status with links, anything worth the user's review (design choices, gaps, things not done), restarts, cleanup, and quota.

## Other
- `a watch --jsonl` streams session events.
- `a task run --prompt-file F --engine codex` runs one task non-interactively and exits with the agent's exit code (good for one-shot jobs).
- `pocketshell sessions list|create|kill [--json]` and `pocketshell usage` (per-provider quota) are PocketShell helpers on the same machine.
- Source and README: `~/git/aplexer` on the remote machine.
