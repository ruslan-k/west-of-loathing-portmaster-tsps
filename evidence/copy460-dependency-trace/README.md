# Texture-copy (460) dependency trace — roadmap section 4 verdict

Opt-in `WOL_COPYTRACE=1` (builds `3878c5de…` / `8a8d113f…`, runs `m1m5-cpt1` / `m1m5-cpt2`,
same layout/save/harness). The trace is bounded (1024 events), read-only, and tracks the
colour-copy pair by OBJECT identity (ids are per-session).

Events: `1`=copy(dst←src), `2`=draw into src, `3`=GPU sample of dst, `4`=GPU sample of src,
`5`=draw into dst. An `analyze_copytrace.py` pass (see `cpt2-copytrace-analysis.json`) folds
the events into inter-copy intervals and flags the lazy-alias hazard
(“dst sampled after the source was re-drawn”).

## Observed steady-state pattern (each frame, 256/256 intervals)

```
copy src→dst   (rotating source: three buffers, objects 0x…850/0x…910/0x…9d0 ≈ ids 30/31/32)
sample dst ×2  (immediately after the copy)
draw into src  (the source is re-rendered for the next frame)
```

SUMMARY windows (every 60 frames through frame 2880): `copies=1/frame`,
`draws-src-since-copy=1`, `samples-dst=2`, `samples-src=0`. No interval anywhere in the run
sampled the destination after the source had been re-drawn
(`hazard_sample_dst_after_redraw = 0`); the destination row of the trace never saw a direct
draw (`kind=5` absent).

## Verdict (roadmap section 4 decision)

- The chain is fully characterised for the stationary scene: the destination is read only
  inside the window `copy → first write to the source`; the source itself is never sampled.
- **A guarded lazy alias is rejected for now.** The source is rewritten on *every* frame, so
  the roadmap’s own deferred-copy construction would have to materialise the destination
  before that per-frame mutation — preserving the full per-frame copy cost and yielding no
  FPS mechanism gain. The only gain path (never materialising) would need an invariant the
  trace cannot guarantee beyond stationary scenes (movement, battle, transitions, CPU reads
  are unmeasured), and it would break exactly the constructs the roadmap forbids (stale
  snapshot substitution).
- `WOL_COPY_GPU` (immediate blit) remains off for the earlier measured reason (mid-frame
  serialisation). The copy chain stays as-is; no runtime behaviour changed by this work.

Artifacts: `cpt1-*` (first corrected run), `cpt2-*` (final trace with dst objects and samples),
`cpt2-copytrace-analysis.json`, `tools/analyze_copytrace.py`.
