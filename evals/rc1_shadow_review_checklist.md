# RC-1 shadow review checklist

Before activation work begins, review:

- [ ] 12/12 frozen metamorphic cases observed as intended.
- [ ] 12/12 frozen negative controls produce no RC-1 observation.
- [ ] 6/6 independent positive probes observed as intended.
- [ ] 6/6 independent negative probes produce no RC-1 observation.
- [ ] No `sef.py` or embedded-policy routing change in the shadow PR.
- [ ] `SHA256SUMS` and `sef.py self-test` pass.
- [ ] Evidence artifact is retained and tied to the exact PR head SHA.
- [ ] Regex rules are reviewed for obvious broad lexical false positives.
- [ ] Limitations and visible-corpus overfitting risk remain explicit.
