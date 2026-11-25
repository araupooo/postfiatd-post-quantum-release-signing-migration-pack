# Claim index — post-quantum release-signing migration assessment

Every substantive claim in this pack carries one label:

- **[MEASURED]** — produced by a script in this pack, with the unedited
  output log cited by file and line. Re-running `bash reproduce.sh`
  regenerates the log; the numbers will differ slightly (rates vary),
  the structure and the lengths will not.
- **[SPEC]** — a value from a published standard, cited to the standard
  (FIPS 204 Table 2, FIPS 205 Table 2, RFC 8032, SEC 1), cross-checked
  against the liboqs 0.14.0 headers and, where the harness prints it,
  against a measured length.
- **[SIMULATED]** — the output of a model or a design in this pack
  (size arithmetic, stage plan), computed from measured/spec values.
  The model is deterministic and re-runnable; the conclusion is only
  as good as its inputs.
- **[UNSUPPORTED]** — a claim the pack cannot establish from any
  primary source. It is recorded so the gap is visible, not hidden.
  Nothing labelled [UNSUPPORTED] is presented as fact anywhere else
  in this pack.

Findings (R-01...) live in `docs/REMEDIATION.md`, not in this file.

## Measured claims

| ID | Claim | Source |
|----|-------|--------|
| M-01 | ML-DSA-44: pk 1,312 B, sk 2,560 B, sig 2,420 B; verify 27,440.658 ops/s, sign ≥ 9,459.385 ops/s, keypair 29,466.451 ops/s (32-byte message, 1 thread) | outputs/benchmark-pq.log:8-35 (lengths :14-17, verify :27, sign :31) |
| M-02 | ML-DSA-65: pk 1,952 B, sk 4,032 B, sig 3,309 B; verify 17,428.242 ops/s, sign ≥ 5,679.135 ops/s, keypair 16,783.733 ops/s (32-byte message, 1 thread) | outputs/benchmark-pq.log:39-66 |
| M-03 | ML-DSA-87: pk 2,592 B, sk 4,896 B, sig 4,627 B; verify 11,574.400 ops/s, sign ≥ 5,951.990 ops/s, keypair 11,503.297 ops/s (32-byte message, 1 thread) | outputs/benchmark-pq.log:70-97 |
| M-04 | SLH-DSA-SHA2-128s: pk 32 B, sk 64 B, sig 7,856 B; verify 2,751.257 ops/s, sign 3.648 ops/s, keypair 28.445 ops/s (32-byte message, 1 thread) | outputs/benchmark-pq.log:101-128 |
| M-05 | SLH-DSA-SHA2-128f: pk 32 B, sk 64 B, sig 17,088 B; verify 992.384 ops/s, sign ≥ 75.228 ops/s, keypair 1,776.489 ops/s (32-byte message, 1 thread) | outputs/benchmark-pq.log:131-158 |
| M-06 | ML-DSA-44 over a 2,048-byte manifest payload: verify 21,614.381 ops/s (vs 27,440.658 for a 32-byte digest), sign ≥ 7,679.484 ops/s | outputs/benchmark-pq.log:165-191 |
| M-07 | SLH-DSA-SHA2-128f over a 2,048-byte manifest payload: verify 1,007.296 ops/s (vs 992.384 for 32 bytes), sign ≥ 73.804 ops/s | outputs/benchmark-pq.log:196-222 |
| M-08 | Ed25519 (OpenSSL speed, 5 s): sign 19,259.4/s, verify 6,181.2/s | outputs/benchmark-classical.log:20-23 |
| M-09 | ECDSA P-256 (OpenSSL speed, 5 s): sign 29,549.4/s, verify 10,292.6/s | outputs/benchmark-classical.log:20-23 |
| M-10 | Hybrid Ed25519 + ML-DSA-44 over a 2,048-byte manifest: combined sig 2,484 B, combined pk 1,344 B; verify 5,036.280 ops/s, sign ≥ 6,377.754 ops/s; controls C-1..C-5 all PASS | outputs/hybrid_bench.log:9-52 (sig len :22, controls :29-42, verify :46, sign :50) |
| M-11 | Hybrid Ed25519 + SLH-DSA-SHA2-128f over a 2,048-byte manifest: combined sig 17,152 B, combined pk 64 B; verify 857.440 ops/s, sign 75.229 ops/s; controls C-1..C-5 all PASS | outputs/hybrid_bench.log:54-93 (sig len :63, controls :70-83, verify :87, sign :91) |
| M-12 | Ed25519 signature length is 64 bytes as produced by OpenSSL EVP | outputs/hybrid_bench.log:20,61 (`ed25519_signature_len: 64`) |
| M-13 | A valid signature verifies and a one-byte-tampered signature is rejected, for all 5 PQ parameter sets at both message sizes (7 blocks) | outputs/benchmark-pq.log:22-23,53-54,84-85,115-116,145-146,179-180,210-211 |
| M-14 | A hybrid signature verifies only when both halves verify; tampering either half rejects; stripping either half rejects by length check (controls C-1..C-5, both hybrids) | outputs/hybrid_bench.log:29-42,70-83 |
| M-15 | ML-DSA-44 verify is consistently slower for a 2,048-byte message than for a 32-byte digest across three runs: 18,246–21,614 ops/s vs 27,440–27,652 ops/s. Signing shows no consistent message-size effect (8,322–10,690 ops/s at 32 bytes vs 7,679–9,589 ops/s at 2,048 bytes, overlapping). | outputs/benchmark-pq.log:27,184; confirmation re-runs recorded in docs/ALGORITHM_COMPARISON.md (not in the vendored log) |
| M-16 | No release-signing step exists in any of the ten pinned workflow files: grep for cosign/sigstore/attest/gpg/sha256sum/checksum/slsa returns no release-signing step | data/signing_inventory.json (negative_searches); outputs/signing_inventory.log |
| M-17 | The testnet release job publishes a GitHub release with `gh release create` from generated notes and nothing else (no signature, attestation, or checksum) | .github/workflows/testnet-build.yml:44-71 (excerpt data/source_excerpts.json) |
| M-18 | Docker images are built and pushed with mutable `-latest` tags and no signing step | .github/workflows/build.yml:71-90 (excerpt data/source_excerpts.json) |
| M-19 | An in-tree review document defers image signing (Cosign), container scanning, and SBOM to "Phase 2 or mainnet" | docs/dynamic-unl/reviews/FeedbackAnalysis_Codex54.md:335,341 (excerpt data/source_excerpts.json) |
| M-20 | postfiatd signs with Ed25519 (64-byte signature) and secp256k1 ECDSA (sha512Half digest, RFC6979 nonce, DER serialization) in-tree; verification enforces ECDSA canonicality with low-S normalization and Ed25519 canonicality with a 0xED key-prefix strip | src/libxrpl/protocol/SecretKey.cpp:230-290; src/libxrpl/protocol/PublicKey.cpp:240-316 (excerpts data/source_excerpts.json) |
| M-21 | Validator manifests are protected against rollback by strict sequence monotonicity on apply, and master-key revocation is sequence == UINT32_MAX | src/xrpld/app/misc/detail/Manifest.cpp:196-216,226-242,405-448 (excerpts data/source_excerpts.json) |
| M-22 | ValidatorList v2 messages only include VLs with sequence larger than the peer's | src/xrpld/app/misc/detail/ValidatorList.cpp:620-648 (excerpt data/source_excerpts.json) |
| M-23 | All 367 vendored excerpt lines match the pinned checkout byte for byte (0 mismatches) | `python3 scripts/signing_inventory.py --pin` run (367 lines checked, 0 mismatches); recorded in docs/REPRODUCTION.md. The vendored outputs/signing_inventory.log is the no-pin run, which is what `bash reproduce.sh` regenerates; the pin cross-check is a manual verification step, not part of reproduce.sh. |

