---
name: tdd-bug-reproduction
description: Establish executable behavioral evidence before fixing bugs or changing testable behavior, using the repository's existing test surfaces and proportionate RED-GREEN-refactor discipline rather than universal coverage or tooling rules.
---

# TDD and Bug Reproduction

## Purpose

Turn intended behavior into executable evidence before relying on an implementation claim.

For a bug, first prove the failure you intend to fix. For a new behavior, define the smallest useful test contract when the repository and task make test-first work informative.

This capability uses TDD as an engineering method, not as a ritual.

## When to use

Use this capability when:

- fixing a reproducible defect;
- changing observable behavior covered by an existing test system;
- adding logic where a focused test can establish the contract before implementation;
- preventing a regression whose failure mode can be captured reliably.

Do not force a synthetic RED phase for documentation-only edits, generated artifacts, one-time exploratory work, or bootstrap/infrastructure steps where no meaningful executable behavior exists yet. In those cases define the closest useful verification instead.

## Core principles

### Reproduce the intended failure, not just any failure

A red test is useful only if it fails for the reason the task is supposed to fix.

### Use the nearest trustworthy test layer

Prefer the smallest layer that can observe the real behavior without mocking away the defect:

- unit when the contract is local and pure;
- component/module when collaboration matters;
- integration when boundaries, persistence, serialization, network adapters, or framework behavior cause the bug;
- end-to-end only when lower layers cannot represent the user-visible contract reliably.

### Repository conventions outrank generic tooling

Use existing test frameworks, fixtures, builders, commands, naming, and setup patterns unless they cannot express the needed evidence.

### Coverage percentage is not the objective

Do not impose a universal line-coverage threshold. The objective is to cover the behavior, material edge cases, and regression risk created by this change.

## Method

### 1. State the behavior contract

Describe in observable terms:

```text
Given <relevant state>
When <action/event>
Then <observable outcome>
```

For a bug, also capture the current incorrect outcome.

If the required outcome is unclear, resolve it with `requirements-to-acceptance` before writing a test that merely codifies an assumption.

### 2. Locate the repository-native test surface

Inspect nearby tests and tooling:

- how similar behavior is tested;
- fixtures/factories/builders already available;
- test isolation expectations;
- commands used by the repository/CI;
- whether the behavior requires integration with a real boundary rather than a mock.

Avoid creating a parallel test framework for one task.

### 3. Create the smallest discriminating reproduction

The test/reproduction should distinguish the broken behavior from the intended behavior with minimal unrelated setup.

For bug fixes:

1. run relevant existing tests first when cheap enough to establish baseline;
2. add or identify a reproduction;
3. run it before the fix;
4. confirm the failure message/state corresponds to the bug.

If the new test passes before the fix, investigate:

- wrong layer;
- wrong setup;
- bug depends on missing state/environment;
- existing implementation already handles the case;
- task understanding is wrong.

Do not mutate production code merely to manufacture a red result.

### 4. Make the minimal behavior change

Change the narrowest authoritative code that can satisfy the reproduction while preserving established surrounding behavior.

Do not combine the fix with broad refactoring unless the structure prevents a safe correction.

### 5. Prove GREEN at the right scope

Run the focused reproduction first.

Then run the smallest relevant regression set that covers adjacent behavior. Broaden to package/service/full-suite verification based on impact, shared interfaces, and repository cost.

A single green new test does not prove the rest of the system is unaffected.

### 6. Add material edge cases

Add cases when they expose distinct failure modes relevant to this change, for example:

- boundary/empty/null behavior;
- permissions or ownership boundary;
- retry/idempotency behavior;
- malformed external input;
- partial failure/rollback;
- compatibility with an existing public interface.

Do not enumerate generic edge cases that cannot realistically occur in the code path.

### 7. Refactor only under green evidence

Once behavior is proven:

- remove test duplication or accidental complexity;
- improve names/structure if it clarifies the local design;
- keep behavior unchanged;
- rerun the relevant evidence after refactoring.

Refactoring is optional when the minimal correct change is already clear and maintainable.

## Expected evidence

For a bug fix, preserve enough evidence to answer:

```text
REPRODUCTION
Behavior/failure reproduced:
Pre-fix result: FAIL for expected reason
Fix scope:
Post-fix focused result: PASS
Relevant regression result:
Material edge cases covered:
Anything not run:
```

Do not fabricate a pre-fix failure if it was not actually observed.

## Decision points

### Unit vs integration

Choose based on where the failure originates. If serialization, persistence, framework middleware, configuration, concurrency, or an external adapter is essential to the failure, a pure unit mock may provide false confidence.

### New test vs existing failing test

If an existing test already reproduces the issue precisely, use it. Do not add a duplicate solely to satisfy a TDD narrative.

### Test-first vs verification-first

Test-first is strongest when behavior can be expressed before implementation. For bootstrap tasks, first establish an executable verification surface; then capture behavior as soon as it becomes meaningful.

### Fix vs refactor

Separate causal correction from cleanup where possible. A narrow fix makes the evidence easier to interpret and reduces regression surface.

## Failure modes and anti-patterns

- Writing the fix first, then creating a test that only confirms the implementation you already chose when a pre-fix reproduction was practical.
- Accepting a red test that fails because of syntax, fixture, import, or environment errors unrelated to the bug.
- Mocking the component that actually contains the failure.
- Creating a new testing stack despite adequate repository-native tooling.
- Enforcing a generic coverage percentage unrelated to risk.
- Expanding one bug fix into broad refactoring.
- Running only the new focused test and ignoring shared regression surface.
- Claiming RED was observed when it was not run.
- Making production code worse solely to simplify a test.

## Verification of capability use

Before completion:

- the behavior contract is explicit;
- pre-fix failure/reproduction is real when practical;
- the test layer observes the actual failure mechanism;
- focused evidence is green after the change;
- relevant adjacent regression evidence is green or truthfully not run;
- the implementation stayed proportionate to the defect/behavior.

## Handoff

Use `systematic-debugging` when reproduction exists but root cause is still uncertain.

Use `verification-before-completion` to calibrate final evidence and completion claims across the actual diff.
