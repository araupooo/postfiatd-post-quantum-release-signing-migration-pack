# Reproduction

## How to reproduce

```sh
bash reproduce.sh
```

Exit code 0 and `REPRODUCE OK` mean every check passed and every
vendored file matches its recorded SHA-256. Requirements: `bash`,
`python3` (3.12), `cc`, `cmake`, `git`, `openssl`, and network
access to clone liboqs tag 0.14.0 on first run (see below). No
postfiatd checkout is needed.

## What reproduce.sh does

1. `bash scripts/run_all.sh`:
   - `harness/environment.sh` — writes the environment file
     (stable facts only: OS, kernel, CPU model, compiler versions,
     liboqs commit, postfiatd pin; no timestamps, no load averages,
     no CPU frequency, so the file is byte-identical across runs on
     the same machine).
   - `python3 scripts/signing_inventory.py` — verifies the vendored
     excerpts and the inventory; writes
     `outputs/signing_inventory.log` (deterministic).
   - `harness/run_benchmarks.sh` — builds liboqs 0.14.0 if needed,
     compiles both harnesses, runs the PQ benchmarks (5 parameter
     sets at 32 bytes, 2 at 2,048 bytes), the classical OpenSSL
     baseline, and the hybrid benchmarks.
   - `python3 scripts/hybrid_model.py` — recomputes every hybrid
     size from the parameter table and checks the measured hybrid
     log for consistency; writes `outputs/hybrid_model.log`
     (deterministic).
   - `python3 scripts/migration_model.py` — checks the migration
     plan's structure and arithmetic; writes
     `outputs/migration_model.log` (deterministic).
   - `python3 scripts/check_measurements.py` — structural check of
     the measurement logs (see below).
2. `bash verify_digests.sh` — `sha256sum -c SHA256SUMS`.
3. Writes `outputs/reproduce_selfcheck.log` containing only the
   deterministic logs, the measurement-structure check, and the
   digest verification output, ending with `REPRODUCE OK`.

When run through `reproduce.sh`, the measurement steps write to a
scratch directory (`MEASUREMENT_OUTDIR`, a fresh `mktemp -d`),
not to `outputs/`: the vendored measurement logs are the recorded
evidence from the original run, and overwriting them with a new
run's rates would silently change the evidence the docs cite.
When run standalone (`bash scripts/run_all.sh`), the measurements
write to `outputs/` as usual. Either way, the structural check
runs against whichever directory the measurements went to, and
its output is identical in both modes (no paths are printed).

## What is verified by digest, and what is not

`SHA256SUMS` covers every pack file **except** itself,
`outputs/reproduce_selfcheck.log`, and the four measurement logs
(`outputs/benchmark-pq.log`, `outputs/benchmark-classical.log`,
`outputs/hybrid_bench.log`, `outputs/environment.txt`):

- The manifest cannot verify itself.
- The self-check log embeds the digest verification output, so it
  cannot be part of its own digest set. It is verified instead by
  byte-identical regeneration: re-running `bash reproduce.sh`
  must regenerate it with the same SHA-256. Its content is
  deterministic (PASS/FAIL lines and digest output only — no
  timestamps, no absolute paths, no measured rates), so this
  holds. Verified: three consecutive runs produced the same
  self-check log hash (see Verification below).
- The measurement logs contain rates that vary between runs, so
  they cannot be in a digest set that a re-run must satisfy.
  They are verified structurally instead, by
  `scripts/check_measurements.py`: every expected algorithm block
  present (5 PQ blocks at 32 bytes, 2 at 2,048 bytes, 2 classical
  blocks, 2 hybrid blocks), every control PASS (7 valid-signature
  + 7 tampered-signature controls in the PQ log; C-1..C-5 in both
  hybrid blocks), every measured length equal to
  `data/algorithm_params.json`, every log ending with
  `result: OK`. The vendored logs are the recorded evidence from
  the original run; a re-run regenerates them and the structural
  check confirms they are consistent with the parameter table.

## The liboqs build

`harness/run_benchmarks.sh` resolves the liboqs source in this
order: `$LIBOQS_SRC` if set; `~/liboqs` if it exists and its HEAD
is the pinned 0.14.0 commit
`94b421ebb82405c843dba4e9aa521a56ee5a333d`; otherwise a fresh clone
of tag 0.14.0 into `.deps/liboqs` (network). The build directory
is `$LIBOQS_BUILD_DIR`, default `$LIBOQS_SRC/build`; an existing
build for the same source tree is reused (this only skips the
build, never the commit check). The script fails if the liboqs
HEAD is not the pinned commit. The build takes a few minutes on
first run and is cached afterwards. CI (fresh clone, no `~/liboqs`)
always clones and builds from source.

## The pin cross-check (manual, not part of reproduce.sh)

The vendored excerpts in `data/source_excerpts.json` were verified
against the pinned checkout with:

```sh
python3 scripts/signing_inventory.py --pin
```

Result: **367 lines checked, 0 mismatches**. This step needs the
checkout at `~/workspace/postfiatd-pin-0085a1f` (HEAD
`0085a1ff885d6a446369cf73a4430f75af22be55`). It is deliberately not
part of `reproduce.sh`: CI has no checkout, and the no-pin run is
the deterministic one that `reproduce.sh` regenerates. The pin
cross-check proves the excerpts are faithful; the no-pin run proves
the inventory is internally consistent.

## CI

`.github/workflows/ci.yml` runs `bash reproduce.sh` on
`ubuntu-latest` with Python 3.12 on every push and pull request.
No secrets are used. The CI run clones liboqs (network) and
builds it; total runtime is a few minutes.

## Verification performed for this pack

- `bash reproduce.sh` run 3 times consecutively (before the
  scratch-directory change, when reproduce still wrote the
  measurements into `outputs/`); each run exit 0, `REPRODUCE OK`;
  the self-check log hash was identical in all three runs:
  `c78048f3b1dc05e726c59b374b84ab1f06ef0579d9f8167fb6ffc0d3becc92ac`.
  The third run's measurement logs are the vendored ones the docs
  cite (ML-DSA-44 verify 27,440.658 ops/s, etc.).
- After the scratch-directory change: `bash reproduce.sh` exit 0,
  `REPRODUCE OK`, the same self-check log hash
  (`c78048f3b1dc05e726c59b374b84ab1f06ef0579d9f8167fb6ffc0d3becc92ac`),
  and the four vendored measurement logs byte-identical before
  and after the run (SHA-256 checked).
- Fresh-copy test: the pack was copied to a fresh directory, the
  postfiatd checkout was temporarily moved aside, and
  `bash reproduce.sh` was run there — exit 0, `REPRODUCE OK`, and
  the self-check log was byte-identical to the pack's. The
  checkout was restored afterwards. This proves the pack has no
  local-checkout dependency (the Task 13 CI lesson).
- `python3 scripts/signing_inventory.py --pin`: 367 lines, 0
  mismatches.
- `bash verify_digests.sh`: all covered files OK.
- `diff -r` of a fresh copy against the pack: clean (excluding
  `scripts/__pycache__`, the compiled harness binaries, and
  `.deps/`, which regenerate on reproduce runs and are not part
  of the pack).
