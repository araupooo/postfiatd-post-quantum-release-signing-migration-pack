# Post-quantum release-signing migration assessment for postfiatd

An evidence pack assessing the migration of postfiatd release
signing from classical signatures to hybrid classical +
post-quantum signatures (ML-DSA and SLH-DSA). Pinned postfiatd
revision: `0085a1ff885d6a446369cf73a4430f75af22be55` (main,
2026-10-10, version 1.0.9). Measurements use liboqs 0.14.0
(commit `94b421ebb82405c843dba4e9aa521a56ee5a333d`), single thread.

## Headline findings

- **Releases are published unsigned today.** The release job
  publishes a GitHub release with `gh release create` and nothing
  else — no signature, no attestation, no checksum. Docker images
  are pushed unsigned under mutable `-latest` tags, and image
  signing (Cosign) is explicitly deferred to "Phase 2 or mainnet"
  in an in-tree review document. The migration therefore starts
  with **stage S0: sign releases at all** (Ed25519), before any
  post-quantum work.
- **Recommended hybrid: Ed25519 + ML-DSA-44** (concatenated dual
  signature, both halves must verify). Combined signature 2,484
  bytes; signing ~157 µs, verification ~199 µs per release
  manifest. ML-DSA-44 verifies at 27,440.658 ops/s alone — faster
  than Ed25519 (6,181.2/s) on this machine.
- **SLH-DSA-128s signs at 3.648 ops/s** (274 ms per signature):
  usable for releases, unusable for anything high-frequency.
  SLH-DSA-128f is the conservative fallback (17,152-byte hybrid
  signature, ~13.3 ms signing).
- **Rollback protection exists for validator data, not for
  releases.** Manifests enforce strict sequence monotonicity and
  revocation via sequence == UINT32_MAX. The release process
  should copy that pattern (signed release manifest with a
  monotonic sequence), not re-invent it.
- **No release-signing code exists in the pinned tree.** The
  migration target is the release process (GitHub releases +
  Docker images), not an in-tree implementation. What the current
  release-signing mechanism is — key holder, storage, procedure —
  is not observable from the tree and is recorded as unsupported
  (U-01), not guessed.

Full findings: `docs/REMEDIATION.md` (2 HIGH, 4 MEDIUM, 3 LOW,
1 INFO). Full claim index: `docs/CLAIMS.md` (every claim labelled
[MEASURED], [SPEC], [SIMULATED], or [UNSUPPORTED]).

## Contents

```
README.md                  this file
SHA256SUMS                 digest manifest (see below)
verify_digests.sh          sha256sum -c SHA256SUMS
reproduce.sh               run every check, verify digests, write the self-check log
.github/workflows/ci.yml  runs reproduce.sh on ubuntu-latest + Python 3.12
data/
  algorithm_params.json    FIPS 204/205 sizes, cross-checked vs liboqs headers
  hybrid_model.json        hybrid combined sizes (arithmetic from the params)
  migration_plan.json      stages S0-S4 with gates (durations are estimates)
  postfiatd_pin.json       pinned postfiatd revision
  signing_inventory.json   signing inventory of the pinned tree (incl. negative searches)
  source_excerpts.json     367 exact source lines from the pinned checkout (9 files)
docs/
  CLAIMS.md                claim index (measured / spec / simulated / unsupported)
  SOURCES.md               every source and what it establishes
  ALGORITHM_COMPARISON.md  size + throughput tables with sources
  HYBRID_DESIGN.md         design H-1, rejected designs, threat model, downgrade analysis
  ROLLBACK_KEY_COMPROMISE.md  in-tree rollback mechanisms + proposed release procedure
  MIGRATION_PLAN.md        stages S0-S4, gates, compatibility matrix
  REMEDIATION.md           findings R-01..R-10
  REPRODUCTION.md          how to reproduce, what is digest-verified and what is not
  FAILURE_MODES.md         how this pack can be wrong
  DECISION_MEMO.md         recommendation in one page
harness/
  bench_sig.c              PQ signature benchmark (liboqs)
  hybrid_bench.c           concatenated dual-signature benchmark (OpenSSL Ed25519 + liboqs)
  classical_speed.sh       OpenSSL speed baseline (Ed25519, ECDSA P-256)
  environment.sh           stable environment facts (no timestamps)
  run_benchmarks.sh        build liboqs if needed, run all benchmarks
scripts/
  signing_inventory.py     verify excerpts + inventory (optional --pin cross-check)
  hybrid_model.py          recompute hybrid sizes, check measured hybrid log
  migration_model.py       check the migration plan's structure and arithmetic
  check_measurements.py    structural check of the measurement logs
  run_all.sh               run every check in order
outputs/
  environment.txt          measurement environment (stable facts)
  benchmark-pq.log         PQ benchmarks (5 sets at 32 B, 2 at 2,048 B)
  benchmark-classical.log  OpenSSL speed baseline
  hybrid_bench.log         hybrid benchmarks + controls C-1..C-5
  signing_inventory.log    inventory check (deterministic)
  hybrid_model.log         hybrid size model check (deterministic)
  migration_model.log      migration plan check (deterministic)
  reproduce_selfcheck.log  self-check log (deterministic; see below)
```

## Reproduce

```sh
bash reproduce.sh
```

Exit code 0 and `REPRODUCE OK` mean every check passed and every
vendored file matches its recorded SHA-256. Requirements: `bash`,
`python3` (3.12), `cc`, `cmake`, `git`, `openssl`, and network
access to clone liboqs tag 0.14.0 on first run. No postfiatd
checkout is needed. See `docs/REPRODUCTION.md`.

## A note on what is digest-verified

`SHA256SUMS` covers every pack file except itself,
`outputs/reproduce_selfcheck.log`, and the four measurement logs
(`outputs/benchmark-pq.log`, `outputs/benchmark-classical.log`,
`outputs/hybrid_bench.log`, `outputs/environment.txt`). The
self-check log is verified by byte-identical regeneration
(re-running `reproduce.sh` must produce the same SHA-256); the
measurement logs contain rates that vary per run, so they are
verified structurally by `scripts/check_measurements.py` instead
(every block present, every control PASS, every measured length
equal to the parameter table). `reproduce.sh` re-runs the
measurements into a scratch directory and does not overwrite the
vendored measurement logs — they are the recorded evidence from
the original run. See `docs/REPRODUCTION.md` and
`docs/FAILURE_MODES.md` (FM-10).

## Honest limits

- The current release-signing mechanism (key holder, storage,
  procedure) is not observable from the pinned tree and is not
  claimed here (U-01, U-02).
- Stage durations are planning estimates, not measured (U-03).
- Measurements are single-machine, single-thread figures; absolute
  rates will differ elsewhere (U-05).
- The hybrid envelope is specified in this pack, not implemented
  as a release tool (FM-05); the threat model is argued, not
  proven (U-06).
- secp256k1 itself is not measured (FM-03); P-256 stands in as
  the 256-bit ECDSA baseline.
