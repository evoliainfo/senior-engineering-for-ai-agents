---
name: implementation-planning
description: Build a proportionate, repository-aware implementation plan from acceptance criteria, sequencing the smallest safe change and its evidence without pretending uncertain file-level details are known.
---

# Implementation Planning

## Purpose

Translate an accepted outcome into the **smallest credible execution path** for the actual repository.

A useful plan reduces avoidable rework, makes dependencies and verification visible, and still leaves the coding agent free to adapt when implementation reveals new evidence.

## When to use

Use this capability when:

- a change spans multiple files, layers, packages, services, schemas, or verification steps;
- ordering matters;
- an unfamiliar repository or hidden dependency makes direct editing risky;
- the task has explicit acceptance criteria that should trace into implementation and tests.

For a trivial local edit with obvious verification, use a one- or two-step mental plan rather than generating ceremony.

## Inputs

Prefer:

- repository map or equivalent local understanding;
- acceptance criteria;
- applicable project instructions;
- known risks, constraints, and unresolved questions.

Do not plan from the user prompt alone when the repository can materially change the right approach.

## Core principles

### Plan outcomes, not keystrokes

A plan should explain **what must become true and how it will be proven**, not predict every line of code.

### Minimize simultaneous uncertainty

Sequence work so that uncertain interfaces, reproduction steps, schemas, or external assumptions are resolved before downstream work depends on them.

### Prefer reversible steps

When two approaches are otherwise comparable, prefer the one that can be validated and corrected with the least collateral change.

### Verification is part of the plan

Do not append “run tests” as an afterthought. Map evidence to the behavior or risk each step introduces.

## Method

### 1. Confirm the planning basis

Summarize:

- desired outcome;
- acceptance criteria;
- relevant repository pattern;
- constraints that affect design;
- material unknowns.

If required behavior is still ambiguous, return to `requirements-to-acceptance` instead of planning around an unstated assumption.

### 2. Identify the change units

Break the work into meaningful engineering units such as:

- behavior/interface change;
- data/schema change;
- adapter/integration change;
- UI/state change;
- migration/backfill;
- tests/fixtures;
- documentation/configuration;
- release or operational work.

Use only units actually needed by the task.

### 3. Order by dependency and learning value

Typical ordering logic:

1. establish or reproduce the current behavior;
2. resolve the highest-impact uncertainty;
3. change the narrowest authoritative layer first;
4. update dependents/adapters;
5. add or update evidence closest to the changed behavior;
6. verify broader regressions proportionally;
7. inspect the actual diff and reassess scope/risk.

This is a heuristic, not a mandatory waterfall. Reorder when the repository or task gives better evidence.

### 4. Define a verification contract per material step

For each step, answer:

- What observable state should exist afterward?
- What test/build/runtime evidence can prove it?
- What failure would invalidate the approach?

Prefer the repository's existing test and build surfaces. Do not invent a new toolchain just to satisfy the plan.

### 5. Mark uncertainty honestly

Use labels such as:

- **known** — directly supported by repository/task evidence;
- **likely** — strong hypothesis that implementation should confirm;
- **open** — material uncertainty that must be resolved before dependent work.

Do not list speculative file names as guaranteed edits.

### 6. Define scope boundaries

State what the plan intentionally does **not** include when scope creep is plausible.

Examples:

- no unrelated framework upgrade;
- no redesign of adjacent feature;
- no global refactor solely to support one localized change;
- no new abstraction unless implementation evidence justifies it.

### 7. Set replanning triggers

Replan only when evidence changes the problem, for example:

- the presumed authoritative code path is wrong;
- an interface is shared more broadly than expected;
- a migration/destructive operation becomes necessary;
- tests reveal hidden behavior;
- the actual diff introduces a material risk not present in the original request.

Do not rewrite the plan after every small implementation detail.

## Expected output

For a material task:

```text
IMPLEMENTATION PLAN
Outcome:
Relevant constraints:

1. Step/outcome
   Evidence:
   Files/area: known or likely
   Invalidated if:

2. Step/outcome
   Evidence:

Scope boundaries:
Open uncertainties:
Replan triggers:
Final verification:
```

Keep the plan proportional. Three precise steps are better than twenty generic ones.

## Decision points

### Change existing path vs create new path

Default to extending the existing authoritative path. Create a new path only when the current architecture cannot satisfy the requirement cleanly or when isolation is a deliberate repository pattern.

### Test first vs implementation first

For bugs and behavior changes with a reproducible contract, prefer a failing behavioral test or reproduction before the fix. For infrastructure/bootstrap work where a useful failing test cannot exist yet, establish the narrowest executable verification first and avoid fake TDD ceremony.

### Refactor before feature vs after

Refactor first only when the existing structure prevents a safe change or makes the behavior impossible to verify. Otherwise implement the requested behavior with minimal disturbance and refactor opportunistically only when evidence justifies it.

## Failure modes and anti-patterns

- Planning before reading the relevant repository.
- Producing a plan whose length is unrelated to task complexity.
- Naming exact files/functions as facts when they are only guesses.
- Encoding preferred libraries without repository evidence.
- Hiding unresolved product decisions inside implementation steps.
- Treating tests as a final generic step rather than evidence tied to behavior.
- Adding unrelated cleanup because it is “nearby.”
- Refusing to adapt when implementation disproves the initial map.
- Replanning continuously for inconsequential details.

## Verification of planning quality

A good plan should satisfy all of these:

- every step traces to acceptance, repository compatibility, or necessary evidence;
- dependencies are ordered so later work does not rely on avoidable unknowns;
- verification is specific enough to falsify the step;
- scope boundaries are clear where useful;
- implementation choices remain flexible where evidence has not yet decided them;
- the plan can shrink for small tasks.

## Handoff

Use `tdd-bug-reproduction` when the task changes observable behavior or fixes a defect that can be reproduced.

Use `systematic-debugging` when the root cause is not yet established.

Always use the principles from `verification-before-completion` before declaring the task finished, even when the plan itself is lightweight.
