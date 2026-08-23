# Semantic Routing v2 — S0/S1 Contract and Shadow Bridge

## Status

This increment implements only S0 and S1 from `docs/SEMANTIC_ROUTING_V2_BUILD_PLAN.md`.

It does **not** modify the frozen v1.5 runtime, does not implement open-vocabulary extraction, does not compose new policy decisions and does not make a new release claim.

Frozen v1.5 runtime SHA-256 remains:

`c2203602cb53229aba55bbbb518725c155785838915e75267714bc4e2d3d35ee`

## S0 — contracts before code

Machine and runtime contracts are defined under `semantic_v2/`.

### Semantic IR

Schema: `sef.semantic-ir.v1`

The IR separates semantic description from policy authority. It contains:

- extractor identity and mode;
- request digest;
- typed semantic facts;
- provenance for every fact;
- explicit uncertainties;
- derived review state;
- non-authoritative metadata.

Initial typed fact families are intentionally relation-oriented rather than business-noun oriented:

- access-control boundary;
- partition isolation;
- authentication protocol;
- server-destination trust;
- external operational dependency;
- consequential decision;
- live data transformation;
- capacity materiality;
- production release change;
- deployment artifact;
- build supply chain;
- untrusted file input.

Business labels remain data in attributes/provenance and are not required to belong to a closed tenant/workspace/organization vocabulary.

### Authority separation

`validate_semantic_ir()` rejects policy-authority keys anywhere in extractor output, including:

- `risk`;
- `packs`;
- `procedures`;
- implementation approval/gate fields;
- release eligibility/approval fields.

A future model-assisted extractor therefore cannot directly decide the governance outcome.

### Uncertainty

Material unresolved semantics require the explicit state:

`SEMANTIC_REVIEW_REQUIRED`

A material ambiguity, unavailable relation, conflict or invalid extraction cannot be represented as a normal resolved IR.

### Interfaces

`Extractor.extract(request, project_context) -> SemanticIR`

`PolicyComposer.compose(validated_semantic_ir) -> policy output`

The composer interface is defined but not implemented in S0/S1. S3 owns policy composition.

## S1 — deterministic bridge

`semantic_v2.bridge_v15` converts already-established v1.5 signals into typed IR facts for migration and shadow evidence.

This bridge is deliberately **not** an open-vocabulary extractor. It cannot repair unknown-language failures such as the historical department case. Its role is to establish a deterministic compatibility baseline before S2.

The bridge:

- maps known v1.5 signals to typed semantic facts;
- preserves unknown legacy signals in metadata rather than pretending coverage;
- emits no risk/packs/procedures in the IR;
- validates every output against the S0 contract;
- produces a stable canonical digest;
- never mutates the input assessment.

`shadow_bridge()` returns both:

1. a deep copy of the canonical v1.5 output; and
2. the shadow Semantic IR.

`canonical_output_changed` must remain `false` throughout S1.

## Acceptance gate

Run:

```bash
PYTHONPATH=. python3 evals/run_semantic_v2_s0_s1.py --output semantic-v2-s0-s1.json
```

The gate verifies:

- a valid typed IR is accepted;
- material uncertainty requires `SEMANTIC_REVIEW_REQUIRED`;
- falsely marking material uncertainty resolved is rejected;
- policy-authority leakage is rejected;
- provenance is mandatory;
- duplicate fact identity is rejected;
- known v1.5 signal families map deterministically;
- unknown legacy signals are surfaced as unmapped;
- bridge output is deterministic;
- the canonical assessment remains exactly unchanged;
- no open-vocabulary or policy-composer claim is made.

The GitHub workflow additionally proves the root `sef.py` checksum remains the frozen v1.5 hash and that the PR contains no `sef.py`/`SHA256SUMS` mutation.

## Exit criteria

S0/S1 are complete only when:

1. the dedicated S0/S1 gate passes completely;
2. existing runtime validation and DEV regression remain green;
3. `sef.py` remains hash-identical to the frozen v1.5 runtime;
4. the increment is merged without enabling Semantic Routing v2 in canonical routing.

After those gates pass, the next architectural phase is **S2: provider-neutral open-vocabulary extraction**, still behind shadow mode.
