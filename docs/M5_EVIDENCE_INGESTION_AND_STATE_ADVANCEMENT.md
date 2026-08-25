# M5 — Evidence ingestion and single-step state advancement

Status: implementation candidate, not end-to-end M5 completion  
Date: 2026-08-25  
Parent mission: `launch-production-web-product`

## Purpose

This is the second executable slice of Modern SEF Phase M5.

The first slice decides the next action without executing it. This slice accepts the result of that action and decides whether the result can support exactly one Project State transition.

```text
M5 decision
+ execution-result envelope
+ artifact files and hashes
+ selected M4 surfaces
+ active M3 pack observations
        ↓
SEF evidence receipt
        ↓
PASS  → persist receipt → add M1 evidence → advance exactly one state
FAIL  → persist receipt → keep Project State unchanged
```

## Core rule

An agent-authored `PASS`, prose claim or completion statement is never sufficient to advance delivery state.

Evidence acceptance requires all of the following:

1. the result is bound to the exact mission id and project id;
2. the result references the exact decision SHA-256 that authorized the action;
3. the result references the exact input Project State SHA-256;
4. the action matches the decision;
5. every declared artifact exists as a real file under the configured artifact root;
6. every artifact SHA-256 matches the bytes on disk;
7. artifact paths cannot escape the artifact root;
8. every `TOOL` artifact is bound to the exact capability and surface selected by M4;
9. every required M4 capability has at least one verified tool-produced artifact;
10. every active Stable Expert Pack has exactly one observation document;
11. evidence-bearing references inside pack observations resolve to declared, verified, tool-produced artifacts;
12. SEF loads and executes the pack evaluator itself;
13. every active pack must return `PASS`;
14. the action must provide the M1 evidence kind required for the next state;
15. the primary evidence must have action-appropriate provenance;
16. only then may M1 advance one state.

## Execution-result envelope

Schema:

`sef.delivery-mission-execution-result.launch-production-web-product.v1`

The envelope contains:

- mission/project binding;
- pre-execution decision digest;
- pre-execution Project State digest;
- action and observed timestamp;
- `SUCCEEDED`, `FAILED` or `INCOMPLETE` execution status;
- artifact records;
- pack-observation references;
- content digest.

Each artifact carries:

- stable id;
- `artifact://...` reference;
- evidence kind;
- artifact-root-relative path;
- SHA-256;
- producer class (`AGENT`, `TOOL`, `SYSTEM`);
- capability/surface binding for `TOOL` artifacts.

A `TOOL` artifact whose capability was not selected by the exact M4 decision is rejected. A `TOOL` artifact claiming the wrong selected surface is also rejected.

## Artifact boundary

Artifacts are resolved only beneath the caller-supplied evidence root.

The verifier rejects:

- absolute paths;
- `..` traversal;
- escape through resolution outside the evidence root;
- missing files;
- empty files;
- files over the bounded verification size;
- SHA-256 mismatches;
- duplicate artifact ids, refs or paths.

Receipts are written atomically and are immutable by default: an existing receipt path is never overwritten.

## Stable Expert Pack execution

The result never supplies a trusted pack report.

Instead, it supplies a pack observation artifact. SEF then:

1. verifies the observation artifact bytes/hash;
2. validates evidence references in the observation;
3. requires evidence-bearing references such as `screenshot_ref`, `deployment_ref`, `runtime_identity_ref`, `evidence_ref`, `pre_ref`, `post_ref`, etc. to resolve to tool-produced artifacts;
4. loads the evaluator entry point from the current validated pack bundle;
5. executes `evaluate(document)` inside SEF;
6. hashes and records the resulting report in the evidence receipt;
7. blocks the transition unless the report status is `PASS`.

The first three packs are therefore executed as gates rather than treated as static instructions:

- `web-experience-visual-quality`;
- `data-change-safety`;
- `production-evidence-operations`.

## Primary evidence by transition

M1 remains canonical and defines the evidence kind for each target state:

