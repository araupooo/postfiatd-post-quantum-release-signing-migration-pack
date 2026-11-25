#!/bin/sh
# environment.sh — record the measurement environment.
# Only stable facts are recorded (no timestamps, no load averages, no
# CPU frequency, no free-memory figures), so outputs/environment.txt is
# byte-identical across runs on the same machine.
set -eu
cd "$(dirname "$0")/.."
OUTDIR="${MEASUREMENT_OUTDIR:-outputs}"
mkdir -p "$OUTDIR"
{
    echo "=== measurement environment ==="
    echo "os: $(grep '^PRETTY_NAME=' /etc/os-release | cut -d'"' -f2)"
    echo "kernel: $(uname -r)"
    echo "arch: $(uname -m)"
    echo "cpu_model: $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2 | sed 's/^ //')"
    echo "cpu_count_logical: $(nproc)"
    echo "cc: $(cc --version | head -1)"
    echo "cmake: $(cmake --version | head -1)"
    echo "openssl: $(openssl version)"
    echo "python3: $(python3 --version)"
    echo "git: $(git --version)"
    echo "liboqs_source: open-quantum-safe/liboqs tag 0.14.0"
    echo "liboqs_commit: 94b421ebb82405c843dba4e9aa521a56ee5a333d"
    echo "postfiatd_pin: 0085a1ff885d6a446369cf73a4430f75af22be55"
    echo "threads: 1"
} > "$OUTDIR/environment.txt"
echo "wrote $OUTDIR/environment.txt"
