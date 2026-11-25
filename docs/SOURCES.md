# Sources

Every source in this pack, what it establishes, and when it was
consulted. Primary sources first; everything else is labelled.

## Primary sources (pinned tree)

| Source | What it establishes | Consulted |
|--------|--------------------|-----------|
| postfiatd main, HEAD `0085a1ff885d6a446369cf73a4430f75af22be55` (2026-10-10), version `1.0.9` (`src/libxrpl/protocol/BuildInfo.cpp:39`) | The pinned tree every in-tree claim is verified against | 2026-11-26 (local checkout `~/workspace/postfiatd-pin-0085a1f`) |
| `src/libxrpl/protocol/SecretKey.cpp:229-290` (excerpts in `data/source_excerpts.json`) | In-tree signing: `signDigest()` secp256k1-only; `sign()` Ed25519 64-byte + secp256k1 ECDSA over sha512Half, RFC6979, DER | 2026-11-26, grep -n |
| `src/libxrpl/protocol/PublicKey.cpp:240-316` (excerpts) | In-tree verification: ECDSA canonicality + low-S normalization; Ed25519 canonicality + 0xED prefix strip | 2026-11-26, grep -n |
| `src/xrpld/app/misc/detail/Manifest.cpp:60-85,196-216,226-242,405-448` (excerpts) | Manifest format, dual-signature verify, revocation (seq == UINT32_MAX), strict sequence monotonicity on apply | 2026-11-26, grep -n |
| `src/xrpld/app/misc/detail/ValidatorList.cpp:620-648` (excerpts) | VL v2 messages only include sequences larger than the peer's | 2026-11-26, grep -n |
| `.github/workflows/testnet-build.yml:28-71` (excerpts) | Release job: version from BuildInfo, `gh release create`, no signing/attestation/checksum step | 2026-11-26, grep -n |
| `.github/workflows/build.yml:71-90` (excerpts) | Docker image build/push with mutable `-latest` tags, no signing step | 2026-11-26, grep -n |
| `docs/dynamic-unl/reviews/FeedbackAnalysis_Codex54.md:331-342` (excerpts) | Image signing (Cosign) deferred to Phase 2 or mainnet | 2026-11-26, grep -n |
| `docs/build/install.md:30-45` (excerpts) | Package installs trust Ripple's GPG key for the rippled package repos — package-repo signing, not postfiatd release signing | 2026-11-26, grep -n |
| All ten `.github/workflows/*.yml` files (listed in `data/signing_inventory.json`) | Negative search: no release-signing step anywhere in the workflows | 2026-11-26, grep -rn |

All 367 vendored excerpt lines were re-verified against the pinned
checkout with `python3 scripts/signing_inventory.py --pin`
(367 lines checked, 0 mismatches). The vendored excerpts are the
evidence; the pin cross-check is the verification.

## Primary sources (standards and libraries)

| Source | What it establishes | Consulted |
|--------|--------------------|-----------|
| NIST FIPS 204, Module-Lattice-Based Digital Signature Standard (Aug 2024), Tables 1–2 | ML-DSA parameter sets, categories (44→2, 65→3, 87→5), key/signature sizes; randomized (hedged) signing by default with a deterministic variant (§5.3/§5.4) | 2026-11-26 (cross-checked via RFC 9964 Table 1 and liboqs headers) |
| NIST FIPS 205, Stateless Hash-Based Digital Signature Standard (Aug 2024), Table 2, §11 | SLH-DSA parameter sets, categories, key/signature sizes; stateless, hash-only security | 2026-11-26 (cross-checked via liboqs headers) |
| RFC 9964 (ML-DSA for JOSE/COSE), Table 1 | Repeats FIPS 204 Table 2 sizes (ML-DSA-44 2560/1312/2420; 65 4032/1952/3309; 87 4896/2592/4627) | 2026-11-26, web |
| RFC 8032 §5.1.5 | Ed25519: 32-byte public key, 64-byte signature | 2026-11-26 (standard reference) |
| SEC 1 (Standards for Efficient Cryptography) | P-256: 32-byte private key, 64-byte raw public key (x\|\|y), 64-byte raw signature (r\|\|s) | 2026-11-26 (standard reference) |
| liboqs 0.14.0, commit `94b421ebb82405c843dba4e9aa521a56ee5a333d` (open-quantum-safe/liboqs, tag 0.14.0) | The implementation the measurements use; headers `src/sig/ml_dsa/sig_ml_dsa.h:9-37` and `src/sig/sphincs/sig_sphincs.h:9-24` confirm the FIPS sizes byte for byte; `src/sig/sig.h` shows the FIPS 205 names are not registered (SPHINCS+ names are used instead) | 2026-11-26 (local checkout `~/liboqs`) |
| OpenSSL 3.0.13 (system) | Classical baseline (`openssl speed ed25519 ecdsap256`) and Ed25519 EVP signing in `harness/hybrid_bench.c` | 2026-11-26 (local run) |

## Secondary sources (cross-checks only, not load-bearing)

| Source | What it was used for |
|--------|---------------------|
| NIST PQC project page / FIPS 203, 204, 205 summaries | Confirming the three standards were approved 13 Aug 2024 and what each covers |
| IETF draft-vitap-ml-dsa-webauthn (COSE registration) | Confirming the FIPS 204 Table 2 sizes from a second independent repetition |

No community/forum source is load-bearing in this pack: every
size and every in-tree fact is verified against a primary source
(a standard, a library header, or the pinned checkout itself).
Where the pack could not verify something, it says so
(`docs/CLAIMS.md`, [UNSUPPORTED] rows U-01–U-06).

## What was NOT used

- No release-signing key, credential, or secret of any kind was
  accessed, read, or reproduced. None exists in the pinned tree
  to access.
- No Task 7 material was touched (that task's repo is blocked by
  an execution-risk check and is out of scope for this pack).
