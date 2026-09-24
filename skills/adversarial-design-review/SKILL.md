---
name: adversarial-design-review
description: Run an independent implementer-versus-reviewer loop for substantial UI redesigns, iterating on rendered evidence until a critical design reviewer explicitly accepts the result. Use when the user asks for adversarial, designer-gated, or unusually high-bar visual review; do not invoke for routine styling fixes.
---

# Adversarial Design Review

Use two independent roles: an implementer and an adversarial design reviewer. Keep the reviewer independent from the implementation context and do not let the implementer approve their own work.

## Establish the contract

Before implementation, have the reviewer inspect the current interface, user references, applicable design system, and representative content. The reviewer must publish concrete acceptance criteria covering the dimensions that matter for the task, normally:

- hierarchy, alignment, spacing, density, typography, palette, and component consistency;
- representative desktop and mobile widths, including overflow and content extremes;
- interaction states, keyboard focus, reduced motion, contrast, and target sizes;
- functional destinations and content fidelity affected by the redesign;
- consistency across the full page family when the problem is systemic.

Turn subjective goals such as “neat” or “10/10” into observable properties. Preserve the user's stated references and product constraints. Do not quietly expand the redesign into unrelated product behavior.

## Implement against evidence

Give one agent ownership of the implementation files. Tell it that others may be working in the same tree and that it must preserve concurrent edits. Require it to:

1. inspect the existing system before changing it;
2. reuse established tokens, shells, and components where appropriate;
3. render the real interface with representative data;
4. capture review artifacts in the repository's approved scratch location;
5. inspect its own artifacts and run proportionate functional checks before requesting review.

Do not commit merely to pass work between roles. Follow the repository's lifecycle and commit rules.

## Review adversarially

The reviewer evaluates rendered output, not only source code or the implementer's description. It should try to falsify quality by checking the acceptance criteria at each required viewport and state.

The verdict must be one of:

- `REVISE`: a prioritized, finite list of concrete failures. Each item identifies the evidence, why it matters, and the observable correction required.
- `ACCEPT`: explicit confirmation that all acceptance criteria were checked and no blocking or material design issue remains.

“Looks better,” “mostly done,” or approval with unresolved material issues is not acceptance. The reviewer should be exacting without inventing personal preferences that conflict with the product's design system or user request.

## Iterate to acceptance

Send every `REVISE` verdict back to the same implementer. The implementer addresses the findings, re-renders all affected viewports/states, and returns new evidence. The independent reviewer then reassesses the whole acceptance contract, including regressions, rather than checking only the latest fixes.

Continue until `ACCEPT`. If the same blocker survives repeated substantially different attempts, identify the underlying constraint, change the implementation approach, and keep progressing. Stop for user input only when acceptance requires a product choice, missing artifact, new authority, or external state that cannot be inferred safely.

After acceptance, run final repository checks and report the accepted artifacts, reviewer verdict, material design decisions, and any intentionally unchanged scope. Commit only when authorized by the user and repository process.
