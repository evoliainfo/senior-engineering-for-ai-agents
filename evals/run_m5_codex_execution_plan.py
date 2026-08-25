#!/usr/bin/env python3
"""Qualification for the deterministic M5 Codex execution hand-off."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import evals.run_launch_production_web_product_m5 as base  # noqa: E402
from delivery_missions import build_execution_plan, decide_next_action, validate_execution_plan  # noqa: E402
from project_state import DELIVERY_STATES  # noqa: E402

REPORT_PATH = ROOT / "eval-results" / "m5-codex-execution-plan-report.json"
SCHEMA_PATH = ROOT / "delivery_missions" / "launch_production_web_product" / "execution-plan.schema.json"


def digest(value: dict) -> str:
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def reseal(plan: dict) -> dict:
    value = copy.deepcopy(plan)
    value.pop("content_sha256", None)
    value["content_sha256"] = digest(value)
    return value


def expect_error(fn, text: str) -> str:
    try:
        fn()
    except Exception as exc:
        message = str(exc)
        assert text in message, (text, message)
        return message
    raise AssertionError(f"expected error containing {text!r}")


def inventory_for(state_name: str, at: str):
    if state_name == "FRAMED":
        return None
    value = base._inventory(captured_at=at)
    if state_name == "ARCHITECTED":
        return base._add_tool(value, "source_control", access="WRITE", sensitivity="LOCAL")
    if state_name == "IMPLEMENTED":
        value = base._add_tool(value, "browser", access="READ", sensitivity="SANDBOX")
        return base._add_tool(value, "visual_capture", access="READ", sensitivity="SANDBOX")
    if state_name == "VERIFIED_LOCAL":
        value = base._add_tool(value, "hosting", access="WRITE", sensitivity="SANDBOX")
        value = base._add_tool(value, "browser", access="READ", sensitivity="SANDBOX")
        return base._add_tool(value, "visual_capture", access="READ", sensitivity="SANDBOX")
    if state_name == "PREVIEW_VERIFIED":
        value = base._add_tool(value, "ci", access="READ", sensitivity="SANDBOX")
        value = base._add_tool(value, "browser", access="READ", sensitivity="SANDBOX")
        return base._add_tool(value, "visual_capture", access="READ", sensitivity="SANDBOX")
    if state_name == "RELEASE_READY":
        return base._add_tool(value, "hosting", access="WRITE", sensitivity="PRODUCTION_SENSITIVE", authorization="NOT_REQUIRED")
    if state_name == "DEPLOYED":
        value = base._add_tool(value, "browser", access="READ", sensitivity="PRODUCTION_SENSITIVE")
        return base._add_tool(value, "observability", access="READ", sensitivity="PRODUCTION_SENSITIVE")
    raise AssertionError(state_name)


def at_for(state_name: str) -> str:
    return base.TIMES[min(DELIVERY_STATES.index(state_name) + 1, len(base.TIMES) - 1)]


def ready(spec: dict, state_name: str, *, capsules=()):
    state = base._state_at(spec, state_name)
    at = at_for(state_name)
    decision = decide_next_action(
        spec,
        state,
        at=at,
        tool_inventory=inventory_for(state_name, at),
        capsules=capsules,
    )
    assert decision["status"] == "READY_FOR_AGENT"
    plan = build_execution_plan(spec, state, decision, generated_at=at)
    validate_execution_plan(plan, spec=spec, decision=decision, state=state)
    return state, decision, plan


def main() -> int:
    results = []

    def check(control_id: str, fn):
        try:
            results.append({"id": control_id, "status": "PASS", "detail": fn()})
        except Exception as exc:
            results.append({"id": control_id, "status": "FAIL", "detail": {"error": repr(exc)}})

    def schema_contract():
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        required = set(schema["required"])
        assert {"project_context_sha256", "expertise_bindings", "selected_tools", "artifact_slots"} <= required
        return {"schema": schema["properties"]["schema"]["const"]}

    check("M5P-01-schema-contract", schema_contract)

    def seven_actions():
        expected = {
            "FRAMED": ("PLAN_ARCHITECTURE", "architecture-decision"),
            "ARCHITECTED": ("IMPLEMENT_PRODUCT", "implementation-change"),
            "IMPLEMENTED": ("VERIFY_LOCAL_PRODUCT", "local-verification"),
            "VERIFIED_LOCAL": ("DEPLOY_AND_VERIFY_PREVIEW", "preview-verification"),
            "PREVIEW_VERIFIED": ("PROVE_RELEASE_READINESS", "release-readiness"),
            "RELEASE_READY": ("DEPLOY_PRODUCTION", "deployment"),
            "DEPLOYED": ("VERIFY_PRODUCTION", "post-deploy-verification"),
        }
        observed = {}
        for state_name, pair in expected.items():
            _, decision, plan = ready(base._spec(), state_name)
            primary = next(item for item in plan["artifact_slots"] if item["role"] == "PRIMARY")
            assert (plan["action"], primary["kind"]) == pair
            assert plan["context_domains"] == decision["context_domains"]
            assert plan["project_context_sha256"] == decision["project_context_sha256"]
            observed[state_name] = pair[0]
        return observed

    check("M5P-02-seven-state-action-plans", seven_actions)

    def pack_scopes():
        _, _, local = ready(base._spec(), "IMPLEMENTED")
        _, _, preview = ready(base._spec(), "VERIFIED_LOCAL")
        _, _, production = ready(base._spec(), "DEPLOYED")
        assert local["pack_tasks"][0]["expected_scope"] == {"target.kind": "local"}
        assert preview["pack_tasks"][0]["expected_scope"] == {"target.kind": "preview"}
        assert production["pack_tasks"][0]["expected_scope"] == {"release.environment_kind": "PRODUCTION"}
        assert local["pack_tasks"][0]["observation_schema"] == "sef.web-visual-observations.v1"
        assert production["pack_tasks"][0]["observation_schema"] == "sef.production-evidence-operations.v1"
        return {"local": "local", "preview": "preview", "production": "PRODUCTION"}

    check("M5P-03-pack-scopes", pack_scopes)

    def pack_observation_producer_truth():
        _, _, plan = ready(base._spec(), "IMPLEMENTED")
        slot = next(item for item in plan["artifact_slots"] if item["role"] == "PACK_OBSERVATION")
        assert slot["allowed_producers"] == ["AGENT", "SYSTEM"]
        return {"allowed_producers": slot["allowed_producers"]}

    check("M5P-04-pack-observation-producers", pack_observation_producer_truth)

    def jit_binding():
        spec = base._provider_spec()
        state = base._state_at(spec, "ARCHITECTED")
        at = base.TIMES[2]
        capsule = base._provider_capsule(spec, state, generated_at=at)
        inventory = inventory_for("ARCHITECTED", at)
        inventory = base._add_tool(inventory, "external_provider_sandbox", access="WRITE", sensitivity="SANDBOX")
        decision = decide_next_action(spec, state, at=at, tool_inventory=inventory, capsules=[capsule])
        assert decision["jit_readiness"][0]["capsule_sha256"] == capsule["content_sha256"]
        plan = build_execution_plan(spec, state, decision, generated_at=at)
        binding = plan["expertise_bindings"][0]
        assert binding["capsule_id"] == capsule["capsule_id"]
        assert binding["capsule_sha256"] == capsule["content_sha256"]
        return {"capsule_id": binding["capsule_id"], "sha256": binding["capsule_sha256"]}

    check("M5P-05-jit-content-binding", jit_binding)

    def blocked_and_complete():
        spec = base._spec()
        state = base._state_at(spec, "RELEASE_READY")
        at = at_for("RELEASE_READY")
        inv = base._add_tool(base._inventory(captured_at=at), "hosting", access="WRITE", sensitivity="PRODUCTION_SENSITIVE", authorization="REQUIRED")
        blocked = decide_next_action(spec, state, at=at, tool_inventory=inv)
        a = expect_error(lambda: build_execution_plan(spec, state, blocked, generated_at=at), "only READY_FOR_AGENT")
        final_state = base._state_at(spec, "POST_DEPLOY_VERIFIED")
        complete = decide_next_action(spec, final_state, at=base.TIMES[8])
        b = expect_error(lambda: build_execution_plan(spec, final_state, complete, generated_at=base.TIMES[8]), "only READY_FOR_AGENT")
        return {"blocked": a, "complete": b}

    check("M5P-06-only-ready-decisions", blocked_and_complete)

    def unsafe_namespace():
        spec = base._spec()
        state = base._state_at(spec, "FRAMED")
        decision = decide_next_action(spec, state, at=base.TIMES[1])
        message = expect_error(
            lambda: build_execution_plan(spec, state, decision, generated_at=base.TIMES[1], evidence_namespace="artifact://m5//escape/"),
            "unsafe path segments",
        )
        return {"rejected": message}

    check("M5P-07-namespace-guard", unsafe_namespace)

    def contextual_substitutions():
        spec = base._spec()
        state, decision, plan = ready(spec, "IMPLEMENTED")
        failures = {}

        surface = copy.deepcopy(plan)
        cap = surface["selected_tools"][0]["capability"]
        surface["selected_tools"][0]["surface_id"] = "alternate-surface"
        for slot in surface["artifact_slots"]:
            if slot["capability"] == cap:
                slot["surface_id"] = "alternate-surface"
        for task in surface["pack_tasks"]:
            for binding in task["required_tool_bindings"]:
                if binding["capability"] == cap:
                    binding["surface_id"] = "alternate-surface"
        surface = reseal(surface)
        validate_execution_plan(surface)
        failures["surface"] = expect_error(lambda: validate_execution_plan(surface, spec=spec, decision=decision, state=state), "not exact M4 projection")

        access = copy.deepcopy(plan)
        browser = next(item for item in access["selected_tools"] if item["capability"] == "browser")
        browser["access"] = "WRITE"
        for task in access["pack_tasks"]:
            for binding in task["required_tool_bindings"]:
                if binding["capability"] == "browser":
                    binding["access"] = "WRITE"
        access = reseal(access)
        validate_execution_plan(access)
        failures["access"] = expect_error(lambda: validate_execution_plan(access, spec=spec, decision=decision, state=state), "not exact M4 projection")

        slot = copy.deepcopy(plan)
        next(item for item in slot["artifact_slots"] if item["role"] == "PRIMARY")["allowed_producers"] = ["SYSTEM"]
        slot = reseal(slot)
        validate_execution_plan(slot)
        failures["slot"] = expect_error(lambda: validate_execution_plan(slot, spec=spec, decision=decision, state=state), "artifact slots are not canonical")

        pack = copy.deepcopy(plan)
        pack["pack_tasks"][0]["expected_scope"] = {"target.kind": "preview"}
        pack["pack_tasks"][0]["evaluator_ref"] = "expert_packs/alternate/evaluator.py"
        pack = reseal(pack)
        validate_execution_plan(pack)
        failures["pack"] = expect_error(lambda: validate_execution_plan(pack, spec=spec, decision=decision, state=state), "pack tasks are not canonical")
        return {key: "REJECTED" for key in failures}

    check("M5P-08-resealed-decision-projections", contextual_substitutions)

    def context_substitution():
        spec = base._spec()
        state, decision, plan = ready(spec, "FRAMED")
        changed = copy.deepcopy(plan)
        changed["context_domains"] = ["product"]
        changed["project_context_sha256"] = "b" * 64
        changed = reseal(changed)
        validate_execution_plan(changed)
        message = expect_error(lambda: validate_execution_plan(changed, spec=spec, decision=decision, state=state), "project context digest diverges")
        return {"rejected": message}

    check("M5P-09-project-context-binding", context_substitution)

    def jit_substitution():
        spec = base._provider_spec()
        state = base._state_at(spec, "ARCHITECTED")
        at = base.TIMES[2]
        capsule = base._provider_capsule(spec, state, generated_at=at)
        inv = inventory_for("ARCHITECTED", at)
        inv = base._add_tool(inv, "external_provider_sandbox", access="WRITE", sensitivity="SANDBOX")
        decision = decide_next_action(spec, state, at=at, tool_inventory=inv, capsules=[capsule])
        plan = build_execution_plan(spec, state, decision, generated_at=at)
        changed = copy.deepcopy(plan)
        changed["expertise_bindings"][0]["capsule_sha256"] = "c" * 64
        changed = reseal(changed)
        validate_execution_plan(changed)
        message = expect_error(lambda: validate_execution_plan(changed, spec=spec, decision=decision, state=state), "JIT bindings diverge")
        return {"rejected": message}

    check("M5P-10-jit-substitution-guard", jit_substitution)

    def tool_freshness():
        spec = base._spec()
        state = base._state_at(spec, "ARCHITECTED")
        at = base.TIMES[2]
        decision = decide_next_action(spec, state, at=at, tool_inventory=inventory_for("ARCHITECTED", at), max_tool_age_seconds=300)
        message = expect_error(lambda: build_execution_plan(spec, state, decision, generated_at=base.TIMES[8]), "tool snapshot is stale")
        return {"rejected": message}

    check("M5P-11-tool-snapshot-freshness", tool_freshness)

    def state_time_guard():
        spec = base._spec()
        state = base._state_at(spec, "ARCHITECTED")
        at = base.TIMES[2]
        decision = decide_next_action(spec, state, at=at, tool_inventory=inventory_for("ARCHITECTED", at))
        message = expect_error(lambda: build_execution_plan(spec, state, decision, generated_at=base.TIMES[0]), "cannot predate current Project State")
        return {"rejected": message}

    check("M5P-12-state-time-guard", state_time_guard)

    def material_data_pack():
        spec = base._spec()
        spec["surfaces"]["persistent_data"] = True
        spec["surfaces"]["material_data_change"] = True
        state = base._state_at(spec, "PREVIEW_VERIFIED")
        at = at_for("PREVIEW_VERIFIED")
        inv = inventory_for("PREVIEW_VERIFIED", at)
        inv = base._add_tool(inv, "database_admin", access="WRITE", sensitivity="SANDBOX")
        decision = decide_next_action(spec, state, at=at, tool_inventory=inv)
        plan = build_execution_plan(spec, state, decision, generated_at=at)
        assert {item["pack_id"] for item in plan["pack_tasks"]} == {"data-change-safety", "web-experience-visual-quality"}
        return {"packs": [item["pack_id"] for item in plan["pack_tasks"]]}

    check("M5P-13-material-data-pack", material_data_pack)

    def nonclaims_and_determinism():
        spec = base._spec()
        state, decision, plan = ready(spec, "RELEASE_READY")
        again = build_execution_plan(spec, state, decision, generated_at=at_for("RELEASE_READY"))
        assert plan == again
        assert not any(plan["claims"].values())
        assert plan["result_contract"]["decision_sha256"] == decision["content_sha256"]
        return {"plan_sha256": plan["content_sha256"], "claims": plan["claims"]}

    check("M5P-14-deterministic-nonclaims", nonclaims_and_determinism)

    def input_immutability():
        spec = base._spec()
        state = base._state_at(spec, "IMPLEMENTED")
        at = at_for("IMPLEMENTED")
        decision = decide_next_action(spec, state, at=at, tool_inventory=inventory_for("IMPLEMENTED", at))
        state_before = copy.deepcopy(state)
        decision_before = copy.deepcopy(decision)
        build_execution_plan(spec, state, decision, generated_at=at)
        assert state == state_before and decision == decision_before
        return {"state_sha256": state["content_sha256"], "decision_sha256": decision["content_sha256"]}

    check("M5P-15-input-immutability", input_immutability)

    def runtime_integrity():
        expected = None
        for raw in (ROOT / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
            parts = raw.strip().split()
            if len(parts) >= 2 and parts[-1].lstrip("*") == "sef.py":
                expected = parts[0]
                break
        observed = hashlib.sha256((ROOT / "sef.py").read_bytes()).hexdigest()
        assert expected and observed == expected
        return {"sef_sha256": observed}

    check("M5P-16-runtime-integrity", runtime_integrity)

    passed = sum(item["status"] == "PASS" for item in results)
    report = {
        "schema": "sef.eval.m5-codex-execution-plan.v1",
        "stage": "M5_CODEX_EXECUTION_HANDOFF",
        "control_count": len(results),
        "pass_count": passed,
        "fail_count": len(results) - passed,
        "status": "PASS" if passed == len(results) else "FAIL",
        "tool_execution_calls": 0,
        "model_calls": 0,
        "provider_calls": 0,
        "network_calls": 0,
        "deployment_claim": False,
        "m5_end_to_end_claim": False,
        "plan_authorization_claim": False,
        "results": results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
