# FPS experiment: direct texture upload from guest storage (`WOL_REFRESH_DIRECT`)

Date: 2026-10-15. Runtime under test: `wol-horizon-build-refreshdirect2`
SHA256 `9b3ca0b505a77d24074420046915e65ed1860173f91c61accc2755e43b3c1667` (A/B arms);
final artifact `wol-horizon-build-refreshdirect3` SHA256
`53e3db5e8409186e58b2965fe7bc64a31f9ca63ad32ea7a70a40913af9a295bb` (opt-in default, sanity
run `rdH1`). **Experimental checkpoint, not a release.** Owner section stays `a25600ce...`.

**Result: the change engaged for every refresh but produced no measurable gain; it stays
opt-in (`WOL_REFRESH_DIRECT=1`), the default is the staging copy.**

## What was tried

`zero_texture_refresh()` re-uploads a texture whenever the guest's CPU-side writes mark it
dirty. For the measured per-frame consumer (texture `id=460`, 3.69 MB every frame) the exact-copy
fast path copied guest storage into a per-refresh `malloc` staging buffer and uploaded that —
i.e. a 3.69 MB memcpy plus malloc/free per frame on top of the upload itself (9.44 GB each per
run, measured earlier in `fps-gpu-copy`).

`WOL_REFRESH_DIRECT=1` uploads straight from the guest pool mapping when the upload is an exact
raw RGBA8 copy (`nvn_texture_rgba8_raw_eligible`: format 0x25, swizzle {2,3,4,5}, byte rows
already at pitch, `GL_UNSIGNED_BYTE`). All other cases keep the staging path unchanged.

## Method

Same device, same section `a25600ce`, same controlled save, same harness (`--cold`, 30 s menu +
30 s street). Arms alternating, six runs for the A/B plus one sanity run on the final build:

| run | arm | menu | game |
|---|---|---:|---:|
| m1m5-rdF1 (scout) | staging | 26.51 | 25.96 |
| m1m5-rdF2 (scout) | direct | 26.04 | 26.30 |
| m1m5-rdG1 | staging | 25.81 | 26.36 |
| m1m5-rdG2 | direct | 25.17 | 25.71 |
| m1m5-rdG3 | direct | 25.82 | 26.07 |
| m1m5-rdG4 | staging | 26.51 | 26.19 |
| m1m5-rdH1 (final build, default) | staging | 26.72 | 25.81 |

Aggregate: staging **menu 26.28 / game 26.17** (3 runs) vs direct **menu 25.68 / game 26.03**
(3 runs) — the direct path is flat-to-slightly-negative, well inside the ±1.5 presents/s
run-to-run noise measured earlier.

## Engagement receipts (the A/B actually tested the code)

- `WOL_REFRESH_DIRECT enabled=1 mode=upload-from-guest-storage` in both direct runs, `enabled=0
  mode=staging-copy` in all control runs and in the final-build sanity run.
- `ZERO_REFRESH_STATS id=460 calls=2560 uploaded-bytes=9437184000 direct-levels=2560` — every one
  of the 2560 refreshes took the direct path; four bounded
  `WOL_REFRESH_DIRECT upload ... staging=malloc-skipped` receipts per run.
- Control runs show zero direct uploads.

## Conclusion and limits

- Skipping the 3.69 MB staging memcpy (and its malloc) per frame did **not** move presents/s:
  the staging copy was not on the critical path. Together with the earlier GPU-blit result
  (`fps-gpu-copy`), both ends of this per-frame chain have now been tested — the chain itself is
  real but not a frame-time lever on either side; do not re-mine it without a new mechanism.
- Default stays the staging copy (the previously validated behaviour); `WOL_REFRESH_DIRECT=1`
  remains available and unit-pinned (`tools/test_wol_rgba8_copy.py` asserts the opt-in gate).
  Diagnostics kept: `ZERO_REFRESH_STATS` now carries `direct-levels`.
- Limits: menu + starting street only; six runs; the direct upload was never faster by more than
  noise, so its slightly negative mean is not itself a regression claim.
- Integrity: every run restored the owner save (SHA256 match), left no `wol-horizon` process and
  produced real Spruce menu frames; the harness reported no GL errors for the direct path.

## Files

- `run-rdF1/ run-rdF2/ run-rdG1..G4/ run-rdH1/` — phase JSONs, receipts, effective env, raw
  runtime log (`runtime.log.xz`). The arm is visible in each log via the `WOL_REFRESH_DIRECT`
  receipt line.
- `m5-layout-refreshdirect2.json` (A/B builds) / `m5-layout-refreshdirect3.json` (final build) —
  descriptor layouts bound to the corresponding ELF SHAs.

No owner bundle, executable or save is distributed here.
