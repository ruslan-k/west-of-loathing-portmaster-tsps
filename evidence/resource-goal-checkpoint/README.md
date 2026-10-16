# Menu/game resource checkpoint (experimental)

This is a checkpoint, **not a release, not a 30 FPS result, and not a sub-1 GB result**. Full per-run values are in `comparison.json`. Owner game data, executable and saves are not distributed.

## Measured result

Separate approximately 30-second windows, real TSPS KMS frames, CONTINUE accepted through diagnostic Npad A before gameplay. CPU percentage is relative to one CPU, not the entire board. Consecutive `MOMO_FRAME` timestamps measure presents, not independently counted panel refreshes.

- Baseline menu/game: **13.745 / 12.953 presents/s**.
- Combined diagnostic readback-OFF + packed4444 + host CPU remap: **21.357 / 19.441 presents/s**. These are diagnostic floors, not normal-play acceptance.
- Combined configuration **with genuine startup proof and periodic checks** (`T2_READBACK_OFF=0`, `COTM_PRESENT_READBACK_60=1`, period 120): **21.815 / 19.042 presents/s**. Each window contains five `NVN_PRESENT_PIXELS ... status=PIXELS` receipts. Unsampled frames remain `NOT-SAMPLED`.
- Periodic menu: mean `/proc/status` RSS **686.23 MiB**, VmSwap **606.01 MiB**; end rollup PSS + SwapPSS **1054.92 MiB**.
- Periodic game: mean status RSS **703.85 MiB**, VmSwap **673.90 MiB**; end rollup PSS + SwapPSS **1079.86 MiB**.

PSS + SwapPSS is committed-page accounting, not the active working set or complete driver allocation. This kernel's status RSS and smaps/rollup RSS disagree materially; both originals are preserved. Do not add GPU estimates blindly to either figure. These results do **not** establish a whole-game footprint below either 1 GB or 1 GiB.

Sequential exploratory runs vary in animation, runtime warm-up and swap/cache state; they are not a replicated one-variable A/B experiment. Do not attribute the combined FPS change to packed4444, affinity or cadence alone. Gameplay major faults varied substantially; a short warm sample is not startup/transition acceptance.

## Authored changes

- Account successful RGB writes from substituted draws, standard draws and proven blits. Exclude skipped/error, stencil-only and alpha-only draws; preserve the real pixel test `nonblack>=32 && t->draws`. This repairs the previously inconclusive proof; it does not turn a draw command into visual proof.
- Optional exact native RGBA4444 upload for eligible original format 0x39, with no dimension reduction. Preserve swizzle/type/stride contracts. The test exhausts **84,934,656** legal value/swizzle cases. Estimated host storage of this group halves; that estimate is not measured driver RAM.
- Optional guest logical CPUs 0..2 -> host CPUs 4..6, pinning before guest entry while preserving logical CPU/mask ABI. No clock changes. Bad configuration/host CPUs fail closed rather than returning invented logical CPU IDs.
- The **TSPS-only experimental launcher** enables these tested options. Runtime helpers remain default-off for other callers. Readback-OFF is not the launch default.

## Verification / limitations

- Fresh overlay built successfully with the existing cross-toolchain. `builds.json` distinguishes the measured binary from the subsequently rebuilt artifact; the latter is undergoing its own device verification. Never assume different SHA-256 artifacts are identical just because the source intent is the same.
- `tests.json`: 22 baseline unit tests, six sprite-metadata cases, compiled geometry/UV/stencil/color/trace/proof/packed-format/CPU-map regressions, launcher syntax and upstream overlay apply check passed. Standalone `tools/test_wol_*.py` scripts take source paths and are not a unittest-discovery directory.
- Real menu portrait masking, Boring Springs bodies and HUD are visible in the attached KMS captures. No physical-button or acoustic audio verification is claimed.
- Additional ZL/Plus diagnostic packets produced a world hint and dialogue history, **not a verified open-map capture** in the periodic run. The known map overlay/layout defect remains open.
- The periodic test was stopped by exact runtime PID; principal restored Spruce (see `restored-menu.png`). The pre-run save snapshot was restored and SHA-256 checked. No unrelated processes were stopped.
- **Independent review: not-cleared**. See `review.json` for the response, evidence-based adjudication and remaining scope. The second reviewer returned only introductory text, not approval. Published at the user's explicit request as experimental progress; no review-clearance claim.

## Recommendations from the local chat notes

Applicable now: correct target color accounting before sparse readback, distinguish native/expanded texture memory, use exact native precision before lossy resizing, and preserve guest CPU ABI while evaluating host placement. Implemented as described above. Not implemented or claimed: ETC2/ASTC transcoding, Unity heap compaction, freeing live guest pages, globally shrinking textures, swapoff, VM tuning or GPU overclocking.

Next: independently re-verify the fresh build, collect measured render/guest/texture costs, and isolate the next change before another menu/game comparison. Guest arena ownership and complete GPU allocation remain unresolved; they are not safe candidates for arbitrary page dropping.
