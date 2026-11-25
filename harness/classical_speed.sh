#!/bin/sh
# classical_speed.sh — classical signature baseline on the same box,
# using the system OpenSSL speed test (no build needed). Appends
# unedited output to outputs/benchmark-classical.log. Single-process
# (no -multi flag), 5 seconds per algorithm.
#
# Ed25519 is what postfiatd uses for Ed25519 keys
# (src/libxrpl/protocol/SecretKey.cpp:263-266, 64-byte signature).
# ECDSA P-256 stands in for the secp256k1 ECDSA path: same ECDSA
# construction over a 256-bit prime curve, different curve. secp256k1
# itself is NOT measured here; see docs/FAILURE_MODES.md.
set -eu
cd "$(dirname "$0")/.."
OUTDIR="${MEASUREMENT_OUTDIR:-outputs}"
LOG="$OUTDIR/benchmark-classical.log"
mkdir -p "$OUTDIR"
{
    echo "=== classical signature baseline (OpenSSL speed) ==="
    echo "openssl: $(openssl version)"
    echo "command: openssl speed -elapsed -seconds 5 ed25519 ecdsap256"
    echo "note: Ed25519 is what postfiatd uses for Ed25519 keys"
    echo "      (SecretKey.cpp:263-266, 64-byte signature)."
    echo "      ECDSA P-256 stands in for the secp256k1 ECDSA path"
    echo "      (same construction, different 256-bit curve)."
    echo "      secp256k1 itself is NOT measured here."
    echo ""
} > "$LOG"
openssl speed -elapsed -seconds 5 ed25519 ecdsap256 >> "$LOG" 2>&1
echo "wrote $LOG"
