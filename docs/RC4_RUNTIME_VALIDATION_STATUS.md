# RC-4 runtime validation status

Integration branch: `integration/rc4-evidence-release`
Base: `main@443a8a0c0fc1d55049f413d51c8a7e68cfcd6c8c`

Checkpoint after canonical runtime patch:

- runtime syntax smoke gate passed during patch application;
- `SHA256SUMS` was regenerated from the modified canonical `sef.py` and immediately verified with `sha256sum -c`;
- the first permanent RC-4 regression run exposed a test-fixture path error (`.sef/state.json` instead of canonical `.sef/project-state.json`); the fixture was corrected without changing runtime semantics;
- this checkpoint commit intentionally re-triggers all PR gates from a normal repository write after the one-shot checksum automation commit;
- promotion remains forbidden until RC-4, Validate SEF, RC-1, RC-2 and RC-3 gates are all green on the same exact integration head;
- CHALLENGE remains sealed.
