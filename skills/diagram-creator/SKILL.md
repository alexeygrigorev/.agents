---
name: diagram-creator
description: Create polished workflow diagrams as deterministic SVG and PNG files from JSON specifications. Use when Codex needs to visualize a process, lifecycle, state flow, branching workflow, circular loop, or ASCII diagram.
---

# Diagram Creator

## Check user-facing diagram copy

When a diagram adds AI-generated, user-facing prose, a stylint check is
required before it ships. Check the natural-language `title`, `description`
(which becomes the SVG description and article alt text), captions, and any
sentence-like node, subtitle, edge, center, or detail text. Prefer running the
check on the article or Markdown file that contains the diagram. When the copy
exists only in JSON, put just those prose strings in a temporary Markdown file
and check that file:

```bash
stylint --agents
stylint path/to/article-or-diagram-copy.md
```

Apply relevant findings to the source JSON or article and run the final check
again without `--ignore`. Do not run stylint on generated SVG or PNG files, or
on geometry, layout values, JSON keys, code, URLs, API paths, icon IDs,
product names, acronyms, metric values, or other technical labels. Preserve
user-written copy; this check applies to AI-generated user-facing prose only.

Before creating or editing a diagram, read the canonical skill instructions
completely:

`/home/alexey/git/diagram-creator/skills/diagram-creator/SKILL.md`

Follow that file and resolve its relative paths from
`/home/alexey/git/diagram-creator/skills/diagram-creator/`.
