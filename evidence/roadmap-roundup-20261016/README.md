# Roadmap round-up — 2026-10-16 (recommended-commits 1–5)

Scope: one day of device rounds on `main` (baseline `a6acb0e` → `54ef07f`), owner section
`a25600ce…` throughout, controlled save, Spruce principal launch, m1m5 harness (30 s menu +
30 s stationary street, cold caches). Every run's receipt records the exact runtime hash.

## What was done, per roadmap item

| Item | Status | Evidence |
| --- | --- | --- |
| 1. Frame timeline + GPU-wait attribution (instrumentation) | Done: `NVN_REPLAY_PHASES` + `NVN_DRAW_SPLIT` sub-spans, profiler-overhead A/B in noise | `evidence/fps-frame-timeline/` |
| 2. Heap/AssetBundle owner + residency inventory | Partial: residency + vertex census measured; phase comparison done; allocation-owner trace and VMA diffs **not implemented** | `evidence/gpu-texture-residency/`, `evidence/m5-heap-owners/` |
| 3. Texture-460 dependency trace → lazy copy | Trace done; **lazy alias rejected** with reasons (source mutates every frame; deferred copy keeps full cost) | `evidence/copy460-dependency-trace/` |
| 4. M6 compressed upload (one texture) | **Not implemented**; first inventory + format-support gate recorded | `evidence/m6-compressed-textures/staging.md` |
| 5. Evidence/report + next candidate | This document | — |
| Section 2 (present proof) | Validated (proof frame 4, sparse period 300, 2895 NOT-SAMPLED) | `evidence/present-proof-sparse/` |
| Section 4 (CPU remap A/B) | Measured: no repeatable gain; stays opt-in | `evidence/cpu-remap-ab/` |
| Phase F — M4 wave2 device A/B | Done: −4.7 MiB menu / −1.7 MiB game PSS+SwapPSS (near noise), −7.5 MiB game swap, no visual regression on the checked frame; baseline section restored | `evidence/m4-wave2-device-ab/` |

## Measured frame split (stationary game, ~37.6 ms frame)

- replay ≈ 25.9 ms: **draw records 8.6–9.2 ms** (texture first-resolve ≈4.4 ms;
  program+constants ≈0.8–1.1 ms; GL submissions ≈1.0 ms; geometry ≈0.2 ms; marshalling
  ≈0.8 ms), decode ≈0.9 ms, non-draw records ≈3.5 ms, copy ≈1.0 ms;
- present ≈2.0 ms, finish (GPU-side wait) ≈11.8 ms, swap ≈1.5 ms;
- guest-thread CPU ≈20 ms/frame; six first-after-target-change draws ≈820 µs each.

## Next production candidate (recommendation, not a commitment)

1. **Texture first-resolve path (`a2c1`, ≈4.4 ms/frame).** Highest measured CPU cost with a
   clear localisation: one `nvn_render_sampler` resolve per draw in the quiet-pick selection
   costs ≈100 µs while the immediate re-resolve of the same handle costs ≈5 µs — so the cost
   is in the first per-frame resolve internals (candidate areas: `zero_texture_refresh` cold
   path, descriptor + RT-storage checks). Next step would be a bounded sub-trace inside that
   call before any change; removing most of it is the shortest measured path toward the
   30 FPS target (needs ≈5–7 ms/frame).
2. Program-switch + constant uploads (≈1 ms) and GL submissions (≈1 ms) as the follow-ups.
3. Memory headline unchanged: PSS + swap ≈ 910–935 MiB, only ≈7 MiB safely reconstructible in
   gameplay; the zero-swap gate is not met and no reclamation is proposed from the current
   evidence (see `evidence/m5-heap-owners/`).

## Known gaps / explicitly not done

- Moving-scene, battle, map and transition coverage (required before promoting any flag).
  First attempt (2026-10-16): the diagnostic stick path accepts and publishes stick events
  (21× `HID_DIAGNOSTIC_PRESS` with `stick=0,±30000` across four directions, verified in the
  runtime log `latest-moving2.log`), but no measurable scene displacement appeared in-game
  (frame diffs ≤ ~1/255 per channel vs. the pre-move frame). The stick-to-gameplay route is
  unresolved; these samples remain open.
- Allocation-owner trace (≥1 MiB allocations with call sites and lifetimes) and repeated
  street→sheriff→street cycles.
- M6 cache implementation and encoder provisioning; texture-460 lazy-copy implementation
  (rejected on trace evidence, revisit only with a new mechanism).
- `glFinish`/GPU-wait classification beyond the existing finish measurement.
