# Decision memo — post-quantum release-signing migration

## Recommendation

1. **Start signing releases now (stage S0), with Ed25519.**
   The gap is not post-quantum: releases are published unsigned
   today. The cheapest, highest-value step is an Ed25519 signature
   plus a SHA-256 checksum with every release.
2. **Then migrate to the hybrid Ed25519 + ML-DSA-44** (design H-1,
   concatenated dual signature, AND-verification). It is the
   smallest (2,484-byte signature), fastest (5,036.280 verify/s in
   the hybrid), and simplest of the measured options, at NIST
   category 2 — matching the classical baseline it replaces.
3. **Keep SLH-DSA-SHA2-128f as the conservative fallback**, not
   the first choice: 17,152-byte hybrid signatures and 13.3 ms
   signing per release are affordable, but there is no reason to
   pay them first when ML-DSA-44 is faster and smaller.
4. **Do not choose SLH-DSA-128s** for release signing: 3.648
   signatures per second is usable for releases but leaves no
   headroom, and its only advantage (a 7,856-byte signature vs
   17,088 for 128f) does not justify the ~21x slower signing
   against 128f, let alone the ~2,600x slower signing against
   ML-DSA-44.

## What was measured

- Five post-quantum parameter sets (ML-DSA-44/65/87,
  SLH-DSA-SHA2-128s/128f) with liboqs 0.14.0, single thread:
  sizes, signing/verification/keypair throughput, at 32-byte and
  2,048-byte message sizes.
- Classical baseline (OpenSSL speed): Ed25519 19,259.4 sign/s,
  6,181.2 verify/s; ECDSA P-256 29,549.4 sign/s, 10,292.6 verify/s.
- Two hybrid combinations over a 2,048-byte manifest payload,
  with tamper and strip controls (C-1..C-5 all PASS, both
  hybrids).

## What was found in the pinned tree

- No release-signing code, workflow step, or document exists
  (R-01, R-02). The migration target is the release process, not
  an in-tree implementation.
- The in-tree signing that does exist is protocol signing
  (validations, manifests): Ed25519 + secp256k1 ECDSA, with
  canonicality enforcement (R-07, R-08).
- The in-tree rollback protection that does exist (manifest
  sequence monotonicity, revocation via UINT32_MAX, VL
  sequence-gated fetch) is a proven pattern the release process
  should copy (R-03).
- Image signing is explicitly deferred to "Phase 2 or mainnet"
  (R-02) — a decision to revisit, with a date or a version.

## What this memo does not decide

- The key holder, key storage, and rotation procedure for
  release keys: unobservable from the pinned tree (U-01). The
  procedure in `docs/ROLLBACK_KEY_COMPROMISE.md` is proposed,
  not observed, and needs a maintainer to adopt it.
- The cutover version and date (stage S2): a maintainer decision,
  to be announced at least one release in advance.
- Whether ML-DSA or SLH-DSA is the long-term choice: stage S4
  re-evaluates annually (U-04).

## Costs (measured, not estimated)

- Signing a hybrid release (Ed25519 + ML-DSA-44): ~157 µs.
- Verifying one: ~199 µs. Verifying 1,000 release artifacts:
  ~0.2 s of single-thread CPU.
- Publishing cost: one extra 2,484-byte signature (plus a
  1,344-byte public key, published once) per release.
- The migration's cost is organisational (tooling, docs, the
  cutover announcement), not computational. The 15–30 week
  planning horizon in `data/migration_plan.json` is an estimate
  for that organisational work (U-03).
