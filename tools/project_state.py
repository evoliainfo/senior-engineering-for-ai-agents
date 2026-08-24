#!/usr/bin/env python3
"""CLI for SEF Project State Spine.

No model/provider calls are performed. This CLI is intended for Delivery Mission
or harness adapters to manipulate repository-local project continuity safely.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from project_state import (
    ProjectStateError,
    add_entry,
    add_evidence,
    advance_delivery_state,
    canonical_digest,
    load_state,
    new_state,
    regress_delivery_state,
    select_context,
    validate_state,
    write_state,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _render(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="SEF deterministic Project State Spine")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create an evidence-backed FRAMED project state")
    init.add_argument("path", type=Path)
    init.add_argument("--project-id", required=True)
    init.add_argument("--product-statement", required=True)
    init.add_argument("--evidence-locator", required=True)
    init.add_argument("--evidence-sha256", default=None)
    init.add_argument("--at", default=None)

    validate = sub.add_parser("validate", help="validate state schema, semantics and digest")
    validate.add_argument("path", type=Path)

    digest = sub.add_parser("digest", help="print canonical state digest")
    digest.add_argument("path", type=Path)

    context = sub.add_parser("context", help="render a selective context slice")
    context.add_argument("path", type=Path)
    context.add_argument("--domains", required=True, help="comma-separated project-state domains")

    evidence = sub.add_parser("add-evidence", help="add a compact evidence reference")
    evidence.add_argument("path", type=Path)
    evidence.add_argument("--id", required=True)
    evidence.add_argument("--kind", required=True)
    evidence.add_argument("--locator", required=True)
    evidence.add_argument("--sha256", default=None)
    evidence.add_argument("--status", default="OBSERVED")
    evidence.add_argument("--at", default=None)

    entry = sub.add_parser("add-entry", help="append a typed project-state entry")
    entry.add_argument("path", type=Path)
    entry.add_argument("--domain", required=True)
    entry.add_argument("--id", required=True)
    entry.add_argument("--kind", required=True)
    entry.add_argument("--statement", required=True)
    entry.add_argument("--authority", required=True)
    entry.add_argument("--status", default="ACTIVE")
    entry.add_argument("--evidence", action="append", default=[])
    entry.add_argument("--at", default=None)

    advance = sub.add_parser("advance", help="advance exactly one evidence-backed delivery state")
    advance.add_argument("path", type=Path)
    advance.add_argument("--to", required=True)
    advance.add_argument("--evidence", action="append", required=True)
    advance.add_argument("--reason", required=True)
    advance.add_argument("--at", default=None)

    regress = sub.add_parser("regress", help="lower delivery truth when evidence invalidates a claim")
    regress.add_argument("path", type=Path)
    regress.add_argument("--to", required=True)
    regress.add_argument("--evidence", action="append", required=True)
    regress.add_argument("--reason", required=True)
    regress.add_argument("--at", default=None)

    args = parser.parse_args()

    try:
        if args.command == "init":
            state = new_state(
                project_id=args.project_id,
                product_statement=args.product_statement,
                evidence_locator=args.evidence_locator,
                evidence_sha256=args.evidence_sha256,
                at=args.at or _now(),
            )
            write_state(args.path, state)
            _render({"status": "PASS", "path": str(args.path), "delivery_state": state["delivery_state"], "content_sha256": state["content_sha256"]})
            return 0

        state = load_state(args.path)

        if args.command == "validate":
            validate_state(state)
            _render({"status": "PASS", "project_id": state["project_id"], "revision": state["revision"], "delivery_state": state["delivery_state"], "content_sha256": state["content_sha256"]})
            return 0
        if args.command == "digest":
            print(canonical_digest(state))
            return 0
        if args.command == "context":
            domains = [item.strip() for item in args.domains.split(",") if item.strip()]
            _render(select_context(state, domains))
            return 0
        if args.command == "add-evidence":
            state = add_evidence(
                state,
                evidence_id=args.id,
                kind=args.kind,
                locator=args.locator,
                observed_at=args.at or _now(),
                sha256=args.sha256,
                status=args.status,
            )
        elif args.command == "add-entry":
            state = add_entry(
                state,
                domain=args.domain,
                entry_id=args.id,
                kind=args.kind,
                statement=args.statement,
                authority=args.authority,
                evidence_refs=args.evidence,
                updated_at=args.at or _now(),
                status=args.status,
            )
        elif args.command == "advance":
            state = advance_delivery_state(
                state,
                to_state=args.to,
                evidence_refs=args.evidence,
                at=args.at or _now(),
                reason=args.reason,
            )
        elif args.command == "regress":
            state = regress_delivery_state(
                state,
                to_state=args.to,
                evidence_refs=args.evidence,
                at=args.at or _now(),
                reason=args.reason,
            )
        else:  # pragma: no cover - argparse guards this
            raise ProjectStateError(f"unsupported command: {args.command}")

        write_state(args.path, state)
        _render({"status": "PASS", "project_id": state["project_id"], "revision": state["revision"], "delivery_state": state["delivery_state"], "content_sha256": state["content_sha256"]})
        return 0
    except ProjectStateError as exc:
        _render({"status": "FAIL", "error": str(exc)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
