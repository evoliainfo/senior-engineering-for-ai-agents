# M5 — Deterministic Codex execution hand-off

Status: implementation candidate, not end-to-end M5 completion
Date: 2026-08-25
Parent mission: `launch-production-web-product`

## Purpose

The first M5 slice decides what should happen next. The second verifies execution evidence and advances M1 only when the evidence supports one transition.

This slice closes the deterministic hand-off between them:

```text
M5 decision
    ↓
Codex execution plan
    ↓
active Codex harness executes
    ↓
execution result + artifacts
    ↓
M5 evidence acceptance
```

The plan does not execute tools. It tells the harness exactly which already-approved context, expertise, tool surfaces, Expert Packs and evidence contracts apply to the current action.

## Canonical authority

The execution plan is not a new source of truth or authorization.

Canonical authority remains:

- M1 Project State for delivery truth;
- the exact M5 decision for current action and blockers;
- M2 JIT capsule content for task-specific current expertise;
- M3 Expert Pack contracts for reusable evaluators;
- M4 resolution for selected tool surfaces and authorization state.

The plan is a deterministic projection of those contracts.

## What the plan binds

Schema:

`sef.codex-execution-plan.launch-production-web-product.v1`

Each plan binds:

- mission id and project id;
- exact decision SHA-256;
- exact Project State SHA-256;
- exact selected Project State context SHA-256 and domains;
- current delivery state and next action;
- exact JIT capsule id + content SHA-256 for every ready expertise need;
- exact M4 requirement and selected surface;
- selected surface access, sensitivity, authentication and authorization state;
- required M1 primary evidence kind;
- minimum tool-support evidence slots;
- active M3 pack skill/evaluator references;
- pack observation schema and mission-specific scope;
- exact result-envelope binding returned to the M5 evidence API;
- content SHA-256.

## Why JIT uses both id and digest

A stable capsule id is not a version identity. A capsule can be regenerated under the same id after documentation, project context or constraints change.

The public M5 decision therefore records `capsule_sha256` alongside `capsule_id`, and the execution plan carries the same pair.

Codex must load the capsule whose content digest matches the plan. It must not silently load a newer/different capsule under the same id. A changed capsule requires a new M5 decision.

## Recomputability rule

A plan cannot become valid merely because an agent edits it and recalculates `content_sha256`.

When the exact M5 decision is supplied to `validate_execution_plan`, SEF recomputes and compares:

- Project State context domains/digest;
- JIT bindings;
- M4 selected tool projection;
- evidence slots;
- M3 pack tasks and mission scope.

Substitution therefore remains detectable even after a syntactically valid re-seal.

## M4 freshness at hand-off time

A decision may have been valid when it was created but become stale before execution starts.

For tool-bound actions, plan generation rechecks the M4 resolution timestamp against its `max_observation_age_seconds`. If the snapshot is stale, plan generation fails and the harness must obtain a fresh inventory and decision.

This prevents an old authenticated/authorized tool snapshot from being carried indefinitely into later execution.

## Project State progressive disclosure

The plan does not embed the entire Project State.

It carries:

- the exact `context_domains` selected by the decision;
- `project_context_sha256`.

The harness loads only those domains and can verify that it is using the same bounded context the decision used.

## Expert Pack hand-off

For every active M3 pack, the plan includes:

- `skill_ref`;
- `evaluator_ref`;
- evaluator-declared observation schema;
- mission-specific expected scope;
- exact M4 tool bindings needed by the pack;
- pack evidence requirements/outputs;
- observation artifact namespace.

The observation document can be assembled by the agent or deterministic harness. Evidence-bearing references inside it are still validated downstream and must resolve to declared `TOOL` artifacts.

## Artifact slots

The plan declares minimum required output slots rather than pretending to enumerate every screenshot/log/file an action may produce.

It always includes exactly one primary M1 evidence slot. Tool-bound actions bind that slot to the action's primary capability/surface. Additional selected capabilities receive required tool-support slots. Active packs receive observation slots.

Pack-specific evidence may require additional tool-produced artifacts beyond these minimum slots; those are governed by the pack observation contract and downstream evidence validation.

## Sequence

Canonical hand-off sequence:

```text
LOAD_BOUND_PROJECT_CONTEXT
LOAD_BOUND_JIT_EXPERTISE
LOAD_ACTIVE_EXPERT_PACKS
EXECUTE_ACTION
COLLECT_SELECTED_TOOL_ARTIFACTS
BUILD_ACTIVE_PACK_OBSERVATIONS
SEAL_EXECUTION_RESULT
SUBMIT_RESULT_TO_SEF_EVIDENCE_API
```

Steps that have no applicable JIT capsule or pack are no-ops; they do not create new requirements.

## Explicit non-claims

Every plan states:

```text
tool_execution_performed = false
evidence_collected = false
state_advanced = false
authorization_granted = false
agent_may_change_selected_surface = false
agent_may_substitute_capsule = false
plan_is_authorization_source = false
```

This slice does not claim that Codex has actually executed the plan.

## Qualification

`evals/run_m5_codex_execution_plan.py` covers:

- schema contract;
- all seven executable M1 states/actions and primary evidence kinds;
- local/preview/production pack scope;
- truthful agent/system ownership of pack observation JSON;
- exact JIT capsule digest binding;
- blocked/complete decision refusal;
- namespace containment;
- re-sealed M4 surface/access substitutions;
- re-sealed artifact-slot and pack-task substitutions;
- Project State context binding;
- JIT digest substitution;
- M4 snapshot freshness at plan generation;
- deterministic non-execution/non-authorization claims;
- input immutability;
- frozen historical runtime integrity.

Qualification performs zero model, provider, network, deployment or real-tool calls.

## Remaining M5 work

This hand-off is still deterministic fixture qualification. M5 is not end-to-end complete until the plan is consumed in real Codex sessions and produces real evidence for at least:

- local browser/visual verification;
- preview deployment + verification;
- release/data/security checks;
- authorized production deployment or truthful block;
- production runtime/observability verification;
- post-deploy critical journeys;
- fresh-session continuation from persisted state/evidence.
