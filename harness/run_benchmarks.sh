#!/bin/sh
# run_benchmarks.sh — build liboqs (if needed), compile the harnesses,
# run the post-quantum, classical, and hybrid benchmarks, and write the
# unedited output to outputs/benchmark-pq.log,
# outputs/benchmark-classical.log, and outputs/hybrid_bench.log.
# Single-threaded throughout. Total runtime a few minutes.
#
# liboqs source: LIBOQS_SRC, or ~/liboqs when it exists and its HEAD is
# the pinned 0.14.0 commit 94b421ebb82405c843dba4e9aa521a56ee5a333d,
# otherwise a fresh clone of tag 0.14.0 into .deps/liboqs (network).
# The build directory is LIBOQS_BUILD_DIR, default $LIBOQS_SRC/build.
# Build progress goes to stdout only; the logs contain only the
# measurement blocks (no timestamps), so the logs are stable apart from
# the measured rates themselves.
set -eu
cd "$(dirname "$0")/.."
PACK_DIR="$(pwd)"
PINNED_LIBOQS_COMMIT="94b421ebb82405c843dba4e9aa521a56ee5a333d"
OUTDIR="${MEASUREMENT_OUTDIR:-outputs}"

if [ -n "${LIBOQS_SRC:-}" ]; then
    LIBOQS_SRC_DIR="$LIBOQS_SRC"
elif [ -d "$HOME/liboqs" ] && [ "$(git -C "$HOME/liboqs" rev-parse HEAD 2>/dev/null || echo none)" = "$PINNED_LIBOQS_COMMIT" ]; then
    LIBOQS_SRC_DIR="$HOME/liboqs"
else
    LIBOQS_SRC_DIR="$PACK_DIR/.deps/liboqs"
    if [ ! -d "$LIBOQS_SRC_DIR" ]; then
        echo "liboqs not found locally; cloning tag 0.14.0..."
        git clone --depth 1 --branch 0.14.0 https://github.com/open-quantum-safe/liboqs.git "$LIBOQS_SRC_DIR"
    fi
fi
LIBOQS_BUILD="${LIBOQS_BUILD_DIR:-$LIBOQS_SRC_DIR/build}"
# Reuse an already-built library for this exact source tree when the
# default build directory has none (e.g. a previous local build in
# /tmp/liboqs/build); this only skips the build, it never skips the
# commit check above, and CI (fresh clone) always builds from source.
if [ ! -f "$LIBOQS_BUILD/lib/liboqs.a" ] && [ "$LIBOQS_SRC_DIR" = "$HOME/liboqs" ] && [ -f /tmp/liboqs/build/lib/liboqs.a ]; then
    LIBOQS_BUILD="/tmp/liboqs/build"
fi
echo "step: liboqs source: $LIBOQS_SRC_DIR"
echo "step: liboqs commit: $(git -C "$LIBOQS_SRC_DIR" rev-parse HEAD)"
if [ "$(git -C "$LIBOQS_SRC_DIR" rev-parse HEAD)" != "$PINNED_LIBOQS_COMMIT" ]; then
    echo "ERROR: liboqs HEAD is not the pinned 0.14.0 commit $PINNED_LIBOQS_COMMIT"
    exit 1
fi
if [ ! -f "$LIBOQS_BUILD/lib/liboqs.a" ]; then
    echo "step: building liboqs (one-time, a few minutes)..."
    cmake -S "$LIBOQS_SRC_DIR" -B "$LIBOQS_BUILD" -DOQS_BUILD_ONLY_LIB=ON -DCMAKE_BUILD_TYPE=Release -DOQS_DIST_BUILD=OFF
    cmake --build "$LIBOQS_BUILD" -j 2
fi
echo "step: liboqs library: $LIBOQS_BUILD/lib/liboqs.a"

mkdir -p "$OUTDIR"
cc -O2 -I"$LIBOQS_SRC_DIR/src" -I"$LIBOQS_BUILD/include" \
    harness/bench_sig.c -L"$LIBOQS_BUILD/lib" -loqs -lcrypto -o harness/bench_sig
