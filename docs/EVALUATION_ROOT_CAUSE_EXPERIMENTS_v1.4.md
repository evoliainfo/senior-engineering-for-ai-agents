# SEF v1.4 Root-Cause Probe Program

Status: PRE-FIX EXPERIMENT DESIGN

Baseline runtime: `v1.4.0-beta` (`sef.py` SHA-256 `31e3dfc1b1a173c83f0a85e2aad6fe4080f33899f328261aa2129a060f5ac68e`).

Purpose: falsify or confirm the four root-cause hypotheses documented in `docs/EVALUATION_ROOT_CAUSE_ANALYSIS_v1.4.md` before any runtime change.

## 1. Probes are not benchmark scenarios

The locked 48-scenario benchmark remains the evaluation target. These diagnostic files live under `evals/probes/root_cause/`, outside the official scenario directories.

They may be inspected while designing future candidate fixes, so they are **not held-out evidence**, are not counted in the official 48, and must never replace the DEV/CHALLENGE split.

The question they answer is narrower:

> Does the hypothesized failure mechanism generalize beyond the exact benchmark wording that exposed it?

A candidate runtime change is not justified merely because it turns one original FAIL green. It must improve the relevant probe family while preserving positive controls and the official baseline.

## 2. Shared rules

1. Establish the immutable v1.4 probe baseline before editing `sef.py`.
2. Use the existing black-box runners only; do not import private SEF internals.
3. Keep fresh fixture state per probe.
4. A probe FAIL is evidence, not a CI infrastructure failure.
5. CI gates malformed contracts, runner errors, missing results, checksum drift and harness faults only.
6. Record both under-routing and over-routing.
7. Include positive controls so a future suppression rule cannot appear to improve by disabling a route globally.
8. During candidate iteration, replay official DEV + probes; do not tune on CHALLENGE.
9. Actual Git diff remains an independent safety layer and must not inherit request-text negation.
10. Do not hard-code probe sentences into routing logic.

## 3. Experiment A — RC-1 normalized task concepts

### Hypothesis

The request router is materially brittle because surface text is mapped directly to regular-expression triggers without an intermediate normalized task-concept representation.

### Initial probes

The first slice covers:
- authorization expressed as `authorized administrator`;
- stored-record migration expressed with the verb `migrate`;
- plural `webhooks`;
- an inbound-event `callback endpoint` positive control;
- third-party SaaS/vendor dependency;
- queue-worker/background semantics;
- search discoverability expressed as `findable in Google/search engines`;
- explicit `SEO` positive control.

### Confirmation rule

RC-1 is supported if semantically equivalent formulations produce materially different routing while the positive controls remain reachable.

Strong evidence includes:
- authorization semantics present but `AUTHORIZATION` absent;
- migration of existing state present but `DATABASE_MIGRATION` absent;
- provider-event trust semantics present but `WEBHOOK_TRUST` absent;
- queue-worker semantics present but `BACKGROUND_JOB` absent.

### Future candidate gate

A candidate must eliminate critical semantic false negatives, improve ordinary variants, preserve positive controls, introduce no new critical official-DEV regression, and avoid materially increasing R0/R1 over-governance. A synonym list is acceptable only if measured behavior supports a stable concept model; probe-specific hard-coding is invalid.

## 4. Experiment B — RC-2 polarity / non-goals

### Hypothesis

Trigger detection is polarity-blind: a sensitive term activates governance even when the request explicitly excludes that area from scope.

### Initial paired probes

- `do not deploy / prepare a release` versus positive production-deployment intent;
- `do not change authentication/authorization` versus a positive authorization-rule change.

### Confirmation rule

RC-2 is supported when the negative formulation activates the same sensitive route as its positive control.

### Future candidate gate

A candidate must suppress only clearly scoped non-goals, preserve paired positive controls, stay conservative under ambiguity, and never allow request negation to hide a sensitive risk detected from the real Git diff.

## 5. Experiment C — RC-3 task-material context gating

### Hypothesis

Broad project-level context candidates can become blocking task decisions even when the current task is unrelated to that context.

### Initial probes

Unrelated-task treatments:
- `company` project + footer typo;
- careers/people project + heading spacing.

Material positive controls:
- explicit cross-tenant organization task;
- explicit candidate personal-data collection task.

### Confirmation rule

RC-3 is supported if unrelated low-risk tasks are blocked solely because a broad project candidate remains unconfirmed, while material positive controls remain governed.

### Future candidate gate

A candidate must let an unrelated R0/R1 task proceed without deleting project-level uncertainty, reactivate blocking when a task touches the corresponding boundary, preserve `MULTI_TENANT` and `PRIVACY` protection for positive controls, and never infer that the whole project is single-tenant/non-PII merely because one task is unrelated.

## 6. Experiment D — RC-4 evidence state and history

### Hypothesis

Verification state is too coarse and too last-result-oriented: inconsistent same-HEAD observations can be erased by the latest pass, while unavailable evidence is collapsed into ordinary failure.

### Initial probes

- same-revision PASS/FAIL/PASS variability;
- unavailable external evidence;
- genuine critical regression failure as a hard-block positive control.

These replicate the Evidence/Release findings with different task wording; the official scenarios remain the primary benchmark evidence.

### Confirmation rule

RC-4 is supported if variable outcomes are not represented as `FLAKY`/`INCONCLUSIVE` and the last pass becomes release-review-ready, or if unavailable evidence is represented only as ordinary `FAIL`, while a genuine regression still blocks release.

### Future candidate gate

A candidate must retain an append-only or equivalently lossless record of materially relevant observations for a revision, distinguish `FAIL` from `UNAVAILABLE/INCONCLUSIVE`, prevent known same-revision flakiness from becoming release-ready solely because the last attempt passed, preserve genuine failure blocking, and define an explicit recovery rule for clearing uncertainty.

## 7. Initial probe inventory

- RC-1: 8 routing probes
- RC-2: 4 polarity probes
- RC-3: 4 materiality probes
- RC-4: 3 evidence probes

Total: **19 diagnostic probes**.

These 19 are intentionally a discriminant first slice, not the maximum probe set. We expand a family only if the result is ambiguous or a root-cause hypothesis needs to be split.

## 8. Decision sequence

After the immutable v1.4 probe baseline is recorded:

1. classify PASS/FAIL by root cause;
2. test whether the four hypotheses still explain the observed patterns;
3. reject or split hypotheses that do not generalize;
4. specify the smallest architectural candidate for RC-1 first;
5. implement that candidate on a separate branch;
6. replay official DEV + root-cause probes;
7. inspect regressions and over-governance;
8. only then move to RC-2, RC-3 and RC-4 candidates;
9. keep CHALLENGE untouched during tuning;
10. after candidates stabilize, run the held-out challenge gate and later L2/L3 agent/pilot layers.

## 9. Non-goals

This program does not create a new SEF version, change the immutable v1.4 tag, alter routing behavior, dictate that an LLM/NLP router is required, permit automatic learning from probes into policy, or replace expert review for security-critical routing.

The objective is causal evidence before intervention.
