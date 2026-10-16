# M4 wave2 — device A/B (2026-10-16)

First on-device evaluation of the staged M4 wave2 section (53 additional world-background
textures promoted to half dimensions; offline-verified byte-exact against original mip slices,
`evidence/memory-profile-m1m5/staged-wave2/`). Roadmap section 2 table / phase F
("Optional later device A/B, not a proven RAM saving") — this is that A/B.

## Protocol

- Same runtime build (`8a8d113f…`, dtime7 instrumentation), same launcher, controlled save,
  m1m5 harness (30 s menu + 30 s stationary street, cold caches), MIN=55% charge gate.
- Sections: baseline `a25600ce…` (two runs: `m1m5-cpt2`, `m1m5-dtime5`) vs wave2 `0deca8e9…`
  (two runs: `m1m5-m4w2-1`, `m1m5-m4w2-2`). Deployment: uploaded with sha256 verification,
  `payload.sha256` updated in place; baseline backup kept at
  `backups/wol-romfs.section.before-m4w2-20261016` and **restored + hash-verified after the
  A/B** (device is back on `a25600ce…`).

## Results (end-of-window PSS + SwapPSS, KiB)

| Run | Section | menu end | game end | game mean swap | presents/s |
| --- | --- | --- | --- | --- | --- |
| cpt2 | baseline | 904,889 | 929,446 | 478,698 | 26.59 |
| dtime5 | baseline | 906,460 | 930,647 | 484,209 | 27.06 |
| m4w2-1 | wave2 | 901,703 | 927,488 | 477,294 | 27.53 |
| m4w2-2 | wave2 | 899,981 | 929,219 | 470,239 | 26.66 |
| **mean Δ wave2 − baseline** | | **−4,832 (−4.7 MiB)** | **−1,693 (−1.7 MiB)** | **−7,687 (−7.5 MiB)** | — |

Baseline run-to-run spread is ±0.8 MiB (menu) and ±0.6 MiB (game), so the menu delta is
outside noise, the game delta is at its edge, and the swap delta (smaller payload → less
swap-in) is directionally consistent but not separable. Guest-heap pagemap (present/swapped
pages) shows no significant change. **This does not confirm the 18.75 MiB payload estimate as
resident RAM** — that figure is decompressed bundle payload; resident host texture effects are
diluted by the working set.

## Visual check

The stationary street frame (Boring Springs, "ALICE M.D." house) was captured under both
sections (`baseline-resume.png`, `wave2-resume.png`, both real KMS frames of the same scripted
position). A vision pass and a numeric pass agree: no visible blurring, missing elements or
artefacts; mean absolute per-channel difference between the two frames is ~2.8/255 (different
runs, not a pixel-exact comparison). Quality acceptance for gameplay remains the owner's
playtest — this check covers one stationary frame only.

## Verdict

Measured: small, mostly menu-side resident reduction (−4.7 MiB menu, −1.7 MiB game, −7.5 MiB
game swap) with no observed visual regression on the checked frame; no FPS change. Not adopted
as a default by this run; the device has been returned to the accepted baseline section and the
staged section remains available for a user-enabled trial.