cc -O2 -I"$LIBOQS_SRC_DIR/src" -I"$LIBOQS_BUILD/include" \
    harness/hybrid_bench.c -L"$LIBOQS_BUILD/lib" -loqs -lcrypto -o harness/hybrid_bench
echo "step: harnesses compiled"

LOG="$OUTDIR/benchmark-pq.log"
{
    echo "=== pq-signature benchmark run ==="
    echo "liboqs: 0.14.0 (open-quantum-safe/liboqs, tag 0.14.0, commit $PINNED_LIBOQS_COMMIT)"
    echo "message: fixed 32-byte vector (256-bit digest length, mirrors postfiatd sha512Half)"
    echo "threads: 1"
    echo "verify_budget_sec: 5"
    echo "sign_budget_sec: 5 (capped at 25 sign iterations per algorithm)"
    echo ""
} > "$LOG"

# liboqs 0.14.0 does not register the FIPS 205 names (SLH-DSA-SHA2-128s);
# the same parameter sets are registered under their SPHINCS+ names.
# "DISPLAY|LIBOQS-NAME" pairs; the raw log keeps the true liboqs name.
for pair in "ML-DSA-44|ML-DSA-44" "ML-DSA-65|ML-DSA-65" "ML-DSA-87|ML-DSA-87" \
            "SLH-DSA-SHA2-128s|SPHINCS+-SHA2-128s-simple" "SLH-DSA-SHA2-128f|SPHINCS+-SHA2-128f-simple"; do
    display="${pair%%|*}"
    alg="${pair#*|}"
    echo "--- $display ---" >> "$LOG"
    echo "liboqs_algorithm_name: $alg" >> "$LOG"
    ./harness/bench_sig "$alg" 5 5 >> "$LOG" 2>&1 || {
        echo "result: BENCHMARK_FAILED for $display ($alg)" >> "$LOG"
        echo "FAILED: $display ($alg) (see $LOG)"
    }
    echo "" >> "$LOG"
done

# Same algorithms over a 2048-byte release-manifest payload, for the two
# schemes the hybrid design uses, to show the message-size effect.
{
    echo "=== pq-signature benchmark, 2048-byte manifest payload ==="
    echo "message: fixed 2048-byte vector (release-manifest payload model)"
    echo ""
} >> "$LOG"
for pair in "ML-DSA-44|ML-DSA-44" "SLH-DSA-SHA2-128f|SPHINCS+-SHA2-128f-simple"; do
    display="${pair%%|*}"
    alg="${pair#*|}"
    echo "--- $display (2048-byte message) ---" >> "$LOG"
    echo "liboqs_algorithm_name: $alg" >> "$LOG"
    ./harness/bench_sig "$alg" 5 5 2048 >> "$LOG" 2>&1 || {
        echo "result: BENCHMARK_FAILED for $display ($alg, 2048-byte)" >> "$LOG"
        echo "FAILED: $display ($alg, 2048-byte) (see $LOG)"
    }
    echo "" >> "$LOG"
done
echo "wrote $LOG"

# Classical baseline (OpenSSL speed, no build needed).
sh harness/classical_speed.sh

# Hybrid dual-signature benchmark (Ed25519 + ML-DSA-44, Ed25519 + SLH-DSA-128f).
HLOG="$OUTDIR/hybrid_bench.log"
{
    echo "=== hybrid dual-signature benchmark ==="
    echo "liboqs: 0.14.0 (commit $PINNED_LIBOQS_COMMIT)"
    echo "classical half: Ed25519 via OpenSSL EVP"
    echo "manifest: fixed 2048-byte release-manifest payload"
    echo "threads: 1"
    echo "verify_budget_sec: 5"
    echo "sign_budget_sec: 5 (capped at 50 sign iterations per hybrid)"
    echo ""
} > "$HLOG"
./harness/hybrid_bench 5 5 >> "$HLOG" 2>&1 || {
    echo "result: HYBRID_BENCHMARK_FAILED" >> "$HLOG"
    echo "FAILED: hybrid benchmark (see $HLOG)"
}
echo "wrote $HLOG"
