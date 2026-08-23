# Semantic Routing v2 — S2 Open-Vocabulary Extractor Boundary

## Status

S2 introduces the provider-neutral model-assisted extraction boundary described by the accepted Semantic Routing v2 ADR.

It does **not** modify root `sef.py`, does not change canonical v1.5 routing, and does not implement the deterministic policy composer planned for S3.

## What S2 implements

`semantic_v2.model_extractor.ModelAssistedExtractor` implements:

```text
extract(request, project_context) -> SemanticIR
```

through a provider-neutral `SemanticProvider` protocol.

A provider can later be backed by OpenAI, another model vendor, a local model, or deterministic replay evidence without changing the Semantic IR/policy boundary.

## Trust boundary

Provider output is untrusted.

The provider may propose only:

- semantic facts;
- semantic uncertainties;
- whether its extraction is complete.

It may not choose:

- governance packs;
- risk levels;
- procedures;
- implementation approval;
- release approval;
- final review state.

The wrapper computes review state and validates the resulting IR.

## Fail-closed semantics

The extractor returns a valid `sef.semantic-ir.v1` object even when the provider fails.

The following conditions produce `SEMANTIC_REVIEW_REQUIRED` instead of a low-risk default:

- provider exception/unavailability;
- malformed provider output;
- unsupported fact kind;
- missing/invalid provenance;
- provider-declared incomplete extraction;
- policy-authority injection;
- provider-reported uncertainty.

During S2 every provider-reported uncertainty is conservatively treated as material. A later deterministic rule may narrow that only with explicit evidence.

## Open-vocabulary property

Open vocabulary lives in literal attributes and entity labels, not in a hard-coded business-noun enum.

For example, all of the following can carry the same typed relation graph:

```text
department
branch
region
division
```

The extractor infrastructure does not need those nouns in a whitelist. A capable provider identifies the relation and preserves the literal source label in Semantic IR.

This does **not** itself prove live-model semantic quality. S2 proves the safety/interface boundary around such a provider.

## Materiality floor

Critical fact families cannot be downgraded by provider output. For example, `ACCESS_CONTROL_BOUNDARY` and `PARTITION_ISOLATION` are forced material even if a provider proposes `material=false`.

## Acceptance controls

The S2 gate covers:

1. four open-vocabulary partition labels with an identical relation graph;
2. complete negative/content-only extraction;
3. provider-declared incomplete extraction;
4. provider unavailability;
5. top-level policy injection;
6. nested policy injection;
7. missing provenance;
8. uncertainty materiality floor;
9. critical-fact materiality floor;
10. provider contract authority separation;
11. source guard against hard-coded metamorphic scope nouns;
12. metamorphic equivalence across the four scope labels.

## Evidence claim

A green S2 gate means:

- the provider boundary is structurally safe under the tested adversarial conditions;
- Semantic IR validation and fail-closed behavior work;
- the infrastructure supports open-vocabulary labels without noun-specific routing code;
- S0/S1 contracts still pass;
- frozen v1.5 remains unchanged.

It does **not** mean a live OpenAI/model configuration has demonstrated sufficient semantic recall or precision. That evidence belongs to later semantic qualification and the post-freeze independent program.
