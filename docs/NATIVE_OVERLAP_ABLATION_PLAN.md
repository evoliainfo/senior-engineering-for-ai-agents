# Native Overlap and Ablation Plan

Status: required gate before primitive catalog merge
Date: 2026-08-24

## Objective

Determine whether the current C2/C3 engineering primitives create measurable value beyond current Codex behavior or merely add context/process overhead.

This is not the final SEF product benchmark. It is a pruning gate.

## Candidate primitive set

The current 12-item candidate includes:

- product-problem-framing;
- requirements-to-acceptance;
- repository-discovery;
- solution-architecture-stack-selection;
- project-bootstrap-foundations;
- environment-secrets-configuration;
- implementation-planning;
- architecture-conformant-implementation;
- tdd-bug-reproduction;
- systematic-debugging;
- code-review-diff-review;
- verification-before-completion.

## Hypothesis

Some of these items will be redundant with current Codex native behavior.

A primitive should survive only if at least one of the following is demonstrated:

1. improves task outcome quality;
2. reduces important omissions;
3. reduces unnecessary expert questions to the user;
4. improves truthfulness of completion claims;
5. reduces regressions or unsafe scope expansion;
6. supplies a reusable artifact needed by higher-order missions;
7. improves consistency with acceptable context/token cost.

## Arms

For each selected task:

A. current Codex native baseline

B. Codex + all candidate primitives relevant to the task

C. Codex + minimal selectively activated primitive subset

ECC is not required in this pruning test; ECC comparison belongs in the later product benchmark.

## Task mix

Use a small but heterogeneous development set, not final holdout tasks:

- ambiguous greenfield product request;
- ordinary greenfield web slice;
- unfamiliar brownfield feature;
- reproducible bug;
- non-obvious cross-layer bug;
- integration/configuration change;
- diff with hidden regression risk;
- task where most primitives should correctly stay inactive.

These tasks are DEV evidence and must not be reused later as independent benchmark evidence.

## Metrics

### Outcome

- functional correctness;
- requirement coverage;
- architecture/project fit;
- regression count;
- unresolved critical issue count.

### Friction

- user questions;
- questions requiring technical knowledge the user should not need;
- token/context overhead;
- tool-call overhead;
- unnecessary ceremony;
- latency where measurable.

### Evidence quality

- unsupported completion claims;
- missing verification;
- inaccurate deploy/readiness state;
- actual diff review quality.

## Primitive dispositions

After evidence, each primitive receives exactly one disposition:

### KEEP_SELECTIVE

Measurable value and should remain available for selective loading.

### INTERNAL_ONLY

Useful as mission composition/evaluation vocabulary, but should not normally be injected as user-facing skill context.

### MERGE_INTO_PACK

Useful method content, but best embedded inside a higher-order Expert Pack or Delivery Mission.

### REMOVE

No material benefit or net negative due to friction/context cost.

## Anti-loop rules

- Do not rewrite a primitive after seeing one task merely to win that task and continue calling the task independent.
- Do not change success metrics after results are known.
- Do not retain a primitive because implementation effort was already spent.
- Do not use skill count or internal contract-test count as evidence of user value.

## Exit

The 12-item PR may be merged only if its retained role is explicit and no longer represented as SEF's differentiated product capability layer.

A green internal contract test is necessary but not sufficient.