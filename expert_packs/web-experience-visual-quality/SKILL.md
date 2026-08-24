---
name: web-experience-visual-quality
description: Evaluate browser-observed web experience quality across critical states, responsive cases, accessibility observations and visual discrepancy iterations. Use for material user-visible web UI changes and preview/release quality claims.
---

# Web Experience & Visual Quality

Use this pack when the mission has a material user-visible web surface. Do not load it for purely backend or non-visual changes.

## What this pack does

It turns real browser/visual observations into a deterministic quality decision. It does not pretend that a code review or model opinion proves rendered UI quality.

## Before evaluation

Declare only the cases that matter to the current product slice. Each case identifies:

- the critical UI state or journey checkpoint;
- the viewport class to exercise;
- whether accessibility evidence is required;
- the expected visual evidence reference.

Prefer a small set of meaningful cases over an exhaustive screenshot catalog.

## Observe with real tools

Resolve `browser` and `visual_capture` through the active harness. M4 owns tool resolution; this pack never invents availability or credentials.

For each required case, collect:

- browser interaction status;
- screenshot or equivalent rendered visual reference;
- accessibility observation/reference when required;
- any discovered visual discrepancy with severity and resolution state.

Visual screenshot baselines must be compared under sufficiently stable rendering conditions. If the environment is not comparable, mark the case incomplete rather than accepting a noisy result.

## Evaluate

Run `evaluators/evaluate.py` against the structured observation document.

The evaluator returns:

- `PASS` only when every declared case has sufficient passing evidence and no unresolved blocker/material discrepancy;
- `FAIL` when observed evidence shows a material product defect;
- `INCOMPLETE` when evidence is missing, not run or incapable of supporting the claim.

Do not convert `INCOMPLETE` into `PASS` because the UI looks plausible from source code.

## Correction loop

When a case fails:

1. preserve the failing observation;
2. correct the UI or accessibility issue;
3. recapture the same declared case under comparable conditions;
4. mark the discrepancy resolved only when the new observation supports it;
5. rerun the evaluator.

## Scope boundary

This pack evaluates supplied browser/visual evidence. It does not itself provide a browser, install Playwright, declare WCAG conformance, or choose provider-specific visual-diff tolerances. Those require actual tool surfaces and project-specific evidence.
