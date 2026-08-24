# Project State Spine M1

Status: implementation candidate
Date: 2026-08-24
Architecture basis: `ADR_PROJECT_STATE_AND_JIT_EXPERTISE.md`

## Purpose

Project State Spine gives SEF a compact engineering source of continuity across agent sessions, Delivery Missions and lifecycle stages.

It is not an AI memory system and it does not call a model.

It exists because chat history alone is not a reliable source of truth for a long-running project.

## Default project location

A consuming project can store state at a repository-local path such as:

```text
.sef/project-state.json
```

M1 does not force that path. Harness/mission packaging can decide the final convention later.

## Canonical contract

Schema:

```text
sef.project-state.v1
```

Published JSON Schema:

```text
project_state/project-state.schema.json
```

Executable semantics and integrity validation:

```text
project_state/core.py
```

CLI:

```text
tools/project_state.py
```

## State domains

M1 defines a closed first schema so fresh sessions agree about the meaning of project state:

- `product`
- `requirements`
- `architecture`
- `interfaces`
- `data`
- `identity_access`
- `integrations`
- `environments`
- `quality`
- `security`
- `release`
- `deployments`
- `observability`
- `open_decisions`
- `known_risks`

The schema can evolve through a new version later. M1 deliberately does not permit arbitrary top-level buckets because silent schema drift would destroy continuity between agents.

## Typed project truth

Each state entry is classified as exactly one of:

### `FACT`

Observed project truth. Requires evidence.

Examples:

- a route exists;
- a deployment target is configured;
- a test run passed;
- an integration contract is present in the repository.

### `DECISION`

An authoritative choice. Requires evidence of the decision artifact/source.

Examples:

- user chose paid subscriptions for first release;
- engineering selected a deployment architecture;
- repository ADR fixes an interface boundary.

### `ASSUMPTION`

An explicit working assumption that can be revised. It does not require fabricated evidence.

### `UNRESOLVED`

A real question still requiring resolution. It remains active until replaced/resolved by later state evolution.

## Authority

Entries identify their authority:

- `USER`
- `REPOSITORY`
- `ENGINEERING`
- `EXTERNAL`
- `SYSTEM`

This lets future missions distinguish a user/business decision from an engineering inference without forcing all decisions back onto the user.

## Evidence references, not evidence blobs

Project State stores compact references such as:

```json
{
  "id": "EVID-TEST-014",
  "kind": "local-verification",
  "locator": "artifact://ci/run-123/test-report",
  "observed_at": "2026-08-24T14:00:00Z",
  "status": "OBSERVED",
  "sha256": null
}
```

Large test logs, screenshots, CI output or provider responses stay in their native evidence location.

This protects context size and makes provenance inspectable.

## No secret values

Project State is not a secret store.

M1 rejects several credential-shaped values including common API key/token/private-key forms. This is defense in depth, not a replacement for repository secret scanning.

State may record that a credential is required or that a secure external secret store is configured, but not the credential value itself.

## Delivery state

M1 uses an evidence-derived delivery progression:

```text
FRAMED
ARCHITECTED
IMPLEMENTED
VERIFIED_LOCAL
PREVIEW_VERIFIED
RELEASE_READY
DEPLOYED
POST_DEPLOY_VERIFIED
```

An agent cannot jump directly from `FRAMED` to `DEPLOYED` by assertion.

Every forward transition:

1. moves exactly one stage;
2. references observed evidence;
3. includes the evidence kind required by the target stage.

Required evidence kinds in M1:

| State | Required evidence kind |
|---|---|
| FRAMED | `product-frame` |
| ARCHITECTED | `architecture-decision` |
| IMPLEMENTED | `implementation-change` |
| VERIFIED_LOCAL | `local-verification` |
| PREVIEW_VERIFIED | `preview-verification` |
| RELEASE_READY | `release-readiness` |
| DEPLOYED | `deployment` |
| POST_DEPLOY_VERIFIED | `post-deploy-verification` |

Future Delivery Missions can impose stricter project-specific evidence in addition to these minimum transition semantics.

## Truth can regress

Project truth is allowed to move backwards.

Example:

- project was `IMPLEMENTED`;
- a large rebase invalidates the architecture/change evidence;
- a new observed regression is recorded;
- state can explicitly regress to `FRAMED` or another earlier truthful stage.

This prevents stale success claims from becoming permanent project memory.

## Integrity digest

Every state contains `content_sha256` calculated from canonical sorted JSON excluding the digest field itself.

If a file is edited without resealing through the state layer, validation fails.

This does not provide cryptographic authorship. It provides deterministic integrity/drift detection.

## Progressive disclosure

`select_context()` returns only requested domains plus evidence referenced by those domains.

Example:

```text
architecture mission
  -> load architecture + interfaces + environments
  -> do not load every historical test, product note or deployment event
```

The mission chooses the minimum useful slice.

## CLI examples

Initialize:

```bash
python3 tools/project_state.py init .sef/project-state.json \
  --project-id my-product \
  --product-statement "Enable customers to complete the primary workflow" \
  --evidence-locator conversation://product-frame/1
```

Validate:

```bash
python3 tools/project_state.py validate .sef/project-state.json
```

Load only architecture context:

```bash
python3 tools/project_state.py context .sef/project-state.json \
  --domains architecture,interfaces,environments
```

Add evidence and advance:

```bash
python3 tools/project_state.py add-evidence .sef/project-state.json \
  --id EVID-ARCH-001 \
  --kind architecture-decision \
  --locator repo://docs/architecture.md

python3 tools/project_state.py advance .sef/project-state.json \
  --to ARCHITECTED \
  --evidence EVID-ARCH-001 \
  --reason "Architecture decision is recorded and current"
```

## M1 qualification

`evals/run_project_state_m1.py` contains 16 deterministic controls covering:

- JSON Schema/code contract alignment;
- evidence-backed initialization;
- fact/decision evidence semantics;
- explicit assumptions;
- missing evidence rejection;
- tamper detection;
- credential-shaped secret rejection;
- transition evidence kinds;
- no skipped delivery states;
- truth regression;
- invalidated evidence rejection;
- progressive context selection;
- fresh-process/session roundtrip;
- canonical digest order;
- closed domain schema;
- immutable historical `sef.py` runtime.

No provider/model/API calls are performed.

## Explicit non-claims

M1 does **not** yet prove:

- that SEF improves Codex outcomes;
- that state extraction/update from natural language is reliable;
- that JIT Expertise works;
- that a Delivery Mission can ship a product;
- that production deployment is supported;
- that state can replace code, tests, ADRs, CI or deployment-system truth.

M1 proves only that the continuity substrate itself has a deterministic, auditable contract suitable for the next layers.