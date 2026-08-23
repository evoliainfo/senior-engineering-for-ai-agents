#!/usr/bin/env python3
"""Run the final-cycle positive/negative generalization controls."""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys, tempfile
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parent
CATALOG=ROOT/'final_generalization_controls.json'
RUNNER=ROOT/'run.py'
FIXTURES=ROOT/'fixtures'
EXPECTED=12

def load(path:Path)->dict[str,Any]:
    with path.open(encoding='utf-8') as f: value=json.load(f)
    if not isinstance(value,dict): raise ValueError(f'expected object: {path}')
    return value

def sha256(path:Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument('--sef',default=str(ROOT.parent/'sef.py')); p.add_argument('--output',default='final-generalization-controls.json'); a=p.parse_args()
    sef=Path(a.sef).resolve(); catalog=load(CATALOG)
    if catalog.get('schema')!='sef.eval.final-generalization-controls.v1': raise SystemExit('unexpected final control schema')
    scenarios=catalog.get('scenarios')
    if not isinstance(scenarios,list) or len(scenarios)!=EXPECTED: raise SystemExit(f'catalog must contain exactly {EXPECTED} controls')
    ids=[str(x.get('id')) for x in scenarios if isinstance(x,dict)]
    if len(ids)!=EXPECTED or len(set(ids))!=EXPECTED: raise SystemExit('control IDs must be present and unique')
    with tempfile.TemporaryDirectory(prefix='sef-final-generalization-') as tmp:
        t=Path(tmp); scenario_root=t/'scenarios'; scenario_root.mkdir()
        for item in scenarios: (scenario_root/f"{item['id']}.json").write_text(json.dumps(item,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        validate=subprocess.run([sys.executable,str(RUNNER),'validate','--scenarios',str(scenario_root)],cwd=ROOT.parent,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
        try: validation=json.loads(validate.stdout)
        except json.JSONDecodeError:
            print(json.dumps({'status':'HARNESS_ERROR','reason':'invalid validation JSON','stdout':validate.stdout[-2000:],'stderr':validate.stderr[-2000:]},indent=2)); return 2
        if validate.returncode!=0 or validation.get('status')!='PASS': print(json.dumps({'status':'HARNESS_ERROR','validation':validation},indent=2)); return 2
        raw_path=t/'raw.json'
        run=subprocess.run([sys.executable,str(RUNNER),'run','--sef',str(sef),'--scenarios',str(scenario_root),'--fixtures',str(FIXTURES),'--set','DEV','--output',str(raw_path)],cwd=ROOT.parent,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
        if not raw_path.is_file(): print(json.dumps({'status':'HARNESS_ERROR','reason':'missing raw report','stdout':run.stdout[-2000:],'stderr':run.stderr[-2000:]},indent=2)); return 2
        raw=load(raw_path)
    results=raw.get('results') if isinstance(raw.get('results'),list) else []
    observed=[str(x.get('scenario_id')) for x in results if isinstance(x,dict)]
    duplicates=sorted({x for x in observed if observed.count(x)>1}); missing=sorted(set(ids)-set(observed)); unexpected=sorted(set(observed)-set(ids)); harness_error_ids=sorted(str(x.get('scenario_id')) for x in results if x.get('status')=='HARNESS_ERROR')
    harness_errors=[]
    if duplicates: harness_errors.append('duplicates: '+', '.join(duplicates))
    if missing: harness_errors.append('missing: '+', '.join(missing))
    if unexpected: harness_errors.append('unexpected: '+', '.join(unexpected))
    if harness_error_ids: harness_errors.append('HARNESS_ERROR: '+', '.join(harness_error_ids))
    if len(results)!=EXPECTED: harness_errors.append(f'observed={len(results)}, expected={EXPECTED}')
    counts={}
    for item in results: counts[str(item.get('status','UNKNOWN'))]=counts.get(str(item.get('status','UNKNOWN')),0)+1
    failures=sorted(str(item.get('scenario_id')) for item in results if item.get('status')!='PASS')
    report={'schema':'sef.eval.final-generalization-acceptance.v1','sef_source_sha256':sha256(sef),'catalog_sha256':sha256(CATALOG),'accounting':{'expected':EXPECTED,'observed':len(results),'unique_observed':len(set(observed)),'missing':missing,'unexpected':unexpected,'duplicates':duplicates},'harness_integrity':'PASS' if not harness_errors else 'FAIL','harness_errors':harness_errors,'benchmark':{'status':'PASS' if not failures and not harness_errors else ('INVALID' if harness_errors else 'FAIL'),'counts':counts,'failures':failures},'results':sorted(results,key=lambda x:str(x.get('scenario_id')))}
    Path(a.output).write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('sef_source_sha256','catalog_sha256','accounting','harness_integrity','harness_errors','benchmark')},indent=2,sort_keys=True))
    if harness_errors: return 2
    return 0 if not failures else 1
if __name__=='__main__': raise SystemExit(main())
