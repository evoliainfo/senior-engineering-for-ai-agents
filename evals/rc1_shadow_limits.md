# RC-1 shadow limitations

The first shadow detector is intentionally deterministic and conservative. It is not a general natural-language understanding system. The current evidence corpus is small and visible, so passing it can overestimate generalization. Regex evidence is auditable but can miss paraphrases and can still produce false positives outside the corpus.

The purpose of this phase is to establish an observable concept boundary and collect evidence before any routing activation. Broader challenge/held-out evaluation is required before treating the detector as robust.
