# CHALLENGE v2 protocol

Status before first execution: **SEALED / UNEXECUTED**

## Candidate under test

- Freeze: `FZ-2026-08-23-4132711F`
- Candidate ref: `candidate/frozen-4132711f`
- Candidate commit: `4132711f9d0ad74ff41b26deff7b9966d6e54e94`
- `sef.py` SHA-256: `bfeda790cd70c78ceb9fae862441df35c9bfe819001c0d429c09c0dde2a0c2bd`

The evaluator branch is not the candidate. CI extracts `sef.py` directly from the frozen candidate commit and verifies the hash before execution.

## Independence rules

1. The 10 scenarios and all expectations are committed before the PR that triggers execution is opened.
2. No candidate output is observed before sealing the catalog.
3. The scenarios are new situations, not direct paraphrases of CHALLENGE #1.
4. The first **valid** run is the official independent verdict.
5. A run with harness/accounting integrity failure is invalid, not a benchmark result. A rerun after such a failure may change only harness mechanics, never scenario semantics, expectations, or the frozen runtime.
6. After the first valid run, CHALLENGE v2 becomes consumed and cannot be used as an independent holdout again.
7. Target: **10/10 PASS** with zero harness errors.

## Coverage

The holdout covers:
- shared-customer authorization/isolation;
- large online data transformation under live write pressure;
- caller-controlled backend network destinations;
- production container/supply-chain reproducibility;
- a regulated consumer-finance decision;
- inbound payment callbacks plus supplier governance;
- outbound SaaS supplier dependency;
- actual-diff container/CI/release escalation;
- actual-diff infrastructure/network escalation;
- proportionality for marketing copy that mentions security features.

Catalog SHA-256 (canonical semantic JSON): `9372dec1460c43d96cdca688113fa1a8bf2ca7a74b04008b387d694eb720f041`
