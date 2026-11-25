# Hybrid signing design and threat model

## The problem, as measured

postfiatd releases are currently published **unsigned**: the testnet
release job publishes a GitHub release with `gh release create` from
generated notes and nothing else — no signature, no attestation, no
checksum (claim M-17). Docker images are built and pushed with mutable
`-latest` tags and no signing step (claim M-18), and image signing
(Cosign) is explicitly deferred to "Phase 2 or mainnet" in an in-tree
review document (claim M-19). The current release-signing mechanism,
if any exists outside the pinned tree, is not observable from it
(claim U-01).

So the migration has two parts, in order: **(0) start signing
releases at all** (stage S0), and **(1) make the signatures
post-quantum** (stages S1–S3). A post-quantum scheme alone, applied
to a process that currently publishes no signature, fixes nothing.
Stage S0 exists for this reason and its gate comes first.

## Design H-1 (recommended): concatenated dual signature

```
hybrid_sig = sig_classical || sig_pq
hybrid_pk  = pk_classical  || pk_pq
```

- Classical half: **Ed25519** (64-byte signature, 32-byte public
  key) — the scheme postfiatd itself uses for Ed25519 keys
  (`src/libxrpl/protocol/SecretKey.cpp:263-266`).
- Post-quantum half: **ML-DSA-44** (2,420-byte signature, 1,312-byte
  public key) — the smallest and fastest of the measured
  post-quantum schemes at NIST category 2.
- Envelope: a versioned header (format version + algorithm
  identifiers for both halves) prepended to the concatenated halves.
  The header is tens of bytes; it is excluded from the combined-size
  arithmetic in `data/hybrid_model.json` (claim D-04).
- Verification policy: **AND** — a hybrid signature is accepted only
  when **both** halves verify. A signature with either half missing
  or invalid is rejected.

Measured envelope (2,048-byte manifest payload, single thread):

| Hybrid | Combined sig | Combined pk | Verify ops/s | Sign ops/s |
|--------|------------:|------------:|------------:|----------:|
| Ed25519 + ML-DSA-44 | 2,484 B | 1,344 B | 5,036.280 | ≥ 6,377.754 |
| Ed25519 + SLH-DSA-SHA2-128f | 17,152 B | 64 B | 857.440 | 75.229 |

Sources: `outputs/hybrid_bench.log:22/:46/:50` and `:63/:87/:91`;
sizes recomputed in `outputs/hybrid_model.log`.

Why concatenated, and why these halves:

- **Concatenation is the simplest construction that the AND-policy
  can be checked against.** Each half is independently verifiable
  with its own standard verifier; no new cryptography is invented.
  A verifier that understands only the classical half can still
  check it (and must say so — see the downgrade analysis below).
- **ML-DSA-44 is the smallest and fastest post-quantum half.**
  Its combined signature (2,484 B) is 38.8x an Ed25519 signature,
  against 268.0x for Ed25519+SLH-DSA-128f. Its verification
  (27,440.658 ops/s alone, 5,036.280 ops/s in the hybrid) is the fastest
  measured post-quantum rate in this pack.
- **Ed25519 keeps compatibility with today's verifiers.** Any
  verifier that checks Ed25519 today keeps working on the classical
  half; the hybrid envelope adds the post-quantum half alongside it.
- **SLH-DSA-128f is the conservative alternative**, not the first
  choice: its public key is 32 bytes and its security rests only on
  hash functions (FIPS 205), but its signature is 17,088 bytes and
  its signing costs ~13.3 ms in the hybrid (75.229 ops/s). Keep it
  as the fallback if the lattice assumption behind ML-DSA is ever
  in doubt (finding R-06).

## Designs considered and rejected

### H-2: Nested signature (sign the classical signature with the PQ key)

`sig = sig_pq(sig_classical(msg))`. Verification requires
verifying the outer PQ signature, then the inner classical one.
It is strictly worse than H-1 for this use: the inner signature
is not independently verifiable without the outer one, a verifier
cannot check the classical half alone (so the S1 fallback mode
"classical-only with a warning" is impossible), and the total size
is the same as concatenation. Rejected: less flexible, same cost.

### H-3: Threshold / K-of-N signatures

Requiring, say, 2 of 3 release keys to sign. This solves a
different problem (key compromise / availability) and is
orthogonal to the post-quantum question. It also needs a key
management story this pack cannot observe (U-01). Not rejected
forever — it can be layered on top of H-1 later — but it is not
the migration design. The key-compromise analysis in
`docs/ROLLBACK_KEY_COMPROMISE.md` covers rotation instead.

### H-4: Pure post-quantum signature (ML-DSA-44 alone, no classical half)

