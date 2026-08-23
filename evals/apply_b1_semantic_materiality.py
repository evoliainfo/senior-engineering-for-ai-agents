#!/usr/bin/env python3
"""Build a B1 semantic-materiality candidate from a frozen SEF source.

This patcher is intentionally temporary. It never edits the input file in place.
Promotion into canonical sef.py is allowed only after the B1 candidate passes the
full deterministic DEV baseline and the B1 positive/negative control surface.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

EXPECTED_INPUT_SHA256 = "c5fdbcf6a1a8428663c25e15247c481c1268849a2c747de8766bc0946544d6b4"

HELPERS = r'''
# ---------- B1 semantic materiality normalization ----------
# B1 recognizes task-material semantic relations before downstream composition.
# It deliberately does not implement transitive pack closure (B2) or actual-diff
# secondary release routing (B2). Rules require conjunctions of meaning-bearing
# signals so isolated technology words do not become policy decisions.
def _b1_semantic_materiality(original_request,positive_request):
    text=_rc1_normalize_text(positive_request)
    original=_rc1_normalize_text(original_request)
    concepts=set(); primary_packs=set(); human_decisions=set(); evidence=[]; risk_floor="R0"

    def has(pattern): return re.search(pattern,text,re.I) is not None
    def add(concept,pack=None,risk=None,reason=""):
        nonlocal risk_floor
        concepts.add(concept)
        if pack: primary_packs.add(pack)
        if risk and RISK_ORDER.get(risk,0)>RISK_ORDER.get(risk_floor,0): risk_floor=risk
        evidence.append({"concept":concept,"reason":reason,"source":"b1_semantic_materiality"})

    # Explicit documentation-only non-goal. This is intentionally narrow: it
    # suppresses legacy Docker token routing only when the request itself says
    # runtime/build/delivery configuration must not change.
    doc_surface=bool(re.search(r"\b(readme|documentation|docs?|documentation note|sentence|example)\b",text,re.I))
    explicit_nonchange=bool(re.search(
        r"\b(?:do not|don't|without|no)\b.{0,90}\b(?:change|modify|touch|edit|alter)\b.{0,120}\b(?:images?|dependencies|ci|pipeline|release|deployment|build|configuration|config)\b",
        text,re.I))
    documentation_only=doc_surface and explicit_nonchange

    # Tenant/object authorization is a relation, not a tenant keyword. Require an
    # organization/workspace/customer scope plus an access action and an explicit
    # cross-scope denial/ownership boundary.
    tenant_scope=has(r"\b(?:organi[sz]ation|workspace|customer account|client account|tenant)\b")
    access_action=has(r"\b(?:read|view|download|export|access|write|edit|delete|return|retrieve)\w*\b")
    cross_scope=has(r"\b(?:other|another|different|any other|cross[- ]?)\b.{0,55}\b(?:organi[sz]ation|workspace|customer|client|tenant)\b") or has(r"\b(?:prevent|deny|block)\b.{0,90}\b(?:other|another|different|cross[- ]?)\b")
    if tenant_scope and access_action and cross_scope:
        add("TENANT_ACCESS_BOUNDARY","MULTI_TENANT","R3","task explicitly constrains object/data access across organization or tenant boundaries")
        add("OBJECT_AUTHORIZATION","AUTHORIZATION","R3","cross-scope denial is an authorization invariant, not only a tenancy label")

    # Large online transformations are material migrations even without the word
    # migration/backfill. Scale + stored-row mutation + live-operation pressure
    # are all required, which keeps local fixture generation out.
    data_objects=has(r"\b(?:rows?|records?|stored data|database entries|existing data)\b")
    transformation=has(r"\b(?:transform|populate|rewrite|recompute|convert|update|change)\w*\b")
    large_scale=has(r"\b(?:\d+(?:\.\d+)?\s*(?:million|billion)|millions? of|billions? of|very large|large[- ]scale|tens of millions?)\b")
    live_pressure=has(r"\b(?:live traffic|normal writes|writes continue|online|without downtime|locking|database load|bound .*load|rollout risk|production traffic)\b")
    if data_objects and transformation and large_scale and live_pressure:
        add("LARGE_ONLINE_DATA_TRANSFORMATION","DATABASE_MIGRATION","R3","large mutation of existing stored rows under live traffic has migration semantics")
        add("LIVE_DATA_CAPACITY_PRESSURE","PERFORMANCE_CAPACITY_COST","R3","online transformation explicitly creates load/locking/capacity risk")

    # Production image build semantics can be expressed without the word Docker.
    # Require image/artifact semantics plus build/publish/promotion semantics and
    # production/release materiality; documentation-only requests are excluded.
    image_semantics=has(r"\b(?:production image|container image|runtime image|oci image|image build|resulting image|release artifact)\b")
    build_semantics=has(r"\b(?:build|publish|promote|package|packag(?:e|ing)|install)\w*\b")
    production_semantics=has(r"\b(?:production|release|promot(?:e|ed|ion)|reproducible)\b")
    if image_semantics and build_semantics and production_semantics and not documentation_only:
        add("PRODUCTION_IMAGE_BUILD","CONTAINER_ENGINEERING","R2","task materially changes a production/release image build")

    # SSRF-like trust boundary: a lower-privilege caller controls where a more
    # privileged backend network client connects. No URL keyword is required.
    backend_actor=has(r"\b(?:backend|server|server-side|service|http client)\b")
    caller_control=has(r"\b(?:caller|user|client)\b.{0,80}\b(?:suppl(?:y|ies|ied)|provide|provided|choose|chooses|selected?|control(?:s|led)?)\b") or has(r"\b(?:user-provided|caller-provided|caller-selected|user-selected)\b")
    remote_destination=has(r"\b(?:url|uri|remote resource|remote location|destination|target address|network location|external location)\b")
    server_fetch=has(r"\b(?:fetch|retrieve|download|request|connect|open|load)\w*\b")
    if backend_actor and caller_control and remote_destination and server_fetch:
        add("SERVER_SIDE_DESTINATION_TRUST","WEBHOOK_TRUST","R3","caller controls a destination reached by a privileged server-side network client")

    # Regulated/high-impact clinical decisions: require both domain semantics and
    # an outcome-affecting recommendation/decision verb. Mere health content or
    # arithmetic remains outside this rule.
    clinical_domain=has(r"\b(?:patient|clinical|medication|medicine|treatment|therapy|diagnos(?:is|e)|symptoms?|clinical measurements?|dose|dosing)\b")
    decision_semantics=has(r"\b(?:decide|decides|determine|determines|recommend|recommends|should receive|prescribe|prescribes|dose|dosing|triage)\b")
    if clinical_domain and decision_semantics:
        add("REGULATED_OUTCOME_DECISION","REGULATED_DOMAIN","R3","software is asked to make or recommend a patient/clinical outcome decision")
        human_decisions.add("REGULATED_DOMAIN")

    return {
      "concepts":sorted(concepts),
      "primary_packs":sorted(primary_packs),
      "human_decisions":sorted(human_decisions),
      "risk_floor":risk_floor,
      "documentation_only":documentation_only,
      "evidence":evidence,
      "normalized_request":text,
      "normalized_original_request":original,
    }
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
        "# ---------- request → engineering task plan ----------\ndef _request_change(profile,request):",
        HELPERS + "\n# ---------- request → engineering task plan ----------\ndef _request_change(profile,request):",
        "helper insertion",
    )
    source = replace_once(
        source,
        "    request,rc2_suppressed,rc2_observation=_rc2_positive_request_text(request)\n    t=request.lower();",
        "    request,rc2_suppressed,rc2_observation=_rc2_positive_request_text(request)\n    b1_observation=_b1_semantic_materiality(original_request,request)\n    t=request.lower();",
        "B1 observation",
    )
    source = replace_once(
        source,
        '    if hit(r"\\b(docker|container|compose)\\b"): add("DOCKERFILE_CHANGED","containerization change requested",["DOCKER"])',
        '    if hit(r"\\b(docker|container|compose)\\b") and not b1_observation.get("documentation_only"): add("DOCKERFILE_CHANGED","containerization change requested",["DOCKER"])',
        "documentation materiality guard",
    )
    source = replace_once(
        source,
        '    if rc2_suppressed:\n        evidence.append({"trigger":"RC2_POLARITY_FILTER","reason":"bounded request non-goal excluded from request-derived routing","source":"rc2_canonical","suppressed_clauses":rc2_suppressed,"polarity_observation":rc2_observation})\n    risk="R0" if triggers=={"UI_STYLE_CHANGED"} else "R1"',
        '    if rc2_suppressed:\n        evidence.append({"trigger":"RC2_POLARITY_FILTER","reason":"bounded request non-goal excluded from request-derived routing","source":"rc2_canonical","suppressed_clauses":rc2_suppressed,"polarity_observation":rc2_observation})\n\n    # B1 primary semantic observations are applied before policy assessment.\n    b1_concepts=set(b1_observation.get("concepts",[]))\n    if "TENANT_ACCESS_BOUNDARY" in b1_concepts:\n        triggers.add("TENANT_BOUNDARY_CHANGED"); contexts.add("MULTI_TENANT"); task_contexts.add("MULTI_TENANT")\n    if "OBJECT_AUTHORIZATION" in b1_concepts: triggers.add("AUTHZ_CHANGED")\n    if "LARGE_ONLINE_DATA_TRANSFORMATION" in b1_concepts:\n        triggers.add("DATABASE_SCHEMA_CHANGED"); contexts.add("DATABASE"); task_contexts.add("DATABASE")\n    if "LIVE_DATA_CAPACITY_PRESSURE" in b1_concepts: triggers.add("PERFORMANCE_SENSITIVE_PATH_CHANGED")\n    if "PRODUCTION_IMAGE_BUILD" in b1_concepts:\n        triggers.add("DOCKERFILE_CHANGED"); contexts.add("DOCKER"); task_contexts.add("DOCKER")\n    if "SERVER_SIDE_DESTINATION_TRUST" in b1_concepts:\n        contexts.add("PUBLIC_API"); task_contexts.add("PUBLIC_API")\n    if "REGULATED_OUTCOME_DECISION" in b1_concepts:\n        contexts.add("REGULATED_DOMAIN"); task_contexts.add("REGULATED_DOMAIN")\n    evidence.extend(b1_observation.get("evidence",[]))\n    risk="R0" if triggers=={"UI_STYLE_CHANGED"} else "R1"\n    b1_floor=str(b1_observation.get("risk_floor") or "R0")\n    if RISK_ORDER.get(b1_floor,0)>RISK_ORDER.get(risk,0): risk=b1_floor',
        "B1 primary trigger application",
    )
    source = replace_once(
        source,
        '    return {"summary":original_request,"risk":risk,"action_class":"A1","contexts":sorted(contexts),"execution_contexts":sorted(task_contexts),"triggers":sorted(triggers),"profiles":sorted(profiles),"environment":"LOCAL","request_detection":evidence}',
        '    return {"summary":original_request,"risk":risk,"action_class":"A1","contexts":sorted(contexts),"execution_contexts":sorted(task_contexts),"triggers":sorted(triggers),"profiles":sorted(profiles),"environment":"LOCAL","request_detection":evidence,"b1_primary_packs":b1_observation.get("primary_packs",[]),"b1_human_decisions":b1_observation.get("human_decisions",[]),"b1_semantic_materiality":b1_observation}',
        "B1 change metadata",
    )
    source = replace_once(
        source,
        '        if "EXTERNAL_SUPPLIER" in _rc1_detected_ids(rc2_positive_request):\n            selected=set(result.get("required_context_packs",[])); selected.add("EXTERNAL_SUPPLIER")\n            result["required_context_packs"]=sorted(selected)\n        result["request_detection"]=change["request_detection"]',
        '        if "EXTERNAL_SUPPLIER" in _rc1_detected_ids(rc2_positive_request):\n            selected=set(result.get("required_context_packs",[])); selected.add("EXTERNAL_SUPPLIER")\n            result["required_context_packs"]=sorted(selected)\n\n        # B1 may add only directly recognized primary packs; transitive composition\n        # remains B2. A risk floor is allowed only for the explicit material concepts\n        # above and cannot downgrade policy output.\n        selected=set(result.get("required_context_packs",[])); selected.update(change.get("b1_primary_packs",[]))\n        result["required_context_packs"]=sorted(selected)\n        floor=str(change.get("risk") or "R0")\n        if RISK_ORDER.get(floor,0)>RISK_ORDER.get(str(result.get("risk") or "R0"),0): result["risk"]=floor\n        result["request_human_decisions"]=sorted(set(change.get("b1_human_decisions",[])))\n        result["b1_semantic_materiality"]=change.get("b1_semantic_materiality",{})\n        result["request_detection"]=change["request_detection"]',
        "B1 assessment primary packs",
    )
    source = replace_once(
        source,
        '        + [ctx for ctx in baseline.get("discovery",{}).get("context_confirmations_needed",[]) if ctx in MATERIAL_CONFIRMATIONS]\n    ))',
        '        + [ctx for ctx in baseline.get("discovery",{}).get("context_confirmations_needed",[]) if ctx in MATERIAL_CONFIRMATIONS]\n        + [ctx for ctx in assessment.get("request_human_decisions",[]) if ctx in MATERIAL_CONFIRMATIONS]\n    ))',
        "B1 task human decisions",
    )
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
