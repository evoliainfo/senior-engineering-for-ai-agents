# Semantic Routing v2 — S4 First-Run Postmortem

## Why this record exists

The first real S4 shadow run was intentionally treated as diagnostic evidence, not as a target whose expectations could be rewritten after observation.

First S4 run:

- workflow run: `32666269823`
- result: **9 PASS / 6 FAIL** in the S4 acceptance surface
- frozen v1.5 runtime mutation: **none**
- S0/S1, S2 and S3 replays before S4: **PASS**

The failures exposed four real v2 safety/parity gaps plus one aggregate-control defect caused by test ordering. The runtime v1.5 remained canonical throughout.

## Observed architecture gaps

### 1. Authorization boundary implementation gate

`S4-PAR-AUTH` had equivalent R3 packs (`AUTHORIZATION`, `MULTI_TENANT`) but v1.5 blocked implementation pending authoritative context while v2 allowed implementation.

Root cause: S3 represented risk/packs but did not yet represent the distinction between a known high-impact control boundary and the availability of authoritative implementation requirements.

Remediation: composer-owned `requires_authoritative_context` semantics. Access-control and partition-isolation facts now compose their obligations while remaining deny-by-default until a future deterministic trusted-context mechanism exists.

### 2. Regulated risk parity

`S4-PAR-REGULATED` produced R4 in v1.5 and R3 in v2, while both blocked implementation and selected `REGULATED_DOMAIN`.

Root cause: S3's `CONSEQUENTIAL_DECISION` risk floor was underspecified.

Remediation: `CONSEQUENTIAL_DECISION` now has an R4 floor and remains blocked pending regulated authority.

### 3. Live-data authoritative context

`S4-PAR-DATA` matched the R3 migration/capacity/release packs but v2 allowed implementation while v1.5 blocked pending authoritative context.

Root cause: large live-data composition modeled technical obligations but not the implementation-authority boundary.

Remediation: `LIVE_DATA_TRANSFORMATION` now requires authoritative context. The existing typed composition still adds release governance without textual keyword matching.

### 4. External authentication composition closure

`S4-PAR-OIDC-SUPPLIER` showed v1.5 obligations for `AUTH_PROTOCOL`, `EXTERNAL_SUPPLIER`, `AUTHORIZATION`, `PRIVACY` and `WEBHOOK_TRUST`, while S3 initially composed only the first two and allowed implementation.

Root cause: S3 had independent fact mappings but lacked the generic composition closure for authentication delegated to an independently operated identity service.

Remediation: a typed `external-authentication-governance-closure` now composes local authorization/session consequences, privacy, callback/response trust and the authoritative-context gate from the conjunction of `AUTHENTICATION_PROTOCOL` and `EXTERNAL_OPERATIONAL_DEPENDENCY`.

This rule contains no OIDC, OAuth, SAML or provider/vendor lexical matching.

## Test-control defect

`S4-SUMMARY-BLOCKS-DOWNGRADE` initially seeded its synthetic aggregate test with the first real shadow item. When that real item was itself a downgrade, the control's exact expected downgrade list became invalid.

This was a control-design defect, not a runtime behavior defect.

Remediation: the aggregate fail-closed test now uses a synthetic known-agreement record plus one synthetic downgrade, making it independent of real-case ordering and health.

## What was deliberately not done

- no S4 expected classification was changed from `AGREEMENT` to `SAFETY_DOWNGRADE` merely to make CI green;
- no failing comparison was suppressed;
- no synonym or business-noun patch was added;
- no root `sef.py` change was made;
- no semantic provider was allowed to self-authorize a high-impact implementation;
- no live-provider quality claim was introduced.

## Interpretation

The first red S4 run is evidence that shadow integration was useful: unit-level S3 tests alone did not expose these cross-system parity gaps.

The remediation is acceptable only if a later S4 run passes the unchanged real-case expectations, all earlier semantic gates replay successfully, legacy DEV remains green and the frozen v1.5 checksum remains exact.
