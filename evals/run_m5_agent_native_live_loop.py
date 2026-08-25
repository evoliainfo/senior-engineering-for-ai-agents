#!/usr/bin/env python3
"""Process-boundary qualification for the M5 agent-native mission loop.

The qualification invokes the public CLI as separate Python processes and uses
real temporary files.  It does not call a model, network, provider or browser;
its purpose is to prove that an active Codex session can use the CLI boundary to
freeze a plan, snapshot tool evidence, seal a result and advance M1 only after
the existing M5 evidence gate accepts the exact bytes.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import evals.run_launch_production_web_product_m5 as base  # noqa: E402
from delivery_missions.launch_production_web_product.agent_native import (  # noqa: E402
    RUN_SCHEMA_ID,
    load_run,
)
from project_state import add_entry, load_state, write_state  # noqa: E402

CLI = ROOT / "tools" / "delivery_mission.py"
REPORT = ROOT / "eval-results" / "m5-agent-native-live-loop-report.json"


def invoke(*args: str, expect: int = 0) -> dict:
    proc = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != expect:
        raise AssertionError(
            f"CLI return code {proc.returncode} != {expect}\nstdout={proc.stdout}\nstderr={proc.stderr}"
        )
    try:
        value = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"CLI stdout is not JSON: {proc.stdout!r}") from exc
    assert isinstance(value, dict)
    return value


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def setup_architected(root: Path) -> tuple[Path, Path, Path, dict]:
    spec = base._spec()
    state = base._state_at(spec, "ARCHITECTED")
    at = base.TIMES[2]
    inventory = base._add_tool(
        base._inventory(captured_at=at),
        "source_control",
        access="WRITE",
        sensitivity="LOCAL",
    )
    spec_path = root / "spec.json"
    state_path = root / "project-state.json"
    inventory_path = root / "inventory.json"
    write_json(spec_path, spec)
    write_state(state_path, state)
    write_json(inventory_path, inventory)
    return spec_path, state_path, inventory_path, spec


def prepare(root: Path, *, expect: int = 0, inventory: bool = True) -> tuple[dict, Path, Path]:
    spec_path, state_path, inventory_path, _ = setup_architected(root)
    run_dir = root / "run"
    args = [
        "prepare",
        "--spec", str(spec_path),
        "--state", str(state_path),
        "--run-dir", str(run_dir),
        "--at", base.TIMES[2],
    ]
    if inventory:
        args += ["--inventory", str(inventory_path)]
    value = invoke(*args, expect=expect)
    return value, run_dir, state_path


def satisfy_required_slots(root: Path, run_dir: Path) -> list[dict]:
    plan = json.loads((run_dir / "plan.json").read_text(encoding="utf-8"))
    registered = []
    for index, slot in enumerate(item for item in plan["artifact_slots"] if item["required"]):
        source = root / f"evidence-{index}.json"
        source.write_text(
            json.dumps({"slot": slot["id"], "observed": True, "index": index}) + "\n",
            encoding="utf-8",
        )
        allowed = slot["allowed_producers"]
        producer = "TOOL" if slot["capability"] is not None else ("AGENT" if "AGENT" in allowed else allowed[0])
        args = [
            "register",
            "--run-dir", str(run_dir),
            "--source", str(source),
            "--id", f"ART-{index}",
            "--kind", slot["kind"],
            "--producer", producer,
            "--slot", slot["id"],
        ]
        if producer == "TOOL":
            args += ["--capability", slot["capability"], "--surface", slot["surface_id"]]
        registered.append(invoke(*args)["artifact"])
    return registered


def full_run(root: Path) -> tuple[Path, Path, list[dict]]:
    prepared, run_dir, state_path = prepare(root)
    assert prepared["status"] == "READY"
    artifacts = satisfy_required_slots(root, run_dir)
    finalized = invoke(
        "finalize", "--run-dir", str(run_dir), "--status", "SUCCEEDED", "--at", base.TIMES[3]
    )
    assert finalized["status"] == "PASS"
    return run_dir, state_path, artifacts


def expect_error(args: list[str], text: str, *, code: int = 2) -> str:
    value = invoke(*args, expect=code)
    assert value["status"] == "FAIL"
    assert text in value["error"], value
    return value["error"]


def main() -> int:
    results: list[dict] = []

    def check(control_id: str, fn):
        try:
            detail = fn()
            results.append({"id": control_id, "status": "PASS", "detail": detail})
        except Exception as exc:
            results.append({"id": control_id, "status": "FAIL", "detail": {"error": repr(exc)}})

    def c01():
        with tempfile.TemporaryDirectory() as temp:
            prepared, run_dir, _ = prepare(Path(temp))
            manifest = load_run(run_dir)
            assert manifest["schema"] == RUN_SCHEMA_ID
            assert prepared["action"] == "IMPLEMENT_PRODUCT"
            return {"schema": manifest["schema"], "action": prepared["action"]}

    def c02():
        with tempfile.TemporaryDirectory() as temp:
            value, run_dir, _ = prepare(Path(temp), expect=3, inventory=False)
            assert value["status"] == "BLOCKED"
            assert "TOOL_INVENTORY_REQUIRED" in value["blockers"]
            assert not run_dir.exists()
            return {"blockers": value["blockers"], "run_created": False}

    def c03():
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, run_dir, _ = prepare(root)
            artifacts = satisfy_required_slots(root, run_dir)
            assert artifacts
            manifest = load_run(run_dir)
            assert manifest["status"] == "COLLECTING"
            for item in manifest["artifacts"]:
                actual = hashlib.sha256((run_dir / item["path"]).read_bytes()).hexdigest()
                assert actual == item["sha256"]
            return {"registered": len(artifacts), "status": manifest["status"]}

    def c04():
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, run_dir, _ = prepare(root)
            plan = json.loads((run_dir / "plan.json").read_text(encoding="utf-8"))
            tool_slot = next(item for item in plan["artifact_slots"] if item["required"] and item["capability"])
            source = root / "wrong-surface.json"
            source.write_text('{"ok":true}\n', encoding="utf-8")
            error = expect_error([
                "register", "--run-dir", str(run_dir), "--source", str(source), "--id", "BAD-SURFACE",
                "--kind", tool_slot["kind"], "--producer", "TOOL", "--slot", tool_slot["id"],
                "--capability", tool_slot["capability"], "--surface", "mcp-wrong-surface",
            ], "surface")
            return {"rejected": error}

    def c05():
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, run_dir, _ = prepare(root)
            error = expect_error([
                "finalize", "--run-dir", str(run_dir), "--status", "SUCCEEDED", "--at", base.TIMES[3]
            ], "required artifact slots are missing")
            return {"rejected": error}

    def c06():
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, run_dir, _ = prepare(root)
            plan = json.loads((run_dir / "plan.json").read_text(encoding="utf-8"))
            slot = next(item for item in plan["artifact_slots"] if item["required"])
            source = root / "dup.json"
            source.write_text('{"ok":true}\n', encoding="utf-8")
            producer = "TOOL" if slot["capability"] else "AGENT"
            common = [
                "--run-dir", str(run_dir), "--source", str(source), "--kind", slot["kind"],
                "--producer", producer, "--slot", slot["id"],
            ]
            if producer == "TOOL":
                common += ["--capability", slot["capability"], "--surface", slot["surface_id"]]
            invoke("register", *common, "--id", "FIRST")
            error = expect_error(["register", *common, "--id", "SECOND"], "slot already satisfied")
            return {"rejected": error}

    def c07():
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, run_dir, _ = prepare(root)
            source = root / "pack.json"
            source.write_text('{"schema":"none"}\n', encoding="utf-8")
            invoke(
                "register", "--run-dir", str(run_dir), "--source", str(source), "--id", "PACK-OBS",
                "--kind", "pack-observation", "--producer", "AGENT"
            )
            error = expect_error([
                "attach-pack", "--run-dir", str(run_dir), "--pack-id", "web-experience-visual-quality",
                "--artifact-id", "PACK-OBS"
            ], "pack is not active")
            return {"rejected": error}

    def c08():
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir, _, _ = full_run(root)
            result = json.loads((run_dir / "execution-result.json").read_text(encoding="utf-8"))
            assert result["status"] == "SUCCEEDED"
            assert load_run(run_dir)["status"] == "FINALIZED"
            return {"status": result["status"], "artifacts": len(result["artifacts"])}

    def c09():
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir, state_path, _ = full_run(root)
            accepted = invoke("accept", "--run-dir", str(run_dir), "--state", str(state_path))
            state = load_state(state_path)
            assert state["delivery_state"] == "IMPLEMENTED"
            assert accepted["delivery_state"] == "IMPLEMENTED"
            assert load_run(run_dir)["status"] == "ACCEPTED"
            assert (run_dir / "evidence-receipt.json").is_file()
            return {"delivery_state": state["delivery_state"], "receipt": accepted["receipt_status"]}

    def c10():
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir, state_path, artifacts = full_run(root)
            target = run_dir / artifacts[0]["path"]
            target.write_text("tampered after finalization\n", encoding="utf-8")
            before = load_state(state_path)["content_sha256"]
            error = expect_error(["accept", "--run-dir", str(run_dir), "--state", str(state_path)], "SHA-256 mismatch")
            after = load_state(state_path)
            assert after["delivery_state"] == "ARCHITECTED"
            assert after["content_sha256"] == before
            return {"rejected": error, "state_unchanged": True}

    def c11():
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir, state_path, _ = full_run(root)
            state = load_state(state_path)
            drifted = add_entry(
                state,
                domain="open_decisions",
                entry_id="UNRESOLVED-DRIFT",
                kind="UNRESOLVED",
                statement="A concurrent unresolved decision changed the state digest.",
                authority="ENGINEERING",
                evidence_refs=[],
                updated_at=base.TIMES[3],
            )
            write_state(state_path, drifted)
            error = expect_error(["accept", "--run-dir", str(run_dir), "--state", str(state_path)], "current Project State")
            assert load_state(state_path)["delivery_state"] == "ARCHITECTED"
            return {"rejected": error}

    def c12():
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, run_dir, _ = prepare(root)
            manifest_path = run_dir / "run.json"
            value = json.loads(manifest_path.read_text(encoding="utf-8"))
            value["status"] = "ACCEPTED"
            write_json(manifest_path, value)
            error = expect_error(["status", "--run-dir", str(run_dir)], "content hash mismatch")
            return {"rejected": error}

    def c13():
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, run_dir, _ = prepare(root)
            marker = run_dir / "marker.txt"
            marker.write_text("occupied\n", encoding="utf-8")
            spec_path, state_path, inventory_path, _ = setup_architected(root / "second")
            error = expect_error([
                "prepare", "--spec", str(spec_path), "--state", str(state_path), "--inventory", str(inventory_path),
                "--run-dir", str(run_dir), "--at", base.TIMES[2]
            ], "refusing to reuse non-empty run directory")
            return {"rejected": error}

    def c14():
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir, state_path, _ = full_run(root)
            invoke("accept", "--run-dir", str(run_dir), "--state", str(state_path))
            error = expect_error(["accept", "--run-dir", str(run_dir), "--state", str(state_path)], "FINALIZED")
            return {"rejected": error}

    def c15():
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, run_dir, _ = prepare(root)
            source = root / "empty.bin"
            source.write_bytes(b"")
            error = expect_error([
                "register", "--run-dir", str(run_dir), "--source", str(source), "--id", "EMPTY",
                "--kind", "implementation-change", "--producer", "AGENT"
            ], "non-empty file")
            return {"rejected": error}

    def c16():
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir, _, _ = full_run(root)
            manifest = load_run(run_dir)
            original = json.loads((run_dir / "decision.json").read_text(encoding="utf-8"))
            assert manifest["decision_sha256"] == original["content_sha256"]
            assert manifest["plan_sha256"] == json.loads((run_dir / "plan.json").read_text(encoding="utf-8"))["content_sha256"]
            return {"decision_bound": True, "plan_bound": True}

    def c17():
        digest = hashlib.sha256((ROOT / "sef.py").read_bytes()).hexdigest()
        checksums = (ROOT / "SHA256SUMS").read_text(encoding="utf-8")
        assert digest in checksums
        return {"sef_sha256": digest}

    def c18():
        return {
            "model_calls": 0,
            "network_calls": 0,
            "provider_calls": 0,
            "browser_calls": 0,
            "live_codex_claim": False,
            "process_boundary_exercised": True,
            "real_file_bytes_verified": True,
        }

    for control_id, fn in [
        ("M5L-01-prepare-run-contract", c01),
        ("M5L-02-block-without-tool-inventory", c02),
        ("M5L-03-register-and-hash-real-files", c03),
        ("M5L-04-reject-surface-substitution", c04),
        ("M5L-05-required-slot-gate", c05),
        ("M5L-06-duplicate-slot-rejected", c06),
        ("M5L-07-inactive-pack-rejected", c07),
        ("M5L-08-finalize-sealed-result", c08),
        ("M5L-09-accept-advances-one-state", c09),
        ("M5L-10-post-finalize-byte-tamper", c10),
        ("M5L-11-current-state-drift", c11),
        ("M5L-12-run-manifest-integrity", c12),
        ("M5L-13-run-directory-immutable-start", c13),
        ("M5L-14-no-double-accept", c14),
        ("M5L-15-empty-evidence-rejected", c15),
        ("M5L-16-bound-snapshot-digests", c16),
        ("M5L-17-runtime-integrity", c17),
        ("M5L-18-explicit-nonclaims", c18),
    ]:
        check(control_id, fn)

    passed = sum(item["status"] == "PASS" for item in results)
    report = {
        "schema": "sef.eval.m5-agent-native-live-loop.v1",
        "stage": "M5_AGENT_NATIVE_LIVE_LOOP",
        "control_count": len(results),
        "pass_count": passed,
        "fail_count": len(results) - passed,
        "model_calls": 0,
        "network_calls": 0,
        "provider_calls": 0,
        "browser_calls": 0,
        "live_codex_claim": False,
        "status": "PASS" if passed == len(results) else "FAIL",
        "results": results,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
