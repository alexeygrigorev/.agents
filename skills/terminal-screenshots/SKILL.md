---
name: terminal-screenshots
description: Render fake terminal "screenshots" (dark window chrome, traffic lights, colored monospace output) as crisp SVGs from JSON specs, for READMEs and docs. Use when a project needs terminal-style hero images, feature shots, or when converting existing PNG terminal screenshots to SVG.
---

# Terminal Screenshots

Fake terminal screenshots as SVG: they look like real terminal captures, stay
crisp at any DPI, weigh ~1-10 KB, and regenerate diff-ably from a spec — no
font embedding, no raster artifacts on GitHub.

The generator is `scripts/termshot_svg.py` (stdlib-only Python). Full spec
reference is in its docstring; this file covers the workflow and the design
system.

## Workflow

1. **Write a spec** — a JSON file next to the target SVG (convention:
   `<name>.spec.json` beside `<name>.svg`). Example:
   `examples/salvage.spec.json`.

   ```json
   {
     "theme": "github-dark",
     "chrome": "window",
     "title": "tmuxctl salvage",
     "width": 1494,
     "pad_bottom": 71,
     "lines": [
       {"spans": [["$ ", "prompt"], ["t salvage", "bright", true]]},
       {"lead": 1, "spans": [
         ["SESSION", "white", true],
         {"t": "STATUS", "c": "white", "b": true, "col": 17},
         {"t": "healthy", "c": "green", "col": 17}
       ]}
     ]
   }
   ```

   A span is `[text, colorKey, bold?]` or `{"t": …, "c": …, "b": …, "col": N,
   "bg": …}`. A line renders at its row; `"lead": 1` inserts one blank row
   before it. `"col"` pins a span to an absolute character column — use it for
   every table column so alignment survives font substitution on the viewer's
   machine (GitHub serves SVGs to whatever monospace the reader has).

2. **Render**:

   ```bash
   python3 scripts/termshot_svg.py path/to/name.spec.json   # writes name.svg
   rsvg-convert name.svg -o name.png                        # for inspection
   ```

3. **Verify visually**: render at native size and compare against the
   reference (if converting an existing PNG) — stack original and new in one
   image and zoom into the edges. Check: no text clipped at the right border,
   columns line up, box-drawing/symbol glyphs (`├── └── │ ● ○ ❯ ← ·`) render
   as glyphs, not tofu.

## Reproducing an existing PNG screenshot

When converting a real PNG, measure it instead of guessing:

- **Palette**: crop each text region and take the most common non-background
  colors (`uv run --with pillow python`, `Counter(crop.getdata())`). The two
  themes below cover both repos this skill was built from; add keys to
  `THEMES` for others.
- **Metrics**: projection-profile the rows (count non-background pixels per
  row) to get cap-top bands → baseline pitch = line height, first baseline =
  first band top + cap height (~0.73 em). Char advance is 0.602 em.
- **Columns**: glyph left edges ÷ char width → character columns. Watch for
  rows that break the grid (e.g. a long status pushing its detail column
  left to avoid overflow).
- Keep 2+ characters of slack between the longest line and the right border;
  viewer-side monospace can be slightly wider than the measurement font.

## Design system

Two looks, both dark, both DejaVu/JetBrains-metric-compatible (0.602 em
advance):

**`github-dark` + `chrome: "window"`** — macOS window: `#0d1117` body,
`#161b22` title bar with rounded-bottom chin, 2px `#30363d` border, radius 16,
traffic lights (`#ff5f56 #ffbd2e #27c93f`, r 12.5, cy 40), centered `#8b949e`
21px title, separator at y 80. Body text starts at baseline 156, left pad 52.
Default font 30, line height 42. Used for command-output shots (`$ cmd` +
tables, trees).

**`one-dark` + `chrome: "plain"`** — bare rounded panel: `#0c1016` body, 2px
`#303642` border, no title bar. Font 30, line height 40, left pad 46. Used for
full-app views (lists, status bars; the inverted bar is a span with `"bg"`).

Color keys (both themes): `fg bright white muted faint green bright_green
blue cyan yellow orange red purple prompt` + `bar_bg bar_fg` for inverted
blocks. Values are in the script; keep hues consistent with the reference
app's actual output style (e.g. git-dash status colors, One Dark for aplexer).

## Embedding

GitHub renders SVG in READMEs fine (`<img src="..." width="720">` or standard
markdown images). Keep the old PNG's display width, keep/rewrite descriptive
alt text, and delete the superseded PNG only after the SVG is verified — it
stays recoverable in git history. Store the `.spec.json` beside the SVG so the
shot stays editable; treat the SVG as a build artifact.

## Canonical examples

- `~/git/tmuxctl/assets/*.spec.json` — window-chrome shots
  (hero-t, units, describe, salvage)
- `~/git/aplexer/docs/screenshots/*.spec.json` — plain-panel shots
  (list with tree + status colors, attach with inverted bar)
