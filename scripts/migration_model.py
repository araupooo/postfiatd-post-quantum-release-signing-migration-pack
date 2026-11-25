#!/usr/bin/env python3
"""migration_model.py — verify the staged migration plan's arithmetic.

Reads data/migration_plan.json and prints a verbose per-stage log:
every stage has an id, a name, a duration estimate, a gate, and at
least one work item; stage ids are S0..S4 in order with no gaps; every
gate is non-empty; durations are labelled estimates. No measured
numbers are involved, so this log is deterministic.

Usage: python3 scripts/migration_model.py
  Writes: outputs/migration_model.log (stdout is redirected by run_all.sh)
"""
import json
import os
import sys

PACK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def log(msg):
    print(msg)


def main():
    with open(os.path.join(PACK, "data", "migration_plan.json")) as f:
        plan = json.load(f)

    log("== migration plan check ==")
    stages = plan["stages"]
    log(f"step: stages: {len(stages)}")
    failures = 0
    expected_ids = [f"S{i}" for i in range(len(stages))]
    actual_ids = [s["id"] for s in stages]
    if actual_ids != expected_ids:
        log(f"FAIL: stage ids {actual_ids} != expected {expected_ids}")
        failures += 1
    else:
        log(f"step: stage ids in order {', '.join(actual_ids)}: PASS")
    for s in stages:
        log(f"step: stage {s['id']} '{s['name']}': "
            f"duration estimate {s['duration_estimate_weeks']} weeks, "
            f"{len(s['work'])} work items")
        if not s["gate"].strip():
            log(f"FAIL: stage {s['id']} has an empty gate")
            failures += 1
        if not s["work"]:
            log(f"FAIL: stage {s['id']} has no work items")
            failures += 1
        if "estimate" not in s["duration_estimate_weeks"] and \
                "-" not in s["duration_estimate_weeks"] and \
                s["duration_estimate_weeks"] != "ongoing":
            log(f"FAIL: stage {s['id']} duration is not a range/ongoing "
                f"estimate: {s['duration_estimate_weeks']}")
            failures += 1
    # Total planning horizon (excluding the ongoing review stage).
    total_low, total_high = 0, 0
    for s in stages:
        d = s["duration_estimate_weeks"]
        if d == "ongoing":
            continue
        lo, hi = d.split("-")
        total_low += int(lo)
        total_high += int(hi)
    log(f"step: planning horizon S0-S3: {total_low}-{total_high} weeks "
        f"(estimates, not a commitment)")
    # Compatibility rule: the plan must never accept a stripped hybrid
    # envelope at or after the S2 cutover; check the S2 gate says so.
    s2 = next(s for s in stages if s["id"] == "S2")
    if "reject" not in s2["gate"].lower() or \
            "stripped" not in s2["gate"].lower():
        log("FAIL: stage S2 gate does not require rejecting a stripped "
            "envelope")
        failures += 1
    else:
        log("step: stage S2 gate requires rejecting stripped envelopes: "
            "PASS")
    # S0 must close the unsigned-release gap before any PQ work starts.
    s0 = next(s for s in stages if s["id"] == "S0")
    if "signature" not in " ".join(s0["work"]).lower():
        log("FAIL: stage S0 does not introduce release signing")
        failures += 1
    else:
        log("step: stage S0 introduces release signing first: PASS")
    if failures:
        log(f"result: FAILED ({failures} checks failed)")
        return 1
    log("result: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
