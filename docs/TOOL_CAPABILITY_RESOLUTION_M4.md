# M4 — Tool Capability Resolution

Status: resolver-contract implementation candidate
Date: 2026-08-25
Roadmap phase: `MODERN_SEF_BUILD_PLAN.md` / M4

## Purpose

M4 answers a question that Project State, JIT Expertise and Stable Expert Packs cannot answer by themselves:

> Can the active coding-agent environment actually perform the required operation, with the required access, scope, evidence and authorization state right now?

The first M4 slice is a harness-neutral, deterministic resolver. It does not build a parallel provider tool ecosystem and it stores no credentials.

## Why this layer exists

An Expert Pack may require abstract capabilities such as:

```text
browser
visual_capture
database_admin
hosting
observability
```

That requirement does not prove a tool is present. Conversely, a tool name in an agent session does not prove it is authenticated, write-capable, safe for the required environment or able to produce the evidence the mission needs.

M4 separates those facts.

## Current OpenAI surface alignment

Current OpenAI tool surfaces distinguish built-in tools, MCP tools/connectors and custom/function tools. SEF therefore normalizes invokable surfaces rather than assuming one provider-specific mechanism.

The M4 source kinds are:

```text
BUILTIN
MCP
FUNCTION
CLI
PROJECT
```

`CLI` and `PROJECT` keep the contract harness-neutral for repository-local and command-line surfaces. A packaged plugin should be represented by the invokable surface it actually exposes (for example MCP) rather than by the packaging label alone.

## Input contract

Schema:

`sef.tool-capability-observations.v1`

Each resolution document contains:

- `resolved_at` — timestamp of the resolution decision;
- `max_observation_age_seconds` — explicit freshness budget;
- `requirements` — abstract capabilities needed by the current task/mission;
- `observations` — evidence-backed observations emitted by the active harness/adapters.

### Requirement

A requirement declares:

- stable id;
- abstract capability;
- minimum access: `READ` or `WRITE`;
- required sensitivity scope: `LOCAL`, `SANDBOX`, or `PRODUCTION_SENSITIVE`;
- evidence kinds that the selected surface must be able to obtain.

### Observation

An observation records one concrete tool surface:

- capability mapping;
- surface id;
- source kind and source reference;
- observed timestamp;
- `AVAILABLE`, `UNAVAILABLE`, or `UNKNOWN`;
- authentication state;
- access level;
- sensitivity scope;
- evidence kinds obtainable;
- evidence reference;
- whether additional authorization is required;
- authorization-policy/evidence reference when that state is known.

No credential values are permitted.

## Freshness

Tool state is session/environment state, so stale evidence must not silently survive.

A resolution declares a maximum observation age. The resolver:

1. rejects future-dated observations;
2. selects the latest state for each capability/surface;
3. excludes latest states older than the freshness budget;
4. returns `UNKNOWN` with `ONLY_STALE_OBSERVATIONS` when stale state is all that exists.

## Conflict semantics

Multiple historical observations for one surface are allowed.

At the newest timestamp:

- semantically equivalent records with different record ids are equivalent, not conflicts;
- contradictory states for the same surface become `CONFLICT`;
- a conflict on one surface does not block a separate, independently proven surface that fully satisfies the requirement.

SEF never guesses through an unresolved latest-state conflict.

## Resolution statuses

A requirement resolves to one of:

```text
READY
AUTHORIZATION_REQUIRED
AUTHORIZATION_UNKNOWN
UNAVAILABLE
UNAUTHENTICATED
INSUFFICIENT_ACCESS
INSUFFICIENT_SCOPE
INSUFFICIENT_EVIDENCE
UNKNOWN
CONFLICT
```

### `READY`

The selected surface is fresh, available, authenticated (or authentication is not applicable), has sufficient access/sensitivity, can produce required evidence, and has evidence that no additional authorization is required.

### `AUTHORIZATION_REQUIRED`

The tool is technically usable, but the recorded policy says a human/other authorization is still required. M5 must not treat this as permission to perform the write.

### `AUTHORIZATION_UNKNOWN`

The technical surface is usable but authorization state is not proven. This is intentionally distinct from `READY`.

## Selection policy

When multiple surfaces satisfy a requirement, the resolver chooses deterministically:

1. least excess sensitivity scope;
2. least excess access privilege;
3. agent-native source priority (`BUILTIN`, then `MCP`, then `FUNCTION`, then `CLI`, then `PROJECT`);
4. stable surface id tie-break.

This prefers least privilege before convenience.

## Evidence and authorization provenance

Known availability must carry `evidence_ref`. Positive authentication/access/evidence claims also require evidence.

A known authorization decision (`REQUIRED` or `NOT_REQUIRED`) must carry `authorization_ref`. `UNKNOWN` authorization deliberately carries no fake policy reference.

The resolver report itself is content-hashed so downstream code can detect mutation.

## Secret boundary

SEF records capability facts and references, not credential values.

The M4 validator rejects common credential-shaped values including API keys, access tokens and private-key material. Provider credentials remain owned by the active agent/tool integration.

## Qualification

The initial deterministic gate covers 31 controls including:

- fully ready multi-source resolution;
- authorization required/unknown distinction;
- unauthenticated/unavailable/unknown states;
- insufficient access/scope/evidence;
- observation expiry;
- newer observation superseding old state;
- equivalent vs contradictory tied observations;
- conflict recovery through an independent valid surface;
- least-privilege and source-priority selection;
- future timestamp rejection;
- evidence provenance for available/unavailable states;
- authorization provenance;
- secret rejection;
- invalid unavailable-access claims;
- duplicate identity rejection;
- freshness/timezone contract;
- deterministic output hash tamper detection;
- production-sensitive write authorization behavior;
- frozen legacy runtime integrity.

The qualification itself performs zero model, provider or network calls.

## Important non-claim

This first M4 slice **does not yet claim live harness discovery**.

It defines and tests the resolver contract that a Codex/OpenAI adapter will feed. A subsequent M4 slice must bind actual agent-native tool inventory/schema observations into this contract. Until that exists, M4 is not complete and M5 must not claim autonomous connected execution.

This boundary is deliberate: a Python library inside the repository cannot magically inspect the coding agent's UI/tool registry. The harness/plugin/MCP integration must explicitly pass observed surfaces to SEF.
