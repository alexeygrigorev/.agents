#!/usr/bin/env python3
"""Render fake terminal "screenshots" as crisp SVGs.

Reads a JSON spec and writes an SVG that mimics a dark terminal window:
macOS-style chrome (traffic lights, title bar) or a plain rounded panel,
monospace text laid out on a character grid with syntax-ish colors.

Usage:
    termshot_svg.py SPEC.json [SPEC.json ...]
    termshot_svg.py SPEC.json -o out.svg

Spec format (all keys optional unless noted):

{
  "theme": "github-dark",          // "github-dark" | "one-dark" (default github-dark)
  "chrome": "window",              // "window" (traffic lights + title) | "plain"
  "title": "tmuxctl salvage",      // title-bar text (window chrome only)
  "font_size": 30,                 // default 30
  "line_height": 42,               // default 1.4 * font_size, rounded
  "pad_x": 52,                     // left/right text inset, default 52
  "width": null,                   // canvas width; default: computed from content
  "min_width": 0,                  // floor for the computed width
  "pad_bottom": 44,                // space after the last text baseline
  "first_row": 3,                  // body row index of the first line (window: 3, plain: 1)
  "lines": [
    {"lead": 2, "col": 0, "spans": [                 // lead = blank rows before this line
      ["$ ", "prompt"],                              // [text, color]
      ["t salvage", "bright", true],                 // [text, color, bold]
      {"t": "verbatim", "c": "blue", "b": true, "col": 17}   // explicit column jump
    ]}
  ]
}

Span shorthand: a bare string means [text, "fg"].
A span with "bg" draws a filled rounded rect behind the text (status-bar style).

Colors resolve per theme; unknown keys fall back to "fg".
"""

import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

THEMES = {
    "github-dark": {
        "bg": "#0d1117",
        "border": "#30363d",
        "header": "#161b22",
        "title": "#8b949e",
        "fg": "#c9d1d9",
        "bright": "#e6edf3",
        "white": "#f0f6fc",
        "muted": "#8b949e",
        "faint": "#6e7681",
        "green": "#3fb950",
        "bright_green": "#7ee787",
        "blue": "#79c0ff",
        "yellow": "#d29922",
        "orange": "#f0883e",
        "red": "#ff7b72",
        "purple": "#d2a8ff",
        "prompt": "#7ee787",
        "bar_bg": "#e6edf3",
        "bar_fg": "#0d1117",
        "light_red": "#ff5f56",
        "light_yellow": "#ffbd2e",
        "light_green": "#27c93f",
    },
    "one-dark": {
        "bg": "#0c1016",
        "border": "#303642",
        "header": "#0c1016",
        "title": "#6a6e75",
        "fg": "#adb1b8",
        "bright": "#dee3ea",
        "white": "#dee3ea",
        "muted": "#9da2a8",
        "faint": "#6a6e75",
        "green": "#98c379",
        "bright_green": "#98c379",
        "blue": "#61afef",
        "cyan": "#56b6c2",
        "yellow": "#e5c07b",
        "orange": "#e8c58a",
        "red": "#e06c75",
        "purple": "#c678dd",
        "prompt": "#dcdcdc",
        "bar_bg": "#dee3ea",
        "bar_fg": "#0c1016",
        "light_red": "#ff5f56",
        "light_yellow": "#ffbd2e",
        "light_green": "#27c93f",
    },
}

FONT_STACK = "JetBrains Mono, DejaVu Sans Mono, Noto Sans Mono, Menlo, Consolas, monospace"
CHAR_WIDTH_EM = 0.602  # monospace advance used for the character grid
BORDER = 2
HEADER_BOTTOM = 109
SEPARATOR_Y = 80
LIGHT_R = 12.5
LIGHT_CX = (44.5, 84.5, 124.5)
LIGHT_CY = 40
TITLE_SIZE = 21
TITLE_BASELINE = 48


def span_normalize(raw):
    if isinstance(raw, str):
        return {"t": raw, "c": "fg"}
    if isinstance(raw, list):
        return {"t": raw[0], "c": raw[1] if len(raw) > 1 else "fg", "b": bool(raw[2]) if len(raw) > 2 else False,
                "col": None, "bg": None}
    return {"t": raw["t"], "c": raw.get("c", "fg"), "b": bool(raw.get("b", False)),
            "col": raw.get("col"), "bg": raw.get("bg")}


def line_normalize(raw):
    if isinstance(raw, dict):
        return {"lead": int(raw.get("lead", 0)), "col": raw.get("col", 0),
                "spans": [span_normalize(s) for s in raw["spans"]]}
    return {"lead": 0, "col": 0, "spans": [span_normalize(raw)]}


