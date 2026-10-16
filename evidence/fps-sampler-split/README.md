# Sampler-path micro-zones (WOL_SAMPLE_SPLIT) - a2c1 named: it is the per-frame re-upload of texture 460 (2026-10-16)

Roadmap section 3 follow-up. Build `dtime8` (opt-in `WOL_SAMPLE_SPLIT=1`; zone timers only, no
behaviour change) adds ten wall-clock zones inside `nvn_render_sampler_prepare_mode` and
`nvn_render_sampler`: `pp1` descriptor+resources, `pp2` identity/sampler rejects, `pp3`
`zero_texture_refresh`, `pp4` require/sample guards, `pp5` sampler builder+filter/wrap, `sm1`
prepare call + copy-trace + storage sampler require, `sm2` unit/packaged/t2 touches, `sm3` bind +
parameters + cpu-image refresh, `sm4` scaled-check + texdiag + reports. One summary line per 60
frames; runtime `414efb1f…`.

## Result - the ~3.8-7.5 ms/frame a2c1 span is 95% `zero_texture_refresh` (zone pp3)

Same device, section `a25600ce…`, controlled `tut_gulch` save, harness (30 s menu + 30 s game),
one-variable arms; ms/frame:

| zone | menu (normal) | game (normal) | menu (GPU-copy arm) | game (GPU-copy arm) |
| --- | --- | --- | --- | --- |
| pp1 descriptor+resources | 0.038 | 0.240 | 0.030 | 0.302 |
| pp2 rejects | 0.011 | 0.034 | 0.011 | 0.052 |
| **pp3 zero_texture_refresh** | **7.576** | **5.773** | **0.004** | **0.019** |
| pp4 guards | 0.007 | 0.019 | 0.006 | 0.030 |
| pp5 builder+wrap | 0.008 | 0.023 | 0.008 | 0.030 |
| sm1 prepare+traces | 7.665 | 6.162 | 0.079 | 0.541 |
| sm2 unit/packaged/t2 | 0.008 | 0.021 | 0.007 | 0.031 |
| sm3 bind+params+cpu-image | 0.155 | 0.200 | 0.068 | 0.275 |
| sm4 scaled+texdiag+reports | 0.003 | 0.010 | 0.003 | 0.015 |
| `a2c1` (NPS) | ~7.5 | 6.15-6.35 | ~0.07 | 0.385 |

Mechanism (counters in the same logs): once per frame the game copies 3.69 MB into texture 460
(1280x720 RGBA8); the flag makes the first sample of 460 in that frame run a full
`glTexSubImage2D` re-upload - `ZERO_TEXTURE_FLUSH_UPLOADED` 3049 events total, **2824 of them
id=460**, `ZERO_REFRESH_STATS id=460 calls=2816 uploaded-bytes=10 380 902 400` (~10.4 GB in one
run, ~578 MB/s effective). The fast `memmove` copy path (`rgba8-copy-levels=1`) is already
engaged, so the cost is the GL upload itself, not a per-pixel decode. The refresh call runs 88
times per frame (nearly free when the flag is clear - the whole 6 ms is the one flagged call).

## GPU-copy arm (existing `WOL_COPY_GPU=1`) re-measured with the zones

`WOL_COPY_GPU=1` removes the chain completely: pp3 -> ~0, FLUSH_UPLOADED 5 events, a2c1 0.385
ms. But `finish` grows: menu 14.49 -> 19.96 ms, game 12.63 -> 25.94 ms, and elapsed goes the
wrong way: menu 37.92 -> 44.01 ms, game 34.00 -> 48.00 ms. The earlier "net negative" verdict is
confirmed with exact attribution: the mid-frame GPU blit serialises the GPU pipeline more than
the overlapped CPU upload costs. A useful future candidate would be a *different* pipeline shape
(blit at frame end with explicit dependency handling), not the current mid-frame swap.

## Conclusion

- a2c1 is closed as a *mystery*: it is the per-frame 3.7 MB texture-460 re-upload on the first
  sample, worth ~6 ms/frame of CPU on this scene (and ~10.4 GB/run of uploads).
- Removing it in-place (GPU copy) costs more than it saves in the current architecture; the
  remaining ideas (frame-end blit pipeline, partial uploads, packed upload formats) each change
  visuals or pipeline semantics and need their own analysis.
- The zone timers are opt-in and stayed clean: 0 GL errors, visual parity, all runs CLEANUP.

## Files

- `run-m1m5-dtime8-1/` (normal) and `run-m1m5-dtime8-gpucopy/` (WOL_COPY_GPU=1) in the spike
  tree: receipts, analyses, effective-env, xz logs.
- Build: `wol-horizon-build-dtime8` (`414efb1f…`) - source edits: ten zone timers in
  `native/nvn_render.h` (block `wol_sample_split` + `wol_ss_*` helpers; entry/exit pairs in
  `nvn_render_sampler_prepare_mode` and `nvn_render_sampler`). The device runs `dtime8` now
  (previous `astcfix1` kept as `wol-horizon.bak-astcfix1-20261016`).
- Harness: `session.py` gained `WOL_SAMPLE_SPLIT` and `COTM_RESOURCE_LOOKUP_CACHE` passthroughs.
