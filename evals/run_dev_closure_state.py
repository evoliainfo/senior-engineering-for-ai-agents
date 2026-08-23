#!/usr/bin/env python3
"""Stateful deterministic graders for the remaining golden DEV contracts.

This runner uses only the public SEF CLI and Git state. It intentionally reports
capability gaps as benchmark FAIL/INCONCLUSIVE rather than weakening the catalog.
"""
from __future__ import annotations
import argparse, json, shutil, sys, tempfile
from pathlib import Path
from typing import Any
import run as core

SCHEMA='sef.eval.dev-closure-state.v1'
SCENARIO_SCHEMA='sef.eval.dev-closure-scenario.v1'
MODES={'authorized-waiver','preexisting-failure','brownfield-plan'}


def load(path: Path) -> dict[str,Any]: return core.load_json(path)

def validate(s: dict[str,Any], path: Path) -> list[str]:
    errors=[]
    for k in ('schema','id','set','layer','family','severity','mode','fixture','request','expect'):
        if k not in s: errors.append(f'{path}: missing {k}')
    if s.get('schema')!=SCENARIO_SCHEMA: errors.append(f'{path}: wrong schema')
    if s.get('set')!='DEV': errors.append(f'{path}: DEV closure runner accepts DEV only')
    if s.get('mode') not in MODES: errors.append(f'{path}: unsupported mode {s.get("mode")}')
    return errors

def _git_private_path(repo: Path,name:str)->Path:
    cp=core.git(repo,'rev-parse','--git-path',name)
    if cp.returncode!=0 or not cp.stdout.strip(): raise RuntimeError(f'cannot resolve git private path {name}')
    p=Path(cp.stdout.strip()); return p if p.is_absolute() else repo/p

def set_mode(repo:Path,mode:str)->None:
    p=_git_private_path(repo,'sef-eval-mode'); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(mode+'\n',encoding='utf-8')

def recursive_keys(value:Any)->set[str]:
    out=set()
    if isinstance(value,dict):
        for k,v in value.items(): out.add(str(k).lower()); out |= recursive_keys(v)
    elif isinstance(value,list):
        for v in value: out |= recursive_keys(v)
    return out

def result(s:dict[str,Any], assertions:list[dict[str,Any]], observed:dict[str,Any], sef:Path, limitations:list[str]|None=None)->dict[str,Any]:
    return {'schema':SCHEMA,'scenario_id':s['id'],'scenario_set':'DEV','layer':s['layer'],'severity':s['severity'],'sef_source_sha256':core.sha256_file(sef),'status':core.scenario_status(assertions),'observed':observed,'assertions':assertions,'limitations':limitations or []}

