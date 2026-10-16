# Resource-lookup hint cache A/B (2026-10-16) - candidate closed, no FPS gain

Roadmap section 3 follow-up: the ranked cost table puts ≈4.4 ms/frame in the draw-path texture
selection (`NPS_A2C1`). The first static review found `nvn_render_resources` (called from
`nvn_render_sampler_prepare_mode` on every texture resolve) doing a full bounded scan of the
4096-entry texture/sampler arrays unless `COTM_RESOURCE_LOOKUP_CACHE=1` enables the hint cache
(existing code, off by default). This pair of runs measures that flag as-is.

## Setup

- Build `astcfix1` (`e46cdd1f…`), owner section `a25600ce…`, controlled save
  `tut_gulch` (Thousand Snakes Gulch), harness `wol_memory_benchmark.py` (30 s menu + 30 s
  game, cold caches), `COTM_REPLAY_PHASES=1` on both arms.
- Arm `m1m5-rlcache-1`: `COTM_RESOURCE_LOOKUP_CACHE=1`. Arm `m1m5-rlctl-1`: only
  `COTM_REPLAY_PHASES=1`. One-variable difference.

## Result (per-frame, ms)

| Span | menu cache | menu ctl | game cache | game ctl |
| --- | --- | --- | --- | --- |
| elapsed | 39.23 | 38.09 | 43.21 | 44.64 |
| replay | 28.21 | 28.32 | 33.65 | 33.72 |
| finish | 14.29 | 14.26 | 20.67 | 20.75 |
| a2c1 (texture selection) | (menu tail ~7.5) | - | 3.82 | 3.86 |

The cache itself works as designed: `NVN_RESOURCE_LOOKUP_PROFILE` reports texture hits 359 028 /
misses 2 118, sampler hits 361 140 / misses 6, scan-steps 376 050 cumulative - with the cache on,
the fallback scan runs only on the 2 118 misses (~177 steps each), and even the uncached scan
amounts to ~0.4 us/frame of work. **No measurable FPS effect** (menu slightly worse, game
slightly better, both within run-to-run noise; `a2c1` unchanged).

## Conclusion

The 4096-entry resolve scan is NOT the a2c1 cost driver. Candidate closed. The remaining ≈3.8
ms/frame (game) / ~7.5 ms/frame (menu, ~1.07 ms per draw) sits elsewhere inside the first
per-frame resolve path; the next step is per-micro-zone wall timers inside
`nvn_render_sampler_prepare_mode` + `nvn_render_sampler` (descriptor, zero-refresh, storage-
sampler-require, rt-storage-require/sample, storage bind+parameters, cpu-image refresh, T2
branches), same NPS-style opt-in aggregation, before any behavioural change.

Harness note: `session.py` gained a `COTM_RESOURCE_LOOKUP_CACHE` passthrough for these runs.

## Files

- `run-m1m5-rlcache-1/` and `run-m1m5-rlctl-1/` in the spike tree: receipts, `analysis.json`,
  `effective-env.json`, `menu.json`/`game.json`, `runtime.log` (xz on the host).
- Device: layout `m5-layout-astcfix1.json`; saves under `/mnt/UDISK/wol-goal-20261015/`.
