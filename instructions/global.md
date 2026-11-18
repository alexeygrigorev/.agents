# Global conventions

Loaded by every agent on every machine set up with `~/git/.agents/configure.sh`:
- Claude: `~/.claude/CLAUDE.md`
- Codex: `~/.codex/AGENTS.md`
- OpenCode: `~/.config/opencode/AGENTS.md`

The maintainer runs agents in skip-permissions mode and does not want to approve anything by hand. The rules below exist because each pattern still forces a manual approval prompt despite that mode.

## Never put `$` in an `rm`/`rmdir` command

Claude Code has a hardcoded `dangerousRemoval` circuit breaker. If a Bash command mentions `rm` or `rmdir` and also contains a `$` anywhere, the removal target is resolved statically. Anything it cannot resolve triggers the breaker, for example:
- `rm -f $D/*`
- `rm -rf "$OUT"`
- `rm $(...)`
- a `cd` before a relative glob

The prompt reads "Dangerous rm operation on statically-unresolvable target" or "Dangerous rm operation on possibly-empty variable path". It is not classifier-approvable: it prompts even under `--dangerously-skip-permissions`, and no permission rule, hook or setting can silence it. Ignore the prompt's own suggestion to use `"${D:?}"/*` and follow the rules below. Subagents hit this too, so put this rule in their briefs.

Do this instead:
- Delete with a **literal absolute path**: `rm -f /home/alexey/git/proj-wt/shots/r2-411/*`.
- If the path is computed, print it in one Bash call, then delete in the **next** call with the literal path pasted in.
- Don't chain `echo`/`ls`/`mkdir` checks around a removal in the same call when anything in it uses `$`.
- Avoid deleting at all where possible. Write each run's output to a fresh unique directory, e.g. `.../shots/run-<timestamp>`, instead of emptying an old one.
- `find /literal/path -mindepth 1 -delete` is fine. `find "$D" -delete` is not.
