---
name: regular-ping
description: Set up, inspect, retarget, pause, or resume recurring tmux pings ("regular pings") using `t jobs`. Use when the user asks to create a scheduled ping for a session, check existing pings, or move a ping to another tmux session.
allowed-tools: Bash(t *), Bash(tmux *)
---

# Regular Ping

In this environment, a "regular ping" means a recurring ping managed through `t jobs`.

## Find the right tmux session

If the user only knows the recent-session ID, resolve it first:

```bash
t
t list
```

If the agent is already inside the target tmux session, `:current` is valid for job commands:

```bash
t jobs add :current --every 20m --message "..."
t jobs edit <job-id> --session :current
```

If multiple similar sessions exist, inspect them before attaching the ping to the wrong one:

```bash
tmux list-panes -t <session> -F '#{session_name}:#{window_index}.#{pane_index}:#{pane_current_command}:#{pane_title}:#{pane_active}'
```

Always prefer the exact tmux session name over a guessed prefix.

## Get existing regular pings

List all jobs:

```bash
t j
```

List jobs for one session:

```bash
t jobs list --session <session>
```

Inspect one job:

```bash
t jobs show <job-id>
```

Check recent delivery logs:

```bash
t jobs logs --limit 20
```

Notes:

- `t j` is shorthand for `t jobs`
- job IDs are not session IDs
- if a job is attached to the wrong session, retarget it with `t jobs edit`

## Set up a new regular ping

For a short inline prompt:

```bash
t jobs add <session> --every 20m --message "Continue until all issues are resolved."
```

For a longer prompt:

```bash
t jobs add <session> --every 20m --message-file prompts/<name>.txt
```

After creating the job, verify it:

```bash
t jobs list --session <session>
t jobs show <job-id>
```

If the user wants an immediate one-off message right now, send it separately:

```bash
t send <session> --message "..."
```

## Update or fix an existing regular ping

Retarget a job to the correct session:

```bash
t jobs edit <job-id> --session <session>
```

Change interval or prompt:

```bash
t jobs edit <job-id> --every 30m
t jobs edit <job-id> --message "..."
```

Pause or resume one job:

```bash
t jobs pause <job-id>
t jobs resume <job-id>
```

Pause or resume all jobs for the current tmux session:

```bash
t jobs pause-current
t jobs resume-current
```

Remove a job that is no longer needed:

```bash
t jobs remove <job-id>
```

## Practical rules

- Verify the target session before creating or moving a job.
- Use the exact session name when multiple similar sessions exist.
- Confirm the result with `t jobs show <job-id>` after changes.
- If the user says "start now", that is separate from regular scheduling; send a one-off message with `t send`.
