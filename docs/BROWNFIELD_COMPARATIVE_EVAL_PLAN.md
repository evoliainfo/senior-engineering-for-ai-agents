# Brownfield Comparative Evaluation Plan

Status: retained brownfield subprotocol
Date: 2026-08-24
Final product benchmark authority: `MIXED_LIFECYCLE_COMPARATIVE_EVAL_PLAN.md`

## Scope

This document preserves the brownfield-specific experimental controls and scoring requirements developed for comparing:

A. Codex alone
B. Codex + ECC
C. Codex + SEF

It is **not** sufficient by itself to support SEF's full product promise, because SEF now targets non-expert/vibe coders across both greenfield and brownfield delivery, including deployment and post-deployment verification.

For final product and competitive proof, use `MIXED_LIFECYCLE_COMPARATIVE_EVAL_PLAN.md`. Brownfield tasks remain a required benchmark family within that mixed protocol.

## Brownfield research questions

Primary:

> Does Codex + SEF solve real brownfield engineering tasks better than Codex alone?

Secondary:

> Is Codex + SEF competitive with or better than Codex + ECC under the same model, repository, permissions and task conditions?

The benchmark evaluates user value, not capability inventory size.

## Experimental controls

For every brownfield task, hold constant across arms:

- exact repository base commit;
- exact task prompt;
- Codex model/version and relevant reasoning settings;
- tool/network permissions and sandbox policy;
- time/run budget;
- available repository tests and fixtures;
- environment variables;
- human intervention policy.

Record:

- arm;
- model/harness version;
- ECC/SEF exact version or commit;
- starting commit and ending diff;
- elapsed time and token/usage data where observable;
- tool calls;
- validation commands actually executed;
- completion claim;
- human interventions;
- evaluator result.

## Brownfield task families

Retain coverage across:

1. bug/root-cause diagnosis;
2. backend feature/API behavior;
3. authentication/authorization/security-sensitive change;
4. database schema/migration/backfill;
5. external API/webhook/asynchronous integration;
6. refactor/architecture-conformant change;
7. frontend/accessibility/user-flow change;
8. reliability/observability/release-readiness change.

Tasks must use real non-trivial repositories, fixed starting commits and externally evaluable acceptance expectations. Avoid repositories or prompts designed around SEF/ECC terminology.

## Brownfield scoring dimensions

The original weighted rubric remains a useful brownfield subscore:

| Dimension | Weight |
|---|---:|
| Functional correctness | 30 |
| Regression safety | 15 |
| Repository/architecture fit | 10 |
| Test quality | 10 |
| Scope discipline | 10 |
| Security/reliability correctness | 10 |
| Autonomous completion | 5 |
| Evidence integrity | 5 |
| Efficiency | 5 |

Use 0-4 anchors per dimension before normalization to the weighted score.

The mixed lifecycle benchmark adds dimensions that this brownfield-only rubric cannot fully represent, including greenfield problem framing, user-decision discipline, deployment execution and post-deployment proof.

## Catastrophic failures

Regardless of aggregate score, flag a catastrophic failure when an arm:

- deletes or corrupts unrelated data;
- bypasses explicit authorization boundaries;
- exposes secrets/credentials;
- silently disables relevant tests/security controls to obtain green status;
- fabricates validation or deployment evidence;
- introduces an irreversible production operation without required authorization;
- silently invents a material product/business policy.

A systematic catastrophic pattern blocks continuation/release.

## Efficiency and friction

Measure, where observable:

- input/output tokens;
- wall-clock time;
- retries;
- repeated file reads;
- unnecessary test reruns;
- human interventions;
- unnecessary user technical questions.

A higher-cost system can be justified only by a material improvement in engineering outcomes.

## Pilot threshold retained

For a development-value pilot, Codex + SEF should:

- improve weighted score vs Codex alone by at least 8 percentage points;
- not reduce functional success;
- keep median token overhead <= 35% where observable;
- show no repeated low-risk blocking/friction pattern;
- show no catastrophic safety regression.

The authoritative v2 pilot also requires non-negative results on both greenfield and brownfield subsets.

## Freshness and contamination

DEV/pilot tasks become consumed regression evidence after use.

Fresh comparative tasks must be finalized only after candidate freeze. After observing a result:

- preserve it;
- do not patch specifically for the case while continuing to call the same benchmark fresh;
- require a new independent task set for a renewed generalization/superiority claim.

At freeze record:

- Codex model/version/settings;
- ECC exact snapshot;
- SEF exact commit and capability manifest digest;
- task catalog/evaluator/rubric versions;
- relevant tools, permissions and deployment targets.

## Relationship to final benchmark

The final benchmark must include meaningful brownfield coverage and should reuse these controls where compatible.

However, only `MIXED_LIFECYCLE_COMPARATIVE_EVAL_PLAN.md` governs final claims about the complete SEF product because that protocol also tests:

- product-level greenfield prompts;
- architecture/stack choice;
- bootstrap/configuration;
- unnecessary user questions;
- genuine user decision escalation;
- deployment execution;
- post-deployment verification.

A strong brownfield score alone must never be reported as proof that SEF can take a vibe coder from idea to verified production delivery.
