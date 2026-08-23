#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location("sef_runtime",ROOT/"sef.py")
sef=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(sef)


def case(name,fn):
    try:
        fn(); print(f"PASS {name}"); return True
    except Exception as exc:
        print(f"FAIL {name}: {exc}"); return False


def test_pass_fail_pass_is_flaky():
    sf={}
    obs=[]
    for i,state in enumerate(["PASS","FAIL","PASS"],1):
        obs.append({"revision":"r1","attempt_id":str(i),"recorded_at":f"t{i}","check_id":"regression","required":True,"state":state,"source":"command"})
    sef._rc4_append_evidence(sf,obs,"r1")
    assert sef._rc4_aggregate_index(sf["verification_evidence_index"],"r1")["state"]=="FLAKY"


def test_raw_eviction_cannot_launder_failure():
    sf={}
    first={"revision":"r1","attempt_id":"0","recorded_at":"t0","check_id":"regression","required":True,"state":"FAIL","source":"command"}
    sef._rc4_append_evidence(sf,[first],"r1")
    for i in range(sef._RC4_EVIDENCE_LIMIT+40):
        sef._rc4_append_evidence(sf,[{"revision":"r1","attempt_id":str(i+1),"recorded_at":f"t{i+1}","check_id":"regression","required":True,"state":"PASS","source":"command"}],"r1")
    assert len(sf["verification_evidence"])==sef._RC4_EVIDENCE_LIMIT
    assert all(x["state"]=="PASS" for x in sf["verification_evidence"])
    summary=sf["verification_evidence_index"]["r1"]["regression"]
    assert set(summary["seen_states"])=={"PASS","FAIL"}
    assert sef._rc4_aggregate_index(sf["verification_evidence_index"],"r1")["state"]=="FLAKY"


def test_explicit_unavailable_not_stderr_guessing():
    assert sef._rc4_normalize_evidence_state(2,"UNAVAILABLE")=="UNAVAILABLE"
    assert sef._rc4_normalize_evidence_state(2)=="FAIL"


def test_stale_revision_not_proof():
    idx={"r1":{"unit":{"required":True,"seen_states":["PASS"],"observation_count":1}}}
    assert sef._rc4_aggregate_index(idx,"r1")["state"]=="PASS"
    assert sef._rc4_aggregate_index(idx,"r2")["state"]=="NOT_RUN"


def test_malformed_unknown_state_is_inconclusive():
    idx={"r1":{"provider":{"required":True,"seen_states":["MAGIC"],"observation_count":1}}}
    assert sef._rc4_aggregate_index(idx,"r1")["state"]=="INCONCLUSIVE"


def test_index_pruning_preserves_current_revision():
    idx={f"r{i}":{"unit":{"required":True,"seen_states":["PASS"]}} for i in range(20)}
    pruned=sef._rc4_prune_index(idx,"r0")
    assert "r0" in pruned
    assert len(pruned)<=sef._RC4_INDEX_REVISION_LIMIT


def _write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data),encoding="utf-8")


def _release_fixture(state,profile=None):
    td=tempfile.TemporaryDirectory(); repo=Path(td.name)
    _write_json(repo/".sef/project-baseline.json",{"project":{"brief":"test project"},"discovery":{"context_confirmations_needed":[]}})
    _write_json(repo/".sef/project-profile.json",profile or {"context_candidates":[]})
    _write_json(repo/".sef/project-state.json",state)
    return td,repo


def test_legacy_last_verification_requires_fresh_index():
    td,repo=_release_fixture({"last_verification":{"revision":"r1","local_verification_state":"LOCAL_PASS"}})
    old_head,old_dirty=sef._git_head,sef._git_dirty
    sef._git_head=lambda _repo:"r1"; sef._git_dirty=lambda _repo:False
    try:
        out=sef.release(repo)
        assert out["release_readiness"]=="BLOCKED"
        assert any("verification evidence index" in x for x in out["blockers"])
    finally:
        sef._git_head,sef._git_dirty=old_head,old_dirty; td.cleanup()


