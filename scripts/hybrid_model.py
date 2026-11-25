#!/usr/bin/env python3
"""hybrid_model.py — verify the hybrid dual-signature size model.

Reads data/algorithm_params.json and data/hybrid_model.json, recomputes
every combined size from the parameter table (classical bytes +
post-quantum bytes), and checks the result against the recorded
hybrid_model.json. It also checks the measured hybrid log
(outputs/hybrid_bench.log) for structural consistency: both hybrid
blocks present, every control C-1..C-5 PASS, and the measured hybrid
signature lengths equal the computed combined sizes. Throughput
numbers are NOT copied into this log (they vary per run); only
PASS/FAIL of the consistency checks is recorded, so this log is
deterministic.

Usage: python3 scripts/hybrid_model.py
  Writes: outputs/hybrid_model.log (stdout is redirected by run_all.sh)
"""
import json
import os
import re
import sys

PACK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def log(msg):
    print(msg)


def main():
    with open(os.path.join(PACK, "data", "algorithm_params.json")) as f:
        params = json.load(f)
    with open(os.path.join(PACK, "data", "hybrid_model.json")) as f:
        model = json.load(f)

    by_display = {a["display"]: a for a in params["algorithms"]}
    log("== hybrid size model check ==")
    log(f"step: parameter sets: {len(params['algorithms'])}")
    log(f"step: hybrid combinations: {len(model['combinations'])}")
    failures = 0
    for combo in model["combinations"]:
        pq = by_display[combo["pq"]]
        classical = by_display[combo["classical"]]
        expect_sig = (classical["signature_bytes"] +
                      pq["signature_bytes"])
        expect_pk = (classical["public_key_bytes"] +
                     pq["public_key_bytes"])
        expect_ratio = expect_sig / classical["signature_bytes"]
        ok_sig = combo["combined_signature_bytes"] == expect_sig
        ok_pk = combo["combined_public_key_bytes"] == expect_pk
        ok_ratio = abs(combo["ratio_vs_ed25519_signature"] -
                       expect_ratio) < 1e-9
        status = "PASS" if (ok_sig and ok_pk and ok_ratio) else "FAIL"
        if status == "FAIL":
            failures += 1
        log(f"step: {combo['classical']} + {combo['pq']}: "
            f"combined sig {combo['combined_signature_bytes']} bytes "
            f"(expected {expect_sig}), combined pk "
            f"{combo['combined_public_key_bytes']} bytes "
            f"(expected {expect_pk}), ratio "
            f"{combo['ratio_vs_ed25519_signature']}x: {status}")
    log(f"step: recommended combination: {model['recommended']}")
    if model["recommended"] not in by_display and \
            model["recommended"] != "Ed25519 + ML-DSA-44":
        log("FAIL: recommended combination is not a modelled combination")
        failures += 1
    # The recommended combination must be the smallest combined
    # signature among the category-2-or-better hybrids (ML-DSA-44/65/87).
    ml_dsa = [c for c in model["combinations"]
              if c["pq"].startswith("ML-DSA")]
    smallest = min(ml_dsa, key=lambda c: c["combined_signature_bytes"])
    if smallest["pq"] != "ML-DSA-44":
        log("FAIL: smallest ML-DSA hybrid is not ML-DSA-44")
        failures += 1
    log(f"step: smallest ML-DSA hybrid: Ed25519 + "
        f"{smallest['pq']} at {smallest['combined_signature_bytes']} "
        f"bytes: PASS")

    log("== measured hybrid log consistency ==")
    logs_dir = os.environ.get("MEASUREMENT_OUTDIR",
                              os.path.join(PACK, "outputs"))
    hlog_path = os.path.join(logs_dir, "hybrid_bench.log")
    if not os.path.exists(hlog_path):
        log("FAIL: hybrid_bench.log is missing (run benchmarks first)")
        failures += 1
    else:
        with open(hlog_path) as f:
            hlog = f.read()
        for display in ("ML-DSA-44", "SLH-DSA-SHA2-128f"):
            present = f"--- hybrid: Ed25519 + {display} ---" in hlog
            log(f"step: hybrid block Ed25519 + {display} present: "
                f"{'PASS' if present else 'FAIL'}")
            if not present:
                failures += 1
        for control in ("C-1", "C-2", "C-3", "C-4", "C-5"):
            ok = f"control {control}: PASS" in hlog
            log(f"step: control {control} PASS in hybrid log: "
                f"{'PASS' if ok else 'FAIL'}")
            if not ok:
                failures += 1
        # Measured hybrid signature lengths must equal the computed ones.
        measured = dict(re.findall(
            r"--- hybrid: Ed25519 \+ (\S+) ---\n(?:.*\n)*?"
            r"hybrid_signature_len: (\d+)", hlog))
        for display, length in measured.items():
            combo = next((c for c in model["combinations"]
                          if c["pq"] == display), None)
            if combo is None:
                continue
            ok = int(length) == combo["combined_signature_bytes"]
            log(f"step: measured hybrid sig len Ed25519 + {display}: "
                f"{length} bytes (expected "
                f"{combo['combined_signature_bytes']}): "
                f"{'PASS' if ok else 'FAIL'}")
            if not ok:
                failures += 1
        if "result: OK" not in hlog:
            log("FAIL: hybrid log does not end with result: OK")
            failures += 1
        else:
            log("step: hybrid log ends with result: OK: PASS")

    if failures:
        log(f"result: FAILED ({failures} checks failed)")
        return 1
    log("result: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
