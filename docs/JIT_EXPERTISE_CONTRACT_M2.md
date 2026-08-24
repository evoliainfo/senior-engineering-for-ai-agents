# Just-In-Time Expertise Contract — M2

Status: implementation candidate  
Stage: `M2_JIT_EXPERTISE_CONTRACT`

## Purpose

M2 defines the deterministic contract used to bind current, task-specific expertise to one SEF project need without turning SEF into a large static provider/framework skill catalog.

The M2 module is deliberately **not** a web client, search engine, model wrapper or Codex adapter. The surrounding coding agent/harness already owns repository, browser/search, plugin, MCP and CLI surfaces. M2 validates the observations collected from those surfaces and compiles them into a compact, auditable Expertise Capsule.

```text
mission need
   +
selected M1 project context
   +
observed authoritative sources
   +
available tool snapshot
   ↓
M2 JIT Expertise contract
   ↓
sealed Expertise Capsule
```

## Files

- `jit_expertise/jit-expertise.schema.json` — public v1 capsule schema.
- `jit_expertise/core.py` — deterministic validator, source ranking, capsule compiler and invalidation logic.
- `jit_expertise/__init__.py` — package surface.
- `evals/run_jit_expertise_m2.py` — deterministic M2 qualification controls.
- `.github/workflows/jit-expertise-m2.yml` — qualification CI gate.

## Capsule contract

A capsule contains:

- `mission_need` — the project-specific need that triggered expertise acquisition;
- `subject` — external provider, framework, repository contract or standard;
- `project_context_sha256` — fingerprint of the selected M1 project-state slice;
- `sources` — observed or unavailable sources with provenance, freshness and optional content digests;
- `constraints` — compact task-specific requirements with source references;
- `tools` — available/unavailable/unauthenticated capability snapshot;
- `verification_paths` — checks required to support the task outcome;
- `uncertainties` — explicit blocking or non-blocking uncertainty;
- `status` — deterministically derived capsule status;
- `content_sha256` — sealed canonical capsule digest.

## Source authority

M2 ranks source classes in this order:

1. `REPOSITORY`
2. `OFFICIAL`
3. `TOOL_SCHEMA`
4. `STANDARD`
5. `SECONDARY`

For an `EXTERNAL_PROVIDER` or `FRAMEWORK`, a current `OFFICIAL` or `TOOL_SCHEMA` source is required before the capsule can become usable. A material constraint cannot rely only on secondary evidence.

For repository-local contracts, repository evidence is required. For standards, standard or official evidence is required.

## Status model

M2 derives one of:

- `READY` — required source and tool surfaces exist and no blocking uncertainty remains;
- `REVIEW_REQUIRED` — authoritative context exists but a blocking uncertainty requires a decision/review;
- `BLOCKED_SOURCE_GAP` — the required authoritative source class is absent or unavailable;
- `BLOCKED_TOOL_GAP` — a required verification capability is absent, unavailable or unauthenticated;
- `STALE` — source material used by the capsule is no longer fresh at capsule generation/validation time.

The caller does not choose the status manually.

## Invalidation

A previously valid capsule must be reconsidered when any relevant input changes. M2 can report:

- `PROJECT_CONTEXT_CHANGED`;
- `TOOL_CAPABILITY_CHANGED`;
- `SOURCE_EXPIRED:<source-id>`;
- `SOURCE_CHANGED:<source-id>`.

The M1 context digest intentionally fingerprints only the selected project-state slice (`schema`, `project_id`, `delivery_state`, selected domains and referenced evidence), not unrelated global revision metadata. An unrelated state revision therefore does not invalidate a capsule whose relevant context did not change.

## Secret handling

Capsules must contain provenance and references, never credentials. Credential-shaped values are rejected by deterministic guards.

SEF does not own provider credentials for ordinary agent-native use.

## What M2 proves

The deterministic M2 qualification tests the contract mechanics:

- schema/runtime alignment;
- project-bound sealed capsules;
- authority-first source ranking;
- required authoritative provider/framework surface;
- rejection of secondary-only material claims;
- unavailable-source rejection;
- source/tool gap statuses;
- blocking vs non-blocking uncertainty semantics;
- source freshness/content invalidation;
- project-context and tool-snapshot invalidation;
- selective-context stability;
- secret-shaped value rejection;
- tamper detection;
- historical `sef.py` integrity.

## Explicit non-claims

M2 does **not** claim that SEF already:

- searches or browses the internet itself;
- calls a model/provider;
- semantically proves that a cited source passage entails a supplied constraint;
- automatically injects a capsule into a live Codex/Claude context;
- measurably reduces user questions in real agent sessions;
- improves integration success over native Codex;
- installs tools or arbitrary remote code;
- ships a production Delivery Mission.

Those require later agent/harness integration, tool-capability resolution and mission-level evaluation.

The contract does, however, preserve the information required for those later layers to act without silently converting missing source/tool evidence into confidence.

## Local qualification

```bash
python3 -m py_compile \
  jit_expertise/__init__.py \
  jit_expertise/core.py \
  evals/run_jit_expertise_m2.py

python3 -m json.tool jit_expertise/jit-expertise.schema.json >/dev/null
python3 evals/run_jit_expertise_m2.py
```

Expected provider/model/network calls from this qualification: **0**.

## Relationship to M1

M1 answers:

> What compact project truth is currently supported by evidence?

M2 answers:

> For this mission need and this selected project context, what current expertise constraints, source provenance, tool surfaces and verification paths may the later mission rely on?

M2 fingerprints the selected M1 context so expertise can be invalidated when relevant project truth changes without coupling capsules to unrelated state churn.
