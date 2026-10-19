# 720p acceptance — current §16 P0

## Frozen protocol (results pending, no acceptance claim)

Follow optimization-roadmap §16 at owner revision `78167a9`; do not resume the older
unbounded memory/clock/cache experiments. This checkpoint prepares the required
three alternating valid stationary/movement A/B pairs. It does **not** claim
interior, battle, extended play, save/load, physical controls/audio or no-swap acceptance.

- One frozen ARM64 ELF: `b60057eaeafa738e9b48cf2b68b356545ee5ffde2c57bb84a5da5722e5935158`.
  Recovered source/overlay identity is in `../allocator-history/overlay-verification.json`.
  The added SDK allocation hooks are inactive with `WOL_ALLOC_TRACE=0`.
- Same corrected-map section: `49bd16718ed0dc46f16599255791c7603e8aa2b5f04898784a39d6cacb9d0722`;
  identical private gulch save hashes must be verified across all arms.
- Required order: `accept-a1`, `accept-b1`, `accept-b2`, `accept-a2`, `accept-a3`,
  `accept-b3` (A-B / B-A / A-B). Only `WOL_UPRENDER_720` changes, OFF for A and ON for B.
- `WOL_UPRENDER_TRACE=0 WOL_ALLOC_TRACE=0 WOL_RT_ORIGIN=0`. No SDK span, pagemap,
  allocation-page, VMA sampling or per-draw trace in timing arms. Sparse TransferMemory,
  upload skip, COW, PBO, ASTC post-copy and other optional speedups stay OFF.
- Stock CPU/GPU policy is left untouched; actual effective frequencies, Mali contexts,
  PSS/SwapPSS, VM faults, swap page-ins/out and MemAvailable/CmaFree are in the same
  lightweight two-second ledger. No false PSS+driver sum or independent panel FPS.
- Require actual KMS title → CONTINUE → gameplay HUD. `route-gulch.json` requests
  20 bounded alternating movement holds, map/return and pause/return; request labels
  are NOT scene/physical input proof. Inspect the saved real frames and delivery log.
- Opt-in adaptive watchdog: **5 seconds in settled gameplay**, **30 seconds during
  menu/load/overlay transitions**. Check every second, including while an input helper
  sleeps/captures. On a real timeout, collect bounded exact-owned PID/start-tick
  proc/thread/GDB diagnostics, then save restoration and actual Spruce recovery.
  GDB is stall-only; a clean run does not claim its branch was exercised.
- Each input request gets monotonic send/capture timestamps. They are diagnostic request
  timings, not physical input proof. Preserve every labelled capture and JSON receipt.
- Any stall/unknown scene/identity mismatch invalidates that arm. Stop the batch for
  cause diagnosis, retain the rejected trial, and never silently substitute a good arm.
- Aggregate complete frame intervals/P50/P95/P99 and long gaps; do not apply the old
  two-second warmup exclusion to short movement actions and then call idle frames moving.

**Promotion remains blocked** until §16's broader route, correctness, saves, controls,
audio and stability gates pass. Normal swap remains enabled. No defaults changed.
