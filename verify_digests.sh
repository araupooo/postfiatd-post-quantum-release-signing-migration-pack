#!/usr/bin/env bash
# Verify every file listed in SHA256SUMS. The manifest covers all pack
# files except itself, outputs/reproduce_selfcheck.log, and the four
# measurement logs (outputs/benchmark-pq.log,
# outputs/benchmark-classical.log, outputs/hybrid_bench.log,
# outputs/environment.txt): the manifest cannot verify itself; the
# self-check log embeds the digest verification output, so it cannot
# be part of its own digest set; and the measurement logs contain
# rates that vary between runs, so they are verified structurally by
# scripts/check_measurements.py instead (see docs/REPRODUCTION.md).
# The self-check log is verified by re-running reproduce.sh: a fresh
# run must regenerate it byte-identically (same SHA-256).
# Run from the pack root.
set -e
cd "$(dirname "$0")"
sha256sum -c SHA256SUMS
