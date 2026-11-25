# Findings and remediation

Severity: **HIGH** — the issue lets an attacker ship a malicious
release (or roll a node back) without detection. **MEDIUM** — the
issue weakens the migration or leaves a real attack path open
during/after it. **LOW** — the issue is real but bounded, or
already mitigated in-tree. **INFO** — a recorded fact, no action
required.

Findings are not claims: measured claims live in
`docs/CLAIMS.md`; these are the judgements drawn from them.

## R-01 — HIGH: GitHub releases are published unsigned

**Evidence.** The testnet release job publishes a GitHub release
with `gh release create` from generated notes and nothing else
(claim M-17; `.github/workflows/testnet-build.yml:44-71`). A grep
of all ten workflow files for cosign/sigstore/attest/gpg/sha256sum/
checksum/slsa returns no release-signing step (claim M-16). No
signature, no attestation, no checksum is published with any
release.

**Impact.** Anyone who can publish (or replace) a release — a
compromised workflow token, a compromised maintainer account, a
registry/compromise in between — can ship arbitrary code to every
operator, and the operator has nothing to check it against. The
documented upgrade path (`docker compose pull`) will happily pull
whatever is published.

**Remediation.** Stage S0: publish an Ed25519 signature and a
SHA-256 checksum file with every release, plus a verifier script
in the repo. Then stage S1: add the hybrid (Ed25519 + ML-DSA-44)
signature alongside it.

## R-02 — HIGH: Docker images are pushed unsigned, under mutable tags, and image signing is explicitly deferred

**Evidence.** `build.yml` builds and pushes images
`agtipft/postfiatd` with mutable `-latest` tags and no signing
step (claim M-18; `.github/workflows/build.yml:71-90`). An in-tree
review document defers image signing (Cosign), container
scanning, and SBOM to "Phase 2 or mainnet" (claim M-19;
`docs/dynamic-unl/reviews/FeedbackAnalysis_Codex54.md:335,341`).

**Impact.** A mutable tag can be re-pointed to any image. An
operator pulling `-light-latest` gets whatever the tag currently
points at, with no signature to check. The deferral note means
this is a known gap, not an oversight — which makes it a
decision to revisit, not a bug to fix silently.

**Remediation.** Stage S0: pin images by digest
(`image@sha256:…`) in the deployment docs and stop directing
operators to `-latest`. Sign images (Cosign, or the hybrid
signature once S1 exists) as part of the release job. Revisit
the deferral decision explicitly: the "Phase 2 or mainnet"
condition should be replaced with a date or a release version.

## R-03 — MEDIUM: no rollback protection for releases

**Evidence.** The release process has no signed version record
and no sequence enforcement. Operators are told to pull a
rolling `-latest` tag (claim M-17 context;
`testnet-build.yml:60-68`). By contrast, validator manifests
have strict sequence monotonicity on apply and revocation via
sequence == UINT32_MAX (claims M-21, M-22).

**Impact.** An old, vulnerable release can be re-served (or an
old image re-tagged as latest) and operators will install it
without any warning. The in-tree pattern that stops this for
validator data does not exist for releases.

**Remediation.** Proposed in
`docs/ROLLBACK_KEY_COMPROMISE.md`: a signed release manifest
with a monotonic release sequence, verifier enforcement
(refuse a sequence that is not strictly greater than the
installed one unless `--allow-downgrade` is passed), and
digest-pinned images. Copy the manifest pattern; do not invent
a new one.

## R-04 — MEDIUM: downgrade risk during the hybrid transition

**Evidence.** Design analysis, not a measured vulnerability:
while any supported verifier accepts classical-only signatures,
an attacker who strips the post-quantum half of a hybrid
signature gets a signature that still verifies classically.
The harness demonstrates the strip itself is detectable
(controls C-4/C-5 reject stripped envelopes by length check;
claims M-14, `outputs/hybrid_bench.log:37-42`) — but only a
verifier that enforces the rule benefits from it.

**Impact.** A downgrade attack during S1/S2 would silently
remove the post-quantum protection while keeping a
valid-looking classical signature.

**Remediation.** The envelope version is part of the signed
data; verifiers reject a hybrid envelope with a missing half
(S1), and reject classical-only signatures for releases at or
above the cutover version (S2 gate). The S2 gate is the fix;
the format alone is not.

## R-05 — MEDIUM: SLH-DSA-128s signing is too slow for any high-frequency use, and SLH-DSA signatures are very large

**Evidence.** SLH-DSA-128s signs at 3.648 ops/s (274 ms per
signature); SLH-DSA-128f at ≥ 75.228 ops/s (claim M-04/M-05).
SLH-DSA-128s signatures are 7,856 bytes and 128f signatures
17,088 bytes (claims S-02, M-04/M-05) — 123.8x and 268.0x an
Ed25519 signature in the hybrid (claim D-01).

