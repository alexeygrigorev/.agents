---
name: stylint
description: Run and fix stylint checks for user-facing prose such as workshops, lessons, articles, public docs, and publishable agent-written text. Do not use for internal engineering documents, process docs, handoff docs, planning notes, or repo maintenance notes unless the user explicitly asks for prose linting or style polish.
allowed-tools: Bash(stylint *), Bash(uv run stylint *), Bash(~/git/stylint/install.sh), Bash(cd ~/git/stylint && ./install.sh)
---

# Stylint

Use `stylint` when editing user-facing prose, Markdown, workshop lessons, public docs, articles, or publishable agent-written explanations.

Do not use `stylint` for internal engineering documents, process docs, handoff
docs, planning notes, or repo maintenance notes unless the user explicitly asks
for prose linting or style polish.

## Before Editing

Read the agent guide first:

```bash
stylint --agents
```

If the task needs a specific guide, print it directly:

```bash
stylint --style-guide voice
stylint --style-guide formatting
stylint --style-guide code-style
stylint --style-guide polish
```

## Run Checks

Check the current project:

```bash
stylint
```

Check a specific folder or repo:

```bash
stylint path/to/content
```

Exclude folders or files that are outside the requested scope:

```bash
stylint path/to/content --exclude _docs --exclude AGENTS.md --exclude README.md
```

Use `--ignore` only for investigation. Do not use it as the final verification pass, because one edit can introduce a different kind of issue.

## Fix Findings

- Fix high-confidence mechanical findings first.
- Use judgment for long sentences, comma warnings, and list suggestions.
- Preserve meaning and intensity; do not make the text more excited than the source.
- Do not blindly turn every comma sentence into bullets. Use bullets only for real lists or steps.
- Prefer rewriting scaffold like `The result is...`, `Rule of thumb:`, or `The only question is:` into the direct sentence.

After editing, always run the full check again without `--ignore`:

```bash
stylint path/to/content
```

## If Stylint Is Missing

If the checkout exists, install it into the shell path:

```bash
cd ~/git/stylint && ./install.sh
source ~/.bashrc
```

Inside the stylint checkout, this also works:

```bash
uv run stylint
```
