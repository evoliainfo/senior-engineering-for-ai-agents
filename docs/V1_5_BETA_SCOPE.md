# v1.5 Beta — Constrained Release Scope

## Status

The frozen deterministic runtime is:

- commit: `3630f563f24b3577ad1e6a0a05e66a86615dabca`
- SHA-256: `c2203602cb53229aba55bbbb518725c155785838915e75267714bc4e2d3d35ee`

The original broad generalization claim is not release-eligible because official CHALLENGE v3 completed at **9/10 PASS** with critical failure `V3-AUTH-002`.

This document defines the narrower claim under which the current runtime may be treated as a beta/experimental deterministic core.

## Supported claim

v1.5 beta provides:

- deterministic request/risk routing for the semantic and technical concepts covered by its evaluated rule set;
- deterministic actual-diff re-assessment;
- specialist procedure composition;
- explicit evidence and verification accounting;
- fail-safe behavior for unavailable required verification evidence;
- strong regression evidence across DEV, B1, B2 and RC-8;
- auditable historical holdout results.

## Claim that is explicitly NOT made

v1.5 beta does **not** claim universal open-ended understanding of every possible business partition, authorization boundary, trust relation or regulated-domain phrasing.

In particular, unfamiliar nouns can encode a real access boundary that the deterministic lexical/relation layer does not recognize. CHALLENGE v3 demonstrated this with a department-scoped authorization requirement.

## Safe operating rule

For changes involving security, cross-user or cross-scope access, external trust boundaries, regulated decisions, destructive data operations or production infrastructure, v1.5 beta must not be the sole authority used to conclude that a request is low risk.

A human or capable engineering agent must still inspect the actual request and repository context. If such review identifies a material boundary that v1.5 did not route, the lower deterministic result must not override the stronger observed risk.

## Evidence labeling

Public/internal reporting must distinguish:

- deterministic regression evidence;
- independent holdout evidence;
- exploratory real-agent L2 evidence;
- future Semantic Routing v2 evidence.

Consumed holdouts may never be relabeled as fresh independent tests.

## Codex L2 role

Codex L2 may be run against v1.5 beta as **exploratory brownfield evidence** after this constrained scope is accepted.

A successful L2 result may show that an engineering agent can use SEF productively while preserving repository conventions. It does not convert the official 9/10 CHALLENGE v3 result into a pass and does not restore the broad semantic-generalization claim.

## Exit from beta limitation

The limitation can be retired only by a new architecture line that earns its own fresh independent semantic evidence. The accepted direction is `docs/ADR_SEMANTIC_ROUTING_V2.md`.
