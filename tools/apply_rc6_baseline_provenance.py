#!/usr/bin/env python3
from pathlib import Path
import hashlib

p=Path('sef.py')
s=p.read_text(encoding='utf-8')

anchor='''def record_verification_evidence(repo,check_id,state,required=True,detail="",source="adapter"):\n'''
if anchor not in s:
    raise SystemExit('RC-6 helper anchor not found')

helper='''def _rc6_nearest_ancestor_evidence(repo,index,base_ref,current_revision):\n    """Return nearest revision-bound evidence on base_ref or its Git ancestors."""\n    if not isinstance(index,dict) or not index:\n        return None,None\n    try:\n        cp=_run(["git","rev-parse",str(base_ref)],repo,timeout=30)\n        if cp.returncode!=0 or not cp.stdout.strip(): return None,None\n        base_revision=cp.stdout.strip().splitlines()[0]\n        cp=_run(["git","rev-list",base_revision],repo,timeout=30)\n        if cp.returncode!=0: return base_revision,None\n        for rev in [x.strip() for x in cp.stdout.splitlines() if x.strip()]:\n            if rev==current_revision: continue\n            bucket=index.get(rev)\n            if isinstance(bucket,dict) and bucket:\n                return base_revision,rev\n        return base_revision,None\n    except Exception:\n        return None,None\n\ndef _rc6_baseline_comparison(repo,index,base_ref,current_revision,current_aggregate):\n    base_revision,baseline_revision=_rc6_nearest_ancestor_evidence(repo,index,base_ref,current_revision)\n    current={str(c.get("check_id")):str(c.get("state") or "NOT_RUN") for c in current_aggregate.get("checks",[]) if c.get("check_id")}\n    bad={"FAIL","FLAKY","UNAVAILABLE","INCONCLUSIVE"}\n    if not baseline_revision:\n        limitation="No comparable revision-bound verification evidence exists on the requested base revision or its retained ancestors; candidate-vs-baseline classification is unavailable."\n        return {\n          "comparison_base_revision":base_revision,"baseline_revision":None,\n          "preexisting_failures":[],"candidate_regressions":sorted(k for k,v in current.items() if v in bad),\n          "resolved_baseline_failures":[],"residual_limitations":[limitation],\n        }\n    baseline=_rc4_aggregate_index(index,baseline_revision)\n    prior={str(c.get("check_id")):str(c.get("state") or "NOT_RUN") for c in baseline.get("checks",[]) if c.get("check_id")}\n    preexisting=sorted(k for k,v in current.items() if v in bad and prior.get(k) in bad)\n    introduced=sorted(k for k,v in current.items() if v in bad and prior.get(k) not in bad)\n    resolved=sorted(k for k,v in prior.items() if v in bad and current.get(k) not in bad)\n    limitations=[]\n    if preexisting:\n        limitations.append("A matching required check was already non-passing on ancestor baseline evidence; matching check identity establishes pre-existing failure evidence but does not prove the failure cause is identical or that the candidate did not worsen it.")\n    return {\n      "comparison_base_revision":base_revision,"baseline_revision":baseline_revision,\n      "preexisting_failures":preexisting,"candidate_regressions":introduced,\n      "resolved_baseline_failures":resolved,"residual_limitations":limitations,\n    }\n\n'''
s=s.replace(anchor,helper+anchor,1)

needle='''    aggregate=_rc4_aggregate_index(statefile.get("verification_evidence_index",{}),revision)\n    result["evidence_state"]=aggregate["state"]; result["evidence_revision"]=revision\n'''
replacement='''    aggregate=_rc4_aggregate_index(statefile.get("verification_evidence_index",{}),revision)\n    result["evidence_state"]=aggregate["state"]; result["evidence_revision"]=revision\n    comparison=_rc6_baseline_comparison(repo,statefile.get("verification_evidence_index",{}),base,revision,aggregate)\n    result["baseline_comparison"]={"comparison_base_revision":comparison.get("comparison_base_revision"),"baseline_revision":comparison.get("baseline_revision")}\n    result["preexisting_failures"]=comparison.get("preexisting_failures",[])\n    result["candidate_regressions"]=comparison.get("candidate_regressions",[])\n    result["resolved_baseline_failures"]=comparison.get("resolved_baseline_failures",[])\n    result["residual_limitations"]=comparison.get("residual_limitations",[])\n'''
if needle not in s:
    raise SystemExit('RC-6 verify anchor not found')
s=s.replace(needle,replacement,1)

p.write_text(s,encoding='utf-8')
h=hashlib.sha256(p.read_bytes()).hexdigest()
Path('SHA256SUMS').write_text(f'{h}  sef.py\n',encoding='utf-8')
print(h)
