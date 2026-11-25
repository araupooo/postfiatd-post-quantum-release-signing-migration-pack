# Algorithm comparison — measured and specified

Machine: single thread, liboqs 0.14.0 (commit
`94b421ebb82405c843dba4e9aa521a56ee5a333d`), OpenSSL 3.0.13.
Full environment in `outputs/environment.txt`. All rates are
operations per second on one thread; the signing rates marked ≥ are
lower bounds (the harness caps signing at 25 iterations per
algorithm, 50 per hybrid, so the run stays short — see
`docs/FAILURE_MODES.md`).

## Size table (bytes)

Sizes are FIPS 204 Table 2 (ML-DSA) and FIPS 205 Table 2 (SLH-DSA),
cross-checked against the liboqs 0.14.0 headers
(`src/sig/ml_dsa/sig_ml_dsa.h:9-37`,
`src/sig/sphincs/sig_sphincs.h:9-24`) and against the measured
lengths printed by `harness/bench_sig.c`. All three agree byte for
byte. Classical sizes are RFC 8032 §5.1.5 (Ed25519) and SEC 1 (P-256).

| Algorithm | NIST category | Public key | Secret key | Signature |
|-----------|---------------|-----------:|-----------:|----------:|
| Ed25519 | — | 32 | 32 | 64 |
| ECDSA P-256 (raw r\|\|s) | — | 64 | 32 | 64 |
| ML-DSA-44 | 2 | 1,312 | 2,560 | 2,420 |
| ML-DSA-65 | 3 | 1,952 | 4,032 | 3,309 |
| ML-DSA-87 | 5 | 2,592 | 4,896 | 4,627 |
| SLH-DSA-SHA2-128s | 1 | 32 | 64 | 7,856 |
| SLH-DSA-SHA2-128f | 1 | 32 | 64 | 17,088 |

Note on names: liboqs 0.14.0 does not register the FIPS 205 names.
`SLH-DSA-SHA2-128s` is registered as `SPHINCS+-SHA2-128s-simple`
and `SLH-DSA-SHA2-128f` as `SPHINCS+-SHA2-128f-simple`; the
parameter sets are identical. The raw logs keep the true liboqs
names; this document uses the FIPS 205 names.

Note on P-256: postfiatd uses secp256k1 ECDSA, not P-256
(`src/libxrpl/protocol/SecretKey.cpp:269-290`, DER serialization
into a 72-byte buffer). P-256 is measured here only as the
OpenSSL-speed baseline for a 256-bit ECDSA; secp256k1 itself is
not measured (see `docs/FAILURE_MODES.md`).

## Throughput table — 32-byte message (a 256-bit digest, the length postfiatd verifies via sha512Half)

| Algorithm | Verify ops/s | Sign ops/s | Keypair ops/s |
|-----------|------------:|----------:|-------------:|
| Ed25519 (OpenSSL speed) | 6,181.2 | 19,259.4 | — |
| ECDSA P-256 (OpenSSL speed) | 10,292.6 | 29,549.4 | — |
| ML-DSA-44 | 27,440.658 | ≥ 9,459.385 | 29,466.451 |
| ML-DSA-65 | 17,428.242 | ≥ 5,679.135 | 16,783.733 |
| ML-DSA-87 | 11,574.400 | ≥ 5,951.990 | 11,503.297 |
| SLH-DSA-SHA2-128s | 2,751.257 | 3.648 | 28.445 |
| SLH-DSA-SHA2-128f | 992.384 | ≥ 75.228 | 1,776.489 |

Sources: `outputs/benchmark-pq.log` (ML-DSA-44 :27/:31, ML-DSA-65
:58/:62, ML-DSA-87 :89/:93, SLH-DSA-128s :120/:124, SLH-DSA-128f
:150/:154), `outputs/benchmark-classical.log:20-23`.

Reading the table:

- **ML-DSA-44 verifies faster than Ed25519** (27,440.658 vs 6,181.2
  ops/s) and faster than ECDSA P-256 (10,292.6 ops/s) on this machine.
  Verification cost is not a reason to avoid ML-DSA-44.
