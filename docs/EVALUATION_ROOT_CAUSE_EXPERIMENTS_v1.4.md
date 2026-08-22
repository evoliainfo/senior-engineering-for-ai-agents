# SEF v1.4 Root-Cause Probe Program

Status: PRE-FIX EXPERIMENT — BASELINE RECORDED

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
- search discoverability expressed in ordinary user language without relying on `SEO`, `crawl`, `indexation`, `sitemap` or other known specialist terms;
- explicit `SEO` positive control.

### Confirmation rule

RC-1 is supported if semantically equivalent formulations produce materially different routing while the positive controls remain reachable.

### Future candidate gate

A candidate must eliminate critical semantic false negatives, improve ordinary variants, preserve positive controls, introduce no new critical official-DEV regression, and avoid materially increasing R0/R1 over-governance. Probe-specific hard-coding is invalid.

## 4. Experiment B — RC-2 polarity / non-goals

### Hypothesis

Trigger detection is polarity-blind: a sensitive term activates governance even when the request explicitly excludes that area from scope.

### Initial paired probes

- `do not deploy / prepare a release` versus positive production-deployment intent;
- `do not change authentication/authorization` versus a positive authorization-rule change expressed with lexical forms already known to v1.4 (`permissions`, `admin`).

### Confirmation rule

RC-2 is supported when the negative formulation activates the sensitive route while a clean positive control demonstrates that the intended route remains reachable.

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

### Confirmation rule

RC-4 is supported if variable outcomes are not represented as `FLAKY`/`INCONCLUSIVE` and the last pass becomes release-review-ready, or if unavailable evidence is represented only as ordinary `FAIL`, while a genuine regression still blocks release.

### Future candidate gate

A candidate must retain an append-only or equivalently lossless record of materially relevant observations for a revision, distinguish `FAIL` from `UNAVAILABLE/INCONCLUSIVE`, prevent known same-revision flakiness from becoming release-ready solely because the last attempt passed, preserve genuine failure blocking, and define an explicit recovery rule for clearing uncertainty.

## 7. Pre-baseline probe review

The first exploratory execution was reviewed before treating its totals as a locked causal baseline. Two probe-design confounders were found and corrected without changing SEF:

1. **SEO probe confounder.** The first `RC1-SEO-001` wording included `crawl` and `index`, both already recognized by v1.4. The treatment was rewritten to ordinary user wording: people should be able to find the public page through a search engine, without specialist SEO vocabulary. The explicit-SEO positive control remains unchanged.
2. **RC-2 auth positive-control confounder.** The first positive control used `authorization` and `administrators`, which themselves exposed RC-1 morphology gaps. It was rewritten to `permissions` and `admin`, lexical forms already recognized by v1.4, so the pair isolates polarity rather than morphology.

These were probe corrections, not runtime tuning. The official benchmark scenarios and v1.4 runtime remained unchanged.

## 8. Recorded v1.4 causal baseline

Final refined CI execution:
- official deterministic routing/actual-diff baseline: **24 = 16 PASS / 8 FAIL**;
- official evidence/release baseline: **4 = 2 PASS / 2 FAIL**;
- official materialized DEV baseline therefore remains **28 = 18 PASS / 10 FAIL**;
- root-cause routing probes: **16 = 6 PASS / 10 FAIL**;
- root-cause evidence probes: **3 = 1 PASS / 2 FAIL**;
- root-cause probes total: **19 = 7 PASS / 12 FAIL**;
- `HARNESS_ERROR`: **0**;
- runtime checksum and embedded self-test: **PASS**.

These arithmetic ratios are **not quality scores**. Probe outcomes are causal evidence and positive controls, not a leaderboard.

### RC-1 — strongly confirmed

Treatment failures:
- `RC1-AUTH-001`: explicit `authorized administrator` object-access semantics miss `AUTHORIZATION`; this is critical.
- `RC1-DATA-001`: `migrate` existing stored timestamps routes `TIME_SEMANTICS` but misses `DATABASE_MIGRATION`.
- `RC1-WEBHOOK-001`: plural `webhooks` misses `WEBHOOK_TRUST`.
- `RC1-SUPPLIER-001`: third-party SaaS/vendor dependency misses `EXTERNAL_SUPPLIER`.
- `RC1-BG-001`: queue worker/retry/exactly-once state semantics miss `BACKGROUND_JOB` and `DATABASE`.
- `RC1-SEO-001`: ordinary wording about people finding a public page through a search engine misses `SEO_WEB_DISCOVERABILITY`.

