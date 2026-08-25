# M4 Codex Tool Inventory Adapter

Status: implementation candidate
Date: 2026-08-25
Parent phase: `TOOL_CAPABILITY_RESOLUTION_M4.md`

## Purpose

This slice connects the harness-neutral M4 capability resolver to an explicit Codex tool inventory without pretending that repository code can inspect a hidden Codex registry or conversation UI.

The contract is:

```text
Codex harness
  -> credential-free inventory snapshot
  -> explicit capability bindings
  -> Codex inventory adapter
  -> M4 observations
  -> M4 capability resolver
  -> mission decision
```

The harness owns discovery of the actual tools exposed in its current session. SEF owns validation, binding provenance and capability resolution.

## Why this boundary exists

SEF cannot safely infer a capability from an arbitrary tool name. A surface named `deploy`, for example, does not prove which provider it targets, whether it is authenticated, whether it can write, whether it is production-sensitive, what evidence it can return, or whether human authorization remains required.

Therefore:

- a concrete tool surface is not automatically a SEF capability;
- every emitted capability observation requires an explicit binding;
- model-only/inferred bindings are rejected;
- unmapped tools remain visible in the adapter report but produce no M4 observation;
- the resolver remains the authority for `READY`, `AUTHORIZATION_REQUIRED`, `UNAVAILABLE`, and related decisions.

## Inventory contract

Schema identifier:

`sef.codex-tool-inventory.v1`

A snapshot contains:

- `harness=CODEX`;
- a non-secret `session_ref`;
- timezone-aware `captured_at`;
- concrete `surfaces` exposed by the harness;
- explicit `bindings` between those surfaces and abstract SEF capabilities.

Each surface records:

- source kind;
- concrete tool name;
- source/evidence reference;
- availability;
- authentication state;
- read/write access;
- sensitivity (`LOCAL`, `SANDBOX`, `PRODUCTION_SENSITIVE`);
- evidence kinds obtainable;
- remaining authorization requirement and policy reference.

The snapshot stores no credentials. Credential-shaped values are rejected.

## Accepted binding provenance

Binding kinds are limited to:

```text
SEF_ADAPTER
REPOSITORY_CONTRACT
HARNESS_METADATA
```

A binding also requires a provenance reference.

`MODEL_INFERRED` or equivalent free-form guessing is intentionally unsupported.

A single concrete surface may map to multiple capabilities when separate explicit bindings prove those relationships. The same surface/capability pair may appear only once.

## Adapter behavior

`tool_capabilities.codex_adapter.adapt_inventory()`:

1. validates the supplied Codex snapshot;
2. rejects secrets, malformed state and ambiguous bindings;
3. preserves surface state and binding provenance;
4. emits observations only for explicitly bound surfaces;
5. records unmapped surfaces rather than guessing capabilities;
6. proves the generated observations satisfy the already-merged M4 observation contract;
7. hashes the source inventory and adapter report for deterministic evidence.

Adapter report schema:

`sef.codex-tool-inventory-adapter-report.v1`

Explicit claims are limited to:

```text
live_registry_read_by_adapter = false
model_inferred_bindings = false
credential_storage = false
```

## Bridge behavior

`tool_capabilities.resolve_codex_inventory()` composes the adapter with the M4 resolver.

Input:

```text
Codex inventory snapshot
+
mission / pack capability requirements
```

Output:

```text
adapter provenance report
+
M4 capability resolution
```

Bridge report schema:

`sef.codex-tool-capability-bridge.v1`

The bridge carries these explicit claims:

```text
inventory_supplied_by_harness = true
hidden_registry_introspection = false
model_inferred_bindings = false
credential_storage = false
```

## Example decision

The qualification fixture contains:

- a bound browser surface;
- a bound visual-capture surface;
- a production-sensitive hosting surface;
- one unrelated unmapped tool.

Expected resolution:

```text
browser        -> READY
visual_capture -> READY
hosting        -> AUTHORIZATION_REQUIRED
```

The unrelated surface remains visible as `unmapped`; it cannot silently acquire a SEF capability.

This distinction matters because technical availability is not equivalent to permission to perform a production write.

## Freshness

The inventory capture time becomes the observation time consumed by the M4 resolver.

The bridge accepts an explicit maximum observation age, defaulting to 300 seconds. The already-merged M4 resolver therefore remains responsible for rejecting stale observations as current capability state.

## Public API

The package exports the adapter/bridge through `tool_capabilities`:

```python
from tool_capabilities import (
    adapt_inventory,
    resolve_codex_inventory,
    validate_inventory,
    validate_adapter_report,
    validate_bridge_report,
)
```

M5 should consume this public surface instead of importing implementation files opportunistically.

## Qualification

`evals/run_codex_inventory_adapter_m4.py` defines 34 deterministic controls covering:

- valid adaptation and end-to-end resolution;
- unmapped-tool behavior;
- binding provenance preservation;
- surface/evidence state preservation;
- timestamp propagation;
- one-surface/multiple-capability support;
- duplicate/ambiguous binding rejection;
- unknown surface rejection;
- no model-inferred binding;
- schema/harness/time/source/tool/capability validation;
- credential-shaped secret rejection;
- unavailable/evidence/access consistency;
- authorization provenance;
- truthful empty inventory behavior;
- deterministic reports;
- provenance-sensitive observation IDs;
- adapter and bridge tamper detection;
- M4 contract composition;
- explicit non-claims;
- frozen legacy runtime integrity.

The CI gate additionally verifies that the adapter/bridge public API is importable.

Expected model/provider/network/hidden-registry calls during qualification: 0.

## What this proves

After qualification, this slice can support the following bounded claim:

> Given an explicit, evidence-backed Codex harness inventory that conforms to the contract, SEF can deterministically translate explicitly bound tool surfaces into M4 observations and resolve mission capability requirements without guessing tool semantics or storing credentials.

## What this does not prove

This slice does **not** prove that:

- current Codex automatically emits this snapshot today;
- repository code can inspect the Codex UI or hidden tool registry;
- SEF can auto-map arbitrary new tools without binding provenance;
- authentication can be inferred from a tool name;
- production authorization can be bypassed because a write tool exists;
- the adapter invokes tools or provider APIs;
- M5 end-to-end connected execution is already operational.

The remaining M4 question is therefore narrower: how the actual Codex harness/session exports or constructs this inventory at execution time. M4 should not be declared complete until that harness hand-off has an operational contract and qualification evidence.
