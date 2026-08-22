#!/usr/bin/env python3
"""Executable RC-2 candidate used only by evaluation.

The canonical root `sef.py` is not modified. During fixture initialization this
wrapper delegates installation to the canonical runtime, then replaces only the
fixture's installed `.sef/sef.py` with this wrapper and keeps the canonical
runtime beside it as `sef_base.py`.

Candidate behavior: remove clearly bounded NON_GOAL clauses from request-derived
routing only. Actual Git-diff analysis remains canonical and independent.
"""
from __future__ import annotations
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
INSTALLED = HERE.parent.name == ".sef" and (HERE.parent / "sef_base.py").exists()
if INSTALLED:
    BASE_PATH = HERE.parent / "sef_base.py"
    SHADOW_PATH = HERE.parent / "rc2_shadow_polarity.py"
else:
    REPO_ROOT = HERE.parents[3]
    BASE_PATH = REPO_ROOT / "sef.py"
    SHADOW_PATH = HERE.parent / "shadow_polarity.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def requested_repo() -> Path:
    # SEF init/adopt/install syntax is `<cmd> [repo] [options]`.
    if len(sys.argv) >= 3 and not sys.argv[2].startswith("-"):
        return Path(sys.argv[2]).resolve()
    return Path(".").resolve()


def initialize_candidate() -> int:
    cp = subprocess.run(
        [sys.executable, str(BASE_PATH), *sys.argv[1:]],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if cp.stdout:
        sys.stdout.write(cp.stdout)
    if cp.stderr:
        sys.stderr.write(cp.stderr)
    if cp.returncode != 0:
        return cp.returncode

    dst = requested_repo() / ".sef"
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BASE_PATH, dst / "sef_base.py")
    shutil.copy2(SHADOW_PATH, dst / "rc2_shadow_polarity.py")
    shutil.copy2(HERE, dst / "sef.py")
    return 0


def positive_request_text(request: str, shadow):
    observation = shadow.annotate(request)
    kept = []
    suppressed = []
    for clause in observation.get("clauses", []):
        text = str(clause.get("clause") or "").strip()
        if not text:
            continue
        if clause.get("polarity") == "NON_GOAL":
            suppressed.append(text)
        else:
            kept.append(text)
    return "; ".join(kept), suppressed, observation


def run_candidate() -> int:
    base = load_module(BASE_PATH, "sef_rc2_candidate_base")
    shadow = load_module(SHADOW_PATH, "sef_rc2_shadow")
    original_request_change = base._request_change
    original_detected_ids = base._rc1_detected_ids

    def request_change(profile, request):
        filtered, suppressed, observation = positive_request_text(request, shadow)
        result = original_request_change(profile, filtered)
        result["summary"] = request
        if suppressed:
            result.setdefault("request_detection", []).append({
                "trigger": "RC2_POLARITY_FILTER",
                "reason": "bounded request non-goal excluded from request-derived routing",
                "source": "rc2_candidate",
                "suppressed_clauses": suppressed,
                "shadow_observation": observation,
            })
        return result

    def detected_ids(request):
        filtered, _, _ = positive_request_text(request, shadow)
        return original_detected_ids(filtered)

    # Only request-derived routing is patched. `assess()` / `verify()` actual-diff
    # detection is left untouched.
    base._request_change = request_change
    base._rc1_detected_ids = detected_ids
    return int(base.main())


def main() -> int:
    if not INSTALLED and len(sys.argv) > 1 and sys.argv[1] in {"init", "adopt", "install"}:
        return initialize_candidate()
    return run_candidate()


if __name__ == "__main__":
    raise SystemExit(main())
