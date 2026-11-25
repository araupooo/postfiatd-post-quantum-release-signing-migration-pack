# Failure modes and limitations

## How this pack can be wrong, and what was done about it

### FM-01 — Measured rates vary between runs and machines

Rates are single-machine, single-thread figures. A re-run on the
same machine gives slightly different numbers (see the ML-DSA-44
confirmation re-runs in `docs/ALGORITHM_COMPARISON.md`:
27,440–27,652 verify ops/s at 32 bytes). Absolute rates will
differ on other machines. **Mitigation:** the pack never treats a
rate as exact — tables report the canonical run's figures, the
docs state the observed ranges where a re-run was done, and no
conclusion in this pack depends on a rate being exact. The
conclusions that matter (ML-DSA-44 is fastest; SLH-DSA-128s
signing is ~3.6/s; hybrids cost ~157 µs / ~13.3 ms per signature)
hold across the observed variation.

### FM-02 — Signing rates are lower bounds (iteration caps)

`bench_sig` caps signing at 25 iterations and `hybrid_bench` at
50, so the reported signing rates come from 25 (or 50) samples
over a few milliseconds. Small differences between parameter
sets (e.g. ML-DSA-87 at ≥ 5,951.990/s vs ML-DSA-65 at ≥ 5,679.135/s)
are timing noise, not a ranking. **Mitigation:** the docs say so
explicitly (`docs/ALGORITHM_COMPARISON.md`) and no conclusion
depends on the ordering of capped signing rates. The uncapped
verification rates (5 s of timing each) are the comparable
figures.

### FM-03 — secp256k1 is not measured

postfiatd uses secp256k1 ECDSA, not P-256. The classical baseline
measures P-256 (same ECDSA construction, different 256-bit
curve) because `openssl speed` offers it directly and liboqs
0.14.0 registers no classical signature algorithms. secp256k1
rates on this machine are therefore [UNSUPPORTED]. **Mitigation:**
the docs state this wherever the baseline is cited, and no
conclusion depends on a secp256k1 rate — the classical baseline
exists only to show the order of magnitude of classical signing
(10^4 ops/s) against which the PQ rates are compared.

### FM-04 — The release-signing mechanism is unobserved (U-01)

The pack cannot say how postfiatd releases are signed today,
because the pinned tree contains no release-signing code,
workflow step, or document. The migration plan therefore starts
with S0 (sign releases at all) and the key-management sections
are designs ([SIMULATED]), not descriptions. **Mitigation:** the
gap is labelled [UNSUPPORTED] in `docs/CLAIMS.md` (U-01, U-02)
and stated in every doc that touches it, rather than filled in
with a guess. If a manual signing step exists outside the tree,
stage S0 should document it instead of assuming it does not.

### FM-05 — The hybrid envelope is specified, not implemented

`harness/hybrid_bench.c` demonstrates the cryptographic core
(concatenated dual signature, AND-verification, tamper/strip
controls) but is not a release-signing tool: it has no envelope
parser, no key storage, no release-manifest format, and no
verifier a release operator would run. The envelope version
field and the cutover policy are design requirements
([SIMULATED]). **Mitigation:** the docs label them as such, and
stage S1's gate requires the envelope to be frozen and the
verifier to be shipped before the migration proceeds.

### FM-06 — The threat model is argued, not proven (U-06)

The AND-policy argument (a forgery needs both halves broken)
is a design rationale, not a formal proof. No security proof of
the hybrid construction is attempted in this pack.
**Mitigation:** labelled [UNSUPPORTED] (U-06); the pack
recommends adopting a standardised composite-signature envelope
when one stabilises (stage S4) rather than treating H-1 as final.

### FM-07 — liboqs 0.14.0 is not the latest liboqs

Measurements use liboqs 0.14.0 because it is the version pinned
by the earlier packs in this series and its FIPS 204/205
parameter sets are final. A newer liboqs may be faster (and may
register the FIPS 205 names directly). **Mitigation:** the
version and commit are pinned and recorded everywhere; the
relative ordering of the schemes is a property of the
algorithms, not the library version. Stage S4 re-measures on
current tooling.

### FM-08 — The 2,048-byte manifest is a model, not a measured release artifact

No actual postfiatd release manifest was signed: releases are
unsigned (R-01), so there is no signed manifest to measure.
The 2,048-byte payload is a fixed repeating-pattern model of a
manifest's size. **Mitigation:** the size is stated as a model
in the harness header and in `docs/ALGORITHM_COMPARISON.md`;
the measured message-size effect (ML-DSA-44 verify ~24–34%
slower at 2,048 bytes) is reported as measured, with the
confirmation re-run figures alongside.

### FM-09 — CI builds liboqs from the network

`reproduce.sh` clones liboqs tag 0.14.0 on first run when no
local checkout is present (CI). A network failure, or a
compromise of the tag, would break or subvert the CI run.
**Mitigation:** the script verifies the cloned HEAD is the
pinned commit `94b421ebb82405c843dba4e9aa521a56ee5a333d` and
fails otherwise; the tag is fetched over HTTPS from the
upstream repository. Vendoring liboqs into the pack was
rejected: it would add ~18 MB of third-party source to the repo.

### FM-10 — Deterministic logs exclude the measurement logs by design

`outputs/benchmark-pq.log`, `outputs/benchmark-classical.log`,
`outputs/hybrid_bench.log`, and `outputs/environment.txt` are
not covered by `SHA256SUMS` because their measured rates vary
per run. A re-run overwrites them. **Mitigation:** they are
verified structurally by `scripts/check_measurements.py`
(every block present, every control PASS, every measured length
equal to the parameter table), and the vendored copies are the
recorded evidence from the original run. See
`docs/REPRODUCTION.md`.
