# RC-8 pre-remediation controls — Round 1

This record freezes the first execution of the RC-8 research control corpus before any runtime remediation.

## Evidence identity

- workflow run: `32642367113`
- artifact: `9493943383`
- artifact name: `rc8-pre-remediation-controls-32642367113`
- artifact digest: `sha256:ee66ea46ab793e5ce30067a6bfa72ae76d27d8942c5ec0cfaa624d28a514eb6e`
- runtime SHA-256: `c5fdbcf6a1a8428663c25e15247c481c1268849a2c747de8766bc0946544d6b4`
- catalog SHA-256: `9581cbc652d24d1feb9918ad8c0e105241bc152c94a82bb0eaf29de2dd866363`
- accounting: 14 expected / 14 observed / 14 unique / no missing / no duplicates
- harness errors: none
- raw result: **5 PASS / 9 FAIL**

This is research evidence, not an independent holdout. Control contracts may be calibrated when they are demonstrably mis-specified, but every calibration must be recorded rather than silently replacing the first observation.

## Raw outcomes

| Control | Raw | Interpretation |
| --- | --- | --- |
| `RC8-H1-P1` | FAIL | valid signal: organization-scoped cross-organization denial failed to route tenant/auth domains and stayed R1 |
| `RC8-H1-N1` | PASS | valid negative: single-user auth did not invent multi-tenancy |
| `RC8-H1-P2` | PASS | important falsifier: external SAML SSO successfully composed `AUTH_PROTOCOL` + `EXTERNAL_SUPPLIER` |
| `RC8-H1-N2` | FAIL | **control-contract defect**: local password verification correctly routed `AUTH_PROTOCOL`; requiring `AUTHORIZATION` conflated authentication with authorization. The intended negative (`EXTERNAL_SUPPLIER` absent) passed |
| `RC8-H1-P3` | FAIL | valid signal: large live row transformation expressed without migration/backfill vocabulary stayed R1 with no specialist pack |
| `RC8-H1-N3` | PASS | valid negative: small local fixture generation did not invent production migration/capacity/release governance |
| `RC8-H1-P4` | FAIL | valid signal: mutable production dependency correctly routed supply-chain/release but missed `CONTAINER_ENGINEERING` despite image-build semantics |
| `RC8-H1-N4` | FAIL | valid over-routing signal: a README-only request containing `docker run` triggered `CONTAINER_ENGINEERING` and R3 |
| `RC8-H2-P1` | FAIL | valid signal: caller-selected backend destination expressed as remote resource/location stayed R1 without trust routing |
| `RC8-H2-N1` | PASS | valid negative: browser-only navigation did not trigger server-side external-input trust |
| `RC8-H3-P1` | FAIL | valid signal: outcome-affecting clinical-treatment decision stayed R1, no regulated pack, implementation READY |
| `RC8-H3-N1` | PASS | valid negative: ordinary carton recommendation did not trigger regulated-domain governance |
| `RC8-H4-P1` | FAIL | mixed: actual diff correctly became R3 + destructive migration but still missed `RELEASE_ENGINEERING`; however the initial-plan control was contaminated by wording that already routed database migration, so that precondition must be recalibrated |
| `RC8-H4-N1` | FAIL | **control-contract defect only**: documentation-only actual diff correctly had no migration/release packs and `DOC_ONLY_CHANGED`; actual risk was R0 rather than the unnecessarily strict expected R1 |

## Causal update after Round 1

Round 1 falsifies the idea that all four plan-time CHALLENGE misses are simply one universal composition-closure defect. `RC8-H1-P2` proves that SEF can compose auth protocol + external supplier for a neighboring SAML case.

The stronger cross-cutting observation is **semantic normalization / trigger brittleness**:

1. **Under-triggering on semantic aliases**
   - organization-scoped isolation wording did not map to tenant/auth packs;
   - large live row transformation did not map to migration/capacity/release;
   - caller-selected remote resource destination did not map to server-side external-input trust;
   - clinical treatment recommendation did not map to regulated-domain governance;
   - production image-build semantics did not map to container engineering even while supply-chain/release were recognized.

2. **Over-triggering on salient lexical tokens**
   - a README-only `docker run` sentence triggered `CONTAINER_ENGINEERING` and R3.

3. **Composition still exists as a separate defect where the primary concept is recognized**
   - official `AUTH-003`: `MULTI_TENANT` recognized, `AUTHORIZATION` absent;
   - official `DATA-003`: migration + release recognized, capacity absent;
   - official `REL-002`: container + release recognized, supply chain absent;
   - official `DIFF-003`: destructive migration recognized on actual diff, release absent.

Therefore RC-8 now treats **semantic normalization/trigger quality** and **secondary composition closure** as distinct mechanisms that can interact.

## Hypothesis refinement

### H0 — Semantic normalization / trigger brittleness

SEF appears materially dependent on narrow surface cues for some domains. Equivalent concepts can under-route when expressed with alternative vocabulary, while non-material documentation can over-route when it contains a salient technology token.

This is now a first-class hypothesis and must be tested before adding more trigger phrases. A lexical patch that merely expands keyword lists is not sufficient evidence of semantic generalization.

### H1 — Secondary plan-time composition closure

Retained, but narrowed: apply only when the primary domain is already recognized and a materially implied secondary pack is missing. SAML success shows this is not universally broken.

### H2 — Server-side destination trust model

Retained. The positive semantic variant failed while the browser-only negative passed.

### H3 — Regulated materiality promotion

Retained and strengthened. A distinct clinical decision variant failed even more strongly than `REQ-004`: no human block, no pack, R1, implementation READY.

### H4 — Actual-diff secondary routing

Retained. The actual destructive diff independently reproduced the missing `RELEASE_ENGINEERING` behavior. The initial-plan portion of the probe requires calibration, but the actual-diff observation is valid.

## Permitted calibration before Round 2

Only research-control contracts are corrected; candidate runtime and official CHALLENGE evidence remain untouched.

- `RC8-H1-N2`: require `AUTH_PROTOCOL` rather than incorrectly requiring `AUTHORIZATION`; continue forbidding `EXTERNAL_SUPPLIER`.
- `RC8-H4-N1`: accept R0 for documentation-only actual diff while retaining forbidden migration/release packs and destructive trigger.
- `RC8-H4-P1`: change only the harmless initial request wording so the control actually establishes the intended low-risk/no-migration precondition before injecting the destructive migration.

No other failed expectation is weakened in Round 2.
