#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    kind = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    git_dir = Path(".git")
    mode_path = git_dir / "sef-eval-mode"
    mode = mode_path.read_text(encoding="utf-8").strip() if mode_path.exists() else "pass"

    if kind != "unit":
        print(f"{kind}: pass")
        return 0

    if mode == "fail-critical":
        print("critical regression failure", file=sys.stderr)
        return 1

    if mode == "unavailable":
        print("required observability provider unavailable", file=sys.stderr)
        return 2

    if mode == "flaky":
        counter_path = git_dir / "sef-eval-flaky-count"
        try:
            count = int(counter_path.read_text(encoding="utf-8").strip())
        except Exception:
            count = 0
        count += 1
        counter_path.write_text(str(count), encoding="utf-8")
        if count % 2 == 0:
            print(f"flaky regression failure on observation {count}", file=sys.stderr)
            return 1
        print(f"flaky regression pass on observation {count}")
        return 0

    print("unit: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