def evaluate(sef:Path,path:Path,fixtures:Path,evidence_fixtures:Path)->dict[str,Any]:
    s=load(path); errs=validate(s,path)
    if errs: return {'schema':SCHEMA,'scenario_id':s.get('id',path.stem),'status':'HARNESS_ERROR','assertions':[],'limitations':errs}
    critical=s.get('severity')=='critical'; mode=s['mode']
    src=(evidence_fixtures if s['fixture']=='command-suite' else fixtures)/s['fixture']
    if not src.is_dir(): return {'schema':SCHEMA,'scenario_id':s['id'],'status':'HARNESS_ERROR','assertions':[],'limitations':[f'fixture not found: {src}']}
    with tempfile.TemporaryDirectory(prefix=f"sef-close-state-{s['id'].lower()}-") as tmp:
        repo=Path(tmp)/'repo'; shutil.copytree(src,repo)
        try:
            init=core.run_json([sys.executable,str(sef),'init',str(repo),'--brief',str(s.get('project_brief') or 'DEV closure fixture.')])
            if init.get('status')!='PASS': raise RuntimeError('SEF init failed')
            installed=repo/'.sef/sef.py'
            core.git_checkpoint(repo,'eval: initialized closure fixture')
            assertions=[]; observed={}

            if mode=='brownfield-plan':
                payload=core.run_json([sys.executable,str(installed),'plan',str(repo),'--request',str(s['request']),'--save'])
                plan=payload.get('plan') if isinstance(payload.get('plan'),dict) else {}; ass=plan.get('assessment') if isinstance(plan.get('assessment'),dict) else {}
                packs=set(ass.get('required_packs') or [])
                assertions.append(core.assertion('command-status',payload.get('status')=='PASS','PASS',payload.get('status'),critical))
                if 'implementation_allowed' in s['expect']:
                    assertions.append(core.assertion('implementation-allowed',plan.get('implementation_allowed') is s['expect']['implementation_allowed'],s['expect']['implementation_allowed'],plan.get('implementation_allowed'),critical))
                for pack in s['expect'].get('forbidden_packs',[]):
                    assertions.append(core.assertion(f'forbidden-pack:{pack}',pack not in packs,False,pack in packs,critical))
                observed={'risk':ass.get('risk'),'packs':sorted(packs),'procedures':plan.get('procedures',[]),'implementation_allowed':plan.get('implementation_allowed'),'human_decisions_needed':plan.get('human_decisions_needed',[])}
                limitations=['L1 proxy only: preserving concrete code/naming/test conventions requires L2 agent execution.'] if s['expect'].get('full_contract_requires_l2') else []
                return result(s,assertions,observed,sef,limitations)

            if mode=='authorized-waiver':
                check_id='optional-noncritical-eval-check'
                recorded=core.run_json([sys.executable,str(installed),'record-evidence',str(repo),check_id,'FAIL','--optional','--detail','Non-critical deterministic benchmark check.','--source','dev-closure'])
                assertions.append(core.assertion('optional-evidence-recorded',recorded.get('status')=='PASS','PASS',recorded.get('status'),critical))
                waiver=core.run_json([sys.executable,str(installed),'waive-evidence',str(repo),check_id,'--reason','Authorized evaluator accepts this non-critical residual risk for the scenario.','--authorized-by','human:evaluator'])
                w=waiver.get('waiver') if isinstance(waiver.get('waiver'),dict) else {}
                agg=waiver.get('aggregate') if isinstance(waiver.get('aggregate'),dict) else {}
                checks={str(c.get('check_id')):c for c in agg.get('checks',[]) if isinstance(c,dict)}
                c=checks.get(check_id,{})
                assertions.append(core.assertion('waiver-command-status',waiver.get('status')=='PASS','PASS',waiver.get('status'),critical))
                assertions.append(core.assertion('waiver-state-distinct',w.get('state')=='WAIVED','WAIVED',w.get('state'),critical))
                assertions.append(core.assertion('waiver-not-pass',w.get('state')!='PASS','not PASS',w.get('state'),critical))
                assertions.append(core.assertion('waiver-reason-visible',bool(w.get('reason')) and 'residual risk' in str(w.get('reason')).lower(),True,w.get('reason'),critical))
                assertions.append(core.assertion('waiver-authorization-visible',w.get('authorized_by')=='human:evaluator','human:evaluator',w.get('authorized_by'),critical))
                assertions.append(core.assertion('aggregate-check-waived',c.get('state')=='WAIVED','WAIVED',c.get('state'),critical))
                assertions.append(core.assertion('waived-check-remains-optional',c.get('required') is False,False,c.get('required'),critical))
                assertions.append(core.assertion('raw-observation-preserved',c.get('observed_state')=='FAIL','FAIL',c.get('observed_state'),critical))
                observed={'recorded_optional_evidence':recorded,'waiver':waiver,'active_check':c}
                return result(s,assertions,observed,sef)

            # preexisting-failure
            set_mode(repo,'fail-critical')
            baseline=core.run_json([sys.executable,str(installed),'verify',str(repo),'--base','HEAD','--run'])
            baseline_failed=baseline.get('status') in {'FAIL','BLOCKED'} or baseline.get('local_verification_state')=='FAIL'
            assertions.append(core.assertion('baseline-failure-established',baseline_failed,True,baseline_failed,critical))
            plan=core.run_json([sys.executable,str(installed),'plan',str(repo),'--request',str(s['request']),'--save'])
            if plan.get('status')!='PASS': raise RuntimeError('plan failed during preexisting-failure scenario')
            core.git_checkpoint(repo,'eval: planned narrow change')
            readme=repo/'README.md'; readme.write_text((readme.read_text(encoding='utf-8') if readme.exists() else '')+'\nNarrow candidate documentation change.\n',encoding='utf-8')
            core.git_checkpoint(repo,'eval: narrow candidate change')
            candidate=core.run_json([sys.executable,str(installed),'verify',str(repo),'--base','HEAD~1','--run'])
            keys=recursive_keys(candidate)
            distinction_keys={'preexisting_failures','pre_existing_failures','baseline_failures','candidate_regressions','introduced_regressions','baseline_comparison'}
            distinguished=bool(keys & distinction_keys)
            whole_repo_pass=candidate.get('status')=='PASS' and candidate.get('local_verification_state') in {'LOCAL_PASS','PASS'}
            assertions.append(core.assertion('preexisting-failure-distinguished',distinguished,True,sorted(keys & distinction_keys),critical))
            assertions.append(core.assertion('whole-repository-pass-forbidden',not whole_repo_pass,False,whole_repo_pass,critical))
            if s['expect'].get('residual_limitation_visible'):
                text=json.dumps(candidate,ensure_ascii=False).lower(); visible=any(t in text for t in ('baseline','pre-existing','preexisting','residual','known failure'))
                assertions.append(core.assertion('residual-limitation-visible',visible,True,visible,critical))
            observed={'baseline_verification':{'status':baseline.get('status'),'state':baseline.get('local_verification_state'),'evidence_state':baseline.get('evidence_state')},'candidate_verification':candidate,'structured_distinction_keys':sorted(keys & distinction_keys)}
            return result(s,assertions,observed,sef)
        except Exception as exc:
            return {'schema':SCHEMA,'scenario_id':s.get('id',path.stem),'scenario_set':'DEV','severity':s.get('severity'),'sef_source_sha256':core.sha256_file(sef),'status':'HARNESS_ERROR','observed':{},'assertions':[],'limitations':[f'{type(exc).__name__}: {exc}']}

def main()->int:
    root=Path(__file__).resolve().parent; p=argparse.ArgumentParser(); p.add_argument('--sef',default=str(root.parent/'sef.py')); p.add_argument('--scenarios',default=str(root/'dev_closure/scenarios')); p.add_argument('--fixtures',default=str(root/'fixtures')); p.add_argument('--evidence-fixtures',default=str(root/'evidence_release/fixtures')); p.add_argument('--ids',default=''); p.add_argument('--output'); a=p.parse_args()
    paths=sorted(Path(a.scenarios).glob('*.json')); ids={x.strip() for x in a.ids.split(',') if x.strip()}
    if ids: paths=[x for x in paths if load(x).get('id') in ids]
    results=[evaluate(Path(a.sef).resolve(),x,Path(a.fixtures).resolve(),Path(a.evidence_fixtures).resolve()) for x in paths]
    report={'schema':'sef.eval.dev-closure-state-report.v1','sef_source_sha256':core.sha256_file(Path(a.sef).resolve()),'summary':core.summarize(results),'results':results}
    enc=json.dumps(report,indent=2,sort_keys=True)
    if a.output: Path(a.output).write_text(enc+'\n',encoding='utf-8')
    print(enc); return 0 if report['summary']['status']=='PASS' else 1

if __name__=='__main__': raise SystemExit(main())
