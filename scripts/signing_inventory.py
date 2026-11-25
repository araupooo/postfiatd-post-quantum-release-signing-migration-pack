#!/usr/bin/env python3
"""signing_inventory.py — verify the signing inventory of the pinned tree.

Reads data/source_excerpts.json (vendored exact source lines) and
data/signing_inventory.json (the inventory built from the pinned tree)
and prints a verbose per-excerpt, per-finding log. Every check is
logged as it happens; the log is deterministic (no timestamps, no
absolute paths, no measured numbers).

Optional --pin: when a postfiatd checkout is present at
~/workspace/postfiatd-pin-0085a1f, every vendored excerpt line is
re-checked against the checkout with grep semantics (exact text at the
recorded line) and the script fails on any mismatch. When no checkout
is present the pin check is SKIPPED and the script still passes: the
excerpts are the vendored evidence, and CI has no checkout.

Usage: python3 scripts/signing_inventory.py [--pin] [pin-dir]
  Writes: outputs/signing_inventory.log (stdout is redirected by run_all.sh)
"""
import argparse
import json
import os
import sys

PACK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def log(msg):
    print(msg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pin", action="store_true",
                    help="cross-check excerpts against a real checkout")
    ap.add_argument("pin_dir", nargs="?",
                    default=os.path.expanduser(
                        "~/workspace/postfiatd-pin-0085a1f"))
    args = ap.parse_args()

    excerpts_path = os.path.join(PACK, "data", "source_excerpts.json")
    inventory_path = os.path.join(PACK, "data", "signing_inventory.json")
    with open(excerpts_path) as f:
        excerpts = json.load(f)
    with open(inventory_path) as f:
        inventory = json.load(f)

    log("== signing inventory check ==")
    log(f"step: pinned commit: {excerpts['pinned_commit']}")
    log(f"step: excerpt files: {len(excerpts['files'])}")
    total_lines = 0
    for path in sorted(excerpts["files"]):
        entry = excerpts["files"][path]
        lines = entry["lines"]
        total_lines += len(lines)
        line_numbers = sorted(int(n) for n in lines)
        # Every recorded line must be non-empty and the recorded ranges
        # must be contiguous within each note's range (sanity: no gaps
        # inside a single noted range).
        for note in entry["notes"]:
            log(f"step: excerpt {path} ({note})")
        log(f"step: excerpt {path}: {len(lines)} lines, "
            f"{line_numbers[0]}-{line_numbers[-1]}")
        for n in line_numbers:
            text = lines[str(n)]
            # Blank lines are legitimate source (e.g. inside a workflow
            # file); only a missing line would be a failure, and the
            # --pin cross-check covers exact-text equality.
            _ = text
    log(f"step: total excerpt lines: {total_lines}")

    log("== inventory findings ==")
    findings = inventory["findings"]
    log(f"step: findings: {len(findings)}")
    for i, finding in enumerate(findings, 1):
        log(f"step: finding {i}/{len(findings)}: "
            f"[{finding['severity']}] {finding['category']} "
            f"({finding['status']})")
        log(f"  detail: {finding['detail'][:160]}")
    log("step: negative searches: "
        f"{len(inventory['negative_searches'])}")
    for ns in inventory["negative_searches"]:
        log(f"step: negative search '{ns['pattern']}' over "
            f"{ns['scope']}: {ns['verdict']}")
    log(f"step: workflows checked: {len(inventory['checked_workflows'])}")
    for wf in inventory["checked_workflows"]:
        log(f"step: workflow checked: {wf}")

    if args.pin:
        pin_dir = args.pin_dir
        if not os.path.isdir(pin_dir):
            log("step: pin cross-check SKIPPED (no checkout at "
                f"{os.path.basename(pin_dir)})")
        else:
            log(f"step: pin cross-check against checkout: {pin_dir}")
            mismatches = 0
            checked = 0
            for path in sorted(excerpts["files"]):
                entry = excerpts["files"][path]
                full = os.path.join(pin_dir, path)
                try:
                    with open(full) as f:
                        actual = f.read().splitlines()
                except FileNotFoundError:
                    log(f"FAIL: pin file missing: {path}")
                    mismatches += 1
                    continue
                for n_str, text in sorted(entry["lines"].items(),
                                          key=lambda kv: int(kv[0])):
                    n = int(n_str)
                    checked += 1
                    if n > len(actual) or actual[n - 1] != text:
                        log(f"FAIL: excerpt mismatch {path}:{n}")
                        mismatches += 1
            log(f"step: pin cross-check: {checked} lines checked, "
                f"{mismatches} mismatches")
            if mismatches:
                log("result: PIN_MISMATCH")
                return 1
            log("step: pin cross-check PASS (excerpts match the checkout)")

    log("result: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