## Specification claims

| ID | Claim | Source |
|----|-------|--------|
| S-01 | FIPS 204 Table 2: ML-DSA-44 pk 1,312 / sk 2,560 / sig 2,420; ML-DSA-65 pk 1,952 / sk 4,032 / sig 3,309; ML-DSA-87 pk 2,592 / sk 4,896 / sig 4,627 (bytes) | NIST FIPS 204 (Aug 2024) Table 2; repeated in RFC 9964 Table 1; liboqs src/sig/ml_dsa/sig_ml_dsa.h:9-37 |
| S-02 | FIPS 205 Table 2: SLH-DSA-SHA2-128s pk 32 / sk 64 / sig 7,856; SLH-DSA-SHA2-128f pk 32 / sk 64 / sig 17,088 (bytes); categories 1 | NIST FIPS 205 (Aug 2024) Table 2; liboqs src/sig/sphincs/sig_sphincs.h:9-24 |
| S-03 | NIST security categories: ML-DSA-44 category 2, ML-DSA-65 category 3, ML-DSA-87 category 5; SLH-DSA-128s/128f category 1 | FIPS 204 Table 1; FIPS 205 Table 2 |
| S-04 | Ed25519: 32-byte public key, 64-byte signature | RFC 8032 section 5.1.5; measured M-12 |
| S-05 | liboqs 0.14.0 does not register the FIPS 205 names; SLH-DSA-SHA2-128s is registered as SPHINCS+-SHA2-128s-simple (same parameter set) | liboqs src/sig/sig.h (no slh_dsa defines; sphincs defines at src/sig/sphincs/sig_sphincs.h) |
| S-06 | SLH-DSA is stateless (no per-signature state to manage) and rests only on hash-function security; ML-DSA rests on Module-LWE/Module-SIS lattice assumptions | FIPS 205 section 1; FIPS 204 section 1 |
| S-07 | ML-DSA signing in FIPS 204 is randomized (hedged) by default, with a deterministic variant defined | FIPS 204 section 5.3 / Algorithm 2 (randomized) and section 5.4 (deterministic) |

