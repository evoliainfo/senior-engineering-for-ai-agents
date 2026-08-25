# M5 — `launch-production-web-product` orchestration slice

Status: implementation candidate, not end-to-end M5 completion
Date: 2026-08-25
Parent roadmap: `MODERN_SEF_BUILD_PLAN.md`

## Purpose

This is the first executable slice of the first Modern SEF Delivery Mission.

It composes the already-qualified M1-M4 substrates into one deterministic decision surface:

```text
mission spec
+ Project State Spine
+ current Codex tool inventory
+ JIT Expertise capsules
+ Stable Expert Pack contracts
        ↓
next action + blockers + relevant context + active packs + tool requirements
```

The slice intentionally does not execute the next action. Its job is to prevent the agent from skipping prerequisites or overstating delivery progress before live execution is wired in.

## Canonical truth

Project State remains the only canonical delivery-state truth.

The mission decision references the state digest and maps the current M1 state to exactly one next action:

| Project State | Next action |
| --- | --- |
| `FRAMED` | `PLAN_ARCHITECTURE` |
| `ARCHITECTED` | `IMPLEMENT_PRODUCT` |
| `IMPLEMENTED` | `VERIFY_LOCAL_PRODUCT` |
| `VERIFIED_LOCAL` | `DEPLOY_AND_VERIFY_PREVIEW` |
| `PREVIEW_VERIFIED` | `PROVE_RELEASE_READINESS` |
| `RELEASE_READY` | `DEPLOY_PRODUCTION` |
| `DEPLOYED` | `VERIFY_PRODUCTION` |
| `POST_DEPLOY_VERIFIED` | `COMPLETE` |

The decision function never calls `advance_delivery_state`. Advancing remains an explicit evidence-backed M1 operation after execution/verification.

## Mission specification

Schema:

`sef.delivery-mission.launch-production-web-product.v1`

The agent structures:

- the first-delivery outcome;
- blocking acceptance criteria and their authority (`USER` or `ENGINEERING`);
- actual technical failure surfaces: web UI, persistent data, material data change, identity/access, billing and external integrations;
- JIT Expertise needs for selected provider/framework/repository/standard contracts;
- the project-state context domains each expertise need depends on.

This is not a prompt dump. The spec is deliberately compact and machine-checkable.

`initialize_project_state()` creates the initial M1 `FRAMED` state and persists each acceptance criterion as an evidence-backed requirements decision. Later mission evaluations reject outcome/acceptance drift between the mission spec and Project State.

## Progressive disclosure

Each next action has a bounded list of Project State domains to load. For example, architecture planning reads product/requirements and relevant risk/integration/data domains, while production verification reads deployment/observability/quality/release domains.

The mission therefore does not inject the complete project history into every action.

## Stable Expert Pack activation

Packs are activated only when their failure surface becomes relevant:

- `web-experience-visual-quality` for local/preview/release visual-browser quality;
- `data-change-safety` only when `material_data_change=true` and the mission reaches data-sensitive verification/release actions;
- `production-evidence-operations` when the project is deployed and the next task is production verification.

Pack tool requirements are merged with mission-native requirements using the strictest required access/sensitivity for each capability.

## Tool requirements and M4 composition

Examples:

- implementation requires `source_control` write access;
- local web verification requires `browser` + `visual_capture`;
- persistent/auth/billing/integration surfaces add `database_admin`, `auth_admin`, `billing_admin` or `external_provider_sandbox` only when relevant;
- preview requires sandbox-capable hosting plus browser/visual evidence;
- release readiness requires CI visibility and material-data safety where applicable;
- production deployment requires production-sensitive hosting write capability;
- production verification requires production-sensitive browser/observability plus the operations pack requirements.

The mission calls the M4 Codex inventory bridge. Any result other than `READY` becomes an explicit blocker. In particular:

`AUTHORIZATION_REQUIRED` is not converted into permission simply because a write-capable tool exists.

### Snapshot freshness boundary

The M4 adapter proves what the Codex harness reported at `captured_at`. M5 additionally compares that capture time to the current mission-decision time.

A snapshot older than `max_tool_age_seconds` cannot support a current action and produces:

`TOOL_INVENTORY_STALE`

A snapshot timestamp later than the decision time is rejected as inconsistent.

This prevents a previously authenticated/authorized tool state from being silently reused as current state.

## JIT Expertise composition

A declared expertise need becomes mandatory from `ARCHITECTED` onward.

M5 requires exactly one matching capsule by:

- project;
- mission need;
- subject;
- selected Project State context.

It validates the M2 capsule and checks:

- capsule status;
- selected-context invalidation;
- authoritative source freshness;
- current semantic tool capability.

M4 owns observation freshness. Therefore M5 does not treat a different `observed_at` timestamp alone as a semantic tool change. It compares capability, availability and access. A real access/availability regression produces `TOOL_CAPABILITY_CHANGED`.

This integration rule avoids recompiling JIT expertise merely because the same tool was re-observed later, while still invalidating expertise when the usable capability changes.

## Decision report

Schema:

`sef.delivery-mission-decision.launch-production-web-product.v1`

A decision includes:

- current project state/digest;
- next action;
- bounded state context domains;
- active Expert Packs;
- merged M4 requirements;
- optional M4 bridge report;
- JIT readiness per declared need;
- explicit blockers;
- content hash.

Explicit non-claims are part of every decision:

```text
tool_execution_performed = false
state_advanced_by_decision = false
deployment_performed = false
production_authorization_granted = false
model_assertion_used_as_evidence = false
```

## Qualification

`evals/run_launch_production_web_product_m5.py` currently defines 34 deterministic controls covering:

- mission schema and M1 initialization;
- all eight state→action mappings;
- progressive-disclosure context;
- source-control/browser/visual/hosting/CI requirements;
- material-data pack activation and non-activation;
- production authorization blocking;
- production operations pack activation;
- missing/stale Codex inventory;
- dynamic data/auth/billing/integration capability requirements;
- missing, ready, expired and context-invalidated JIT capsules;
- semantic tool re-observation vs actual access regression;
- state/spec outcome and acceptance alignment;
- web-scope/data-surface invariants;
- secret-value rejection;
- decision tamper detection;
- proof that deciding does not mutate Project State;
- frozen legacy runtime integrity.

Qualification itself performs zero model, provider, network, deployment or tool-execution calls.

## What this slice proves

If qualified, the bounded claim is:

> Given a structured outcome/acceptance mission, valid Project State, an explicit current Codex tool inventory and any required JIT capsules, SEF can deterministically decide the next production-web delivery action, load only relevant Expert Packs, resolve required capabilities, and state exact blockers without executing tools or overstating delivery state.

## What remains before M5 can be called complete

The roadmap requires real execution evidence. Later M5 slices must connect this decision loop to actual agent actions and demonstrate at least:

- architecture/implementation evidence creation;
- real browser local verification;
- visual/accessibility/responsive pack execution;
- preview deployment and verification;
- release/data/security checks;
- authorized production deployment or truthful production block;
- deployed-runtime identity and observability evidence;
- post-deploy critical-journey verification;
- evidence ingestion and M1 state advancement after each verified gate;
- fresh-session continuation.

Until those are demonstrated, this PR must not be described as end-to-end M5 completion.
