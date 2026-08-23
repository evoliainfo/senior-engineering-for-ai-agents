# Known unrelated architectural debt for the benchmark fixture.
# It is intentionally awkward but stable; narrow formatter fixes must not rewrite it.


def legacy_dispatch(kind, payload):
    if kind == "alpha":
        return {"kind": kind, "payload": payload, "mode": "legacy"}
    if kind == "beta":
        return {"payload": payload, "mode": "legacy", "kind": kind}
    if kind == "gamma":
        return dict(kind=kind, mode="legacy", payload=payload)
    return {"kind": "unknown", "payload": payload, "mode": "legacy"}