## Simulated claims (models and designs)

| ID | Claim | Source |
|----|-------|--------|
| D-01 | Hybrid combined sizes: Ed25519+ML-DSA-44 sig 2,484 B (38.8x Ed25519 alone); +ML-DSA-65 sig 3,373 B (52.7x); +ML-DSA-87 sig 4,691 B (73.3x); +SLH-DSA-128s sig 7,920 B (123.8x); +SLH-DSA-128f sig 17,152 B (268.0x). Arithmetic from M-01..M-05 and S-04. | data/hybrid_model.json; outputs/hybrid_model.log |
| D-02 | Recommended first hybrid: Ed25519 + ML-DSA-44 — smallest combined signature among category-2-or-better hybrids, fastest measured PQ signing/verification in this pack | data/hybrid_model.json (recommended); docs/HYBRID_DESIGN.md |
| D-03 | The staged migration plan (S0–S4, 15–30 weeks planning horizon for S0–S3) with gates as specified | data/migration_plan.json; outputs/migration_model.log |
| D-04 | Envelope framing overhead is tens of bytes (version + algorithm identifiers); excluded from the combined-size arithmetic | docs/HYBRID_DESIGN.md (design H-1) |
| D-05 | A release signed once a day with SLH-DSA-128s costs ~0.27 s of signing per release (3.648 sig/s), so signing speed is not a blocker for releases; it is a blocker only for high-frequency signing | M-04 arithmetic: 1 / 3.648 s per signature |
| D-06 | Verifying one hybrid Ed25519+ML-DSA-44 signature costs ~199 µs (5,036.280/s); verifying 1,000 release artifacts costs ~0.2 s of single-thread CPU | M-10 arithmetic |

## Unsupported claims (gaps, recorded not hidden)

| ID | Claim | Why it is unsupported |
|----|-------|----------------------|
| U-01 | The current release-signing mechanism of postfiatd (key holder, key storage, signing tool, verification procedure for operators) | Not observable from the pinned tree: no release-signing code, workflow step, or document describes it (M-16, M-17). If a manual step exists outside the tree, this pack cannot see it. |
| U-02 | Whether any published postfiatd release or Docker image has ever been signed, and with what key | Same as U-01; the tree contains no signature, checksum, or key record for any release. |
| U-03 | The cost (in wall-clock time, operator effort, or money) of the migration stages | Durations in data/migration_plan.json are planning estimates ([ESTIMATE]), not measured; no migration has been run. |
| U-04 | Whether ML-DSA or SLH-DSA will remain the recommended schemes (standards, CNSA 2.0 timelines, and IETF composite-signature work are still moving) | Standards status as of the pack date; see docs/SOURCES.md. Stage S4 exists for this reason. |
| U-05 | Performance of these schemes on the machines that actually build and verify postfiatd releases (CI runners, operator laptops) | Measurements are on this pack's machine only (outputs/environment.txt). Relative ordering is expected to hold; absolute rates will differ. |
| U-06 | Security of the hybrid design against a quantum adversary that breaks the classical half only (the design's AND-policy is argued in docs/HYBRID_DESIGN.md, not proven here) | No formal proof is attempted in this pack; the argument is a design rationale, not a theorem. |
