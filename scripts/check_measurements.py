#!/usr/bin/env python3
"""check_measurements.py — structural check of the measurement logs.

The measurement logs (outputs/benchmark-pq.log,
outputs/benchmark-classical.log, outputs/hybrid_bench.log) contain
rates that vary between runs, so they are NOT covered by SHA256SUMS
and are NOT copied into outputs/reproduce_selfcheck.log. This script
is the reproducibility check for them: it verifies that every expected
algorithm block is present, every control passed, every measured
length equals the parameter table in data/algorithm_params.json, and
every log ends with result: OK. It prints only PASS/FAIL lines (no
measured numbers), so its output is deterministic.

Usage: python3 scripts/check_measurements.py
  Exit 0 when every structural check passes.
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
    by_display = {a["display"]: a for a in params["algorithms"]}

    failures = 0
    log("== measurement logs structural check ==")
    logs_dir = os.environ.get("MEASUREMENT_OUTDIR",
                              os.path.join(PACK, "outputs"))

    # --- PQ benchmark log ---
    pq_path = os.path.join(logs_dir, "benchmark-pq.log")
    if not os.path.exists(pq_path):
        log("FAIL: benchmark-pq.log is missing")
        failures += 1
        pq = ""
    else:
        with open(pq_path) as f:
            pq = f.read()
    for display in ("ML-DSA-44", "ML-DSA-65", "ML-DSA-87",
                    "SLH-DSA-SHA2-128s", "SLH-DSA-SHA2-128f"):
        block = f"--- {display} ---" in pq
        log(f"step: pq block {display} (32-byte message) present: "
            f"{'PASS' if block else 'FAIL'}")
        if not block:
            failures += 1
    for display in ("ML-DSA-44", "SLH-DSA-SHA2-128f"):
        block = f"--- {display} (2048-byte message) ---" in pq
        log(f"step: pq block {display} (2048-byte message) present: "
            f"{'PASS' if block else 'FAIL'}")
        if not block:
            failures += 1
    # Lengths: every length_* line must equal the parameter table.
    for m in re.finditer(
            r"algorithm: (\S+)\n(?:.*\n)*?length_public_key: (\d+)\n"
            r"length_secret_key: (\d+)\nlength_signature: (\d+)", pq):
        liboqs_name, pk, sk, sig = m.groups()
        display = next((a["display"] for a in params["algorithms"]
                        if a["liboqs_name"] == liboqs_name), None)
        if display is None:
            log(f"FAIL: unknown liboqs algorithm in pq log: {liboqs_name}")
            failures += 1
            continue
        want = by_display[display]
        ok = (int(pk) == want["public_key_bytes"] and
              int(sk) == want["secret_key_bytes"] and
              int(sig) == want["signature_bytes"])
        log(f"step: measured lengths {display}: pk {pk} sk {sk} sig "
            f"{sig} (expected {want['public_key_bytes']}/"
            f"{want['secret_key_bytes']}/{want['signature_bytes']}): "
            f"{'PASS' if ok else 'FAIL'}")
        if not ok:
            failures += 1
    # Controls: every block must have both controls PASS.
    n_valid = pq.count("control_valid_signature_verifies: PASS")
    n_tamper = pq.count("control_tampered_signature_rejected: PASS")
    log(f"step: valid-signature controls PASS: {n_valid} blocks "
        f"(expected 7): {'PASS' if n_valid == 7 else 'FAIL'}")
    log(f"step: tampered-signature controls PASS: {n_tamper} blocks "
        f"(expected 7): {'PASS' if n_tamper == 7 else 'FAIL'}")
    if n_valid != 7 or n_tamper != 7:
        failures += 1
    n_ok = pq.count("result: OK")
    log(f"step: pq log result OK lines: {n_ok} (expected 7): "
        f"{'PASS' if n_ok == 7 else 'FAIL'}")
    if n_ok != 7:
        failures += 1

    # --- Classical benchmark log ---
    cl_path = os.path.join(logs_dir, "benchmark-classical.log")
    if not os.path.exists(cl_path):
        log("FAIL: benchmark-classical.log is missing")
        failures += 1
        cl = ""
    else:
        with open(cl_path) as f:
            cl = f.read()
    for alg in ("ed25519", "ecdsap256"):
        present = alg in cl
        log(f"step: classical block {alg} present: "
            f"{'PASS' if present else 'FAIL'}")
        if not present:
            failures += 1
    # OpenSSL speed prints a "sign/s" and "verify/s" column header.
    for marker in ("sign/s", "verify/s"):
        present = marker in cl
        log(f"step: classical log contains '{marker}' column: "
            f"{'PASS' if present else 'FAIL'}")
        if not present:
            failures += 1

    # --- Hybrid benchmark log ---
    hy_path = os.path.join(logs_dir, "hybrid_bench.log")
    if not os.path.exists(hy_path):
        log("FAIL: hybrid_bench.log is missing")
        failures += 1
        hy = ""
    else:
        with open(hy_path) as f:
            hy = f.read()
    for display in ("ML-DSA-44", "SLH-DSA-SHA2-128f"):
        present = f"--- hybrid: Ed25519 + {display} ---" in hy
        log(f"step: hybrid block Ed25519 + {display} present: "
            f"{'PASS' if present else 'FAIL'}")
        if not present:
            failures += 1
    for control in ("C-1", "C-2", "C-3", "C-4", "C-5"):
        count = hy.count(f"control {control}: PASS")
        log(f"step: hybrid control {control} PASS in both blocks: "
            f"{count} (expected 2): {'PASS' if count == 2 else 'FAIL'}")
        if count != 2:
            failures += 1
    if "result: OK" not in hy:
        log("FAIL: hybrid log does not end with result: OK")
        failures += 1
    else:
        log("step: hybrid log ends with result: OK: PASS")
    # Ed25519 signature length measured by EVP must be 64.
    ed_lens = re.findall(r"ed25519_signature_len: (\d+)", hy)
    for length in ed_lens:
        ok = int(length) == 64
        log(f"step: measured Ed25519 signature length {length} "
            f"(expected 64): {'PASS' if ok else 'FAIL'}")
        if not ok:
            failures += 1

    if failures:
        log(f"result: FAILED ({failures} checks failed)")
        return 1
    log("result: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