- **ML-DSA signing is fast enough for releases by orders of
  magnitude**: even the slowest ML-DSA signing rate (≥ 5,679/s)
  signs a release in well under a millisecond.
- **SLH-DSA-128s signs at 3.648 ops/s (274 ms per signature).**
  That is usable for releases (a few signatures a day) and unusable
  for anything high-frequency. SLH-DSA-128f signs at ≥ 75.228/s
  (13 ms per signature) — usable, but ~126x slower than ML-DSA-44
  signing.
- **SLH-DSA verification is the slowest of the set** (992–2,751
  ops/s), but still fast in absolute terms: verifying 1,000 release
  artifacts with SLH-DSA-128f takes about 1 second of single-thread
  CPU.
- The ML-DSA-87 signing rate (≥ 5,951.990/s) is higher than ML-DSA-65
  (≥ 5,679.135/s) in this run. Both hit the 25-iteration signing cap,
  so small differences between parameter sets are timing noise at
  millisecond scale, not a real ordering. Do not read a ranking
  into the capped signing figures; the verification figures (5
  seconds of timing each) are the comparable ones.

## Throughput table — 2,048-byte release-manifest payload

| Algorithm | Verify ops/s | Sign ops/s |
|-----------|------------:|----------:|
| ML-DSA-44 | 21,614.381 | ≥ 7,679.484 |
| SLH-DSA-SHA2-128f | 1,007.296 | ≥ 73.804 |

Sources: `outputs/benchmark-pq.log:184/:188` (ML-DSA-44),
`:215/:219` (SLH-DSA-128f).

Message-size effect: ML-DSA-44 verification is consistently
slower for a 2,048-byte message than for a 32-byte digest across
three runs on this machine: 18,246–21,614 ops/s for 2,048 bytes
against 27,440–27,652 ops/s for 32 bytes. (The vendored log holds
the latest run: 21,614.381 vs 27,440.658 ops/s; the earlier runs
are recorded in claim M-15.) Signing shows no consistent
message-size effect (8,322–10,690 ops/s at 32 bytes vs
7,679–9,589 ops/s at 2,048 bytes, overlapping ranges). The
practical consequence is small either way: even at the slowest
measured ML-DSA-44 verify rate, a release manifest verifies in
~55 µs.

## Hybrid throughput — 2,048-byte manifest payload

| Hybrid | Combined sig | Verify ops/s | Sign ops/s |
|--------|------------:|------------:|----------:|
| Ed25519 + ML-DSA-44 | 2,484 B | 5,036.280 | ≥ 6,377.754 |
| Ed25519 + SLH-DSA-SHA2-128f | 17,152 B | 857.440 | 75.229 |

Sources: `outputs/hybrid_bench.log:46/:50` (ML-DSA-44 hybrid),
`:87/:91` (SLH-DSA-128f hybrid). Controls C-1..C-5 all PASS in
both blocks (`:29-42`, `:70-83`).

A hybrid verification costs roughly the sum of its halves:
5,036/s for Ed25519+ML-DSA-44 is consistent with ML-DSA-44
verification dominating the cost. Signing a hybrid release with
Ed25519+ML-DSA-44 takes ~157 µs; with Ed25519+SLH-DSA-128f it
takes ~13.3 ms. Both are negligible against a release process
that takes minutes.

## What the numbers do and do not say

- They say the post-quantum schemes are fast enough for release
  signing on ordinary hardware. Nothing in this table blocks the
  migration on performance grounds, except SLH-DSA-128s signing
  speed if signing were ever needed at high frequency (it is not,
  for releases).
- They do not say anything about security: throughput is not a
  security argument. The security argument is in
  `docs/HYBRID_DESIGN.md` and rests on the FIPS standards and the
  AND-verification policy, not on these rates.
- They are single-machine, single-thread figures
  (`outputs/environment.txt`). Absolute rates will differ on CI
  runners and operator laptops; the relative ordering (ML-DSA-44
  fastest, SLH-DSA-128s signing slowest by far) is expected to
  hold, because it follows from the algorithms, not the machine.
