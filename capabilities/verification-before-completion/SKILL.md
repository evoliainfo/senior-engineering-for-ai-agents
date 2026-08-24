---
name: verification-before-completion
description: Verify that the evidence actually supports the completion claim before saying work is done. Use after implementation, debugging, refactoring, or any material change, and distinguish code-complete, deployable, deployed, and post-deploy-verified states.
---

# Verification Before Completion

Use this capability when a change appears complete but the claim still needs evidence.

The goal is not to run every possible check. The goal is to produce the **smallest sufficient evidence set for the exact claim being made**.

## Core Principle

> The strength of the completion claim must never exceed the strength of the evidence.

A passing unit test can support a narrow behavior claim. It cannot by itself prove that a production deployment succeeded, that an external provider ingested an event, or that a user journey works end to end.

## 1. Define the Claim Boundary

Before verifying, state what is actually being claimed.

Useful claim levels include:

1. **implemented** — the intended code/configuration change exists;
2. **locally verified** — relevant repository-native checks passed in the available environment;
3. **deployable** — build/package/configuration evidence supports deployment readiness;
4. **deployed** — deployment execution itself was observed to succeed;
5. **post-deploy verified** — relevant production/runtime behavior was observed after deployment.

Do not collapse these states into a generic "done".

If the task did not include deployment, do not imply deployment occurred.

## 2. Re-read the Acceptance Contract

For every applicable acceptance criterion, identify:

- what observable fact would prove it;
- what test, command, inspection, runtime observation, or external evidence can establish that fact;
- what evidence is unavailable in the current environment.

Explicit user requirements, inferred engineering requirements, and optional improvements must remain distinguishable.

## 3. Inspect the Actual Change Surface

Verification must follow what actually changed, not only what was planned.

Inspect the current diff or equivalent change set and ask:

- Did implementation touch additional modules, contracts, data, configuration, permissions, dependencies, or deployment behavior?
- Did it create new failure modes not represented in the original plan?
- Did it introduce a material domain that needs additional verification?

If the actual change surface materially exceeds the plan, expand verification or re-plan before claiming completion.

## 4. Discover Repository-Native Verification

Prefer the repository's real mechanisms over generic commands.

Inspect, as relevant:

- package/project scripts;
- test configuration and existing test patterns;
- type-check and lint configuration;
- build/package commands;
- integration or E2E harnesses;
- CI definitions;
- migration/validation tooling;
- deployment configuration;
- project instructions.

Do **not** assume `npm test`, 80% coverage, Playwright, pytest, Docker, or any other tool merely because it is common elsewhere.

## 5. Build a Proportionate Evidence Ladder

Select checks according to the changed behavior and risk.

Possible layers:

### Static evidence

- focused code/configuration inspection;
- schema/type validation;
- lint/static analysis where relevant.

### Behavioral evidence

- focused unit or regression test;
- integration test;
- error/negative-path test;
- boundary-condition test.

### Assembly evidence

- build/package success;
- application startup or smoke test;
- migration dry run or equivalent safe validation.

### User-journey evidence

- E2E test;
- browser/API flow;
- complete critical path when the change spans multiple layers.

### Deployment/runtime evidence

- deployment status;
- health/readiness checks;
- logs/metrics/traces;
- externally observable behavior;
- provider ingestion or downstream effect when relevant.

Use only the layers needed to support the claim. A trivial local edit should not trigger production-level ceremony; a production-critical change should not be accepted on a syntax check.

## 6. Verify Negative Space

For material changes, test or inspect the failure modes most likely to invalidate the happy path.

Examples:

- invalid or missing input;
- authorization boundary;
- unavailable dependency;
- duplicate/retry behavior;
- empty state;
- rollback/recovery path;
- incompatible configuration;
- partial failure.

Select relevant cases from repository and task evidence. Do not manufacture irrelevant checklist items.

## 7. Record Truthful Evidence States

Use explicit evidence states rather than turning everything into PASS/FAIL.

Recommended states:

- `PASS`
- `FAIL`
- `NOT_RUN`
- `UNAVAILABLE`
- `INCONCLUSIVE`
- `FLAKY`
- `N_A`
- `WAIVED` when an authorized waiver genuinely exists
- `BLOCKED`

Never convert `NOT_RUN`, `UNAVAILABLE`, or `INCONCLUSIVE` into PASS.

## 8. Produce the Completion Decision

For each acceptance criterion, record:

- criterion;
- evidence actually obtained;
- result state;
- residual uncertainty.

Then make the narrowest justified conclusion:

- **VERIFIED** — evidence supports all required claims at the stated level;
- **VERIFIED_WITH_RESIDUAL_RISK** — required behavior is supported but explicit residual uncertainty remains and is acceptable for the requested claim;
- **NOT_VERIFIED** — evidence is insufficient or contradictory;
- **BLOCKED** — required evidence cannot responsibly be obtained without a missing dependency, environment, permission, decision, or specialist review.

Do not say "ready for production" unless production readiness itself was evaluated. Do not say "deployed" unless deployment happened. Do not say "works in production" unless relevant post-deploy behavior was observed.

## Repository Adaptation Rules

- Reuse existing verification scripts and conventions before introducing new tooling.
- Run the smallest relevant checks first, then widen only when evidence or risk justifies it.
- Follow dependency boundaries: a changed shared contract may require wider tests than a leaf implementation.
- Prefer existing fixtures and realistic test data over invented parallel harnesses.
- Preserve repository-defined release/deployment processes.
- Treat CI evidence as useful but not automatically equivalent to runtime/production evidence.

## Context Budget

Load only:

1. acceptance criteria;
2. actual changed files/diff;
3. relevant verification/test configuration;
4. failing or relevant test output;
5. deployment/runtime evidence only when the claim includes those layers.

Do not reload the whole repository merely to produce a completion report.

## Anti-Patterns

Avoid:

- declaring success because code was written;
- treating a green build as proof of all behavior;
- running a fixed universal command list regardless of stack;
- claiming deployment from deployment configuration alone;
- claiming external-provider success from a client-side event firing;
- ignoring newly introduced diff scope;
- hiding skipped checks;
- creating tests that do not exercise the changed behavior;
- inflating minor residual uncertainty into unnecessary blocking;
- downplaying material missing evidence to keep momentum.

## Evidence Contract

A strong completion report should answer:

1. What exactly is being claimed?
2. Which acceptance criteria were verified?
3. What evidence supports each criterion?
4. What actual checks ran, and what were their outcomes?
5. What relevant checks were not run and why?
6. Did the actual diff introduce new verification requirements?
7. What residual risks or uncertainties remain?
8. Is the state implemented, locally verified, deployable, deployed, or post-deploy verified?

## Handoff

If verification exposes a new defect or unexplained failure, use `systematic-debugging`.

If acceptance criteria were ambiguous or changed during implementation, return to `requirements-to-acceptance` and re-plan rather than forcing a completion claim.
