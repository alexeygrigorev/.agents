---
name: adversarial-redesign
description: Redesign a UI that "feels AI-generated" into something that looks deliberately art-directed. Attack the current design's generic tells first, then commit to one opinionated direction via a written design contract, implement, and verify in a rendered browser screenshot. Use when the user says a design feels AI-generated, too generic, or template-like and wants a distinctive, high-quality redesign.
---

# Adversarial redesign

The failure mode this skill fixes: output that is *plausible* but anonymous — Inter,
soft-radius cards, pastel tint chips, a dark sidebar beside a light canvas, an eyebrow
label over every heading, an icon on every button. Individually fine; collectively it
reads as "the model's default admin panel". Users notice within seconds.

The fix is not decoration. It is **commitment**: pick one strong art direction and apply
it without exceptions, the way a designer with a position would.

## Phase 1 — Attack (adversarial pass)

Before touching a line of CSS, enumerate what makes the current design anonymous. Audit
against this list of known AI tells:

1. **Default font stack** — Inter / system-ui-first, no typographic identity.
2. **Gradient or tint-as-decoration** — purple/blue gradients, pastel washes, glassmorphism.
3. **Uniform rounding** — the same border-radius on every element.
4. **Chips for everything** — pill badges with pale tinted backgrounds for every status.
5. **Eyebrow over everything** — 11px uppercase letterspaced micro-label above each heading.
6. **Explainer sub-line under every heading** — a muted sentence repeating what the title said.
7. **Redundant icons** — an icon on every button, every list row, every empty state.
8. **The template layout** — dark sidebar + light content + 4-equal-stat metric row.
9. **No tension** — everything the same size, weight, and contrast; nothing oversized, nothing brutal.

Write the attack down as a list of specific, verifiable claims about *this* codebase.

## Phase 2 — Commit (the design contract)

Choose one direction and write it into a **design contract** (commit it to the repo,
e.g. `docs/design-contract.md`) before implementing. A direction is only valid if it
says **no** to things. Pick based on what the product *is*, not what looks trendy:

- **Technical/engineered tool** → monospace identity, hairline rules, 0px radii, dense
  tables, one signal accent. Good for CLIs' consoles, infra, data products.
- **Editorial** → serif display, paper background, rules instead of cards, generous
  whitespace. Good for content, writing, marketing.
- **Industrial** → heavy borders, hard offset shadows, uppercase condensed type, safety accent.
- **Humanist product** → characterful grotesque (not Inter), warm neutrals, one confident radius.

The contract must pin down, with concrete values: typefaces and where each is used,
the type scale, the full color palette (hex), radius policy, border/shadow policy,
spacing, component treatments (buttons, badges, tables, inputs, dialogs), and a
**banned list** of tells that must never reappear.

## Phase 3 — Execute

- Implement against the contract with zero exceptions. One "just this once" rounded
  corner or pastel chip reintroduces the generic feel everywhere.
- Keep every class name and behavior contract stable where possible — this is a
  *re-skin*, not a rewrite; dynamic markup emitted by JS must keep working.
- Typography does the heavy lifting. If the identity font is a system stack, get
  character from weight contrast, case, tracking, and scale jumps (e.g. mono labels at
  11px vs mono numerals at 32px) instead of the font file.

## Phase 4 — Verify like a designer

Serve the real UI, screenshot every state (login, app shell, tables, dialogs, mobile
width), and judge against the attack list from Phase 1: every tell gone? Any element
that still looks "default"? Iterate until a hostile reviewer would call it opinionated.
Then run the functional smoke check (all views render, dialogs open, no console errors).