Smaller than the hybrid (2,420 B vs 2,484 B) and simpler. Rejected
for the migration's first step for two reasons: (1) it drops
compatibility with every existing Ed25519 verifier at once, so
the cutover is a flag day instead of a staged transition; (2) if
ML-DSA is ever weakened, a pure-ML-DSA release has no fallback,
while a hybrid still has its classical half. Pure ML-DSA is the
right end state only after the classical half is retired for a
separate, later decision — not part of this migration.

## Threat model

Adversary capabilities assumed:

| # | Capability | Covered by H-1? |
|---|-----------|-----------------|
| T-1 | Classical adversary: can forge neither Ed25519 nor ML-DSA signatures; can read, copy, replay, and strip parts of a published release | Yes — both halves must verify; stripping either half is rejected (controls C-4, C-5) |
| T-2 | Quantum adversary: can break Ed25519 (and ECDSA) by Shor's algorithm, cannot break ML-DSA-44 | Yes for integrity — the ML-DSA-44 half still verifies; the classical half is broken but the AND-policy means the broken half alone never accepts a forgery |
| T-3 | Quantum adversary that can also break ML-DSA-44 (lattice break) | No — if both halves fall, H-1 falls. Mitigation is diversity, not this design: keep SLH-DSA-128f as a fallback (R-06) |
| T-4 | Adversary that compromises the release-signing key | Partially — key compromise is a rotation problem, not a signature-algorithm problem; see `docs/ROLLBACK_KEY_COMPROMISE.md` |
| T-5 | Adversary that compromises the release pipeline (GitHub Actions token, workflow) and publishes a malicious release | Partially — a signature does not stop a compromised pipeline from signing; it makes the forgery detectable by anyone who checks the signature against the published key, and it stops a pipeline compromise from silently replacing an already-signed release |
| T-6 | Adversary that replays an old, validly signed release to roll a node back to a vulnerable version | Only if the envelope carries a version/monotonic sequence and verifiers enforce it — see `docs/ROLLBACK_KEY_COMPROMISE.md`. H-1 alone does not stop replay |

## Downgrade analysis

The dangerous moment in any hybrid migration is the transition:
while some verifiers accept classical-only signatures, an
attacker who strips the post-quantum half gets a signature that
still verifies classically. H-1 handles this with an explicit
policy, enforced by the envelope version:

1. **Before the cutover version (stage S1):** verifiers accept
   both classical-only signatures (old releases) and hybrid
   signatures, but a hybrid envelope with a missing PQ half is
   **rejected** — it is not a classical-only signature, it is a
   damaged hybrid signature. This is exactly control C-4 in
   `harness/hybrid_bench.c`: a stripped hybrid is rejected by
   length check (`outputs/hybrid_bench.log:37-39`).
2. **At and after the cutover version (stage S2):** verifiers
   **reject classical-only signatures for new releases** and accept
   only hybrid signatures. Old releases keep their classical-only
   validity for their own versions (they are not retroactively
   re-signed); the rule applies to releases at or above the
   cutover version, identified by the envelope version field.
3. **The envelope version is part of the signed data.** A
   downgrade attacker cannot rewrite the version field to an older
   value, because the version is covered by both signatures. (This
   is a design requirement on the envelope format, [SIMULATED] —
   the envelope is specified here, not implemented in this pack.)

What H-1 does **not** protect against: a verifier that was never
updated and still accepts classical-only signatures for new
releases. That is a deployment problem, solved by the S2 gate
(all supported verifiers require the PQ half), not by the
signature format.

## Key management (what this pack can and cannot say)

- The hybrid needs two keypairs (Ed25519 + ML-DSA-44) and two
  public keys published for verifiers. The combined public key is
  1,344 bytes — small enough to publish anywhere a 32-byte key is
  published today.
- ML-DSA-44 secret keys are 2,560 bytes (vs 32 for Ed25519). Key
  storage must hold the larger key; that is a tooling detail, not
  a blocker.
- ML-DSA signing in FIPS 204 is randomized (hedged) by default,
  with a deterministic variant defined (FIPS 204 §5.3/§5.4). The
  randomized variant needs a good RNG at signing time; the
  deterministic variant needs no RNG but produces the same
  signature for the same message and key (which is fine for
  releases — a release is signed once). Either is acceptable; the
  choice is a signing-tool decision, [SIMULATED].
- SLH-DSA is stateless: there is no per-signature state to manage
  and no nonce-reuse failure mode. That is its main operational
  advantage over stateful hash-based schemes (XMSS/LMS), which
  this pack does not recommend for releases.
- Where the keys live, who holds them, and how they are rotated
  today is [UNSUPPORTED] (U-01). The rotation procedure proposed
  for the migrated process is in
  `docs/ROLLBACK_KEY_COMPROMISE.md`.