**Impact.** None for releases: a release is signed a few times
a day, and 274 ms per signature is irrelevant there (claim
D-05). The risk is a future reuse of the chosen scheme for
something high-frequency (validations, manifests), where 3.6
signatures per second would be a hard blocker. The size cost is
real for releases too: a 17,152-byte hybrid signature has to be
published, stored, and fetched with every release.

**Remediation.** Choose ML-DSA-44 for the first hybrid (D-02).
Keep SLH-DSA-128f as the conservative fallback (R-06), and do
not choose SLH-DSA-128s for anything unless its small
signature (7,856 B) matters more than its signing speed.

## R-06 — LOW: ML-DSA's security rests on lattice assumptions; a lattice break would break the PQ half

**Evidence.** FIPS 204 rests on Module-LWE/Module-SIS (claim
S-06). SLH-DSA rests only on hash-function security (FIPS 205).

**Impact.** If Module-LWE is ever broken, the ML-DSA-44 half of
every hybrid signature falls. The classical half still stands
(the AND-policy means a forgery needs both halves broken), so
the release is no worse off than it is today — but the
post-quantum protection is gone.

**Remediation.** Keep SLH-DSA-128f as a documented fallback
combination (already modelled in `data/hybrid_model.json`) and
re-evaluate at stage S4. Do not put all post-quantum trust in
one assumption family.

## R-07 — LOW: secp256k1 ECDSA DER signatures are malleable unless canonicality is enforced — already mitigated in-tree

**Evidence.** `verifyDigest()` rejects non-canonical ECDSA
signatures and normalizes low-S when the signature is not fully
canonical (`src/libxrpl/protocol/PublicKey.cpp:240-283`).

**Impact.** None currently: the mitigation exists and is
measured in-tree. Recorded so a future change to the
verification path is checked against this requirement.

**Remediation.** None. Any future change to `verifyDigest()` or
`verify()` must preserve the canonicality check.

## R-08 — INFO: Ed25519 verification enforces canonicality and strips the 0xED key prefix

**Evidence.** `verify()` checks Ed25519 signature canonicality
and strips the 0xED prefix from the public key before calling
`ed25519_sign_open` (`src/libxrpl/protocol/PublicKey.cpp:289-316`).

**Impact.** None. Recorded as a fact about the in-tree
classical baseline the hybrid builds on.

## R-09 — MEDIUM: no published key-rotation procedure exists for release keys

**Evidence.** The release key, its holder, its storage, and its
rotation are not observable from the pinned tree (claims U-01,
U-02). No document describes what happens if a release key is
compromised.

**Impact.** On compromise, the response would have to be
improvised. An improvised rotation is where mistakes happen
(old key still trusted, new key not distributed, revocation
never published).

**Remediation.** Adopt the rotation procedure proposed in
`docs/ROLLBACK_KEY_COMPROMISE.md` (detect/contain, offline
re-generation, published new public key with a stated effective
sequence, re-sign at the next sequence, exercised rotation at
the S3 gate). A backup (offline) key must exist before it is
needed — generating it is a stage-S0 setup task.

## R-10 — LOW: the release pipeline's trust anchor is a GitHub Actions token, and signing alone does not fix a compromised pipeline

**Evidence.** The release job runs with `contents: write`
permission and a `GH_TOKEN` (`.github/workflows/testnet-build.yml:40-71`).
A signature does not stop a compromised pipeline from signing a
malicious release; it only makes the forgery detectable by
anyone who checks the signature against the published key.

**Impact.** Bounded: signing moves the attack from "publish
anything silently" to "publish something that fails verification
for anyone who checks". That is a real improvement, but it is
not a complete fix for pipeline compromise.

**Remediation.** Signing (S0/S1) plus: least-privilege tokens
for the release job, branch protection on the release workflow,
and an independent check (a second person, or a separate CI job)
that verifies a published release's signature before the
release is announced.

## Summary

| ID | Severity | Title |
|----|----------|-------|
| R-01 | HIGH | GitHub releases are published unsigned |
| R-02 | HIGH | Docker images pushed unsigned, mutable tags, Cosign deferred |
| R-03 | MEDIUM | No rollback protection for releases |
| R-04 | MEDIUM | Downgrade risk during the hybrid transition |
| R-05 | MEDIUM | SLH-DSA-128s signing too slow; SLH-DSA signatures very large |
| R-06 | LOW | ML-DSA rests on lattice assumptions |
| R-07 | LOW | ECDSA DER malleability — already mitigated in-tree |
| R-08 | INFO | Ed25519 canonicality + 0xED prefix enforced |
| R-09 | MEDIUM | No published key-rotation procedure |
| R-10 | LOW | Release pipeline trust anchor is a GitHub token |

Counts: HIGH 2, MEDIUM 4, LOW 3, INFO 1. Total 10.
