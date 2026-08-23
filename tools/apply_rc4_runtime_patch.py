#!/usr/bin/env python3
from pathlib import Path

p=Path('sef.py')
text=p.read_text(encoding='utf-8')
start=text.index('# ---------- verification ----------')
end=text.index('# ---------- health ----------')
new_section=r'''# ---------- verification ----------
_RC4_EVIDENCE_LIMIT=256
_RC4_INDEX_REVISION_LIMIT=8
_RC4_RAW_STATES={"PASS","FAIL","UNAVAILABLE","INCONCLUSIVE","NOT_RUN"}


def _verification_commands(profile,risk,triggers):
    desired=["lint","typecheck","unit"]
    if "DOC_ONLY_CHANGED" not in triggers: desired.append("build")
    if RISK_ORDER.get(risk,1)>=2: desired += ["integration","e2e"]
    out=[]
    sets=profile.get("command_sets",[])
    if not sets and any(profile.get("commands",{}).values()): sets=[{"path":".","manager":"unknown","commands":profile.get("commands",{})}]
    for cs in sets:
        for k in desired:
            cmd=(cs.get("commands") or {}).get(k)
            if cmd: out.append({"workspace":cs.get("path","."),"kind":k,"command":cmd})
    seen=set(); res=[]
    for x in out:
        key=(x["workspace"],x["kind"],x["command"])
        if key not in seen: seen.add(key); res.append(x)
    return res


def _rc4_check_id(workspace,kind,command):
    raw=f"{workspace}|{kind}|{command}".encode('utf-8',errors='replace')
    return f"{kind}:{hashlib.sha256(raw).hexdigest()[:16]}"


def _rc4_normalize_evidence_state(returncode=None,adapter_state=None):
    explicit=str(adapter_state or '').upper().strip()
    if explicit:
        if explicit not in _RC4_RAW_STATES-{"NOT_RUN"}:
            raise ValueError(f"unsupported explicit evidence state: {explicit}")
        return explicit
    if returncode is None: return "NOT_RUN"
    return "PASS" if int(returncode)==0 else "FAIL"


def _rc4_prune_index(index,current_revision):
    if not isinstance(index,dict): return {}
    if len(index)<=_RC4_INDEX_REVISION_LIMIT: return index
    keys=list(index.keys())
    keep=[]
    if current_revision in index: keep.append(current_revision)
    for rev in reversed(keys):
        if rev not in keep: keep.append(rev)
        if len(keep)>=_RC4_INDEX_REVISION_LIMIT: break
    return {rev:index[rev] for rev in keys if rev in set(keep)}


def _rc4_append_evidence(statefile,observations,current_revision):
    ledger=statefile.setdefault("verification_evidence",[])
    if not isinstance(ledger,list): ledger=[]; statefile["verification_evidence"]=ledger
    index=statefile.setdefault("verification_evidence_index",{})
    if not isinstance(index,dict): index={}; statefile["verification_evidence_index"]=index
    for obs in observations:
        revision=str(obs.get("revision") or '')
        check_id=str(obs.get("check_id") or '')
        raw_state=str(obs.get("state") or '').upper()
        if not revision or not check_id or raw_state not in _RC4_RAW_STATES:
            continue
        entry={
          "revision":revision,"attempt_id":str(obs.get("attempt_id") or ''),"recorded_at":str(obs.get("recorded_at") or _now()),
          "check_id":check_id,"required":bool(obs.get("required",True)),"state":raw_state,
          "source":str(obs.get("source") or "runtime"),"command":obs.get("command"),"returncode":obs.get("returncode"),
          "detail":str(obs.get("detail") or '')[-2000:],
        }
        ledger.append(entry)
        bucket=index.setdefault(revision,{})
        summary=bucket.setdefault(check_id,{"required":entry["required"],"seen_states":[],"observation_count":0,"first_recorded_at":entry["recorded_at"],"last_recorded_at":entry["recorded_at"]})
        summary["required"]=bool(summary.get("required",False) or entry["required"])
        seen=set(str(x).upper() for x in summary.get("seen_states",[]) if str(x).upper() in _RC4_RAW_STATES)
        seen.add(raw_state)
        summary["seen_states"]=sorted(seen)
        summary["observation_count"]=int(summary.get("observation_count",0) or 0)+1
        summary["last_recorded_at"]=entry["recorded_at"]
    if len(ledger)>_RC4_EVIDENCE_LIMIT:
        statefile["verification_evidence"]=ledger[-_RC4_EVIDENCE_LIMIT:]
    statefile["verification_evidence_index"]=_rc4_prune_index(index,current_revision)
    return statefile


def _rc4_check_state(seen_states):
    seen=set(str(x).upper() for x in (seen_states or []))
    if any(x not in _RC4_RAW_STATES for x in seen): return "INCONCLUSIVE"
    if "PASS" in seen and "FAIL" in seen: return "FLAKY"
    if "INCONCLUSIVE" in seen: return "INCONCLUSIVE"
    if "UNAVAILABLE" in seen: return "UNAVAILABLE"
    if "FAIL" in seen: return "FAIL"
    if seen=={"PASS"}: return "PASS"
    return "NOT_RUN"


def _rc4_aggregate_index(index,revision):
    if not revision or not isinstance(index,dict): return {"revision":revision,"state":"NOT_RUN","checks":[]}
    bucket=index.get(revision)
    if not isinstance(bucket,dict) or not bucket: return {"revision":revision,"state":"NOT_RUN","checks":[]}
    checks=[]
    malformed=False
    for check_id,summary in sorted(bucket.items()):
        if not isinstance(summary,dict):
            malformed=True; checks.append({"check_id":check_id,"required":True,"state":"INCONCLUSIVE"}); continue
        required=bool(summary.get("required",True))
        state=_rc4_check_state(summary.get("seen_states",[]))
        checks.append({"check_id":check_id,"required":required,"state":state,"observation_count":summary.get("observation_count",0)})
    required_states=[c["state"] for c in checks if c["required"]]
    if malformed: overall="INCONCLUSIVE"
    elif not required_states: overall="NOT_RUN"
    elif "FLAKY" in required_states: overall="FLAKY"
    elif "INCONCLUSIVE" in required_states: overall="INCONCLUSIVE"
    elif "UNAVAILABLE" in required_states: overall="UNAVAILABLE"
    elif "FAIL" in required_states: overall="FAIL"
    elif "NOT_RUN" in required_states: overall="NOT_RUN"
    elif all(x=="PASS" for x in required_states): overall="PASS"
    else: overall="INCONCLUSIVE"
    return {"revision":revision,"state":overall,"checks":checks}


def record_verification_evidence(repo,check_id,state,required=True,detail="",source="adapter"):
    repo=Path(repo).resolve(); revision=_git_head(repo); raw_state=str(state or '').upper().strip()
    if revision is None: return {"status":"BLOCKED","reason":"NO_GIT_REVISION"}
    if raw_state not in {"PASS","FAIL","UNAVAILABLE","INCONCLUSIVE"}:
        return {"status":"BLOCKED","reason":"INVALID_EVIDENCE_STATE","allowed":["PASS","FAIL","UNAVAILABLE","INCONCLUSIVE"]}
    check_id=str(check_id or '').strip()
    if not check_id: return {"status":"BLOCKED","reason":"CHECK_ID_REQUIRED"}
    now=_now(); attempt=hashlib.sha256(f"{revision}|{check_id}|{now}|{os.getpid()}".encode()).hexdigest()[:20]
    sp=_state_path(repo); statefile=_load_json(sp,{})
    obs={"revision":revision,"attempt_id":attempt,"recorded_at":now,"check_id":check_id,"required":bool(required),"state":raw_state,"source":str(source or 'adapter'),"detail":detail}
    _rc4_append_evidence(statefile,[obs],revision)
    aggregate=_rc4_aggregate_index(statefile.get("verification_evidence_index",{}),revision)
    statefile["verification_evidence_state"]={"at":now,**aggregate}; statefile["updated_at"]=now; _write_json(sp,statefile)
    return {"status":"PASS","recorded":obs,"aggregate":aggregate}


def verify(repo,base="HEAD",run_commands=False,allow_risky_exec=False):
    repo=Path(repo).resolve(); a=assess(repo,base); profile=_load_json(repo/".sef/project-profile.json",{})
    triggers=set(a.get("triggers",[])); risk=a.get("risk","R1"); planned=_verification_commands(profile,risk,triggers)
    actual_web_contexts,actual_web_evidence=_actual_web_execution_contexts(repo,a)
    actual_execution_contexts=sorted(set(a.get("contexts",[]))|set(actual_web_contexts))
    required_execution_procedures=_execution_skills(actual_execution_contexts,triggers,risk,a.get("required_context_packs",[]))
    saved_task=(_load_json(_state_path(repo),{}) or {}).get("current_task") or {}
    saved_procedures=set(saved_task.get("procedures",[]))
    newly_required_web_procedures=sorted(p for p in required_execution_procedures if p in {"seo-web-discoverability-engineering","geo-ai-discoverability-engineering","analytics-conversion-instrumentation"} and p not in saved_procedures)
    risky=bool(triggers & {"PACKAGE_SCRIPT_EXECUTION","UNTRUSTED_PR_CODE"})
    revision=_git_head(repo); now=_now(); attempt_id=hashlib.sha256(f"{revision}|{now}|{os.getpid()}".encode()).hexdigest()[:20]
    observations=[]
    if run_commands and risky and not allow_risky_exec:
        result={"status":"BLOCKED","local_verification_state":"BLOCKED_RISKY_EXECUTION","reason":"Diff changes an execution/supply-chain boundary; refuse automatic local project command execution without --allow-risky-exec.","assessment":a,"planned_commands":planned}
    elif not run_commands:
        result={"status":"PASS","local_verification_state":"PLANNED","assessment":a,"planned_commands":planned,"note":"Use --run to execute detected project commands."}
    else:
        runs=[]
        for item in planned:
            cwd=repo/item["workspace"]
            check_id=_rc4_check_id(item["workspace"],item["kind"],item["command"])
            try:
                cp=_run(item["command"],cwd,timeout=300,shell=True)
                run={**item,"check_id":check_id,"returncode":cp.returncode,"stdout":cp.stdout[-4000:],"stderr":cp.stderr[-4000:]}
            except subprocess.TimeoutExpired:
                run={**item,"check_id":check_id,"returncode":124,"stderr":"timeout"}
            run["evidence_state"]=_rc4_normalize_evidence_state(run.get("returncode"))
            runs.append(run)
            observations.append({"revision":revision,"attempt_id":attempt_id,"recorded_at":now,"check_id":check_id,"required":True,"state":run["evidence_state"],"source":"command","command":item["command"],"returncode":run.get("returncode"),"detail":run.get("stderr","")[-2000:]})
        failures=[r for r in runs if r["returncode"]!=0]
        if failures: state="FAIL"
        elif not runs: state="INCOMPLETE_NO_PROJECT_COMMANDS"
        elif RISK_ORDER.get(risk,1)>=3 and a.get("specialist_control_count",0)>0: state="LOCAL_PASS_SPECIALIST_EVIDENCE_OUTSTANDING"
        else: state="LOCAL_PASS"
        result={"status":"FAIL" if failures else "PASS","local_verification_state":state,"assessment":a,"runs":runs,"specialist_evidence_outstanding":a.get("specialist_control_count",0) if RISK_ORDER.get(risk,1)>=3 else 0}
    result["actual_execution_contexts"]=actual_execution_contexts
    result["actual_web_detection"]=actual_web_evidence
    result["newly_required_web_procedures"]=newly_required_web_procedures
    if newly_required_web_procedures:
        result["agent_action"]="Load guidance for the actual diff and apply newly routed web/analytics procedures before claiming DONE; then verify again."
        if result.get("local_verification_state") in {"LOCAL_PASS","LOCAL_PASS_SPECIALIST_EVIDENCE_OUTSTANDING"}: result["local_verification_state"]="LOCAL_PASS_NEW_PROCEDURE_REVIEW_REQUIRED"
    sp=_state_path(repo); statefile=_load_json(sp,{})
    if observations and revision:
        _rc4_append_evidence(statefile,observations,revision)
    aggregate=_rc4_aggregate_index(statefile.get("verification_evidence_index",{}),revision)
    result["evidence_state"]=aggregate["state"]; result["evidence_revision"]=revision
    if run_commands and result.get("status")=="PASS" and aggregate["state"] in {"FLAKY","UNAVAILABLE","INCONCLUSIVE","FAIL"}:
        result["status"]="BLOCKED"; result["reason"]="REVISION_EVIDENCE_NOT_STABLE"
    statefile["last_verification"]={"at":now,"revision":revision,**{k:v for k,v in result.items() if k not in {"assessment","runs"}},"risk":risk,"triggers":sorted(triggers)}
    statefile["verification_evidence_state"]={"at":now,**aggregate}
    statefile["updated_at"]=now; _write_json(sp,statefile)
    return result

# ---------- release readiness ----------
def release(repo):
    repo=Path(repo).resolve(); blockers=[]; warnings=[]; head=_git_head(repo); dirty=_git_dirty(repo); profile=_load_json(repo/".sef/project-profile.json",{}); baseline=_load_json(repo/".sef/project-baseline.json",{}); state=_load_json(_state_path(repo),{})
    if head is None: blockers.append("No exact Git revision available.")
    if dirty: blockers.append("Working tree is dirty; release identity does not match a committed exact revision.")
    if not baseline.get("project",{}).get("brief"): blockers.append("Project brief/baseline discovery is incomplete.")
    unresolved=sorted(set(
        [c.get("context") for c in profile.get("context_candidates",[]) if c.get("context") in MATERIAL_CONFIRMATIONS]
        + [ctx for ctx in baseline.get("discovery",{}).get("context_confirmations_needed",[]) if ctx in MATERIAL_CONFIRMATIONS]
    ))
    if unresolved: blockers.append("Material project contexts remain unconfirmed: "+", ".join(sorted(set(unresolved))))
    lv=state.get("last_verification") or {}
    if not lv: blockers.append("No recorded verification exists for this project state.")
    elif lv.get("revision")!=head: blockers.append("Last verification is not tied to the current HEAD revision.")
    elif lv.get("local_verification_state") not in {"LOCAL_PASS","LOCAL_PASS_SPECIALIST_EVIDENCE_OUTSTANDING"}: blockers.append("Last local verification is not passing.")
    if lv.get("local_verification_state")=="LOCAL_PASS_SPECIALIST_EVIDENCE_OUTSTANDING": blockers.append("Specialist evidence is still outstanding; local command success is not sufficient for production VERIFIED.")
    index=state.get("verification_evidence_index")
    if not isinstance(index,dict) or not index:
        blockers.append("No revision-bound verification evidence index exists; run fresh verification on the current revision.")
        evidence={"revision":head,"state":"NOT_RUN","checks":[]}
    else:
        evidence=_rc4_aggregate_index(index,head)
        if evidence.get("state")!="PASS": blockers.append("Current revision required evidence is not passing: "+str(evidence.get("state")))
    readiness="BLOCKED" if blockers else "READY_FOR_RELEASE_REVIEW"
    result={"status":"PASS" if not blockers else "BLOCKED","release_readiness":readiness,"revision":head,"evidence":evidence,"blockers":blockers,"warnings":warnings,"note":"READY_FOR_RELEASE_REVIEW is not an automatic deployment. R3/R4/human gates remain policy-controlled."}
    state["last_release_check"]={"at":_now(),**result}; state["updated_at"]=_now(); _write_json(_state_path(repo),state)
    return result

'''
text=text[:start]+new_section+text[end:]
parser_anchor='    x=sub.add_parser("verify"); x.add_argument("repo",nargs="?",default="."); x.add_argument("--base",default="HEAD"); x.add_argument("--run",action="store_true"); x.add_argument("--allow-risky-exec",action="store_true")\n'
parser_insert=parser_anchor+'    x=sub.add_parser("record-evidence"); x.add_argument("repo",nargs="?",default="."); x.add_argument("check_id"); x.add_argument("state",choices=["PASS","FAIL","UNAVAILABLE","INCONCLUSIVE"]); x.add_argument("--optional",action="store_true"); x.add_argument("--detail",default=""); x.add_argument("--source",default="adapter")\n'
if parser_anchor not in text: raise SystemExit('verify parser anchor not found')
text=text.replace(parser_anchor,parser_insert,1)
dispatch_anchor='    elif args.cmd=="verify": r=verify(args.repo,args.base,args.run,args.allow_risky_exec)\n'
dispatch_insert=dispatch_anchor+'    elif args.cmd=="record-evidence": r=record_verification_evidence(args.repo,args.check_id,args.state,not args.optional,args.detail,args.source)\n'
if dispatch_anchor not in text: raise SystemExit('verify dispatch anchor not found')
text=text.replace(dispatch_anchor,dispatch_insert,1)
p.write_text(text,encoding='utf-8')
print('RC-4 runtime patch applied')
