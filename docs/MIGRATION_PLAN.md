# Staged migration plan

Durations are [ESTIMATE] (planning figures for one maintainer at
the current release cadence, not measured). **Gates are the binding
part**: a stage is complete only when its gate check passes. The
plan is also encoded in `data/migration_plan.json` and checked by
`scripts/migration_model.py` (`outputs/migration_model.log`).

## Stage S0 — Sign what exists today (1–2 weeks)

**Work:**

- Publish an Ed25519 signature **and** a SHA-256 checksum file
  with every GitHub release. The release job currently publishes
  neither (R-01).
- Publish a verifier script in the repo that checks the signature
  and the checksum against the release tag.
- Pin Docker images by digest in the deployment docs; stop
  telling operators to pull mutable `-latest` tags (R-02/R-03).

**Gate:** a signed release exists (Ed25519) whose signature and
SHA-256 checksum are published alongside the release, and the
verifier script checks both. Gate check: independent
re-verification of a published release passes.

**Why first:** a post-quantum signature on an unsigned process
fixes nothing. S0 closes the gap that exists today, with the
cheapest possible change, and gives the migration something to
build on.

## Stage S1 — Hybrid envelope, dual-sign in parallel (2–4 weeks)

**Work:**

- Freeze the hybrid envelope format (H-1 concatenated dual
  signature, Ed25519 + ML-DSA-44; see `docs/HYBRID_DESIGN.md`).
- Sign every release twice: classical (Ed25519) and hybrid
  (Ed25519 + ML-DSA-44); publish both signatures.
- Ship a verifier that understands the hybrid envelope and falls
  back to classical-only **with an explicit warning, never
  silently**.

**Gate:** the envelope format is specified, and
`harness/hybrid_bench.c` demonstrates a hybrid signature that
verifies only when both halves verify (controls C-1..C-5 all
PASS). Gate check: `bash reproduce.sh` passes, including the
hybrid controls.

**Compatibility:** old verifiers (Ed25519-only) keep working on
the classical half. New verifiers check both halves. No operator
is broken by S1.

## Stage S2 — Verifiers require the PQ half (4–8 weeks)

**Work:**

- Update operator tooling and install docs to require the PQ half
  for releases at or above the cutover version.
- Add a policy flag: before the cutover version, classical-only is
  accepted with a warning; at/after it, classical-only is rejected.
- Publish the cutover version and date in the release notes.

**Gate:** all supported verifiers accept hybrid signatures and
reject a stripped (classical-only) hybrid envelope. Gate check:
the C-4 downgrade control in `harness/hybrid_bench.c` is mirrored
by an operator-tooling test that rejects a stripped envelope.

**Compatibility:** this is the sharp edge of the migration. Old
releases (below the cutover version) keep their classical-only
validity for their own versions — they are not retroactively
re-signed. Only releases at or above the cutover version require
the PQ half. Operators who do not update their tooling before the
cutover cannot verify new releases; the cutover version and date
must be announced at least one release in advance.

## Stage S3 — Classical-only retired for new releases (8–16 weeks)

**Work:**

- Make the release job fail closed when either signature half is
  missing.
- Exercise the key-rotation procedure
  (`docs/ROLLBACK_KEY_COMPROMISE.md`) on a test release.
- Keep verifying old classical-only releases (they remain valid
  for their versions).

**Gate:** no supported release is classical-only; a dry-run
release with a missing PQ half fails the job; a rotated key
verifies.

**Compatibility:** after S3, a verifier that only understands
Ed25519 cannot verify new releases. That is the intended end
state of this migration, not an accident — it is why S1 and S2
come first.

## Stage S4 — Review and re-evaluate (ongoing)

**Work:**

- Re-run this pack's benchmarks on current hardware and compare
  with `outputs/benchmark-pq.log`.
- Track NIST/IETF hybrid-signature standards (composite
  signatures, CNSA 2.0 timelines) and adopt a standard envelope
  when one stabilises.
- Re-evaluate ML-DSA-65/87 if the threat model changes.

**Gate:** a dated review note is published with the re-measured
numbers. Annual.

## Planning horizon

S0–S3: **15–30 weeks** in total (estimates, not a commitment).
The long pole is S2/S3 (tooling updates and the cutover
announcement), not the cryptography: the measured signing cost
of a hybrid release is ~157 µs (Ed25519+ML-DSA-44) and the
verification cost is ~199 µs per signature.

## Compatibility matrix

| Verifier | Old release (classical-only) | New release, before cutover | New release, at/after cutover |
|----------|------------------------------|----------------------------|-------------------------------|
| Old (Ed25519-only) | Verifies | Verifies (classical half) | **Cannot verify** — must update |
| New (hybrid-aware) | Verifies, warns | Verifies both halves | Verifies both halves |
| New, strict mode | Verifies, warns | Verifies both halves | Verifies both halves; rejects classical-only |

## What is deliberately not in this plan

- **Retroactive re-signing of old releases.** Old releases keep
  the signatures they were published with (currently: none).
  Re-signing history would create confusion about which signature
  is authoritative and is not needed: the S2 rule is
  version-gated, not history-rewriting.
- **Pure ML-DSA (no classical half).** See H-4 in
  `docs/HYBRID_DESIGN.md`: it is a possible later end state, not
  part of this migration.
- **Threshold (K-of-N) release signing.** See H-3: orthogonal to
  the post-quantum question; can be layered on H-1 later.
