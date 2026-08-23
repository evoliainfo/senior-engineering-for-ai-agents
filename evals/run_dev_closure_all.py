#!/usr/bin/env python3
"""Unified 38-scenario DEV closure orchestration.

Runs the four deterministic DEV harness surfaces against one exact sef.py source
and combines their normalized results without allowing duplicate or missing IDs.
Benchmark FAIL is data; harness/accounting defects are separately identified.
CHALLENGE is never discovered or executed by this runner.
"""
from __future__ import annotations
import argparse, json, subprocess, sys, tempfile
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parent


def load(path:Path)->dict[str,Any]:
    with path.open(encoding='utf-8') as f: return json.load(f)

def run_report(command:list[str],output:Path)->tuple[int,dict[str,Any]]:
    cp=subprocess.run(command,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
    if not output.exists():
        raise RuntimeError(f"runner produced no output: {' '.join(command)}\nstdout={cp.stdout[-2000:]}\nstderr={cp.stderr[-2000:]}")
    return cp.returncode,load(output)

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument('--sef',default=str(ROOT.parent/'sef.py')); p.add_argument('--manifest',default=str(ROOT/'dev_coverage_manifest.json')); p.add_argument('--output',default='dev-closure-all.json'); a=p.parse_args()
    sef=str(Path(a.sef).resolve()); manifest=load(Path(a.manifest)); harnesses=manifest['harnesses']
    with tempfile.TemporaryDirectory(prefix='sef-dev-closure-all-') as tmp:
        t=Path(tmp)
        core_ids=','.join(harnesses['general_core']['ids'])
        semantic_ids=','.join(harnesses['semantic_requirements']['ids'])
        state_ids=','.join(harnesses['stateful_brownfield']['ids'])
        commands=[
            ('general_core',[sys.executable,str(ROOT/'run.py'),'run','--sef',sef,'--set','DEV','--ids',core_ids,'--output',str(t/'general.json')],t/'general.json'),
            ('evidence_release',[sys.executable,str(ROOT/'run_dev_closure_evidence.py'),'--sef',sef,'--output',str(t/'evidence.json')],t/'evidence.json'),
            ('semantic_requirements',[sys.executable,str(ROOT/'run_dev_closure_extra.py'),'--sef',sef,'--ids',semantic_ids,'--output',str(t/'semantic.json')],t/'semantic.json'),
            ('stateful_brownfield',[sys.executable,str(ROOT/'run_dev_closure_state.py'),'--sef',sef,'--ids',state_ids,'--output',str(t/'stateful.json')],t/'stateful.json'),
        ]
        runner_exit_codes={}; all_results=[]; harness_errors=[]
        for name,cmd,out in commands:
            code,report=run_report(cmd,out); runner_exit_codes[name]=code
            rs=report.get('results',[])
            if not isinstance(rs,list): harness_errors.append(f'{name}: results is not a list'); rs=[]
            for r in rs:
                rr=dict(r); rr['harness']=name; all_results.append(rr)
        expected=[]
        for h in harnesses.values(): expected.extend(h['ids'])
        duplicate_expected=sorted({x for x in expected if expected.count(x)>1})
        observed=[str(r.get('scenario_id')) for r in all_results]
        duplicate_observed=sorted({x for x in observed if observed.count(x)>1})
        missing=sorted(set(expected)-set(observed)); unexpected=sorted(set(observed)-set(expected))
        harness_error_ids=sorted(str(r.get('scenario_id')) for r in all_results if r.get('status')=='HARNESS_ERROR')
        if duplicate_expected: harness_errors.append('manifest duplicate IDs: '+', '.join(duplicate_expected))
        if duplicate_observed: harness_errors.append('duplicate results: '+', '.join(duplicate_observed))
        if missing: harness_errors.append('missing results: '+', '.join(missing))
        if unexpected: harness_errors.append('unexpected results: '+', '.join(unexpected))
        if harness_error_ids: harness_errors.append('HARNESS_ERROR results: '+', '.join(harness_error_ids))
        if len(expected)!=manifest.get('dev_total'): harness_errors.append(f"manifest expected IDs={len(expected)} but dev_total={manifest.get('dev_total')}")
        if len(all_results)!=manifest.get('dev_total'): harness_errors.append(f"observed results={len(all_results)} but dev_total={manifest.get('dev_total')}")
        sha_values=sorted({str(r.get('sef_source_sha256')) for r in all_results if r.get('sef_source_sha256')})
        if len(sha_values)!=1: harness_errors.append(f'non-uniform SEF hashes: {sha_values}')
        counts={}
        for r in all_results: counts[str(r.get('status','UNKNOWN'))]=counts.get(str(r.get('status','UNKNOWN')),0)+1
        critical_failures=sorted(str(r.get('scenario_id')) for r in all_results if r.get('severity')=='critical' and r.get('status')!='PASS')
        failures=sorted(str(r.get('scenario_id')) for r in all_results if r.get('status')!='PASS')
        report={
            'schema':'sef.eval.dev-closure-all.v1',
            'challenge_status':manifest.get('challenge_status'),
            'challenge_ids_executed':[],
            'sef_source_sha256':sha_values[0] if len(sha_values)==1 else None,
            'accounting':{'expected_dev':manifest.get('dev_total'),'observed_dev':len(all_results),'unique_observed':len(set(observed)),'missing':missing,'unexpected':unexpected,'duplicates':duplicate_observed},
            'runner_exit_codes':runner_exit_codes,
            'harness_integrity':'PASS' if not harness_errors else 'FAIL',
            'harness_errors':harness_errors,
            'benchmark':{'status':'PASS' if not failures and not harness_errors else 'FAIL','counts':counts,'failures':failures,'critical_failures':critical_failures},
            'known_l2_followups':manifest.get('known_l2_followups',[]),
            'results':sorted(all_results,key=lambda x:str(x.get('scenario_id'))),
        }
        Path(a.output).write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        print(json.dumps({k:report[k] for k in ('challenge_status','sef_source_sha256','accounting','harness_integrity','harness_errors','benchmark','known_l2_followups')},indent=2,sort_keys=True))
        if harness_errors: return 2
        return 0 if not failures else 1

if __name__=='__main__': raise SystemExit(main())
