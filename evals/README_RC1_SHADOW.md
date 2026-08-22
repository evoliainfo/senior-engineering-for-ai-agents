# RC-1 shadow evidence corpus

The shadow gate evaluates two evidence classes:

- **Frozen pre-implementation contracts**: 12 metamorphic cases and 12 negative controls merged before runtime work began.
- **Independent probes**: six additional positive formulations and six lexical near-misses in `rc1_shadow_probe_requests.json`.

The independent probes are not a replacement for held-out evaluation. They are a small anti-overfitting check for the first shadow implementation.

A shadow PASS means only that the detector observed the intended concepts in this visible corpus while producing no concept observation on the visible negatives. It does not authorize routing changes.
