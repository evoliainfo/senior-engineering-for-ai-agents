# CHALLENGE v3 — Official Independent Verdict

## Executive verdict

The final fresh deterministic holdout for the current SEF architecture completed as a **valid independent measurement** and did **not** meet the predeclared 10/10 target.

- frozen candidate commit: `3630f563f24b3577ad1e6a0a05e66a86615dabca`
- runtime SHA-256: `c2203602cb53229aba55bbbb518725c155785838915e75267714bc4e2d3d35ee`
- catalog SHA-256: `acf2d37f2c5692a05acca90b7116b3fd66c10ed1ba103e288596d310d564bacb`
- official run: `32657568114`
- harness integrity: **PASS**
- accounting: **10 expected / 10 observed / 10 unique**
- result: **9 PASS / 1 FAIL**
- critical failure: **`V3-AUTH-002`**
- artifact: `9497844102`
- artifact digest: `sha256:702e855db549d229e4b186dda522c77dccbc37e318db86cdde1de60469a4ca0d`
- official decision: **`STOP_DETERMINISTIC_TUNING_ARCHITECTURE_DECISION`**

The holdout is now consumed. Its scenarios may be used only as regression evidence and must never be presented as a fresh independent benchmark again.

## Why the measurement is valid

The v3 scenarios and expectations were materialized only after the candidate had been frozen. Before the first execution the evaluator branch contained only the holdout protocol, manifest, workflow and ten scenario files; `sef.py` and `SHA256SUMS` were unchanged.

The one-shot workflow then proved before execution that:

1. `candidate/frozen-3630f563` resolved to the declared frozen commit;
2. the runtime extracted from that commit matched the declared SHA-256;
3. all ten scenario IDs were unique and complete;
4. the canonicalized scenario catalog matched the predeclared catalog hash;
5. all ten scenarios executed exactly once;
6. no harness error occurred;
7. the result was produced by the exact frozen runtime.

The final benchmark gate failed only because the benchmark score was below 10/10, not because the measurement was invalid.

## The single failure

### `V3-AUTH-002`

The request described a shared application with separate departmental work queues. An operator assigned to one department could edit only that department's work items, and supplying another department identifier must never expose or modify the other department's items.

Expected governance:

- risk at least `R3`;
- `AUTHORIZATION`;
- partition-isolation governance represented by the existing `MULTI_TENANT` pack;
- specialist authorization and isolation procedures.

Observed:

- risk `R1`;
- packs `[]`;
- no authorization procedure;
- no isolation procedure;
- implementation gate `READY`.

This is a complete miss of a material access boundary.

## Fairness check on the expectation

There is one legitimate ontology question: should an internal department be represented by a pack named `MULTI_TENANT`, or should that pack be reserved for customer/tenant boundaries?

That question does **not** invalidate the failure. Even if `MULTI_TENANT` were removed from the expected outcome, the request explicitly defines an authorization constraint: an operator must not access or modify another department's objects. The runtime also failed to activate `AUTHORIZATION` and remained at `R1`.

Therefore the critical classification failure survives the most conservative interpretation of the expected ontology.

## Structural diagnosis

The current deterministic architecture has improved substantially: nine new v3 scenarios generalized successfully across object authorization, high-volume online data transformation, server-side destination trust, ordinary external supplier dependency, employment-domain consequential decisions, content-only non-goals and actual-diff release proportionality.

The remaining failure exposes a structural limitation rather than a justified one-line patch opportunity. Business-partition recognition still depends on a bounded semantic vocabulary and relation patterns. Previously exercised terms such as tenant, workspace, organization, dealer group or franchise can route correctly; a new but valid partition concept such as department can fall outside that bounded vocabulary.

Adding `department` to another regular expression would make this particular test pass but would not establish generalization to division, region, business unit, legal entity, branch, school, clinic, account domain or future unseen partition terms. Retuning against the final holdout would also violate the predeclared finite completion policy.

## What is now prohibited

For this deterministic architecture line:

- do not patch `V3-AUTH-002` into the frozen runtime;
- do not create CHALLENGE v4;
- do not relabel v3 as a pass;
- do not use a Codex L2 success to erase the deterministic critical failure;
- do not claim robust open-ended business-partition generalization.

## Architecture choices

### A. Full semantic-routing redesign

Replace the most safety-sensitive open-ended lexical routing with a structured semantic classification stage. The classifier should emit a typed intermediate representation such as actors, resources, actions, ownership/scoping relations, trust boundaries, external dependencies, regulated decisions and materiality. Deterministic policy composition then operates on that structured representation rather than directly on a growing vocabulary of phrases.

This is the strongest route to the original ambition, but it is a new architecture line. It requires new calibration controls, new independent holdouts and renewed L2 qualification.

### B. Constrained beta release

Preserve the current frozen deterministic engine as a beta/experimental release whose documented claim is narrower than universal semantic governance. State explicitly that the deterministic router is strong on covered concepts but may miss unfamiliar business-partition language and therefore must not be treated as the sole security-policy authority for high-impact changes.

This allows the substantial deterministic work to remain usable without overstating what the independent evidence proves.

### C. Hybrid recommendation

The recommended path is a hybrid of A and B:

1. preserve the current runtime and all benchmark evidence as an auditable **v1.5 beta deterministic core**;
2. do not advertise full generalized policy routing;
3. optionally run Codex L2 as **exploratory brownfield evidence**, clearly separated from release-gate evidence;
4. open a new architecture track for a typed semantic-classification layer focused first on authorization/partition/trust relations;
5. only make a stronger release claim after that new architecture earns new independent holdout evidence.

This avoids both failure modes: endless regex tuning on one side, and discarding a largely successful and well-tested deterministic core on the other.

## Release status

Current machine-readable release state is **`ARCHITECTURE_DECISION_REQUIRED`** with `release_eligible=false` under the original full-generalization objective.

Codex L2 remains `NOT_RUN`. It is not the next automatic gate. Its role depends on the chosen release scope: exploratory evidence for a constrained beta, or later qualification evidence for a redesigned architecture.
