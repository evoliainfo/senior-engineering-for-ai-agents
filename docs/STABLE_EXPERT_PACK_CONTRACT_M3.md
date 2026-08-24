# M3 — Stable Expert Pack Contract

Status: implementation candidate
Date: 2026-08-24
Roadmap authority: `MODERN_SEF_BUILD_PLAN.md`

## Purpose

M3 defines the durable executable specialty layer that sits beside native agent capability and JIT Expertise.

A Stable Expert Pack is not valuable because it contains more instructions. It is valuable when it packages repeatable executable behavior, fixtures, evaluators, evidence collectors or recovery semantics that the base coding agent does not reliably reproduce from generic prompting alone.

## Boundary with JIT Expertise

Use JIT Expertise for volatile current contracts such as provider API syntax, framework versions, deployment settings and current service limitations.

Use a Stable Expert Pack for durable executable specialty behavior such as visual evidence loops, migration rehearsal harnesses or deployment/post-deploy evidence collection.

A Delivery Mission may combine both.

## Portable agent surface

Each pack contains a portable `SKILL.md`. This preserves compatibility with agent-skill conventions while keeping SEF-specific machine-readable metadata in `pack.json`.

The skill is the agent-facing orchestration entry point. The pack metadata is the deterministic contract used by SEF.

## Required bundle contract

A discovered pack must provide:

- `SKILL.md` whose frontmatter `name` equals the directory/pack id;
- `pack.json` with schema `sef.expert-pack.v1`;
- semantic version;
- lifecycle status: `experimental`, `candidate` or `stable`;
- evidence-based activation conditions;
- abstract tool requirements;
- at least one executable entry point;
- evidence requirements and evidence outputs;
- explicit failure modes;
- explicit recovery actions;
- explicit stop conditions;
- deterministic file hashes and bundle digest.

## Abstract tool requirements

Pack metadata does not bind directly to one vendor tool. It declares capability such as:

```text
browser
visual_capture
database_admin
hosting
observability
```

M4 will resolve these abstract requirements to the tools actually available in Codex/plugins/MCP/CLI surfaces.

Each requirement also declares:

- `READ` or `WRITE` access;
- `LOCAL`, `SANDBOX` or `PRODUCTION_SENSITIVE` sensitivity;
- whether the tool is required;
- what observable evidence the tool can provide.

M3 does not claim that the tool is currently available or authenticated.

## Executable entry points

Supported entry-point kinds:

- `SCRIPT` under `scripts/`;
- `EVALUATOR` under `evaluators/`;
- `COLLECTOR` under `collectors/`;
- `ADAPTER` under `adapters/`.

Paths are confined to the pack directory and must exist. A pack with no executable entry point is rejected.

This deliberately prevents a prompt-only checklist from being promoted to Stable Expert Pack merely by adding metadata.

## Evidence contract

Every pack declares:

- evidence it requires before or during execution;
- evidence it produces.

At least one evidence output is mandatory. The actual mission/runtime must later attach that evidence to Project State; M3 only defines and validates the pack-side contract.

## Failure and recovery

A pack must describe all three:

1. material failure modes;
2. safe recovery actions;
3. stop conditions where the system must refuse to claim success.

This is part of the executable specialty, not optional documentation.

## Integrity and supply-chain boundary

M3 fingerprints all bundle files and seals the generated manifest. The contract rejects:

- path traversal from declared entry points;
- missing entry-point files;
- duplicate tool or entry-point identities;
- unsupported top-level bundle content;
- credential-shaped secret values;
- provider/API credential configuration embedded in metadata;
- oversized bundles/files beyond the bounded contract.

A previously generated manifest fails validation if any pack file changes.

## Progressive disclosure

The pack manifest indexes resources for integrity. It does not imply that every file should be loaded into model context.

Delivery Missions should load only the pack and resources required by the current failure surface.

## M3 deterministic qualification

The M3 gate exercises the contract with temporary pack fixtures and checks:

- schema/runtime alignment;
- valid executable pack loading;
- deterministic manifest generation;
- Agent Skill/pack identity binding;
- semantic versioning;
- closed tool requirement semantics;
- executable entry-point presence and confinement;
- entry kind/directory consistency;
- evidence output requirement;
- failure/recovery requirement;
- provider configuration exclusion;
- secret-shaped value rejection;
- tamper detection;
- historical `sef.py` runtime integrity.

Expected network/model/provider calls: **0**.

## Explicit non-claims

Passing M3 does **not** mean that SEF already has production-quality implementations of the three initial packs.

It does not claim:

- visual QA is already operational;
- migration rehearsal is already operational;
- deployment/post-deploy evidence collection is already operational;
- tool requirements are resolved to live Codex/plugin/MCP tools;
- a Delivery Mission can already invoke packs automatically;
- the packs improve real engineering outcomes over native Codex.

Those claims require the three pack implementations, M4 tool resolution, M5 mission integration and later outcome-level evaluation.

## Next M3 substeps after contract qualification

Implement and evaluate only:

1. `web-experience-visual-quality`;
2. `data-change-safety`;
3. `production-evidence-operations`.

Do not add provider-specific auth/billing/hosting packs merely to increase catalog breadth. Provider-specific volatile knowledge belongs primarily in JIT Expertise unless measured evidence justifies a durable executable component.
