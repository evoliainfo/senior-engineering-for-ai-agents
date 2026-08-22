# RC-1 shadow output contract

`detect_concepts(request)` returns a JSON-serializable object with:

- `mode = SHADOW_ONLY`
- `version`
- original and normalized request text
- zero or more `observations`
- candidate output `{kind, id}` for each observation
- matched regex evidence with exact normalized-text spans
- `routing_effect = NONE`

Consumers must treat `candidate_outputs` as telemetry, not as SEF routing instructions, until a later activation change explicitly promotes them.
