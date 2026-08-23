"""Isolated RC-4 evidence-state candidate.

Research-only: this module is intentionally outside canonical sef.py.
It models revision-scoped verification evidence without changing runtime behavior.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Iterable, Optional

PASSING = {"PASS"}
BLOCKING_REQUIRED = {"NOT_RUN", "FAIL", "UNAVAILABLE", "INCONCLUSIVE", "FLAKY"}
VALID = PASSING | BLOCKING_REQUIRED | {"WAIVED"}


@dataclass(frozen=True)
class Observation:
    check_id: str
    revision: str
    attempt: int
    required: bool
    state: str
    source: str = "command"
    detail: str = ""
    waiver_authorized: bool = False

    def __post_init__(self):
        if self.state not in VALID:
            raise ValueError(f"invalid evidence state: {self.state}")
        if not self.check_id:
            raise ValueError("check_id is required")
        if not self.revision:
            raise ValueError("revision is required")
        if self.attempt < 1:
            raise ValueError("attempt must be >= 1")
        if self.state == "WAIVED" and not self.waiver_authorized:
            raise ValueError("WAIVED requires waiver_authorized=True")


def from_command_result(*, check_id: str, revision: str, attempt: int, required: bool,
                        returncode: Optional[int], adapter_state: Optional[str] = None,
                        stderr: str = "") -> Observation:
    """Normalize one command/evidence-adapter result.

    Explicit adapter_state is authoritative for evidence availability semantics.
    stderr is intentionally ignored for classification so textual messages cannot
    silently promote ordinary failures into UNAVAILABLE/INCONCLUSIVE.
    """
    explicit = str(adapter_state or "").upper().strip()
    if explicit:
        if explicit not in VALID - {"WAIVED"}:
            raise ValueError(f"unsupported adapter_state: {explicit}")
        state = explicit
    elif returncode is None:
        state = "NOT_RUN"
    elif returncode == 0:
        state = "PASS"
    else:
        state = "FAIL"
    return Observation(
        check_id=check_id,
        revision=revision,
        attempt=attempt,
        required=required,
        state=state,
        detail=stderr,
    )


def aggregate_check(observations: Iterable[Observation], *, revision: str, check_id: str,
                    required: bool) -> dict:
    scoped = sorted(
        [o for o in observations if o.revision == revision and o.check_id == check_id],
        key=lambda o: o.attempt,
    )
    if not scoped:
        return {"check_id": check_id, "revision": revision, "required": required,
                "state": "NOT_RUN", "observations": []}

    states = [o.state for o in scoped]
    concrete = {s for s in states if s not in {"NOT_RUN", "WAIVED"}}

    # Contradictory pass/fail evidence on the same revision is flaky. A later
    # pass cannot erase the contradiction; a new revision is the resolution boundary.
    if "PASS" in concrete and "FAIL" in concrete:
        state = "FLAKY"
    elif "INCONCLUSIVE" in concrete:
        state = "INCONCLUSIVE"
    elif "UNAVAILABLE" in concrete:
        state = "UNAVAILABLE"
    elif "FAIL" in concrete:
        state = "FAIL"
    elif concrete == {"PASS"}:
        state = "PASS"
    elif any(o.state == "WAIVED" and o.waiver_authorized for o in scoped):
        state = "WAIVED"
    else:
        state = "NOT_RUN"

    return {
        "check_id": check_id,
        "revision": revision,
        "required": required,
        "state": state,
        "observations": [asdict(o) for o in scoped],
    }


def synthesize(observations: Iterable[Observation], *, revision: str,
               required_checks: Iterable[str], optional_checks: Iterable[str] = ()) -> dict:
    obs = list(observations)
    checks = []
    for check_id in sorted(set(required_checks)):
        checks.append(aggregate_check(obs, revision=revision, check_id=check_id, required=True))
    for check_id in sorted(set(optional_checks)):
        checks.append(aggregate_check(obs, revision=revision, check_id=check_id, required=False))

    required_states = [c["state"] for c in checks if c["required"]]
    if not required_states:
        overall = "NOT_RUN"
    elif "FLAKY" in required_states:
        overall = "FLAKY"
    elif "INCONCLUSIVE" in required_states:
        overall = "INCONCLUSIVE"
    elif "UNAVAILABLE" in required_states:
        overall = "UNAVAILABLE"
    elif "FAIL" in required_states:
        overall = "FAIL"
    elif "NOT_RUN" in required_states:
        overall = "NOT_RUN"
    elif all(s == "PASS" for s in required_states):
        overall = "PASS"
    else:
        overall = "INCONCLUSIVE"

    return {"revision": revision, "state": overall, "checks": checks}


def release_gate(*, evidence: dict, current_revision: str, dirty: bool = False,
                 unresolved_material_confirmations: Iterable[str] = ()) -> dict:
    blockers = []
    if dirty:
        blockers.append("DIRTY_WORKTREE")
    if evidence.get("revision") != current_revision:
        blockers.append("STALE_EVIDENCE_REVISION")
    state = evidence.get("state", "NOT_RUN")
    if state != "PASS":
        blockers.append(f"REQUIRED_EVIDENCE_{state}")
    unresolved = sorted(set(unresolved_material_confirmations))
    if unresolved:
        blockers.append("UNRESOLVED_MATERIAL_CONFIRMATIONS:" + ",".join(unresolved))
    return {
        "release_readiness": "READY_FOR_RELEASE_REVIEW" if not blockers else "BLOCKED",
        "blockers": blockers,
        "evidence_state": state,
    }
