#!/usr/bin/env python3
"""Build an isolated B2 composition-closure candidate from canonical B1.

B2 is deliberately bounded. It derives only secondary governance that is materially
implied by already-recognized request concepts, and adds one actual-diff closure for
destructive migrations. It does not implement all-to-all pack expansion.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

EXPECTED_INPUT_SHA256 = "a32437274e4617da28626c027f4162328d2ea0ded831366db1677bd815360cc3"

REQUEST_HELPER = r'''
# ---------- B2 bounded request composition closure ----------
def _b2_request_composition(request,change,result):
    positive,_,_=_rc2_positive_request_text(request)
    text=_rc1_normalize_text(positive)
    packs=set(result.get("required_context_packs",[]))
    b1=change.get("b1_semantic_materiality",{}) if isinstance(change,dict) else {}
    concepts=set(b1.get("concepts",[]))
    obligations=[]; evidence=[]

    def has(pattern): return re.search(pattern,text,re.I) is not None
    def add_pack(pack,reason):
        if pack not in packs:
            packs.add(pack)
            evidence.append({"pack":pack,"reason":reason,"source":"b2_composition"})
    def add_obligation(obligation):
        if obligation not in obligations: obligations.append(obligation)

    # External identity protocol + material provider contract => supplier governance.
    # Local authentication remains outside this composition.
    auth_protocol=has(r"\b(?:oauth(?:\s*2(?:\.0)?)?|oidc|openid(?: connect)?|saml|authorization[- ]code)\b")
    external_identity=(
        has(r"\b(?:external|third[- ]party|federated|enterprise)\b.{0,90}\b(?:identity provider|identity service|idp|provider)\b")
        or has(r"\b(?:identity provider|identity service|idp)\b.{0,90}\b(?:external|third[- ]party|federated|enterprise)\b")
    )
    callback_flow=has(r"\b(?:callback|redirect|authorization[- ]code|auth code|session establishment|establish(?:ing)? (?:the )?session)\b")
    if "AUTH_PROTOCOL" in packs and auth_protocol and external_identity:
        add_pack("EXTERNAL_SUPPLIER","authentication correctness materially depends on an external identity-provider contract")
        if callback_flow:
            add_obligation("EXTERNAL_AUTH_CALLBACK_INTEGRITY")

    # Large online data work => capacity and release governance in addition to migration.
    large_scale=has(r"\b(?:\d+(?:\.\d+)?\s*(?:million|billion)|(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)\s+(?:million|billion)|millions? of|billions? of|tens of millions?|very large|large[- ]scale)\b")
    live_pressure=has(r"\b(?:live traffic|traffic continues?|normal writes|writes continue|service remains online|remain(?:s|ing)? online|online|without downtime|locking|database load|bound .*load|rollout risk|blast radius|production traffic)\b")
    large_online=("LARGE_ONLINE_DATA_TRANSFORMATION" in concepts) or ("DATABASE_MIGRATION" in packs and large_scale and live_pressure)
    if large_online:
        add_pack("DATABASE_MIGRATION","large online stored-data transformation has migration semantics")
        add_pack("PERFORMANCE_CAPACITY_COST","large online transformation creates material load/locking/capacity pressure")
        add_pack("RELEASE_ENGINEERING","large online transformation requires staged rollout and recovery-aware release control")
        add_obligation("BOUNDED_ONLINE_DATA_TRANSFORMATION")

    # Mutable production build inputs invalidate reproducibility without provenance.
    mutable_source=has(r"(?:\:[ ]*latest\b|\b(?:floating|unpinned|mutable)\s+(?:tag|version|base|dependency|reference|source)\b|\b(?:default|main|master)\s+branch\b|\bfrom\s+(?:the\s+)?default\s+branch\b)")
    production_artifact=(
        "CONTAINER_ENGINEERING" in packs
        or "PRODUCTION_IMAGE_BUILD" in concepts
        or has(r"\b(?:production|release)\s+(?:container|image|artifact)\b")
    )
    reproducibility=has(r"\b(?:reproducib|reproducible|provenance|publish|promote|release|artifact identity)\w*\b")
    image_surface=has(r"\b(?:container|production image|container image|runtime image|oci image|image build|resulting image)\b")
    if mutable_source and production_artifact and reproducibility:
        if image_surface: add_pack("CONTAINER_ENGINEERING","mutable input participates in a production image/artifact build")
        add_pack("CI_SUPPLY_CHAIN","mutable production build input makes provenance and reproducibility a supply-chain concern")
        add_pack("RELEASE_ENGINEERING","reproducibility claim is material to a promoted release artifact")
        add_obligation("MUTABLE_PRODUCTION_BUILD_INPUT")

    # B1 owns primary SSRF/trust recognition; B2 adds the concrete derived obligation.
    if "SERVER_SIDE_DESTINATION_TRUST" in concepts:
        add_obligation("CALLER_CONTROLLED_SERVER_DESTINATION")

    return {
      "required_context_packs":sorted(packs),
      "obligations":obligations,
      "evidence":evidence,
    }
'''

ACTUAL_DIFF_HELPER = r'''
# ---------- B2 actual-diff composition closure ----------
def _b2_actual_diff_composition(assessment):
    if not isinstance(assessment,dict): return assessment
    triggers=set(assessment.get("triggers",[]))
    packs=set(assessment.get("required_context_packs",[]))
    evidence=list(assessment.get("b2_actual_diff_composition",[])) if isinstance(assessment.get("b2_actual_diff_composition",[]),list) else []
    if "DESTRUCTIVE_DATA_CHANGE" in triggers and "DATABASE_MIGRATION" in packs:
        if "RELEASE_ENGINEERING" not in packs:
            packs.add("RELEASE_ENGINEERING")
            evidence.append({"pack":"RELEASE_ENGINEERING","reason":"destructive migration discovered in actual diff requires release/recovery governance","source":"b2_actual_diff"})
    assessment["required_context_packs"]=sorted(packs)
    assessment["b2_actual_diff_composition"]=evidence
    return assessment
'''


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one anchor, found {count}")
    return source.replace(old, new, 1)


def build(source: str) -> str:
    source = replace_once(
        source,
        '    large_scale=has(r"\\b(?:\\d+(?:\\.\\d+)?\\s*(?:million|billion)|millions? of|billions? of|very large|large[- ]scale|tens of millions?)\\b")',
        '    large_scale=has(r"\\b(?:\\d+(?:\\.\\d+)?\\s*(?:million|billion)|(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)\\s+(?:million|billion)|millions? of|billions? of|very large|large[- ]scale|tens of millions?)\\b")',
        "B1 scale invariant completion",
    )
    source = replace_once(
        source,
        '    caller_control=has(r"\\b(?:caller|user|client)\\b.{0,80}\\b(?:suppl(?:y|ies|ied)|provide|provided|choose|chooses|selected?|control(?:s|led)?)\\b") or has(r"\\b(?:user-provided|caller-provided|caller-selected|user-selected)\\b")',
        '    caller_control=(has(r"\\b(?:caller|user|client)\\b.{0,80}\\b(?:suppl(?:y|ies|ied)|provide|provided|choose|chooses|selected?|control(?:s|led)?)\\b") or has(r"\\b(?:user-provided|caller-provided|caller-selected|user-selected)\\b") or has(r"\\b(?:accept|accepts|receive|receives|take|takes)\\b.{0,90}\\b(?:from|by)\\s+(?:the\\s+)?(?:caller|user|client)\\b") or has(r"\\b(?:url|uri|remote resource|remote location|destination|target address|network location|external location)\\b.{0,90}\\b(?:from|by)\\s+(?:the\\s+)?(?:caller|user|client)\\b"))',
        "B1 caller-destination relation completion",
    )
    source = replace_once(
        source,
        'def _assess_request(repo,request):',
        REQUEST_HELPER + '\n\ndef _assess_request(repo,request):',
        "B2 request helper insertion",
    )
    source = replace_once(
        source,
        '        result["request_human_decisions"]=sorted(set(change.get("b1_human_decisions",[])))\n        result["b1_semantic_materiality"]=change.get("b1_semantic_materiality",{})\n        result["request_detection"]=change["request_detection"]',
        '        result["request_human_decisions"]=sorted(set(change.get("b1_human_decisions",[])))\n        result["b1_semantic_materiality"]=change.get("b1_semantic_materiality",{})\n        b2=_b2_request_composition(request,change,result)\n        result["required_context_packs"]=b2.get("required_context_packs",result.get("required_context_packs",[]))\n        result["b2_obligations"]=b2.get("obligations",[])\n        result["b2_composition_evidence"]=b2.get("evidence",[])\n        result["request_detection"]=change["request_detection"]',
        "B2 request composition application",
    )
    source = replace_once(
        source,
        '    for p in sorted(packs): req += by.get(p,[])\n    exec_ctx=set(assessment.get("request_execution_contexts",[]))',
        '    for p in sorted(packs): req += by.get(p,[])\n    b2_obligations=set(assessment.get("b2_obligations",[]))\n    if "EXTERNAL_AUTH_CALLBACK_INTEGRITY" in b2_obligations:\n        req += ["For an external authorization-code/OIDC callback, bind and verify state/CSRF protection, validate the exact redirect/callback target and code exchange before session establishment, and verify provider-specific behavior against current authoritative provider documentation."]\n    if "BOUNDED_ONLINE_DATA_TRANSFORMATION" in b2_obligations:\n        req += ["Execute the online data transformation/backfill in bounded batches or chunks with explicit pause/resume and reconciliation semantics; measure lock duration, database load and capacity impact before increasing rollout scope."]\n    if "MUTABLE_PRODUCTION_BUILD_INPUT" in b2_obligations:\n        req += ["A floating/latest tag or mutable branch cannot establish reproducible artifact identity by itself; pin an immutable digest/revision and preserve build provenance before release claims."]\n    if "CALLER_CONTROLLED_SERVER_DESTINATION" in b2_obligations:\n        req += ["Treat caller-controlled server destinations as untrusted external input: prevent SSRF to internal/private network and cloud metadata targets, and define explicit allowlist/deny plus destination validation before the server performs the request."]\n    exec_ctx=set(assessment.get("request_execution_contexts",[]))',
        "B2 derived obligations",
    )
    old_assess = 'def assess(repo,base="HEAD"):\n    repo=Path(repo).resolve(); td,root=_runtime_root()\n    try: return _load_bootstrap(root).assess_git(repo,base,True)\n    finally: td.cleanup()'
    new_assess = ACTUAL_DIFF_HELPER + '\n\ndef assess(repo,base="HEAD"):\n    repo=Path(repo).resolve(); td,root=_runtime_root()\n    try:\n        result=_load_bootstrap(root).assess_git(repo,base,True)\n        return _b2_actual_diff_composition(result)\n    finally: td.cleanup()'
    source = replace_once(source, old_assess, new_assess, "B2 actual-diff composition")
    return source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow-input-sha", default=EXPECTED_INPUT_SHA256)
    args = parser.parse_args()

    inp = Path(args.input)
    out = Path(args.output)
    raw = inp.read_bytes()
    actual = sha256(raw)
    if actual != args.allow_input_sha:
        raise SystemExit(f"unexpected input SHA-256: {actual}; expected {args.allow_input_sha}")
    candidate = build(raw.decode("utf-8"))
    out.write_text(candidate, encoding="utf-8")
    print(f"input_sha256={actual}")
    print(f"candidate_sha256={sha256(candidate.encode('utf-8'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
