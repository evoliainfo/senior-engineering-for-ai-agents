# M3 Pack 1 — Web Experience & Visual Quality

Status: experimental implementation candidate
Date: 2026-08-24
Parent contract: `STABLE_EXPERT_PACK_CONTRACT_M3.md`

## Purpose

`web-experience-visual-quality` is the first Stable Expert Pack in the Modern SEF roadmap.

Its durable value is not generic advice such as “make the page responsive.” It provides an executable evidence evaluator that forces a Delivery Mission to declare the web states that matter, observe them through real browser/visual tools, preserve discrepancies and distinguish:

- proven acceptable behavior;
- observed material defects;
- missing or incomparable evidence.

## Tool boundary

The pack declares two abstract required capabilities:

```text
browser
visual_capture
```

It does not implement or install those tools. M4 Tool Capability Resolution will bind these requirements to surfaces actually available through Codex, plugins, MCP or project tooling.

This separation is deliberate: Playwright and similar tools can produce browser observations, screenshots and visual comparisons, but the Stable Expert Pack should remain harness-neutral.

## Observation contract

Input schema identifier:

`sef.web-visual-observations.v1`

A document contains:

- target kind/locator;
- `required_cases` chosen for the current product slice;
- one or more observations for those cases.

Each required case declares:

- stable case id;
- critical state/journey checkpoint;
- viewport class;
- whether accessibility evidence is required.

Each observation records:

- case id;
- evidence iteration;
- interaction result;
- screenshot/equivalent visual reference;
- whether capture conditions are stable/comparable;
- accessibility result/reference;
- visual discrepancies with severity and resolution state.

The pack intentionally does not hard-code global mobile/desktop pixel widths. The mission/project decides the meaningful viewport classes and the browser tool records the concrete execution environment.

## Decision semantics

The evaluator returns exactly one meaningful quality state:

### `PASS`

Every required case has current sufficient evidence:

- interaction passed;
- visual capture exists;
- capture is comparable;
- accessibility passed and has evidence where required;
- no unresolved `BLOCKER` or `MATERIAL` discrepancy remains.

Unresolved `ADVISORY` discrepancies are visible but do not automatically fail the gate.

### `FAIL`

Observed evidence demonstrates a material defect, including:

- failed required interaction;
- failed required accessibility observation;
- unresolved blocker/material visual discrepancy.

### `INCOMPLETE`

The claim cannot yet be supported because evidence is absent or inconclusive, including:

- missing required case;
- `NOT_RUN` / `INCONCLUSIVE` interaction;
- missing visual capture;
- unstable/incomparable capture;
- missing/not-proven accessibility evidence where required.

`INCOMPLETE` must never be converted to `PASS` from source-code inspection or model confidence.

## Visual discrepancy loop

A case may have multiple observations. The evaluator uses the highest iteration as the current evidence while preserving `history_count` in the report.

This supports a correction loop:

```text
observe defect
→ preserve failing observation
→ modify UI
→ recapture same declared case
→ resolve discrepancy only with new evidence
→ reevaluate
```

The old failure is not erased; the new observation establishes the current state.

## Why no universal pixel threshold

The pack does not define a universal screenshot-difference tolerance. Rendering can vary by browser, operating system, fonts and execution environment. Project/tool-specific visual comparison settings belong to the resolved execution surface and current project context.

SEF instead verifies that the evidence is declared comparable and that material discrepancies are resolved before a quality claim advances.

## Accessibility boundary

The pack records and gates accessibility observations but does not claim standards conformance by itself.

A future Delivery Mission/tool binding may use accessibility-tree snapshots, automated analyzers and targeted manual/agent checks. A green automated observation alone must not be mislabeled as full WCAG conformance.

## Qualification

The deterministic pack gate covers:

- conformance to the M3 Expert Pack contract;
- inclusion in the deterministic pack manifest;
- full passing evidence;
- missing critical case → `INCOMPLETE`;
- material visual discrepancy → `FAIL`;
- failed interaction → `FAIL`;
- accessibility failure → `FAIL`;
- missing accessibility evidence → `INCOMPLETE`;
- unstable visual capture → `INCOMPLETE`;
- missing screenshot → `INCOMPLETE`;
- advisory discrepancy proportionality;
- correction loop/latest-iteration behavior;
- `NOT_RUN` truthfulness;
- unknown/duplicate case rejection;
- explicit non-claims;
- legacy runtime integrity.

The qualification itself makes zero browser, network or model calls. It tests the durable evaluator semantics against controlled evidence fixtures.

## Explicit non-claims

This pack does not yet prove that SEF can autonomously:

- launch or control a browser;
- capture screenshots;
- choose a concrete Playwright/MCP/plugin implementation;
- generate pixel-diff baselines;
- establish WCAG conformance;
- improve visual quality over native Codex in a real project.

Those outcome claims require M4 tool binding, M5 mission integration and M6 comparative evaluation.
