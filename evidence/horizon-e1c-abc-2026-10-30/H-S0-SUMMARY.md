# H-S0 — offline read of the committed sampler-split log (c8)

Source: `evidence/horizon-e1c-abc-2026-10-30/c8-samsplit.log.xz` (ELF `f5c6f6f2`, 65 completed
60-frame windows, `WOL_SAMPLE_SPLIT=1`). No device run, no new numbers invented.

| zone | median ms/frame | p95 |
|---|---:|---:|
| pp1 descriptor + resource resolve | 0.304 | 0.336 |
| pp2 reject/coherence checks | 0.058 | 0.072 |
| **pp3 `zero_texture_refresh`** | **6.774** | **7.065** |
| pp4 cpu-view validation | 0.025 | 0.039 |
| pp5 tail | 0.033 | 0.043 |
| sm1 (enclosing `nvn_render_sampler` up to the storage require) | 7.318 | 7.564 |
| sm2 packaged materialize | 0.037 | 0.047 |
| sm3 sampler-state upload | 0.328 | 0.365 |
| sm4 diagnostics | 0.014 | 0.020 |

Call counts per frame: 120.1 for pp1/pp3/pp4/pp5 (pp2 is incremented twice per call by design).

## What this means together with H-D1

- These are **nested** spans: sm1 contains pp1..pp5. 0.304+0.058+6.774+0.025+0.033 = 7.194 ≈ sm1 7.318,
  so the enclosing span is fully explained and adds nothing.
- The load is one zone: `zero_texture_refresh`, ~6.8 ms of a 40.4 ms frame, spread over 120 sampler
  calls — but H-D1 measured **5.644 ms in just three calls** (the quiet-pick resolution inside the
  three DrawArrays). So the expensive calls are the draw-side picks, at roughly 1.9 ms each, while the
  remaining ~117 calls average ~9 µs. H-S1 must therefore tag the caller class, not just the totals.
- `zero_texture_refresh` re-uploads texture `id=82` (1280x720, format 0x25) as 3.69 MB **every frame**
  (`ZERO_REFRESH_STATS calls == frames`, 14 GB per run). That is the single routine H-S1 has to
  attribute and H-S2 may then optimise — with the standing caveat that the same upload tested as
  off-critical-path twice on the older build, and the frame is bandwidth-shaped rather than
  core-clock-shaped (Mali pinned at 600 MHz changed nothing).