def test_current_index_pass_can_reach_release_review():
    state={
      "last_verification":{"revision":"r1","local_verification_state":"LOCAL_PASS"},
      "verification_evidence_index":{"r1":{"unit":{"required":True,"seen_states":["PASS"],"observation_count":1}}},
    }
    td,repo=_release_fixture(state)
    old_head,old_dirty=sef._git_head,sef._git_dirty
    sef._git_head=lambda _repo:"r1"; sef._git_dirty=lambda _repo:False
    try:
        out=sef.release(repo)
        assert out["release_readiness"]=="READY_FOR_RELEASE_REVIEW",out
    finally:
        sef._git_head,sef._git_dirty=old_head,old_dirty; td.cleanup()


def test_material_confirmation_still_blocks():
    state={
      "last_verification":{"revision":"r1","local_verification_state":"LOCAL_PASS"},
      "verification_evidence_index":{"r1":{"unit":{"required":True,"seen_states":["PASS"],"observation_count":1}}},
    }
    profile={"context_candidates":[{"context":"MULTI_TENANT","evidence":"test"}]}
    td,repo=_release_fixture(state,profile)
    old_head,old_dirty=sef._git_head,sef._git_dirty
    sef._git_head=lambda _repo:"r1"; sef._git_dirty=lambda _repo:False
    try:
        out=sef.release(repo)
        assert out["release_readiness"]=="BLOCKED"
        assert any("Material project contexts" in x for x in out["blockers"])
    finally:
        sef._git_head,sef._git_dirty=old_head,old_dirty; td.cleanup()


def test_specialist_evidence_still_blocks():
    state={
      "last_verification":{"revision":"r1","local_verification_state":"LOCAL_PASS_SPECIALIST_EVIDENCE_OUTSTANDING"},
      "verification_evidence_index":{"r1":{"unit":{"required":True,"seen_states":["PASS"],"observation_count":1}}},
    }
    td,repo=_release_fixture(state)
    old_head,old_dirty=sef._git_head,sef._git_dirty
    sef._git_head=lambda _repo:"r1"; sef._git_dirty=lambda _repo:False
    try:
        out=sef.release(repo)
        assert out["release_readiness"]=="BLOCKED"
        assert any("Specialist evidence" in x for x in out["blockers"])
    finally:
        sef._git_head,sef._git_dirty=old_head,old_dirty; td.cleanup()


def test_adapter_ingestion_is_revision_bound():
    td,repo=_release_fixture({})
    old_head=sef._git_head; sef._git_head=lambda _repo:"r1"
    try:
        out=sef.record_verification_evidence(repo,"observability-provider","UNAVAILABLE",True,"provider timeout","adapter")
        assert out["status"]=="PASS"
        assert out["aggregate"]["state"]=="UNAVAILABLE"
        persisted=json.loads((repo/".sef/project-state.json").read_text(encoding="utf-8"))
        assert persisted["verification_evidence_index"]["r1"]["observability-provider"]["seen_states"]==["UNAVAILABLE"]
    finally:
        sef._git_head=old_head; td.cleanup()


CASES=[
  ("pass_fail_pass_is_flaky",test_pass_fail_pass_is_flaky),
  ("raw_eviction_cannot_launder_failure",test_raw_eviction_cannot_launder_failure),
  ("explicit_unavailable_not_stderr_guessing",test_explicit_unavailable_not_stderr_guessing),
  ("stale_revision_not_proof",test_stale_revision_not_proof),
  ("malformed_unknown_state_is_inconclusive",test_malformed_unknown_state_is_inconclusive),
  ("index_pruning_preserves_current_revision",test_index_pruning_preserves_current_revision),
  ("legacy_last_verification_requires_fresh_index",test_legacy_last_verification_requires_fresh_index),
  ("current_index_pass_can_reach_release_review",test_current_index_pass_can_reach_release_review),
  ("material_confirmation_still_blocks",test_material_confirmation_still_blocks),
  ("specialist_evidence_still_blocks",test_specialist_evidence_still_blocks),
  ("adapter_ingestion_is_revision_bound",test_adapter_ingestion_is_revision_bound),
]

passed=sum(case(name,fn) for name,fn in CASES)
print(f"RC-4 runtime regression: {passed}/{len(CASES)} PASS")
raise SystemExit(0 if passed==len(CASES) else 1)
