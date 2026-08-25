#!/usr/bin/env python3
"""Agent-native CLI for the first Modern SEF Delivery Mission.

This is the interface an active Codex session can call from the repository.  It
does not launch a model or own provider credentials.  Codex remains responsible
for executing the exact surfaces named in the generated plan; this CLI freezes
the hand-off, snapshots returned evidence bytes, seals the execution result and
submits it to the existing M5 evidence gate.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from delivery_missions import (  # noqa: E402
    MissionError,
    advance_from_execution,
    decide_next_action,
)
from delivery_missions.launch_production_web_product.agent_native import (  # noqa: E402
    AgentNativeRunError,
    attach_pack_observation,
    finalize_run,
    load_run,
    mark_accepted,
    prepare_run,
    register_artifact,
)
from project_state import load_state, write_state  # noqa: E402


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json(path: Path, label: str) -> dict:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AgentNativeRunError(f"cannot read {label}: {path}") from exc
    if not isinstance(value, dict):
        raise AgentNativeRunError(f"{label} root must be an object")
    return value


def _render(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="SEF agent-native launch-production-web-product runner")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="decide the next action and freeze a READY execution plan")
    prepare.add_argument("--spec", type=Path, required=True)
    prepare.add_argument("--state", type=Path, required=True)
    prepare.add_argument("--run-dir", type=Path, required=True)
    prepare.add_argument("--inventory", type=Path, default=None)
    prepare.add_argument("--capsule", type=Path, action="append", default=[])
    prepare.add_argument("--at", default=None)
    prepare.add_argument("--max-tool-age-seconds", type=int, default=300)

    register = sub.add_parser("register", help="snapshot one evidence file into a prepared run")
    register.add_argument("--run-dir", type=Path, required=True)
    register.add_argument("--source", type=Path, required=True)
    register.add_argument("--id", required=True)
    register.add_argument("--kind", required=True)
    register.add_argument("--producer", choices=["AGENT", "SYSTEM", "TOOL"], required=True)
    register.add_argument("--slot", default=None)
    register.add_argument("--capability", default=None)
    register.add_argument("--surface", default=None)

    pack = sub.add_parser("attach-pack", help="bind a registered observation document to an active Expert Pack")
    pack.add_argument("--run-dir", type=Path, required=True)
    pack.add_argument("--pack-id", required=True)
    pack.add_argument("--artifact-id", required=True)

    finalize = sub.add_parser("finalize", help="seal execution-result.json from snapshotted evidence")
    finalize.add_argument("--run-dir", type=Path, required=True)
    finalize.add_argument("--status", choices=["SUCCEEDED", "FAILED", "INCOMPLETE"], default="SUCCEEDED")
    finalize.add_argument("--at", default=None)

    accept = sub.add_parser("accept", help="run the canonical M5 evidence gate and advance Project State once")
    accept.add_argument("--run-dir", type=Path, required=True)
    accept.add_argument("--state", type=Path, required=True)
    accept.add_argument("--receipt", default="evidence-receipt.json")

    status = sub.add_parser("status", help="render the integrity-checked run manifest")
    status.add_argument("--run-dir", type=Path, required=True)

    args = parser.parse_args()

    try:
        if args.command == "prepare":
            spec = _json(args.spec, "mission spec")
            state = load_state(args.state)
            inventory = _json(args.inventory, "tool inventory") if args.inventory is not None else None
            capsules = [_json(path, f"JIT capsule {path}") for path in args.capsule]
            at = args.at or _now()
            decision = decide_next_action(
                spec,
                state,
                at=at,
                tool_inventory=inventory,
                capsules=capsules,
                max_tool_age_seconds=args.max_tool_age_seconds,
            )
            if decision["status"] != "READY_FOR_AGENT":
                _render(
                    {
                        "status": decision["status"],
                        "next_action": decision["next_action"],
                        "blockers": decision["blockers"],
                        "decision_sha256": decision["content_sha256"],
                        "run_created": False,
                    }
                )
                return 3
            manifest = prepare_run(spec, state, decision, run_dir=args.run_dir, generated_at=at)
            plan = _json(args.run_dir / "plan.json", "execution plan")
            _render(
                {
                    "status": "READY",
                    "run_id": manifest["run_id"],
                    "run_dir": str(args.run_dir),
                    "action": plan["action"],
                    "context_domains": plan["context_domains"],
                    "selected_tools": plan["selected_tools"],
                    "pack_tasks": plan["pack_tasks"],
                    "artifact_slots": plan["artifact_slots"],
                    "sequence": plan["sequence"],
                    "plan_sha256": plan["content_sha256"],
                }
            )
            return 0

        if args.command == "register":
            artifact = register_artifact(
                args.run_dir,
                args.source,
                artifact_id=args.id,
                kind=args.kind,
                producer=args.producer,
                slot_id=args.slot,
                capability=args.capability,
                surface_id=args.surface,
            )
            _render({"status": "PASS", "artifact": artifact})
            return 0

        if args.command == "attach-pack":
            link = attach_pack_observation(
                args.run_dir,
                pack_id=args.pack_id,
                artifact_id=args.artifact_id,
            )
            _render({"status": "PASS", "pack_observation": link})
            return 0

        if args.command == "finalize":
            result = finalize_run(args.run_dir, observed_at=args.at or _now(), status=args.status)
            _render(
                {
                    "status": "PASS",
                    "execution_status": result["status"],
                    "execution_result": str(args.run_dir / "execution-result.json"),
                    "content_sha256": result["content_sha256"],
                }
            )
            return 0

        if args.command == "accept":
            root = args.run_dir
            manifest = load_run(root)
            if manifest["status"] != "FINALIZED":
                raise AgentNativeRunError("run must be FINALIZED before evidence acceptance")
            spec = _json(root / "spec.json", "mission spec")
            decision = _json(root / "decision.json", "mission decision")
            result = _json(root / "execution-result.json", "execution result")
            current_state = load_state(args.state)
            next_state, receipt = advance_from_execution(
                spec,
                current_state,
                decision,
                result,
                artifact_root=root,
                receipt_path=args.receipt,
            )
            write_state(args.state, next_state)
            manifest = mark_accepted(
                root,
                evidence_receipt_ref=args.receipt,
                state_after_sha256=next_state["content_sha256"],
            )
            _render(
                {
                    "status": "PASS",
                    "run_id": manifest["run_id"],
                    "delivery_state": next_state["delivery_state"],
                    "project_state_sha256": next_state["content_sha256"],
                    "receipt_status": receipt["status"],
                    "receipt": str(root / args.receipt),
                }
            )
            return 0

        if args.command == "status":
            _render(load_run(args.run_dir))
            return 0

        raise AgentNativeRunError(f"unsupported command: {args.command}")
    except (AgentNativeRunError, MissionError) as exc:
        _render({"status": "FAIL", "error": str(exc)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
