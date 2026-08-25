---
name: production-evidence-operations
description: Evaluate deployment and post-deploy operational evidence across runtime identity, health/smoke, observability, recovery and post-deploy monitoring. Use when a mission claims a preview, staging or production deployment is actually healthy and recoverable.
---

# Production Evidence & Operations

Use this pack when a mission has deployed a material web/service release and must prove more than “the deploy command succeeded.”

## What this pack does

It converts deployment and operational observations into a deterministic evidence decision. It does not assume that a provider-reported successful deployment means the intended release is actually serving correctly.

## Before evaluation

Declare the release target and the intended/deployed release references. Collect evidence for:

- deployment completion;
- runtime identity showing which release is actually serving;
- the observed runtime release identity itself, which must match the deployed release identity;
- health verification;
- at least one blocking smoke journey;
- operational observability controls;
- recovery strategy verification;
- a post-deploy observation window.

## Observe with real tools

Resolve `hosting` and `observability` through M4/tool resolution. The active harness may use Codex-native tools, plugins, MCP or project tooling; this pack does not invent credentials or provider availability.

For the deployed target, capture evidence that binds checks to the current running release rather than to source code or a previous deployment. Record `observed_release_ref` from that runtime evidence. A `runtime_identity_status=PASS` declaration is insufficient if `observed_release_ref` is absent or differs from `deployed_release_ref`.

## Evaluate

Run `evaluators/evaluate.py` against the structured evidence document.

The evaluator returns:

- `PASS` only when deployment is proven, the observed runtime release matches the deployed release, health passes, every blocking smoke check passes, required observability controls pass with evidence, recovery is proven, and post-deploy monitoring is clear;
- `FAIL` when observed evidence demonstrates a material deployment/runtime/health/smoke/observability/recovery/post-deploy defect;
- `INCOMPLETE` when required evidence is missing, not run or inconclusive.

A non-blocking smoke failure remains visible as a warning but does not by itself fail the release gate.

## Observability accounting

The document must explicitly account for the durable controls:

- `logs`
- `error_visibility`
- `metrics`
- `alerting`

Each control is either required for this release and evidenced, or explicitly marked `N_A`. At least one observability control must be required; the pack will not accept a release with no operational visibility at all.

## Recovery semantics

Declare one of `ROLLBACK`, `REDEPLOY_PREVIOUS` or `ROLL_FORWARD`. `NONE` cannot support a passing release claim.

A rehearsal may run on preview/staging but must not be labeled as a production rehearsal. Evidence from an actual observed production recovery can be recorded separately by the mission when legitimately available and authorized.

## Post-deploy semantics

A passing deploy must include a post-deploy observation window reference and evidence reference. The pack does not hard-code a universal duration; the mission/project chooses a proportionate window and the evidence records what was observed.

## Scope boundary

This pack does not deploy software, choose a hosting provider, own credentials, create monitors, trigger a production rollback, or claim provider-specific operational correctness. Those live-tool and provider details belong to JIT Expertise, M4 capability resolution and Delivery Missions.
