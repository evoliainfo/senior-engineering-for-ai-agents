# Semantic Routing v2 — S3 Deterministic Policy Composer

## Purpose

S3 turns **validated Semantic IR relations** into canonical governance without invoking a model or re-reading free text.

This is the authority boundary of Semantic Routing v2:

- S2 may propose semantic facts.
- S3 alone maps validated facts to governance packs, procedures and minimum risk.
- S3 never calls a semantic provider.
- Literal business nouns such as `department`, `branch`, `region` or `division` do not appear in policy rules.
- A semantic provider cannot grant the authoritative context needed to execute a high-impact change.

The frozen v1.5 root runtime remains unchanged and canonical routing is still v1.5 until later promotion/freeze gates are completed.

## Core mappings

| Semantic relation | Governance |
| --- | --- |
| `ACCESS_CONTROL_BOUNDARY` | `AUTHORIZATION`, R3, authoritative context required |
| `PARTITION_ISOLATION` | `MULTI_TENANT`, R3, authoritative context required |
| `SERVER_DESTINATION_TRUST` | `WEBHOOK_TRUST`, R3 |
| `EXTERNAL_OPERATIONAL_DEPENDENCY` | `EXTERNAL_SUPPLIER`, R3 |
| `CONSEQUENTIAL_DECISION` | `REGULATED_DOMAIN`, R4, implementation blocked pending qualified authority |
| `LIVE_DATA_TRANSFORMATION` | `DATABASE_MIGRATION`, R3, authoritative context required |
| `CAPACITY_MATERIALITY` | `PERFORMANCE_CAPACITY_COST`, R3 |
| `PRODUCTION_RELEASE_CHANGE` | `RELEASE_ENGINEERING`, R2 |
| `AUTHENTICATION_PROTOCOL` | `AUTH_PROTOCOL`, R2 |
| `DEPLOYMENT_ARTIFACT` | `CONTAINER_ENGINEERING`, R2 |
| `BUILD_SUPPLY_CHAIN` | `CI_SUPPLY_CHAIN`, R2 |
| `UNTRUSTED_FILE_INPUT` | `FILE_UPLOAD_SECURITY`, R2 |

## Deterministic composition closure

### Large live data

A material `LIVE_DATA_TRANSFORMATION` together with `CAPACITY_MATERIALITY` adds `RELEASE_ENGINEERING` and the progressive-delivery procedure. This is a typed relation composition, not a keyword rule.

### External authentication

`AUTHENTICATION_PROTOCOL` together with `EXTERNAL_OPERATIONAL_DEPENDENCY` closes the generic governance obligations created when authentication is delegated to an independently operated identity service:

- `AUTHORIZATION` for the local identity/session boundary;
- `PRIVACY` for identity/personal-data processing;
- `WEBHOOK_TRUST` for the externally supplied authentication response/callback;
- R3 minimum risk;
- authoritative context required before implementation.

This composition is protocol- and vendor-agnostic. The policy rule contains no OIDC, SAML, OAuth or provider-name matching.

## Authoritative-context gate

Some validated semantic facts prove that a material control boundary exists, but they do **not** prove that the project has supplied authoritative requirements sufficient to implement that boundary safely.

For those families S3 is deny-by-default:

- governance packs/procedures and minimum risk are still composed;
- `implementation_allowed=false`;
- `implementation_gate=BLOCKED_PENDING_AUTHORITATIVE_CONTEXT`;
- the model cannot clear the gate by asserting that authority exists.

A later deterministic trusted-context mechanism may clear such a gate only with auditable non-provider evidence. Until then the block is intentional.

## Fail-closed semantics

### Valid but unresolved Semantic IR

If `review_state = SEMANTIC_REVIEW_REQUIRED`:

- confirmed facts retain their minimum governance packs/procedures;
- final `risk` is `null` rather than inventing a low-risk answer;
- `minimum_risk_from_resolved_facts` preserves known safety evidence;
- implementation is blocked;
- release decision is `BLOCKED_SEMANTIC_REVIEW`.

### Invalid Semantic IR

Invalid IR produces `INVALID_IR` with no policy claims and blocks implementation.

### Consequential decisions

`CONSEQUENTIAL_DECISION` maps to regulated escalation at **R4** and blocks implementation until qualified authority/policy exists. S3 does not grant that authority itself.

## Required invariants

1. deterministic: same IR -> byte-equivalent policy object;
2. idempotent: repeated composition does not change output;
3. monotonic safety: adding material facts cannot lower risk, remove packs/procedures or turn an existing deny into allow;
4. order independent at the governance level;
5. complete rule coverage for every fact kind declared in `sef.semantic-ir.v1`;
6. no provider/model/network imports or calls in the composer;
7. business noun variation does not change governance for the same relation graph;
8. high-impact authority cannot be self-granted by semantic-provider output;
9. root `sef.py` and `SHA256SUMS` remain unchanged.

## Evidence boundary

S3 validates **deterministic policy composition only**. It does not prove live-provider semantic accuracy and it does not promote v2 to canonical routing. S4 runs v1.5 and v2 side-by-side and measures disagreements.
