#!/usr/bin/env python3
from pathlib import Path
import hashlib,re

p=Path('sef.py')
s=p.read_text(encoding='utf-8')

# --- clean accidental duplicate RC-5 helper / invocation ---
helper_pat=re.compile(r'(def _rc5_observable_requirement_dod\(request\):\n(?:    .*\n|\n)+?    return out\n)\n(?=def _rc5_observable_requirement_dod\(request\):)',re.M)
m=helper_pat.search(s)
if m:
    s=s[:m.start()]+s[m.end():]
s=s.replace('    dod += _rc5_observable_requirement_dod(request)\n    dod += _rc5_observable_requirement_dod(request)\n','    dod += _rc5_observable_requirement_dod(request)\n')

# --- clean accidental duplicate RC-6 helper pair ---
start='def _rc6_nearest_ancestor_evidence(repo,index,base_ref,current_revision):\n'
first=s.find(start)
if first!=-1:
    second=s.find(start,first+len(start))
    if second!=-1:
        end=s.find('def record_verification_evidence(',second)
        if end==-1: raise SystemExit('cannot bound duplicate RC-6 helper block')
        s=s[:second]+s[end:]

assign='''    comparison=_rc6_baseline_comparison(repo,statefile.get("verification_evidence_index",{}),base,revision,aggregate)\n    result["baseline_comparison"]={"comparison_base_revision":comparison.get("comparison_base_revision"),"baseline_revision":comparison.get("baseline_revision")}\n    result["preexisting_failures"]=comparison.get("preexisting_failures",[])\n    result["candidate_regressions"]=comparison.get("candidate_regressions",[])\n    result["resolved_baseline_failures"]=comparison.get("resolved_baseline_failures",[])\n    result["residual_limitations"]=comparison.get("residual_limitations",[])\n'''
s=s.replace(assign+assign,assign)

