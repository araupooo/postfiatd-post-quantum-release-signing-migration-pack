# Rollback protection and key compromise

## What "rollback" means here

Two different rollbacks matter for releases:

1. **Version rollback:** an operator (or an attacker who can serve
   a release) installs an older, validly signed release that
   contains a known vulnerability, instead of the current one.
2. **Key rollback:** after a key rotation, an old (compromised or
   retired) key is used to sign a new release, and verifiers still
   accept it.

Both are stopped by the same mechanism: a **monotonic version or
sequence that verifiers enforce**, plus a **revocation** mechanism
for keys. postfiatd already has this mechanism — for validator
data. It does not have it for releases.

## What exists in-tree (validator data — measured)

### Validator manifests: strict sequence monotonicity

`ManifestCache::applyManifest()` rejects a manifest whose sequence
number is not strictly greater than the stored one
(`src/xrpld/app/misc/detail/Manifest.cpp:411-413`, logged
`Invalid`). A manifest is accepted only if it verifies under both
its ephemeral signing key and its master key
(`Manifest::verify()`, `Manifest.cpp:196-216`). Sequence numbers
are a required field of the manifest format (`Manifest.cpp:60-85`).

### Master-key revocation: sequence == UINT32_MAX

`Manifest::revoked()` treats the maximum possible sequence number
as a master-key revocation (`Manifest.cpp:226-242`). A revoked
manifest is logged `Revoked` on apply (`Manifest.cpp:438-444`).
Revocation is therefore a first-class, in-band operation: the key
holder publishes one final manifest with the maximum sequence, and
every node that sees it stops trusting the key.

### Validator lists: sequence-gated fetch

ValidatorList v2 protocol messages only include VLs with a
sequence larger than the peer's (`ValidatorList.cpp:623-648`). A
peer cannot be fed an older list.

These three mechanisms together mean: **signed validator data
cannot be rolled back, and a compromised validator key can be
revoked in-band.** The design pattern is proven in the pinned
tree. The release process should copy it, not re-invent it.

## What does not exist (releases — measured absence)

- **No version pinning for releases.** The release job publishes a
  GitHub release tagged `v<version>` (from `BuildInfo.cpp:39`,
  currently `1.0.9`) and Docker images tagged
  `testnet-{light,medium,full}-<version>` — but the documented
  upgrade path tells operators to pull the rolling
  `` `-light-latest` `` tag (`testnet-build.yml:60-68`). A mutable
  `-latest` tag is, by definition, re-pointable: whoever controls
  the registry can move it to any image, including an old or
  malicious one, and the operator's `docker compose pull` will
  follow it. There is no signed version record the operator can
  check.
- **No signature to roll back to.** Because releases are published
  unsigned (R-01), there is no signed artifact whose version a
  verifier could enforce. Rollback protection for releases cannot
  exist until S0 (sign releases) is done.
- **No published key-rotation procedure.** How a release key is
  rotated, who authorizes it, and how verifiers learn the new key
  are not documented anywhere in the pinned tree (U-01). The
  procedure below is proposed ([SIMULATED]), not observed.

## Proposed rollback protection for releases (design, [SIMULATED])

Copy the manifest pattern:

1. **Signed version record.** Every release publishes a signed
   manifest (a small JSON file) containing: the version string,
   the release tag, the SHA-256 of every artifact, and a
   monotonically increasing **release sequence number**. The
   manifest is signed with the hybrid signature (H-1). The
   sequence starts at 1 and increases by 1 per release; it is
   part of the signed data, so it cannot be altered without
   invalidating the signature.
2. **Verifier enforcement.** Operator tooling records the highest
   release sequence it has installed. It refuses to install a
   release whose sequence is not strictly greater than the
   installed one (same rule as `applyManifest`, `Manifest.cpp:411`),
   unless the operator passes an explicit `--allow-downgrade`
   flag that prints a warning. The flag exists so a genuine
   emergency rollback is possible — but it is loud, not silent.
3. **Immutable tags.** Publish images by digest (`image@sha256:…`)
   in the deployment docs alongside the version tag, and stop
   telling operators to pull `-latest`. A digest is content
   addressed: it cannot be re-pointed.
4. **Revocation.** Reserve the maximum release sequence
   (`2^32 - 1`, mirroring `Manifest::revoked()`) as a key
   revocation: a release manifest with that sequence, signed by
   the old key, tells verifiers to stop trusting the old key.
   This is the same pattern as the manifest revocation and needs
   no new machinery in the verifier beyond the sequence check.

## Key compromise: response and rotation (proposed, [SIMULATED])

### What happens on compromise today

Today, there is no release key whose compromise can be described
— the key, its holder, and its storage are [UNSUPPORTED] (U-01).
If the release pipeline (GitHub Actions token with
`contents: write`) is compromised, the attacker can publish a
malicious release and the operator has no signature to check it
against. That is finding R-01/R-02, not a key-compromise scenario:
there is no key to compromise.

### Proposed rotation procedure (for the migrated process)

1. **Detect and contain.** Revoke the pipeline token that
   published the release. Publish a revocation manifest (maximum
   release sequence, signed with the old key if it is still
   available; if the old key itself is compromised, publish the
   revocation signed with a pre-generated offline backup key —
   this requires a backup key to exist, which is a stage-S0
   setup task).
2. **Generate the new keypair.** Ed25519 + ML-DSA-44 (H-1).
   Generate offline, on a machine that never touches the
   pipeline. Record the key generation in the release notes
   (date, operator, key fingerprint) — the record is public,
   the secret key never leaves the offline machine.
3. **Publish the new public key.** In the repository (a
   `keys/` directory with the public keys and their
   fingerprints), in the release notes, and in the install
   docs. The new key becomes effective at a stated release
   sequence; verifiers accept both keys for a stated overlap
   window (one release), then only the new key.
4. **Re-sign and re-publish.** Re-sign the current release with
   the new key and publish it at the next release sequence.
   Do not rewrite history: the compromised release stays
   published with a revocation notice, so anyone who installed
   it can see it was revoked.
5. **Verify the rotation.** The stage-S3 gate requires one
   exercised rotation on a test release before classical-only
   signing is retired.

### What compromise of each half means (hybrid)

- **Classical half (Ed25519) compromised, PQ half intact:** the
  attacker can produce a valid classical half but not a valid PQ
  half, so a hybrid signature cannot be forged. Rotate the
  Ed25519 key; the ML-DSA-44 key is untouched.
- **PQ half (ML-DSA-44) compromised, classical half intact:**
  symmetric — the Ed25519 half still stands, rotate the ML-DSA-44
  key.
- **Both halves compromised (or the pipeline token):** the attacker
  can sign. This is the revocation case above. The defense is
  detection (someone checks a signature against the published key
  and finds a release that should not exist) and the rotation
  procedure — not the signature scheme.

### What this pack does not claim

- The rotation procedure has not been exercised (U-03). Its
  durations are estimates.
- The compromise scenarios are hypothetical inputs to a design
  ([SIMULATED]), not observed incidents. No compromise of any
  postfiatd release key is known to this pack, because no release
  key is observable in the first place (U-01).
