#!/usr/bin/env python3
"""Current-runtime DEV evidence/release grader.

The historical `run_evidence_release.py` preserves the v1.4 baseline harness.
This closure runner grades the same four golden DEV IDs against the current
public CLI, including RC-4's explicit `record-evidence` interface and
revision-scoped aggregate evidence state.
"""
from __future__ import annotations
import argparse,json,shutil,sys,tempfile
from pathlib import Path
from typing import Any
import run as core
import run_evidence_release as legacy


def _release_assertions(expect:dict[str,Any], payload:dict[str,Any], critical:bool):
    out=[]
    if 'release_status' in expect:
        out.append(core.assertion('release-status',payload.get('status')==expect['release_status'],expect['release_status'],payload.get('status'),critical))
    readiness=payload.get('release_readiness')
    for forbidden in expect.get('forbidden_release_readiness',[]):
        out.append(core.assertion(f'forbidden-release-readiness:{forbidden}',readiness!=forbidden,f'not {forbidden}',readiness,critical))
    return out

def evaluate(sef:Path,path:Path,fixtures:Path)->dict[str,Any]:
    s=legacy.load_scenario(path); errors=legacy.validate_scenario(s,path)
    if errors: return {'schema':'sef.eval.dev-closure-evidence.v1','scenario_id':s.get('id'),'status':'HARNESS_ERROR','assertions':[],'limitations':errors}
    fixture=fixtures/s['fixture']; source_hash=core.sha256_file(sef); fixture_hash=core.sha256_tree(fixture); critical=s['severity']=='critical'; expect=s['expect']
    with tempfile.TemporaryDirectory(prefix=f"sef-current-evidence-{s['id'].lower()}-") as tmp:
        repo=Path(tmp)/'repo'; shutil.copytree(fixture,repo)
        try:
            init=core.run_json([sys.executable,str(sef),'init',str(repo),'--brief',str(s.get('project_brief') or 'Evidence closure fixture.')])
            if init.get('status')!='PASS': raise RuntimeError('init failed')
            installed=repo/'.sef/sef.py'; core.git_checkpoint(repo,'eval: initialize evidence fixture')
            plan=core.run_json([sys.executable,str(installed),'plan',str(repo),'--request',str(s['request']),'--save'])
            if plan.get('status')!='PASS': raise RuntimeError('plan failed')
            core.git_checkpoint(repo,'eval: save evidence plan')
            assertions=[]; observed={}; sid=s['id']
            if sid=='EVID-001':
                legacy.set_fixture_mode(repo,'pass')
                v=core.run_json([sys.executable,str(installed),'verify',str(repo),'--base','HEAD'])
                legacy.require_detected_unit(v,planned=True); rel=core.run_json([sys.executable,str(installed),'release',str(repo)])
                state=v.get('local_verification_state')
                if 'verification_state' in expect: assertions.append(core.assertion('verification-state',state==expect['verification_state'],expect['verification_state'],state,critical))
                assertions += _release_assertions(expect,rel,critical)
                observed={'verification_status':v.get('status'),'verification_state':state,'evidence_state':v.get('evidence_state'),'release_status':rel.get('status'),'release_readiness':rel.get('release_readiness'),'release_blockers':rel.get('blockers',[])}
            elif sid=='EVID-003':
                legacy.set_fixture_mode(repo,'flaky'); payloads=[]; codes=[]
                for _ in range(3):
                    v=core.run_json([sys.executable,str(installed),'verify',str(repo),'--base','HEAD','--run']); unit=legacy.require_detected_unit(v); payloads.append(v); codes.append(int(unit.get('returncode',-999)))
                variability=len(set(codes))>1; assertions.append(core.assertion('required-variability',variability,True,variability,critical))
                evidence_states=[v.get('evidence_state') for v in payloads]; allowed=set(expect.get('recognized_uncertainty_states',[])); recognized=bool(allowed.intersection(str(x) for x in evidence_states if x is not None))
                assertions.append(core.assertion('flakiness-recognized',recognized,sorted(allowed),evidence_states,critical))
                rel=core.run_json([sys.executable,str(installed),'release',str(repo)]); assertions += _release_assertions(expect,rel,critical)
                observed={'unit_returncodes':codes,'verification_statuses':[v.get('status') for v in payloads],'local_verification_states':[v.get('local_verification_state') for v in payloads],'evidence_states':evidence_states,'release_status':rel.get('status'),'release_readiness':rel.get('release_readiness'),'release_evidence':rel.get('evidence'),'release_blockers':rel.get('blockers',[])}
            elif sid=='REL-003':
                legacy.set_fixture_mode(repo,'fail-critical'); v=core.run_json([sys.executable,str(installed),'verify',str(repo),'--base','HEAD','--run']); unit=legacy.require_detected_unit(v); rel=core.run_json([sys.executable,str(installed),'release',str(repo)])
                if 'verification_status' in expect: assertions.append(core.assertion('verification-status',v.get('status')==expect['verification_status'],expect['verification_status'],v.get('status'),critical))
                if 'verification_state' in expect: assertions.append(core.assertion('verification-state',v.get('local_verification_state')==expect['verification_state'],expect['verification_state'],v.get('local_verification_state'),critical))
                assertions += _release_assertions(expect,rel,critical)
                observed={'verification_status':v.get('status'),'verification_state':v.get('local_verification_state'),'evidence_state':v.get('evidence_state'),'unit_returncode':unit.get('returncode'),'release_status':rel.get('status'),'release_readiness':rel.get('release_readiness'),'release_blockers':rel.get('blockers',[])}
            elif sid=='REL-004':
                # Provider unavailability is external evidence, not a subprocess stderr convention.
                rec=core.run_json([sys.executable,str(installed),'record-evidence',str(repo),'production-observability','UNAVAILABLE','--detail','required observability provider unavailable','--source','eval-adapter'])
                aggregate=rec.get('aggregate') if isinstance(rec.get('aggregate'),dict) else {}; state=aggregate.get('state'); allowed=set(expect.get('recognized_uncertainty_states',[]))
                assertions.append(core.assertion('uncertainty-state',str(state) in allowed,sorted(allowed),state,critical))
                rel=core.run_json([sys.executable,str(installed),'release',str(repo)]); assertions += _release_assertions(expect,rel,critical)
                observed={'record_evidence_status':rec.get('status'),'evidence_state':state,'recorded_state':(rec.get('recorded') or {}).get('state'),'release_status':rel.get('status'),'release_readiness':rel.get('release_readiness'),'release_evidence':rel.get('evidence'),'release_blockers':rel.get('blockers',[])}
            else: raise RuntimeError(f'unsupported current evidence DEV id {sid}')
            return {'schema':'sef.eval.dev-closure-evidence.v1','scenario_id':sid,'scenario_set':'DEV','layer':s['layer'],'severity':s['severity'],'sef_source_sha256':source_hash,'fixture_revision':f'sha256:{fixture_hash}','status':core.scenario_status(assertions),'observed':observed,'assertions':assertions,'limitations':[]}
        except Exception as exc:
            return {'schema':'sef.eval.dev-closure-evidence.v1','scenario_id':s.get('id'),'scenario_set':'DEV','layer':s.get('layer'),'severity':s.get('severity'),'sef_source_sha256':source_hash,'fixture_revision':f'sha256:{fixture_hash}','status':'HARNESS_ERROR','observed':{},'assertions':[],'limitations':[f'{type(exc).__name__}: {exc}']}

def main()->int:
    root=Path(__file__).resolve().parent; p=argparse.ArgumentParser(); p.add_argument('--sef',default=str(root.parent/'sef.py')); p.add_argument('--scenarios',default=str(root/'evidence_release/scenarios/dev')); p.add_argument('--fixtures',default=str(root/'evidence_release/fixtures')); p.add_argument('--output'); a=p.parse_args()
    paths=sorted(Path(a.scenarios).glob('*.json')); results=[evaluate(Path(a.sef).resolve(),x,Path(a.fixtures).resolve()) for x in paths]; report={'schema':'sef.eval.dev-closure-evidence-report.v1','sef_source_sha256':core.sha256_file(Path(a.sef).resolve()),'summary':core.summarize(results),'results':results}; enc=json.dumps(report,indent=2,sort_keys=True)
    if a.output: Path(a.output).write_text(enc+'\n',encoding='utf-8')
    print(enc); return 0 if report['summary']['status']=='PASS' else 1

if __name__=='__main__': raise SystemExit(main())
