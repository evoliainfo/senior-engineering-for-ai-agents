#!/usr/bin/env python3
from pathlib import Path
import hashlib

p=Path('sef.py')
s=p.read_text(encoding='utf-8')

anchor='''def task_plan(repo,request,save=False):\n    repo=Path(repo).resolve(); baseline=_load_json(repo/".sef/project-baseline.json",{}); assessment=_assess_request(repo,request)\n    risk=assessment.get("risk","R1"); packs=assessment.get("required_context_packs",[])\n    req=_implicit_requirements(request,assessment,baseline)\n    dod=[\n'''
if anchor not in s:
    raise SystemExit('RC-5 anchor not found')

helper='''def _rc5_observable_requirement_dod(request):\n    """Translate vague quality language into observable DoD without inventing targets."""\n    text=str(request or '')\n    low=text.lower()\n    out=[]\n\n    perf_signal=re.search(r"\\b(fast|faster|performant|performance|responsive|low[- ]latency|latency|throughput|optimi[sz](?:e|ation|ing)?)\\b",low,re.I)\n    measurable_perf=re.search(r"(?:\\b(?:p50|p90|p95|p99|rps|qps|tps)\\b|\\b\\d+(?:\\.\\d+)?\\s*(?:ms|milliseconds?|s|seconds?|rps|qps|tps|req(?:uests?)?/s)\\b|\\b(?:latency|response time|throughput)\\s*(?:target|budget|slo)\\b)",low,re.I)\n    if perf_signal and not measurable_perf:\n        out.append("Performance success requires an explicit measurable target (for example applicable latency, response-time, throughput or capacity criteria) rather than the adjective alone; do not invent the target.")\n        out.append("Benchmark, load-test or equivalent measurement evidence must demonstrate the agreed performance target before claiming the API is fast or performance-successful.")\n\n    vague_secure=bool(re.search(r"\\bsecure\\b",low,re.I))\n    vague_robust=bool(re.search(r"\\b(?:robust|resilien(?:t|ce)|reliable)\\b",low,re.I))\n    if vague_secure:\n        out.append("Security acceptance criteria must be observable for the affected trust/access boundaries, with applicable negative or abuse-path tests and verification evidence; 'secure' is not itself a passed criterion.")\n    if vague_robust:\n        out.append("Robustness/resilience acceptance criteria must define observable failure, fault and error behavior and be verified with applicable tests/evidence; 'robust' is not itself a passed criterion.")\n    return out\n\n'''
s=s.replace(anchor,helper+anchor,1)

needle='''    dod=[\n      "Explicit task acceptance criteria satisfied without unrelated changes.",\n      "Architecture/data/API/security implications from the plan are addressed or deliberately recorded.",\n      "Required specialist procedures are applied for routed packs.",\n      "Direct project verification passes; unavailable required evidence remains NOT_VERIFIED.",\n      "Actual diff is re-assessed and does not reveal unhandled higher risk.",\n      "Known residual risk and follow-up debt are explicit rather than hidden."\n    ]\n'''
replacement=needle+'''    dod += _rc5_observable_requirement_dod(request)\n'''
if needle not in s:
    raise SystemExit('RC-5 DoD anchor not found')
s=s.replace(needle,replacement,1)

p.write_text(s,encoding='utf-8')
h=hashlib.sha256(p.read_bytes()).hexdigest()
Path('SHA256SUMS').write_text(f'{h}  sef.py\n',encoding='utf-8')
print(h)
