# Capability System Build Plan

Status: historical baseline through C2; superseded for C3+
Date: 2026-08-24
Architecture: `ADR_CAPABILITY_SYSTEM_VNEXT.md`

## Current authority

This document defined the first capability-system roadmap and remains the historical record for C0-C2.

The user/product requirement was subsequently sharpened: SEF must support a non-expert/vibe coder across the full professional delivery lifecycle, from idea and problem framing through architecture, implementation, release, deployment and post-deployment verification.

The original C3-C9 sequence was too brownfield-centric to satisfy that complete product contract.

For all work after C2, the authoritative roadmap is now:

- [`SENIOR_DELIVERY_CONTRACT.md`](SENIOR_DELIVERY_CONTRACT.md) — lifecycle/product contract;
- [`SENIOR_DELIVERY_BUILD_PLAN_V2.md`](SENIOR_DELIVERY_BUILD_PLAN_V2.md) — authoritative C3-C10 implementation sequence;
- [`MIXED_LIFECYCLE_COMPARATIVE_EVAL_PLAN.md`](MIXED_LIFECYCLE_COMPARATIVE_EVAL_PLAN.md) — final mixed greenfield + brownfield comparative methodology;
- [`BROWNFIELD_COMPARATIVE_EVAL_PLAN.md`](BROWNFIELD_COMPARATIVE_EVAL_PLAN.md) — retained brownfield subprotocol only.

## Completed baseline

### C0 — Strategic reset and ECC capability benchmark

Completed. SEF pivoted from governance-first/semantic-routing promotion toward a capability-first engineering system.

### C1 — Capability contract and registry

Completed and merged.

Established:

- portable `capabilities/<id>/SKILL.md` agent-facing format;
- SEF-only `capability.json` metadata sidecar;
- deterministic registry/manifest;
- reference/cycle/provider-configuration validation;
- progressive-disclosure resource indexing;
- deterministic qualification gate.

### C2 — Foundation capability tranche A

Completed and merged.

Capabilities:

1. `repository-discovery`
2. `requirements-to-acceptance`
3. `implementation-planning`
4. `tdd-bug-reproduction`
5. `systematic-debugging`
6. `verification-before-completion`

C2 also introduced `SENIOR_DELIVERY_CONTRACT.md`, making full lifecycle gaps explicit rather than implying that six brownfield-oriented skills already satisfy idea-to-production delivery.

## Historical principles that remain binding

Although the sequencing below C2 has been superseded, these original architectural principles remain active:

- capabilities must improve observable engineering outcomes, not maximize skill count;
- no mandatory SEF-owned LLM API call in the normal path;
- repository/project evidence outranks generic framework preference;
- user-owned instructions are preserved;
- ordinary low-risk work remains proportional;
- targeted guardrails exist for materially risky operations rather than dominating every task;
- each capability requires DEV qualification before outcome-level evidence;
- freeze before independent/fresh evaluation;
- consumed benchmark cases become regression-only;
- failed evidence is preserved;
- no benchmark-specific patch may retain a claim that the same benchmark is fresh;
- comparative superiority claims require controlled evidence against the tested ECC version;
- `sef.py` deterministic beta runtime remains regression-green during migration unless an explicit future architecture decision changes that policy.

## Why the sequence changed

The original plan prioritized twelve brownfield engineering capabilities before workflow composition. That was useful for validating the capability architecture, but it left critical lifecycle stages without explicit ownership:

- initial product/problem framing;
- greenfield architecture and stack selection;
- project bootstrap/foundations;
- environment and secret configuration;
- actual deployment execution;
- post-deployment verification.

A product aimed at non-expert/vibe coders cannot require the user to know that these stages exist and manually request them. Therefore C3+ is governed by the Senior Delivery Spine roadmap instead.

## Do not implement from the old C3-C9 sequence

Any former C3-C9 section from earlier revisions is historical only. Use `SENIOR_DELIVERY_BUILD_PLAN_V2.md` for current implementation order, pilot gates, lifecycle completion, Codex-native packaging, final benchmark and release decision.
