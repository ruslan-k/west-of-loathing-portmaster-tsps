# FPS frame-timeline and draw-path attribution (2026-10-16)

Roadmap section 3 / recommended commit 1 ("instrumentation only: lightweight frame timeline and
GPU-wait attribution"). All runs use owner section `a25600ce…`, the controlled save, the Spruce
principal launch path and the m1m5 harness (30 s menu + 30 s stationary Boring Springs, cold
caches). Runtime hash per build is recorded in each `*-receipt.json`.

## Instrumentation (opt-in, off by default)

`COTM_REPLAY_PHASES=1` enables, per 60 frames:

- Phase wall clocks: `decode` (command decode), `other` (non-draw records), `drawcall` (draw
  records, full interval), `drawfirst` (subset: first draw after a render-target change),
  `copy`, `draw-cpu` (thread CPU inside draws), `NVN_REPLAY_OP` top-10 operations,
  `NVN_RECORD_PROFILE` (guest-thread recording).
- `NVN_DRAW_SPLIT` — draw-path sub-spans, independent of the phase mark chain:
  `a1` entry→catalog resolve, `a2a` assignments/bank copy/slot logs, `a2b` glUseProgram +
  uniform uploads, `a2c1` texture selection (quiet-pick resolve), `a2c2` t0 resolve+bind,
  `a2c3` second-sampler resolve+bind, `a2c4` remainder, `a3` geometry decode, `mid` vertex
  marshalling + colour state, `index` element-buffer prep, `submit` the GL draw calls.

Profiler overhead A/B (matched pair, build `dtime1`): within run-to-run noise (game elapsed
−0.7 ms ON, menu +1.4 ms ON; replay identical). All figures below are from profiled runs.

## Measured draw split (stationary game, stable windows)

| Span (ms/frame) | dtime1 | dtime3 | dtime4 | dtime5 |
| --- | --- | --- | --- | --- |
| a1 entry+catalog | (in front) | 0.50 | 0.52 | 0.39 |
| a2a banks/logs | (in front) | (in a2) | 0.16 | 0.12 |
| a2b glUseProgram+uniforms | (in front) | (in a2) | 1.01 | 0.81–0.84 |
| a2c1 texture selection | (in front) | (in a2) | (in a2c) | **4.33–4.55** |
| a2c2 t0 resolve+bind | — | — | (in a2c) | 0.22 |
| a2c3 second sampler | — | — | (in a2c) | 0.005 |
| a2c4 remainder | — | — | (in a2c) | 0.006 |
| a3 geometry decode | (in front) | 0.24 | 0.24 | 0.21 |
| mid marshal+state | 0.90 | 0.92 | 0.94 | 0.77–0.78 |
| index prep | 0.33 | 0.33 | 0.33 | 0.27 |
| submit (GL calls) | 1.11 | 1.12 | 1.12 | 0.97–1.02 |
| front (a1+…+a3) | 6.35–6.68 | 5.46–5.73 | — | — |

Cross-checks: `NVN_REPLAY_OP` total for draw records ≈ 8.8–9.2 ms/frame; phase `drawcall` +
`drawfirst` ≈ 8.5–9.2 ms. The 6 first-after-target-change draws average ≈ 820 µs each; the
remaining ≈ 62 draws average ≈ 68 µs. `quiet-pick` resolves slot 0 on every draw (one
`nvn_render_sampler` call per draw); the same handle re-resolved immediately afterwards costs
≈ 5 µs — so the ≈ 100 µs/draw sits in the first per-frame resolve path, not in the call itself.

## Ranked critical-path costs (CPU side, stationary game)

1. **Texture-block first resolve (`a2c1`, ≈4.4 ms/frame)** — one `nvn_render_sampler` resolve
   per draw (~100 µs each, ~44–70 draws/frame) in the quiet-pick selection. To verify before
   any change: what inside the first per-frame resolve is expensive (the immediate re-resolve
   of the same handle is ~5 µs) — candidate: cold path in `zero_texture_refresh` / descriptor
   and RT-storage checks.
2. **Shader program switch + constant uploads (`a2b`, ≈0.8–1.1 ms/frame)** — one
   `glUseProgram` plus two 96-float `glUniform1fv` per draw.
3. **GL draw submission (`submit`, ≈1.0 ms/frame, ~60 calls ≈17 µs/call)**.

Frame context (dtime5 game): elapsed ≈ 37.6 ms, replay ≈ 25.9 ms (replay CPU ≈ 13.6 ms),
present ≈ 2.0 ms, finish ≈ 11.8 ms, swap ≈ 1.5 ms; `other` ≈ 3.5 ms; decode ≈ 0.9 ms;
guest-thread CPU ≈ 20 ms/frame.

## Files

- `dtime1-*`, `dtime1-noph-*` (runtime `66434aab…`) — first split + profiler overhead pair.
- `dtime2-*` (`d636f9fb…`), `dtime3-*` (`a4d52519…`) — front/mid, then a1/a2/a3 refinement.
- `dtime4-*` (`30668295…`) — a2a/a2b/a2c refinement.
- `dtime5-*` (`a535d241…`) — texture-block refinement (a2c1..a2c4).
- `profphases2-*` — initial replay-phase profile with the operation table.

## Limitations

- Stationary scenes only (menu + stationary street); movement, battle, map and transitions
  are not covered yet (roadmap requires them before promoting any flag).
- Sub-spans are wall time on the replay thread; overlapping guest-thread work is not folded in.
- `a2c1` includes several bounded diagnostic blocks whose per-session spend is reported by
  their own counters; the dominating cost is the per-draw resolve, not those blocks.
- No runtime behavior changed by this instrumentation; all spans are additive counters.
