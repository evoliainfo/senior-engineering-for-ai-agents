# RC-2 Polarity / Negation — Experiment Gate

Status: PRE-IMPLEMENTATION RESEARCH

Baseline runtime: `main` after RC-1 additive routing (`687c0f31fede90a517d90e5435f97ce8be24e5b6`).

No runtime change is authorized by this document.

## 1. Confirmed symptom

Official scenario `DIFF-004` asks:

> Update README documentation wording only; do not change runtime, deployment or infrastructure.

The plan must remain documentation-only. The actual diff later adds Docker, GitHub Actions and Terraform and must still escalate to the corresponding actual-diff controls.

The residual failure is pre-diff: request routing sees sensitive nouns inside a negative scope (`do not change ... deployment or infrastructure`) and activates specialist routing that the user explicitly excluded.

RC-1 intentionally did not solve this because concept normalization and polarity are separate concerns.

## 2. Safety objective

RC-2 must distinguish a bounded negative/non-goal statement from a positive requested change without weakening actual-diff detection.

Required invariant:

```text
negative request scope may suppress request-derived routing

actual diff evidence can NEVER be suppressed by request polarity
```

A phrase such as `do not change deployment` may affect the *plan* request route. If deployment files are actually changed, verify/actual-diff must still route them normally.

## 3. Candidate architecture boundary

Preferred first candidate: deterministic clause-local polarity classification applied only to request-derived signals.

Pipeline:

```text
raw request
  -> clause segmentation
  -> bounded polarity cues
  -> positive / negative / uncertain clause annotation
  -> legacy + RC-1 request detections with source spans
  -> suppress only detections fully governed by a clear negative clause
  -> existing policy engine

actual diff --------------------------------> independent existing routing
```

No LLM, embeddings, generic sentiment model or broad NLP dependency is introduced.

## 4. Polarity cues to test

Initial English cues:

- `do not`, `don't`
- `must not`, `should not`
- `without changing`, `without modifying`, `without touching`
- `leave ... unchanged`
- `keep ... unchanged`
- `no changes to`
- `out of scope`, `not in scope`

Initial French cues:

- `ne ... pas`
- `sans changer`, `sans modifier`, `sans toucher`
- `laisser ... inchangé`
- `garder ... inchangé`
- `aucun changement de/à`
- `hors périmètre`

These are candidate cues, not an authorization to implement them before probes are frozen.

## 5. Required treatment probes

At minimum freeze probes for:

1. `Update README only; do not change deployment or infrastructure.`
2. `Change the copy without touching authentication or permissions.`
3. `Refactor the parser; no changes to the database schema.`
4. `Update documentation; leave CI and Docker unchanged.`
5. `Modifie le README sans changer le déploiement ni l'infrastructure.`
6. `Change the API and authorization, but do not change deployment.` — positive auth must remain routed; deployment must not.
7. `Do not remove authorization checks; strengthen the admin permission rule.` — positive authorization intent must remain routed despite a nearby negative cue.
8. `Do not disable the webhook signature check; add replay protection.` — webhook/security intent must remain routed.

## 6. Required negative controls against over-suppression

The polarity layer must NOT suppress routing in:

1. `Add authorization so users cannot access another user's profile.`
2. `Prevent duplicate webhook processing.`
3. `Ensure the migration does not lose stored data.`
4. `The deployment must not expose port 80 publicly; change the infrastructure accordingly.`
5. `Do not forget to add the database migration.`
6. `We cannot leave authentication unchanged; add MFA.`
7. `No unauthenticated user may access admin endpoints.`
8. `Without authorization this endpoint is unsafe; implement role checks.`

These controls are critical because lexical negation does not always mean “exclude this engineering domain”. Sometimes the negation describes the required safety property or appears inside a double-negative/obligation construction.

## 7. Metamorphic requirements

Equivalent non-goal formulations should produce equivalent request routing:

- `do not change deployment`
- `leave deployment unchanged`
- `without modifying deployment`
- French equivalent where supported

Equivalent positive safety requirements must continue to route:

- `users cannot access other users`
- `deny cross-user access`
- `prevent access to another user's record`

## 8. Hard gates before behavioral integration

1. Freeze treatment + over-suppression controls before runtime tuning.
2. Record baseline results on current `main` with durable CI evidence.
3. Zero new critical false negatives on official DEV.
4. Zero regression of RC-1 routing gate.
5. Zero new suppression of actual-diff specialist routing.
6. `DIFF-004` plan becomes light while its mutated actual diff still escalates to Docker/CI/IaC R3.
7. RC-3 (`WEB-001`) and RC-4 Evidence/Release expectations are not weakened or changed in the RC-2 patch.
8. CHALLENGE remains held out from tuning.

## 9. Design risks

### Over-suppression

The largest risk. A naive `not` window could suppress real security intent, e.g. `users must not access other users`.

### Clause leakage

A negative cue in one clause must not suppress a positive change in a later clause: `do not change deployment; add authorization`.

### Double-negative / obligation language

`do not forget to add migration`, `cannot leave auth unchanged`, and prohibitive safety requirements are semantically positive engineering requirements.

### Span quality

RC-1 observations currently carry match spans. Legacy routing evidence is less span-rich. The RC-2 implementation must not silently infer broad suppression across an entire request merely because one cue exists.

## 10. Recommended implementation sequence

1. Freeze RC-2 probes and controls in a dedicated diagnostic set.
2. Persist baseline artifacts on unchanged post-RC-1 runtime.
3. Implement a shadow polarity annotator only; no routing effect.
4. Audit treatment/control behavior.
5. Build an executable additive/suppressive candidate outside canonical runtime if needed.
6. Compare official DEV + RC-1 gates + RC-2 probes + Evidence/Release.
7. Promote into canonical `sef.py` only if all hard gates pass.

## 11. Current decision

Proceed with RC-2 diagnostic probes and shadow polarity observation. Do not modify canonical request routing yet.