# --- RC-7: waiver overlay is deliberately separate from raw evidence ---
if 'def waive_verification_evidence(' not in s:
    agg_anchor='''def _rc6_nearest_ancestor_evidence(repo,index,base_ref,current_revision):\n'''
    waiver_helpers='''def _rc7_active_waiver(waivers,revision,check_id):\n    if not isinstance(waivers,dict) or not revision: return None\n    bucket=waivers.get(revision)\n    if not isinstance(bucket,dict): return None\n    item=bucket.get(check_id)\n    if not isinstance(item,dict) or item.get("state")!="WAIVED": return None\n    return item\n\ndef _rc7_overlay_waivers(aggregate,waivers):\n    revision=aggregate.get("revision")\n    checks=[]\n    for check in aggregate.get("checks",[]):\n        c=dict(check)\n        waiver=_rc7_active_waiver(waivers,revision,str(c.get("check_id") or ""))\n        if waiver and not bool(c.get("required",True)):\n            c["observed_state"]=c.get("state")\n            c["state"]="WAIVED"\n            c["waiver"]={k:waiver.get(k) for k in ("state","revision","check_id","reason","authorized_by","recorded_at","authorization_provenance")}\n        checks.append(c)\n    out=dict(aggregate); out["checks"]=checks\n    # Overall remains based only on required raw evidence, exactly as RC-4.\n    out["waivers"]=[c["waiver"] for c in checks if c.get("state")=="WAIVED" and isinstance(c.get("waiver"),dict)]\n    return out\n\ndef waive_verification_evidence(repo,check_id,reason="",authorized_by=""):\n    repo=Path(repo).resolve(); revision=_git_head(repo)\n    if revision is None: return {"status":"BLOCKED","reason":"NO_GIT_REVISION"}\n    check_id=str(check_id or '').strip(); reason=str(reason or '').strip(); authorized_by=str(authorized_by or '').strip()\n    if not check_id: return {"status":"BLOCKED","reason":"CHECK_ID_REQUIRED"}\n    if not reason: return {"status":"BLOCKED","reason":"WAIVER_REASON_REQUIRED"}\n    if not authorized_by: return {"status":"BLOCKED","reason":"WAIVER_AUTHORIZATION_REQUIRED"}\n    sp=_state_path(repo); statefile=_load_json(sp,{})\n    index=statefile.get("verification_evidence_index")\n    bucket=index.get(revision) if isinstance(index,dict) else None\n    summary=bucket.get(check_id) if isinstance(bucket,dict) else None\n    if not isinstance(summary,dict): return {"status":"BLOCKED","reason":"UNKNOWN_CHECK","revision":revision,"check_id":check_id}\n    if bool(summary.get("required",True)):\n        return {"status":"BLOCKED","reason":"REQUIRED_CHECK_CANNOT_BE_WAIVED","revision":revision,"check_id":check_id}\n    now=_now()\n    waiver={"state":"WAIVED","revision":revision,"check_id":check_id,"reason":reason,"authorized_by":authorized_by,"recorded_at":now,"authorization_provenance":"operator_asserted"}\n    waivers=statefile.setdefault("verification_waivers",{})\n    if not isinstance(waivers,dict): waivers={}; statefile["verification_waivers"]=waivers\n    waivers.setdefault(revision,{})[check_id]=waiver\n    raw=_rc4_aggregate_index(index,revision)\n    aggregate=_rc7_overlay_waivers(raw,waivers)\n    statefile["verification_evidence_state"]={"at":now,**aggregate}; statefile["updated_at"]=now; _write_json(sp,statefile)\n    return {"status":"PASS","waiver":waiver,"aggregate":aggregate,"note":"WAIVED is explicit residual-risk authorization and is never normalized to PASS."}\n\n'''
    if agg_anchor not in s: raise SystemExit('RC-7 aggregate insertion anchor not found')
    s=s.replace(agg_anchor,waiver_helpers+agg_anchor,1)

    # Expose waiver overlay on direct record results.
    old='''    aggregate=_rc4_aggregate_index(statefile.get("verification_evidence_index",{}),revision)\n    statefile["verification_evidence_state"]={"at":now,**aggregate}; statefile["updated_at"]=now; _write_json(sp,statefile)\n    return {"status":"PASS","recorded":obs,"aggregate":aggregate}\n'''
    new='''    raw_aggregate=_rc4_aggregate_index(statefile.get("verification_evidence_index",{}),revision)\n    aggregate=_rc7_overlay_waivers(raw_aggregate,statefile.get("verification_waivers",{}))\n    statefile["verification_evidence_state"]={"at":now,**aggregate}; statefile["updated_at"]=now; _write_json(sp,statefile)\n    return {"status":"PASS","recorded":obs,"aggregate":aggregate}\n'''
    if old not in s: raise SystemExit('RC-7 record-evidence anchor not found')
    s=s.replace(old,new,1)

    # Show active waiver state in verify output, while RC-6 compares raw states.
    old='''    aggregate=_rc4_aggregate_index(statefile.get("verification_evidence_index",{}),revision)\n    result["evidence_state"]=aggregate["state"]; result["evidence_revision"]=revision\n    comparison=_rc6_baseline_comparison(repo,statefile.get("verification_evidence_index",{}),base,revision,aggregate)\n'''
    new='''    raw_aggregate=_rc4_aggregate_index(statefile.get("verification_evidence_index",{}),revision)\n    aggregate=_rc7_overlay_waivers(raw_aggregate,statefile.get("verification_waivers",{}))\n    result["evidence_state"]=aggregate["state"]; result["evidence_revision"]=revision; result["evidence_checks"]=aggregate.get("checks",[]); result["waivers"]=aggregate.get("waivers",[])\n    comparison=_rc6_baseline_comparison(repo,statefile.get("verification_evidence_index",{}),base,revision,raw_aggregate)\n'''
    if old not in s: raise SystemExit('RC-7 verify aggregate anchor not found')
    s=s.replace(old,new,1)

    # Release sees exact-revision waivers but required-state readiness stays raw/conservative.
    old='''        evidence=_rc4_aggregate_index(index,head)\n        if evidence.get("state")!="PASS": blockers.append("Current revision required evidence is not passing: "+str(evidence.get("state")))\n'''
    new='''        raw_evidence=_rc4_aggregate_index(index,head)\n        evidence=_rc7_overlay_waivers(raw_evidence,state.get("verification_waivers",{}))\n        if raw_evidence.get("state")!="PASS": blockers.append("Current revision required evidence is not passing: "+str(raw_evidence.get("state")))\n'''
    if old not in s: raise SystemExit('RC-7 release anchor not found')
    s=s.replace(old,new,1)

    # CLI surface.
    old='''    x=sub.add_parser("record-evidence"); x.add_argument("repo",nargs="?",default="."); x.add_argument("check_id"); x.add_argument("state",choices=["PASS","FAIL","UNAVAILABLE","INCONCLUSIVE"]); x.add_argument("--optional",action="store_true"); x.add_argument("--detail",default=""); x.add_argument("--source",default="adapter")\n    x=sub.add_parser("release"); x.add_argument("repo",nargs="?",default=".")\n'''
    new='''    x=sub.add_parser("record-evidence"); x.add_argument("repo",nargs="?",default="."); x.add_argument("check_id"); x.add_argument("state",choices=["PASS","FAIL","UNAVAILABLE","INCONCLUSIVE"]); x.add_argument("--optional",action="store_true"); x.add_argument("--detail",default=""); x.add_argument("--source",default="adapter")\n    x=sub.add_parser("waive-evidence"); x.add_argument("repo",nargs="?",default="."); x.add_argument("check_id"); x.add_argument("--reason",default=""); x.add_argument("--authorized-by",default="")\n    x=sub.add_parser("release"); x.add_argument("repo",nargs="?",default=".")\n'''
    if old not in s: raise SystemExit('RC-7 CLI parser anchor not found')
    s=s.replace(old,new,1)
    old='''    elif args.cmd=="record-evidence": r=record_verification_evidence(args.repo,args.check_id,args.state,not args.optional,args.detail,args.source)\n    elif args.cmd=="release": r=release(args.repo)\n'''
    new='''    elif args.cmd=="record-evidence": r=record_verification_evidence(args.repo,args.check_id,args.state,not args.optional,args.detail,args.source)\n    elif args.cmd=="waive-evidence": r=waive_verification_evidence(args.repo,args.check_id,args.reason,args.authorized_by)\n    elif args.cmd=="release": r=release(args.repo)\n'''
    if old not in s: raise SystemExit('RC-7 CLI dispatch anchor not found')
    s=s.replace(old,new,1)

p.write_text(s,encoding='utf-8')
h=hashlib.sha256(p.read_bytes()).hexdigest()
Path('SHA256SUMS').write_text(f'{h}  sef.py\n',encoding='utf-8')
print(h)
