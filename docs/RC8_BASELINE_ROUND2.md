# RC-8 calibrated controls — Round 2 conclusion

Round 2 applies only the three transparent research-control calibrations documented after Round 1. Candidate runtime and official CHALLENGE evidence remain unchanged.

## Evidence identity

- workflow run: `32642511765`
- artifact: `9493982380`
- artifact name: `rc8-calibrated-controls-32642511765`
- artifact digest: `sha256:d3a314679a5c75a359016680102f47826b6021321de7d3ae3312692527ae07ce`
- runtime SHA-256: `c5fdbcf6a1a8428663c25e15247c481c1268849a2c747de8766bc0946544d6b4`
- calibrated catalog SHA-256: `74f1cdd0b270bfeca4b80c7ac5540a24307e5da990f42b31157e70c831b70cc1`
- accounting: 14 expected / 14 observed / 14 unique / no missing / no duplicates
- harness errors: none
- calibrated result: **7 PASS / 7 FAIL**

## Remaining valid failures

| Control | Failure class |
| --- | --- |
| `RC8-H1-P1` | organization-scoped isolation/auth semantics under-route completely and stay R1 |
| `RC8-H1-P3` | large live row transformation under-routes completely and stays R1 |
| `RC8-H1-P4` | supply-chain/release detected, but production image-build semantics do not route container engineering |
| `RC8-H1-N4` | README-only `docker run` mention over-routes container engineering and R3 |
| `RC8-H2-P1` | caller-selected privileged backend destination remains R1 with no external-input trust route |
| `RC8-H3-P1` | outcome-affecting clinical decision remains R1, no regulated pack, implementation allowed |
| `RC8-H4-P1` | destructive actual diff routes database migration at R3 but still omits release engineering |

All calibrated negatives now pass.

## Metamorphic evidence

The combined official CHALLENGE and RC-8 controls provide meaning-preserving contrasts without changing the runtime.

### Tenant / authorization

- official `AUTH-003`: explicit `multi-tenant` wording → `MULTI_TENANT` recognized, `AUTHORIZATION` missed;
- `RC8-H1-P1`: organization/cross-organization equivalent semantics → both packs missed, R1;
- `RC8-H1-N1`: explicitly single-user private object access → `AUTHORIZATION` recognized, `MULTI_TENANT` correctly absent.

Interpretation: both semantic normalization and cross-domain composition are implicated.

### Large production data change

- official `DATA-003`: explicit migration/backfill wording → migration + release recognized, capacity missed;
- `RC8-H1-P3`: equivalent very-large live row transformation wording → all three specialist domains missed, R1;
- `RC8-H1-N3`: small local fixture generation → specialist production packs correctly absent.

Interpretation: narrow trigger vocabulary exists upstream of a separate composition gap.

### External identity provider

- official `AUTH-007`: OAuth external provider → auth protocol recognized, external supplier missed;
- `RC8-H1-P2`: SAML external provider → auth protocol + external supplier both recognized;
- calibrated `RC8-H1-N2`: local password auth → auth protocol recognized, external supplier correctly absent.

Interpretation: provider governance composition is not universally broken; behavior varies by protocol/trigger path.

### Container / supply chain

- official `REL-002`: explicit production container + floating base → container + release recognized, supply chain missed;
- `RC8-H1-P4`: mutable remote build dependency + production image → supply chain + release recognized, container missed;
- `RC8-H1-N4`: documentation-only `docker run` sentence → container engineering incorrectly triggered at R3.

Interpretation: raw lexical cues appear to dominate material task semantics in some container routes.

### Trust boundary

- official `EXT-004`: arbitrary caller URL fetched by server → no trust route, R1;
- `RC8-H2-P1`: same privileged-network effect expressed as caller-selected remote resource location → no trust route, R1;
- `RC8-H2-N1`: browser-only navigation with no server fetch → trust route correctly absent.

Interpretation: the gap is broader than the exact word `URL`; server-side destination control is not modeled strongly enough.

### Regulated materiality

- official `REQ-004`: medication-dose recommendation → regulated human decision detected, but pack/risk promotion missing;
- `RC8-H3-P1`: different clinical treatment decision → regulated signal missed entirely, R1, implementation READY;
- `RC8-H3-N1`: ordinary carton recommendation → regulated pack correctly absent.

Interpretation: regulated detection is both narrow and inconsistently propagated into risk/pack/implementation gates.

### Actual diff

- official `DIFF-003`: destructive migration in diff → R1→R3, database migration present, release absent;
- calibrated `RC8-H4-P1`: independent destructive migration variant → same missing release behavior;
- calibrated `RC8-H4-N1`: doc-only actual diff → R0, no migration/release, no destructive trigger.

Interpretation: actual-diff secondary release routing is reproducibly incomplete, while the negative path is clean.

## Final RC-8 causal model

### Confirmed C0 — semantic trigger/materiality brittleness

Strong evidence. SEF can both under-route semantically equivalent wording and over-route salient technology words in non-material documentation. This is broader than adding seven missing phrases.

### Confirmed C1 — secondary composition closure gaps

Strong evidence, but non-universal. When one domain is recognized, materially coupled domains can still be absent. The SAML control proves composition exists on some paths, so remediation must target interaction invariants rather than globally adding every related pack.

### Confirmed C2 — server-side destination trust gap

Strong evidence. Two positive formulations fail and the client-only negative passes.

### Confirmed C3 — regulated materiality classification/promotion gap

Strong evidence. One official case partially detects material context without pack/risk promotion; an independent clinical variant misses the regulated signal entirely.

### Confirmed C4 — actual-diff secondary release-routing gap

Strong evidence. Reproduced independently with a clean doc-only negative.

## Finite remediation plan

RC-8 research is complete. Runtime work is intentionally limited to **two structural integration phases plus one regression-only closeout**, rather than an open-ended sequence of lexical RC patches.

### Runtime Phase B1 — semantic materiality layer

Goal: improve concept recognition while preventing lexical over-triggering.

Required outcomes:
- material task semantics outrank incidental documentation words;
- organization/tenant aliases normalize to the same underlying boundary when task-material;
- large live data transformations normalize to migration/capacity semantics without requiring the word `backfill`;
- production image/container semantics normalize without requiring one exact Docker token;
- caller-controlled privileged server destinations become an explicit trust concept;
- outcome-affecting regulated/clinical decisions become an explicit regulated-materiality concept;
- existing negatives remain negative.

### Runtime Phase B2 — composition closure across plan and actual diff

Goal: derive only materially implied secondary governance from recognized concepts.

Required outcomes:
- tenant-scoped object access composes tenant isolation + authorization;
- external protocol/provider dependencies compose supplier governance only when a provider contract is material;
- large online data transformation composes migration + capacity + release;
- production reproducibility/provenance composes container/supply-chain/release as applicable;
- destructive production migrations found in the actual diff add release governance;
- no global all-to-all pack expansion.

### Phase B3 — regression closeout only

No new architecture in B3. Required before freeze:
- existing deterministic DEV remains 38/38;
- official consumed CHALLENGE cases become explicit regression cases and all pass;
- calibrated RC-8 positives and negatives all pass;
- RC-1..RC-7 gates all remain green;
- no unresolved broad over-routing introduced by B1/B2.

After B3, freeze the new candidate. Only then create concrete CHALLENGE v2 content and execute its first valid run.

## RC-8 research verdict

**COMPLETE — READY_FOR_SEPARATE_RUNTIME_INTEGRATION**

No concrete CHALLENGE v2 scenarios have been materialized. `sef.py` and `SHA256SUMS` remain unchanged in this research PR.
