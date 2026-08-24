---
name: systematic-debugging
description: Diagnose non-obvious failures by reproducing the symptom, separating facts from hypotheses, narrowing the causal path with discriminating experiments, and fixing the smallest verified root cause.
---

# Systematic Debugging

## Purpose

Find and verify the **cause** of a failure rather than iterating through plausible patches until the symptom disappears.

The method is evidence-driven and repository-aware. It should reduce uncertainty on every meaningful step.

## When to use

Use this capability when:

- a test, build, runtime flow, integration, or production-like behavior fails for an unclear reason;
- a defect is intermittent or crosses multiple layers;
- a previous fix treated a symptom but the problem persists;
- there are several plausible causes and editing immediately would confound the diagnosis.

For an obvious local defect whose cause is already proven by direct evidence, fix it and verify it rather than producing a debugging ceremony.

## Core principles

### Separate observation from explanation

A stack trace, failing assertion, log line, changed value, request payload, or timing measurement is an observation.

“Probably a race condition” is a hypothesis until evidence discriminates it from alternatives.

### Change one causal variable at a time where practical

Experiments should distinguish hypotheses. Multiple simultaneous speculative edits destroy information even when they accidentally make the symptom disappear.

### Debug the narrowest real path

Start at the observed failure and trace backward/forward through the actual data/control path. Do not scan unrelated code merely because it uses the same technology.

### A disappearing symptom is not automatically a root-cause proof

Verify why the fix works and add regression evidence when the failure is reproducible.

## Method

### 1. Capture the symptom precisely

Record:

- expected behavior;
- observed behavior;
- where and when it occurs;
- reproducibility/frequency;
- relevant environment/version/config differences;
- exact failure output when available.

Preserve raw evidence before interpreting it.

### 2. Establish a reproduction or observation loop

Prefer the fastest deterministic loop that still contains the failure mechanism:

- one focused test;
- minimal request/input;
- isolated command;
- reduced fixture;
- controlled integration environment;
- repeatable instrumentation for intermittent behavior.

If the failure cannot yet be reproduced, identify what evidence can still narrow it: logs, traces, metrics, state snapshots, recent diffs, correlation IDs, or boundary payloads.

Do not claim a deterministic reproduction when you only observed the symptom once.

### 3. Identify the failure boundary

Ask where the first known-good state becomes known-bad.

Trace relevant boundaries such as:

- caller -> callee;
- parser -> domain object;
- application -> database;
- service -> external API;
- source -> build artifact;
- event producer -> consumer;
- state transition -> rendering/output.

Inspect inputs and outputs at boundaries before opening every implementation file.

### 4. Build a small hypothesis set

Rank hypotheses using existing evidence.

For each hypothesis capture:

```text
Hypothesis:
Evidence supporting it:
Evidence against it:
What observation would discriminate it:
Cheapest safe experiment:
```

Keep the set small. Add alternatives when evidence contradicts the current model, not merely to be exhaustive.

### 5. Run discriminating experiments

A good experiment changes or observes something that makes competing hypotheses predict different outcomes.

Examples:

- hold input constant and change only configuration;
- bypass one boundary with a known-good fixture;
- compare pre/post serialization values;
- run the same test against two revisions;
- add temporary instrumentation around the suspected state transition;
- isolate concurrency or ordering rather than changing timing blindly.

Prefer instrumentation and targeted probes before permanent code changes.

### 6. Localize the root cause

A root cause should explain:

- the observed symptom;
- why it occurs under the reproduced conditions;
- why nearby successful cases do not fail;
- why the proposed change should remove the failure mechanism.

If the explanation cannot account for the observations, the diagnosis is incomplete.

### 7. Fix the narrowest authoritative cause

Correct the source of the invalid state/decision where practical, not every downstream symptom.

Examples:

- validate/normalize at the authoritative boundary rather than adding defensive checks in five consumers;
- fix ownership/lifecycle rather than adding delays to a race;
- correct the shared serializer rather than patching one rendered output, if the serializer is genuinely the source.

But do not broaden to a shared component unless evidence proves the shared component is wrong for all affected callers.

### 8. Prove causality after the fix

Use the original reproduction/observation loop:

1. demonstrate the previous failure no longer occurs;
2. demonstrate the intended behavior;
3. run relevant neighboring regression evidence;
4. remove temporary debugging instrumentation unless it has durable operational value;
5. inspect the actual diff for accidental workaround behavior.

When practical, preserve a regression test that would fail if the root cause returned.

## Intermittent failures

For flaky/timing/concurrency problems:

- estimate frequency rather than relying on one pass;
- control seeds, clocks, scheduling, network responses, or external state where feasible;
- compare distributions/repeated trials when deterministic reproduction is impossible;
- distinguish **FLAKY** from **PASS**;
- avoid increasing timeouts/sleeps unless evidence shows the allowed latency itself is the intended contract.

A reduction in failure frequency is not proof of elimination.

## Expected output

For non-trivial debugging:

```text
DEBUG EVIDENCE
Symptom:
Reproduction/observation loop:
Known facts:
Top hypotheses:
Discriminating experiment(s):
Root cause:
Fix:
Causal proof:
Regression evidence:
Residual uncertainty:
```

Keep this internal unless the user benefits from seeing it.

## Decision points

### Instrument vs edit

Instrument first when you do not yet know which state transition or boundary is wrong. Edit when evidence identifies an authoritative incorrect behavior.

### Bisect vs inspect

Use revision comparison/bisect when the failure is known to have appeared between working and failing revisions and the history can reduce uncertainty faster than code inspection.

### Workaround vs root fix

Use a workaround only when the root fix is unavailable or disproportionate and the trade-off is explicit. Do not silently relabel a workaround as root-cause correction.

### Ask for environment data vs continue locally

Ask only when missing runtime state, credentials, production-only evidence, user reproduction details, or other inaccessible context prevents meaningful discrimination.

## Failure modes and anti-patterns

- Shotgun edits across multiple plausible causes.
- Searching by technology keyword instead of following the failing path.
- Treating correlation as causation.
- Increasing retries, timeouts, sleeps, or catch-all exception handling without proving the failure mechanism.
- Mocking away the boundary that causes the defect.
- Stopping when the symptom disappears without explaining why.
- Ignoring evidence that contradicts the favored hypothesis.
- Leaving debugging logs, bypasses, flags, or temporary code accidentally enabled.
- Calling an intermittent failure fixed after one successful run.

## Verification of debugging quality

Before handoff:

- symptom and expected behavior are precise;
- facts and hypotheses are distinguishable;
- at least one experiment or direct evidence discriminates the selected root cause from alternatives for non-obvious failures;
- the fix targets an authoritative cause rather than merely masking output;
- original reproduction is green after the fix;
- relevant regressions are checked or truthfully marked not run;
- residual uncertainty is explicit.

## Handoff

Use `tdd-bug-reproduction` to preserve a reliable failing/passing behavioral regression when applicable.

Use `verification-before-completion` to calibrate broader proof and final claims against the actual diff.
