# M3 Pack 3 — Production Evidence & Operations

Status: experimental implementation candidate
Date: 2026-08-25
Parent contract: `STABLE_EXPERT_PACK_CONTRACT_M3.md`

## Purpose

`production-evidence-operations` is the third initial Stable Expert Pack in the Modern SEF roadmap.

Its durable value is not generic advice such as “check production after deploy.” It provides an executable evidence evaluator that distinguishes:

- a deployment command/provider event that completed;
- the release that is actually serving;
- runtime health and critical user/service smoke behavior;
- operational visibility;
- recovery readiness;
- post-deploy evidence.

A provider-reported successful deployment is therefore insufficient by itself for a passing delivery claim.

## Tool boundary

The pack declares two abstract tool requirements:

```text
hosting
observability
```

It does not implement or authenticate those tools. M4 Tool Capability Resolution binds them to actual Codex/plugin/MCP/CLI/project surfaces.

## Evidence document

Input schema identifier:

`sef.production-evidence-operations.v1`

The document contains:

- `release`: target environment, intended/deployed release references, deployment evidence and runtime-identity evidence;
- `health`: required current-runtime health evidence;
- `smoke_checks`: declared critical/non-critical post-deploy behaviors;
- `observability`: explicitly accounted operational signals;
- `recovery`: selected recovery strategy and verification evidence;
- `post_deploy`: observation-window definition and evidence.

Supported release environment kinds:

```text
PREVIEW
STAGING
PRODUCTION
```

## Deployment and runtime identity

`deployment_status=PASS` alone is insufficient.

A passing claim requires:

1. deployment evidence reference;
2. `runtime_identity_status=PASS`;
3. runtime-identity evidence showing which release is actually serving.

This prevents a stale/previous version from being mistaken for the newly deployed artifact merely because the deploy API returned success.

## Health and smoke semantics

At least one smoke check must be declared `blocking=true`.

Blocking checks:

- `FAIL` → overall `FAIL`;
- `NOT_RUN`/`INCONCLUSIVE` → overall `INCOMPLETE` unless another failure already exists;
- `PASS` without evidence → `INCOMPLETE`.

Non-blocking checks remain visible as warnings and do not by themselves prevent `PASS`.

The health check is always evidence-bearing and cannot be marked `N_A`.

## Observability accounting

The document must account for exactly these durable controls:

```text
logs
error_visibility
metrics
alerting
```

This is not a claim that every release requires every control. Each item is either:

- `required=true`, with a real status/evidence requirement; or
- `required=false`, `status=N_A`, no evidence reference.

At least one observability control must be required. A release cannot pass with zero operational visibility.

Provider-specific mechanisms and queries remain JIT/tool concerns.

## Recovery semantics

Supported strategies:

```text
ROLLBACK
REDEPLOY_PREVIOUS
ROLL_FORWARD
NONE
```

`NONE` is representable for truthful reporting but cannot support `PASS`.

Evidence kinds:

```text
REHEARSAL
OBSERVED_RECOVERY
CURRENT_RECOVERY
NONE
```

A `REHEARSAL` cannot declare `PRODUCTION` as its environment kind. This prevents a planned safety rehearsal from being silently performed against production. Actual authorized production recovery events can be represented as observed/current recovery evidence instead.

The pack never triggers recovery itself.

## Post-deploy observation

A passing release requires:

- post-deploy status `PASS`;
- a `window_ref` describing the chosen observation window;
- an evidence reference for what was observed.

The pack deliberately does not hard-code one universal duration. Appropriate observation duration depends on release surface, traffic, async work and risk. The Delivery Mission chooses a proportionate window and records it.

## Decision semantics

### `PASS`

All blocking evidence is present and passing:

- deployment;
- runtime identity;
- health;
- blocking smoke checks;
- required observability controls;
- recovery verification;
- post-deploy observation.

Warnings from non-blocking smoke checks may remain visible.

### `FAIL`

Observed evidence demonstrates a material operational problem, including deployment failure, wrong running release, health failure, blocking smoke failure, required observability failure, failed/missing recovery strategy, or failed post-deploy observation.

### `INCOMPLETE`

The evidence cannot yet support the claim because required verification is missing, not run or inconclusive.

`INCOMPLETE` must not be promoted from source-code inspection, provider optimism or model confidence.

## Qualification

The deterministic qualification covers 32 controls:

- M3 pack contract conformance;
- deterministic manifest inclusion of all three initial packs;
- successful production evidence;
- runtime identity mismatch;
- deployment failure and missing deployment evidence;
- health failure and missing evidence;
- blocking/non-blocking smoke semantics;
- duplicate/missing blocking smoke declarations;
- complete observability accounting;
- minimum operational visibility;
- required observability failure/missing evidence;
- explicit `N_A` semantics;
- recovery presence, failure and evidence;
- no fake recovery evidence when strategy is `NONE`;
- no production-labeled recovery rehearsal;
- post-deploy failure/missing window/missing evidence/not-run handling;
- explicit non-claims;
- frozen legacy runtime integrity.

The qualification itself performs zero hosting, observability, model or network calls.

## Explicit non-claims

This pack does not yet prove that SEF can autonomously:

- deploy to a real provider;
- identify a running release through live provider tooling;
- perform browser/service smoke checks;
- read production logs/metrics;
- create alerts/monitors;
- execute rollback/redeploy/roll-forward operations;
- establish that SEF outperforms native Codex operationally.

Those outcome claims require M4 tool binding, M5 Delivery Mission integration and M6 comparative evaluation.