Positive controls pass:
- `RC1-WEBHOOK-CONTROL-001`: known `callback endpoint` wording routes `WEBHOOK_TRUST`.
- `RC1-SEO-CONTROL-001`: explicit `SEO` wording routes web discoverability.

**Conclusion:** the failure generalizes across authorization, migration, webhook, supplier, async/stateful and search-discoverability domains. Known lexical forms remain reachable while ordinary equivalent formulations fail. RC-1 is not credibly explained as one isolated missing pack rule.

### RC-2 — cleanly confirmed with paired controls

Negative treatments fail:
- `RC2-AUTH-NEG-001`: `do not change authentication, authorization, sessions or permissions` still activates `AUTH_PROTOCOL` and `AUTHORIZATION`.
- `RC2-REL-NEG-001`: `do not deploy / prepare a release` still activates `RELEASE_ENGINEERING`.

Positive controls pass:
- `RC2-AUTH-POS-001`: `Change permissions so only admin...` routes `AUTHORIZATION`.
- `RC2-REL-POS-001`: explicit production-deployment intent routes `RELEASE_ENGINEERING`.

**Conclusion:** the route is reachable when intended, but request polarity/non-goal scope is ignored. RC-2 is confirmed independently of RC-1 morphology.

### RC-3 — cleanly confirmed with materiality controls

Unrelated low-risk treatments fail:
- `RC3-COMPANY-001`: the task itself selects no `MULTI_TENANT` pack, yet implementation is blocked by a broad project-level multi-tenant candidate inferred from `company`.
- `RC3-PII-001`: the task itself selects no `PRIVACY` pack, yet a spacing-only task is blocked by a broad PII candidate inferred from the careers/people project context.

Material positive controls pass:
- `RC3-TENANT-POS-001`: explicit cross-tenant work routes `MULTI_TENANT` and blocks appropriately.
- `RC3-PII-POS-001`: explicit personal-data collection routes `PRIVACY` and blocks appropriately.

**Conclusion:** project uncertainty should be preserved, but not every unresolved project-level possibility is material to every task. RC-3 is confirmed without weakening the safety behavior of the positive controls.

### RC-4 — cleanly confirmed with a genuine-failure control

Treatment failures:
- `RC4-FLAKY-001`: same-revision `LOCAL_PASS → FAIL → LOCAL_PASS` is not represented as flaky/inconclusive; the final release check becomes `READY_FOR_RELEASE_REVIEW`.
- `RC4-UNAVAILABLE-001`: an explicitly unavailable required provider is represented as generic `FAIL`; release remains safely blocked, but the epistemic state is inaccurate.

Positive control passes:
- `RC4-FAIL-CONTROL-001`: a genuine critical regression failure remains `FAIL` and blocks release.

**Conclusion:** the problem is evidence semantics/history, not a general inability to block known failures. RC-4 is confirmed.

## 9. Causal decision

All four hypotheses survive the refined diagnostic program:

- **RC-1: strongly confirmed**;
- **RC-2: confirmed with paired positive controls**;
- **RC-3: confirmed with unrelated/material task pairs**;
- **RC-4: confirmed with an independent genuine-failure control**.

The probe program has therefore reached its intended pre-fix decision threshold. Broadening probes further is not the highest-value next action unless a candidate later produces ambiguous regressions.

The next step is **candidate architecture design for RC-1**, not immediate runtime patching. The candidate must introduce a more stable concept-normalization boundary while keeping policy/risk mapping auditable and deterministic, preserving actual-diff reassessment as an independent safety layer, and avoiding a probe-specific synonym patchwork.

## 10. Candidate sequence

1. Specify the smallest RC-1 candidate architecture and invariants.
2. Review it before code.
3. Implement on a separate branch only after explicit approval.
4. Replay official DEV + all root-cause probes.
5. Reject the candidate if it introduces critical regressions or material R0/R1 over-governance.
6. Keep CHALLENGE untouched during tuning.
7. Only after RC-1 stabilizes, repeat the candidate-design process for RC-2, RC-3 and RC-4.
8. After candidates stabilize, run held-out CHALLENGE and later L2/L3 agent/pilot layers.

## 11. Non-goals

This program does not create a new SEF version, change the immutable v1.4 tag, dictate that an LLM/NLP router is required, permit automatic learning from probes into policy, or replace expert review for security-critical routing.

The objective is causal evidence before intervention.
