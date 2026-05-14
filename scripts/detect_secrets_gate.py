#!/usr/bin/env python3
"""detect-secrets gate — fail iff there are findings not in .secrets.baseline.

Usage:
    scripts/detect_secrets_gate.py [baseline-path]

The default baseline path is .secrets.baseline in the project root. Re-scans
git-tracked files plus untracked-but-not-ignored files with the local
detect-secrets plugin set, then computes the set difference: any
(file, hashed_secret) pair present in the current scan but absent from the
baseline is a NEW secret and triggers exit 1.

Exclusions (skip these paths during scan) are kept here as the single
source of truth — the same EXCLUDE pattern is used to (re)generate the
baseline so it stays consistent:
    detect-secrets scan \\
        --exclude-files "$(scripts/detect_secrets_gate.py --print-exclude)" \\
        > .secrets.baseline

The gate intentionally does NOT mutate .secrets.baseline. After remediating
a true positive (move secret out of code), the developer regenerates the
baseline with the command above.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


# SSOT exclusion pattern (regex alternation per detect-secrets --exclude-files).
# Covers: virtualenv, Galaxy collections, molecule ephemeral, runner results,
# coverage data, local Ansible runtime, binary drop artifacts, the baseline
# file itself, and the git dir.
EXCLUDE_PATTERN = (
    r"\.venv/|collections/|\.molecule/|test_results/"
    r"|\.ansible/|__pycache__/|\.git/|\.coverage|\.secrets\.baseline"
    r"|codex-[^/]+\.tar\.gz"
)
EXCLUDE_RE = re.compile(EXCLUDE_PATTERN)


def discover_scan_paths() -> list[str]:
    """Return git-tracked + untracked non-ignored files for local pre-merge use."""
    try:
        completed = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError:
        return []

    if completed.returncode != 0:
        return []

    paths: list[str] = []
    for raw_path in completed.stdout.split(b"\0"):
        if not raw_path:
            continue
        path = raw_path.decode("utf-8", errors="surrogateescape")
        if EXCLUDE_RE.search(path):
            continue
        if Path(path).is_file():
            paths.append(path)
    return paths


def load_findings(path: Path) -> set[tuple[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        (f, item["hashed_secret"])
        for f, items in data.get("results", {}).items()
        for item in items
    }


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] == "--print-exclude":
        print(EXCLUDE_PATTERN)
        return 0

    baseline = Path(argv[1] if len(argv) > 1 else ".secrets.baseline")
    if not baseline.is_file():
        print(f"FATAL: baseline not found at {baseline}", file=sys.stderr)
        print(
            "Generate via:\n"
            f"    detect-secrets scan --exclude-files '{EXCLUDE_PATTERN}' "
            "> .secrets.baseline",
            file=sys.stderr,
        )
        return 2

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as tmp:
        tmp_path = Path(tmp.name)
    try:
        scan_paths = discover_scan_paths()
        if not scan_paths:
            print("detect-secrets: clean (no git-tracked or unignored files to scan)")
            return 0

        with tmp_path.open("w") as out:
            completed = subprocess.run(
                ["detect-secrets", "scan", "--exclude-files", EXCLUDE_PATTERN, *scan_paths],
                stdout=out,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            rc = completed.returncode
        if rc != 0:
            print(f"FATAL: detect-secrets scan exited {rc}", file=sys.stderr)
            if completed.stderr:
                print(completed.stderr, file=sys.stderr, end="")
            return rc

        current = load_findings(tmp_path)
        known = load_findings(baseline)
        new = sorted(current - known)
        if new:
            print("FAIL: new secrets detected (not in baseline):", file=sys.stderr)
            for f, h in new:
                print(f"  {f}: {h[:16]}…", file=sys.stderr)
            print(
                f"\nRemediate (move the secret out of the code) then "
                f"regenerate the baseline:\n"
                f"    detect-secrets scan --exclude-files '{EXCLUDE_PATTERN}' "
                f"> .secrets.baseline",
                file=sys.stderr,
            )
            return 1

        print(
            f"detect-secrets: clean ({len(known)} known finding(s) in baseline; "
            f"{len(scan_paths)} file(s) scanned)"
        )
        return 0
    except FileNotFoundError:
        print("FATAL: detect-secrets executable not found in PATH", file=sys.stderr)
        return 2
    finally:
        tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
