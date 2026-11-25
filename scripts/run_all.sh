#!/usr/bin/env bash
# run_all.sh — run every check in order and write the logs to outputs/.
# Deterministic checks (signing inventory, hybrid model, migration
# model) produce byte-identical logs across runs. Measurement logs
# (benchmark-pq, benchmark-classical, hybrid_bench, environment) vary
# per run in their measured rates only; they are checked structurally
# by scripts/check_measurements.py, not by digest.
# Usage: bash scripts/run_all.sh   (run from the pack root)
set -e
cd "$(dirname "$0")/.."
mkdir -p outputs
sh harness/environment.sh
python3 scripts/signing_inventory.py "$@" > outputs/signing_inventory.log
sh harness/run_benchmarks.sh
python3 scripts/hybrid_model.py > outputs/hybrid_model.log
python3 scripts/migration_model.py > outputs/migration_model.log
python3 scripts/check_measurements.py
echo "run_all: all checks passed"
