#!/usr/bin/env python3
"""Supplemental deterministic graders for golden-catalog DEV closure.

This runner stays black-box with respect to SEF: it invokes only the public CLI.
It grades semantic planning invariants across all observable obligation surfaces,
not one implementation-specific field.
"""
from __future__ import annotations
import argparse, json, shutil, sys, tempfile
from pathlib import Path
from typing import Any
import run as core


def _text(value: Any) -> str:
    if isinstance(value, str): return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _contains_group(haystack: str, group: list[str]) -> bool:
    h=haystack.lower()
    return any(str(term).lower() in h for term in group)


def evaluate_plan(sef_path: Path, scenario_path: Path, fixtures_root: Path) -> dict[str, Any]:
    scenario=core.load_json(scenario_path)
    errors=core.validate_scenario(scenario,scenario_path)
    if errors:
        return {"schema":"sef.eval.dev-closure.v1","scenario_id":scenario.get("id"),"status":"HARNESS_ERROR","limitations":errors,"assertions":[]}
    fixture=fixtures_root/scenario["fixture"]
    if not fixture.is_dir():
        return {"schema":"sef.eval.dev-closure.v1","scenario_id":scenario["id"],"status":"HARNESS_ERROR","limitations":[f"fixture not found: {fixture}"],"assertions":[]}
    critical=scenario.get("severity")=="critical"
    with tempfile.TemporaryDirectory(prefix=f"sef-dev-close-{scenario['id'].lower()}-") as tmp:
        repo=Path(tmp)/"repo"; shutil.copytree(fixture,repo)
        try:
            init=core.run_json([sys.executable,str(sef_path),"init",str(repo),"--brief",str(scenario.get("project_brief") or "Evaluation fixture project.")])
            if init.get("status")!="PASS": raise RuntimeError("SEF init failed")
            installed=repo/".sef"/"sef.py"
            payload=core.run_json([sys.executable,str(installed),"plan",str(repo),"--request",str(scenario["request"]),"--save"])
            assertions,observed=core.grade_plan(scenario,payload)
            plan=payload.get("plan") if isinstance(payload.get("plan"),dict) else {}
            observed["human_decisions_needed"]=plan.get("human_decisions_needed",[])
            observed["implicit_professional_requirements"]=plan.get("implicit_professional_requirements",[])
            observed["verification_strategy"]=plan.get("verification_strategy",[])
            observed["architecture_questions"]=plan.get("architecture_questions",[])
            custom=scenario.get("dev_closure_expect") or {}
            decisions_text=_text(observed["human_decisions_needed"]).lower()
            for term in custom.get("forbidden_human_decision_terms",[]):
                assertions.append(core.assertion(f"forbidden-human-decision-term:{term}",str(term).lower() not in decisions_text,False,str(term).lower() in decisions_text,critical))
            groups=custom.get("block_or_obligation_term_groups",[])
            if groups:
                obligation_surfaces={
                    "implicit_professional_requirements":plan.get("implicit_professional_requirements",[]),
                    "definition_of_done":plan.get("definition_of_done",[]),
                    "verification_strategy":plan.get("verification_strategy",[]),
                    "architecture_questions":plan.get("architecture_questions",[]),
                }
                obligation_text=_text(obligation_surfaces)
                blocked=observed.get("implementation_allowed") is False
                group_results=[_contains_group(obligation_text,list(g)) for g in groups]
                assertions.append(core.assertion("blocked-or-observable-obligation",blocked or all(group_results),{"blocked":True,"or_all_term_groups":groups},{"blocked":blocked,"group_matches":group_results,"obligation_surfaces":obligation_surfaces},critical))
            return {"schema":"sef.eval.dev-closure.v1","scenario_id":scenario["id"],"scenario_set":scenario["set"],"severity":scenario["severity"],"sef_source_sha256":core.sha256_file(sef_path),"status":core.scenario_status(assertions),"observed":observed,"assertions":assertions,"limitations":[]}
        except Exception as exc:
            return {"schema":"sef.eval.dev-closure.v1","scenario_id":scenario.get("id"),"scenario_set":scenario.get("set"),"severity":scenario.get("severity"),"sef_source_sha256":core.sha256_file(sef_path),"status":"HARNESS_ERROR","observed":{},"assertions":[],"limitations":[f"{type(exc).__name__}: {exc}"]}


def main() -> int:
    root=Path(__file__).resolve().parent
    p=argparse.ArgumentParser(); p.add_argument("--sef",default=str(root.parent/"sef.py")); p.add_argument("--scenarios",default=str(root/"scenarios/dev")); p.add_argument("--fixtures",default=str(root/"fixtures")); p.add_argument("--ids",required=True); p.add_argument("--output")
    a=p.parse_args(); ids=[x.strip() for x in a.ids.split(',') if x.strip()]
    sroot=Path(a.scenarios); byid={core.load_json(x).get('id'):x for x in sroot.glob('*.json')}
    missing=[x for x in ids if x not in byid]
    if missing:
        print(json.dumps({"status":"FAIL","reason":"MISSING_SCENARIOS","ids":missing},indent=2)); return 2
    results=[evaluate_plan(Path(a.sef).resolve(),byid[x],Path(a.fixtures).resolve()) for x in ids]
    report={"schema":"sef.eval.dev-closure-report.v1","sef_source_sha256":core.sha256_file(Path(a.sef).resolve()),"summary":core.summarize(results),"results":results}
    encoded=json.dumps(report,indent=2,sort_keys=True)
    if a.output: Path(a.output).write_text(encoded+'\n',encoding='utf-8')
    print(encoded)
    return 0 if report['summary']['status']=='PASS' else 1

if __name__=='__main__': raise SystemExit(main())
