#!/usr/bin/env python3
"""B1 candidate patcher with uniquely-scoped task-plan anchor."""
from __future__ import annotations

import argparse
from pathlib import Path

import apply_b1_semantic_materiality as v1


def r(source: str, old: str, new: str, label: str) -> str:
    return v1.replace_once(source, old, new, label)


def build(source: str) -> str:
    source = r(source,
        "# ---------- request → engineering task plan ----------\ndef _request_change(profile,request):",
        v1.HELPERS + "\n# ---------- request → engineering task plan ----------\ndef _request_change(profile,request):",
        "helper insertion")
    source = r(source,
        "    request,rc2_suppressed,rc2_observation=_rc2_positive_request_text(request)\n    t=request.lower();",
        "    request,rc2_suppressed,rc2_observation=_rc2_positive_request_text(request)\n    b1_observation=_b1_semantic_materiality(original_request,request)\n    t=request.lower();",
        "B1 observation")
    source = r(source,
        '    if hit(r"\\b(docker|container|compose)\\b"): add("DOCKERFILE_CHANGED","containerization change requested",["DOCKER"])',
        '    if hit(r"\\b(docker|container|compose)\\b") and not b1_observation.get("documentation_only"): add("DOCKERFILE_CHANGED","containerization change requested",["DOCKER"])',
        "documentation materiality guard")
    source = r(source,
        '    if rc2_suppressed:\n        evidence.append({"trigger":"RC2_POLARITY_FILTER","reason":"bounded request non-goal excluded from request-derived routing","source":"rc2_canonical","suppressed_clauses":rc2_suppressed,"polarity_observation":rc2_observation})\n    risk="R0" if triggers=={"UI_STYLE_CHANGED"} else "R1"',
        '    if rc2_suppressed:\n        evidence.append({"trigger":"RC2_POLARITY_FILTER","reason":"bounded request non-goal excluded from request-derived routing","source":"rc2_canonical","suppressed_clauses":rc2_suppressed,"polarity_observation":rc2_observation})\n\n    # B1 primary semantic observations are applied before policy assessment.\n    b1_concepts=set(b1_observation.get("concepts",[]))\n    if "TENANT_ACCESS_BOUNDARY" in b1_concepts:\n        triggers.add("TENANT_BOUNDARY_CHANGED"); contexts.add("MULTI_TENANT"); task_contexts.add("MULTI_TENANT")\n    if "OBJECT_AUTHORIZATION" in b1_concepts: triggers.add("AUTHZ_CHANGED")\n    if "LARGE_ONLINE_DATA_TRANSFORMATION" in b1_concepts:\n        triggers.add("DATABASE_SCHEMA_CHANGED"); contexts.add("DATABASE"); task_contexts.add("DATABASE")\n    if "LIVE_DATA_CAPACITY_PRESSURE" in b1_concepts: triggers.add("PERFORMANCE_SENSITIVE_PATH_CHANGED")\n    if "PRODUCTION_IMAGE_BUILD" in b1_concepts:\n        triggers.add("DOCKERFILE_CHANGED"); contexts.add("DOCKER"); task_contexts.add("DOCKER")\n    if "SERVER_SIDE_DESTINATION_TRUST" in b1_concepts:\n        contexts.add("PUBLIC_API"); task_contexts.add("PUBLIC_API")\n    if "REGULATED_OUTCOME_DECISION" in b1_concepts:\n        contexts.add("REGULATED_DOMAIN"); task_contexts.add("REGULATED_DOMAIN")\n    evidence.extend(b1_observation.get("evidence",[]))\n    risk="R0" if triggers=={"UI_STYLE_CHANGED"} else "R1"\n    b1_floor=str(b1_observation.get("risk_floor") or "R0")\n    if RISK_ORDER.get(b1_floor,0)>RISK_ORDER.get(risk,0): risk=b1_floor',
        "B1 primary trigger application")
    source = r(source,
        '    return {"summary":original_request,"risk":risk,"action_class":"A1","contexts":sorted(contexts),"execution_contexts":sorted(task_contexts),"triggers":sorted(triggers),"profiles":sorted(profiles),"environment":"LOCAL","request_detection":evidence}',
        '    return {"summary":original_request,"risk":risk,"action_class":"A1","contexts":sorted(contexts),"execution_contexts":sorted(task_contexts),"triggers":sorted(triggers),"profiles":sorted(profiles),"environment":"LOCAL","request_detection":evidence,"b1_primary_packs":b1_observation.get("primary_packs",[]),"b1_human_decisions":b1_observation.get("human_decisions",[]),"b1_semantic_materiality":b1_observation}',
        "B1 change metadata")
    source = r(source,
        '        if "EXTERNAL_SUPPLIER" in _rc1_detected_ids(rc2_positive_request):\n            selected=set(result.get("required_context_packs",[])); selected.add("EXTERNAL_SUPPLIER")\n            result["required_context_packs"]=sorted(selected)\n        result["request_detection"]=change["request_detection"]',
        '        if "EXTERNAL_SUPPLIER" in _rc1_detected_ids(rc2_positive_request):\n            selected=set(result.get("required_context_packs",[])); selected.add("EXTERNAL_SUPPLIER")\n            result["required_context_packs"]=sorted(selected)\n\n        # B1 adds directly recognized primary packs only; transitive closure is B2.\n        selected=set(result.get("required_context_packs",[])); selected.update(change.get("b1_primary_packs",[]))\n        result["required_context_packs"]=sorted(selected)\n        floor=str(change.get("risk") or "R0")\n        if RISK_ORDER.get(floor,0)>RISK_ORDER.get(str(result.get("risk") or "R0"),0): result["risk"]=floor\n        result["request_human_decisions"]=sorted(set(change.get("b1_human_decisions",[])))\n        result["b1_semantic_materiality"]=change.get("b1_semantic_materiality",{})\n        result["request_detection"]=change["request_detection"]',
        "B1 assessment primary packs")
    source = r(source,
        '    project_profile=_load_json(repo/".sef/project-profile.json",{})\n    human_decisions=sorted(set(\n        [c.get("context") for c in project_profile.get("context_candidates",[]) if c.get("context") in MATERIAL_CONFIRMATIONS]\n        + [ctx for ctx in baseline.get("discovery",{}).get("context_confirmations_needed",[]) if ctx in MATERIAL_CONFIRMATIONS]\n    ))',
        '    project_profile=_load_json(repo/".sef/project-profile.json",{})\n    human_decisions=sorted(set(\n        [c.get("context") for c in project_profile.get("context_candidates",[]) if c.get("context") in MATERIAL_CONFIRMATIONS]\n        + [ctx for ctx in baseline.get("discovery",{}).get("context_confirmations_needed",[]) if ctx in MATERIAL_CONFIRMATIONS]\n        + [ctx for ctx in assessment.get("request_human_decisions",[]) if ctx in MATERIAL_CONFIRMATIONS]\n    ))',
        "B1 task human decisions")
    return source


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--output",required=True); p.add_argument("--allow-input-sha",default=v1.EXPECTED_INPUT_SHA256); a=p.parse_args()
    inp=Path(a.input); raw=inp.read_bytes(); actual=v1.sha256(raw)
    if actual!=a.allow_input_sha: raise SystemExit(f"unexpected input SHA-256: {actual}; expected {a.allow_input_sha}")
    candidate=build(raw.decode("utf-8")); Path(a.output).write_text(candidate,encoding="utf-8")
    print(f"input_sha256={actual}"); print(f"candidate_sha256={v1.sha256(candidate.encode('utf-8'))}")
    return 0

if __name__=="__main__": raise SystemExit(main())
