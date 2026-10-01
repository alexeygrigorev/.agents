---
name: aplexer-handoff
description: Hand an orchestrator or long-running agent session over to a fresh aplexer session (Codex, Claude, Gemini, Grok, opencode) before context runs out. Writes a handoff document, starts the successor in the same workspace, sends it the takeover prompt, and verifies it picked up the work. Use when the user asks to hand off, take over, continue in a new session, or when your context is nearly full.
---

# Handing a session off through aplexer

Goal: a successor session can resume your work with no access to your conversation. It gets
everything it needs from one handoff document plus a short takeover prompt.

## 1. Write the handoff document

Put it in the workspace, in a gitignored scratch folder the successor can read. For example,
`<repo>/.tmp/handoff-YYYY-MM-DD-<tag>.md`. Don't commit it unless asked. Include, concretely:

| Section | Contents |
|---|---|
| Current state | prod/dev version tags, `origin/main` SHA, what's deployed vs only pushed, local servers (port, worktree, DB, how to update them) |
| In flight | each open item: issue number, worktree path + branch, agent status (running, committed but not pushed), and the exact next steps through to "verified in prod" |
| Owner decisions | decisions already made and where they're recorded (issue comment ids), so the successor doesn't re-ask them |
| Follow-ups | people to contact, things to verify at a specific date/time |
| Coordination | peer sessions, mailbox names, who owns which files, the push-notice etiquette peers expect |
| Procedures | deploy/promote commands, how to watch CI, rate limits |
| Hard rules learned | mistakes made this session, and pointers to memory files |
| Open questions | anything still waiting on the owner |

Use real SHAs, paths, ids and commands, not summaries. Re-read it once as if you knew nothing.

## 2. Pick the engine and check it works

```bash
aplexer engines        # codex, claude, gemini, grok, opencode, zcodex, shell
aplexer profiles       # engine variants, e.g. godex/zodex/zcodex (codex), zlaude (claude)
aplexer list           # existing sessions per workspace; pick an unused tag
```

- The tag must be unique in the workspace (e.g. `release2`). `aplexer list` groups by workspace.
- Engine default flags already add the skip-permissions argv (`--dangerously-bypass-approvals-and-sandbox` for Codex, `--dangerously-skip-permissions` for Claude). Pass `--no-skip-permissions` only if the user wants prompts.
- **Models:** don't hardcode a model the account may not serve. On 2026-10-01, `codex -m gpt-5.6` failed in the TUI with `The 'gpt-5.6' model is not supported when using Codex with a ChatGPT account`. The account default (`~/.codex/config.toml`, `model = ...`) worked. If the repo's AGENTS.md pins a model, try it, then fall back to the account default and tell the user.

## 3. Start the successor in the same workspace

Plain engine:

```bash
aplexer start --workspace /path/to/repo --tag release2 --engine codex
aplexer start --workspace /path/to/repo --tag release2 --engine claude
aplexer start --workspace /path/to/repo --tag release2 --engine codex --profile zodex
```

Custom flags (reasoning effort, model) go in a full command after `--`. Include the skip-permissions flag yourself in that command. Then check with `aplexer status <session>` (the `command:` line) that it appears exactly once:

```bash
aplexer start --workspace /path/to/repo --tag release2 --engine codex -- \
  "$(command -v codex)" -c check_for_update_on_startup=false \
  -c model_reasoning_effort=high --dangerously-bypass-approvals-and-sandbox
```

```bash
aplexer start --workspace /path/to/repo --tag release2 --engine claude -- \
  "$(command -v claude)" --model opus --dangerously-skip-permissions
```

To replace a failed start: `aplexer kill /path/to/repo:release2`, then start again.

## 4. Confirm it booted

```bash
aplexer status /path/to/repo:release2          # state: running, worker_alive: true
aplexer capture /path/to/repo:release2 --screen --plain | grep -v '^\s*$' | tail -8
```

Wait until the screen shows the idle prompt (`› Ask Codex to do anything` for Codex, or Claude's input box) and the model line. Fix any error shown before sending work.

## 5. Send the takeover prompt

Keep it short and point at the document:

```bash
aplexer send /path/to/repo:release2 "You are taking over as <role> from the previous session. Read <handoff path> in full first, then AGENTS.md and <process docs>. Use the aplexer mailbox '<name>' for peer coordination. Continue the open items in order: (1) ... (2) ... (3) .... Start by summarizing your understanding and the current state to the owner." --enter
```

- `--enter` presses Enter. Without it the text sits in the input box.
- For long prompts, use `aplexer send <session> --stdin --enter < prompt.txt`. Avoid unescaped quotes in shell arguments.
- Then capture the screen after about 20–30s. The successor should acknowledge, mention reading the handoff, and start on item 1. If the screen shows an API error, fix it (usually the model) and restart.

## 6. Tell the peers and the user

- Peers on the aplexer mailbox: send a HANDOFF NOTICE naming the successor session, the doc path, and which open items or files it now owns. File ownership stays explicit: name the paths.
- The user:
  - the successor selector (`aplexer attach /path/to/repo:release2`);
  - the engine and model it runs;
  - the doc path;
  - what it will do first;
  - anything still running in the old session that it will inherit, e.g. a subagent that commits without pushing.

## Pitfalls seen

- **Subagents you started keep running after you hand off.** Make them commit without pushing, and list their worktree and branch in the doc so the successor can finish them.
- **Wait loops of the form `until ... ! pgrep -f "<pattern>"`** match their own command line and never exit. Kill your own background loops before handing off: `pgrep -f "until "`.
- **The successor can't read your memory of conversations**, only files, issues and the memory directory. Anything decided only in chat must go into the doc or an issue comment.
- **Don't hand off mid-push.** Finish or abandon the push, and record the exact state: pushed SHA, Deploy Dev run id, whether it was promoted.