def build_svg(spec):
    theme = THEMES[spec.get("theme", "github-dark")]
    chrome = spec.get("chrome", "window")
    font = float(spec.get("font_size", 30))
    lh = float(spec.get("line_height", round(font * 1.4)))
    pad_x = float(spec.get("pad_x", 52))
    char_w = font * CHAR_WIDTH_EM
    lines = [line_normalize(l) for l in spec["lines"]]
    title = spec.get("title", "")

    # row layout
    rows = []  # (row_index, line)
    row = spec.get("first_row", 3 if chrome == "window" else 1)
    for line in lines:
        row += line["lead"]
        rows.append((row, line))
        row += 1
    top_gap = spec.get("first_row", 3 if chrome == "window" else 1)
    first_baseline = spec.get("first_baseline")
    if first_baseline is None:
        first_baseline = 156 if chrome == "window" else round(font * 1.8)
    last_baseline = first_baseline + (rows[-1][0] - top_gap) * lh if rows else first_baseline
    pad_bottom = float(spec.get("pad_bottom", 44))

    # content extent in characters
    max_end = 0
    for _, line in rows:
        col = 0
        for s in line["spans"]:
            if s["col"] is not None:
                col = s["col"]
            col += len(s["t"])
        max_end = max(max_end, col)
    width = spec.get("width")
    if width is None:
        width = max(pad_x * 2 + max_end * char_w, spec.get("min_width", 0),
                    640 if chrome == "plain" else 900)
    width = float(width)
    height = round(last_baseline + pad_bottom)

    p = []
    p.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:g}" height="{height}" '
             f'viewBox="0 0 {width:g} {height}" role="img" aria-label="{escape(title or "terminal")}">')
    # window background + border
    p.append(f'<rect x="1" y="1" width="{width - 2:g}" height="{height - 2}" rx="16" '
             f'fill="{theme["bg"]}" stroke="{theme["border"]}" stroke-width="{BORDER}"/>')
    if chrome == "window":
        # header panel with rounded bottom corners, then separator
        r = 10
        p.append(f'<path d="M 2 16 Q 2 2 16 2 L {width - 16:g} 2 Q {width - 2:g} 2 {width - 2:g} 16 '
                 f'L {width - 2:g} {HEADER_BOTTOM - r} Q {width - 2:g} {HEADER_BOTTOM} {width - 2 - r:g} {HEADER_BOTTOM} '
                 f'L {16 + r} {HEADER_BOTTOM} Q 16 {HEADER_BOTTOM} 16 {HEADER_BOTTOM - r} Z" '
                 f'fill="{theme["header"]}"/>')
        p.append(f'<line x1="2" y1="{SEPARATOR_Y}" x2="{width - 2:g}" y2="{SEPARATOR_Y}" '
                 f'stroke="{theme["border"]}" stroke-width="{BORDER}"/>')
        for cx, color in zip(LIGHT_CX, (theme["light_red"], theme["light_yellow"], theme["light_green"])):
            p.append(f'<circle cx="{cx}" cy="{LIGHT_CY}" r="{LIGHT_R}" fill="{color}"/>')
        if title:
            p.append(f'<text x="{width / 2:g}" y="{TITLE_BASELINE}" text-anchor="middle" '
                     f'font-family="{FONT_STACK}" font-size="{TITLE_SIZE}" fill="{theme["title"]}">{escape(title)}</text>')
    for row_i, line in rows:
        base = first_baseline + (row_i - top_gap) * lh
        col = line["col"]
        x = pad_x + col * char_w
        for s in line["spans"]:
            if s["col"] is not None:
                col = s["col"]
                x = pad_x + col * char_w
            if not s["t"]:
                continue
            color = theme.get(s["c"], theme["fg"])
            weight = ' font-weight="bold"' if s["b"] else ""
            if s["bg"]:
                p.append(f'<rect x="{x - 10:g}" y="{base - font * 0.82:g}" '
                         f'width="{len(s["t"]) * char_w + 20:g}" height="{font * 1.14:g}" '
                         f'rx="3" fill="{theme.get(s["bg"], theme["bar_bg"])}"/>')
                color = theme.get(s["c"], theme["bar_fg"])
            p.append(f'<text x="{x:g}" y="{base:g}" font-family="{FONT_STACK}" '
                     f'font-size="{font:g}"{weight} fill="{color}" '
                     f'xml:space="preserve">{escape(s["t"])}</text>')
            col += len(s["t"])
            x = pad_x + col * char_w
    p.append("</svg>")
    return "\n".join(x for x in p if x)


def main(argv):
    out = None
    paths = []
    i = 1
    while i < len(argv):
        if argv[i] == "-o":
            out = argv[i + 1]
            i += 2
        else:
            paths.append(argv[i])
            i += 1
    if not paths:
        print(__doc__)
        return 2
    for path in paths:
        spec = json.loads(Path(path).read_text())
        svg = build_svg(spec)
        if out and len(paths) == 1:
            dest = Path(out)
        else:
            src = Path(path)
            stem = src.name[:-10] if src.name.endswith(".spec.json") else src.stem
            dest = src.with_name(stem + ".svg")
        dest.write_text(svg)
        print(f"{dest}  ({len(svg)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