| Action | Target state | Required M1 evidence kind | Primary provenance |
| --- | --- | --- | --- |
| `PLAN_ARCHITECTURE` | `ARCHITECTED` | `architecture-decision` | agent/system artifact |
| `IMPLEMENT_PRODUCT` | `IMPLEMENTED` | `implementation-change` | selected `source_control` tool |
| `VERIFY_LOCAL_PRODUCT` | `VERIFIED_LOCAL` | `local-verification` | selected `browser` tool |
| `DEPLOY_AND_VERIFY_PREVIEW` | `PREVIEW_VERIFIED` | `preview-verification` | selected `hosting` tool |
| `PROVE_RELEASE_READINESS` | `RELEASE_READY` | `release-readiness` | selected `ci` tool |
| `DEPLOY_PRODUCTION` | `DEPLOYED` | `deployment` | selected `hosting` tool |
| `VERIFY_PRODUCTION` | `POST_DEPLOY_VERIFIED` | `post-deploy-verification` | selected `browser` tool |

A successful execution status without the required evidence kind still fails the gate.

## Evidence receipt

Schema:

`sef.delivery-mission-evidence-receipt.launch-production-web-product.v1`

The receipt records:

- exact decision and input-state hashes;
- input and target delivery states;
- required M1 evidence kind;
- verified artifact inventory;
- per-capability tool evidence coverage;
- SEF-computed pack reports and hashes;
- blockers;
- explicit trust-boundary claims;
- content digest.

A `PASS` receipt has no blockers. A `FAIL` receipt must contain blockers.

`advance_from_execution()` always persists the receipt. If the receipt fails, the input Project State is returned unchanged. If it passes, the receipt file SHA-256 becomes M1 evidence and M1 advances exactly one state.

## Explicit non-claims

Every receipt states:

```text
artifact_bytes_verified = true
pack_reports_computed_by_sef = true
state_advanced_by_evaluation = false
external_truth_cryptographically_proven = false
model_assertion_sufficient = false
```

The distinction matters.

This slice can prove that the exact artifact bytes existed under the evidence root, that they were hash-bound to the execution result, that their claimed tool provenance matches the M4-selected surface, and that the SEF pack evaluator returned `PASS`.

It cannot cryptographically prove that an external provider itself generated those bytes unless the active provider/tool integration exposes a verifiable signed receipt or equivalent authoritative mechanism. That deeper provenance belongs to the harness/provider integration layer, not to a fabricated claim in this module.

## Qualification

`evals/run_m5_evidence_ingestion.py` defines 33 deterministic/adversarial controls covering:

- both JSON contracts;
- exact decision/state/action binding;
- result and receipt tamper detection;
- path traversal, missing-file and hash mismatch rejection;
- failed execution preserving Project State;
- primary evidence requirements;
- per-capability M4 evidence coverage;
- wrong selected surface rejection;
- automatic execution of visual/data/production pack evaluators;
- pack failure blocking;
- dangling pack evidence rejection;
- tool-only pack evidence requirements;
- local, preview, release-ready, production deploy and post-deploy progression;
- material-data safety gating;
- blocked production authorization remaining blocked;
- receipt immutability;
- explicit non-claims;
- all seven delivery transitions advancing exactly one state;
- frozen legacy runtime integrity.

Qualification performs zero model, network, provider or real tool-execution calls. It uses temporary files to exercise the evidence verifier and the actual M3 evaluator code paths.

## Bounded claim after qualification

If this slice passes qualification, the defensible claim is:

> Given a READY M5 decision and an execution-result envelope whose evidence files are locally available, SEF can bind the result to the exact decision/state, verify artifact bytes and M4-selected tool provenance, execute all active Stable Expert Pack evaluators, persist an immutable evidence receipt, and advance Project State by exactly one state only when every required gate passes.

This is still not end-to-end M5 completion.

## Remaining M5 work

The mission still needs live harness demonstrations that create these envelopes from real Codex actions, including:

- architecture and implementation in a representative project;
- real browser collection rather than fixture observations;
- preview hosting output;
- CI/release evidence;
- authorized production deployment or truthful authorization block;
- real production observability/post-deploy evidence;
- provider/JIT integration where required;
- state-domain updates that preserve important architecture/deployment facts for fresh-session continuation;
- a fresh-session continuation demonstration;
- an end-to-end mission run whose final delivery state is supported by the accumulated receipts.
