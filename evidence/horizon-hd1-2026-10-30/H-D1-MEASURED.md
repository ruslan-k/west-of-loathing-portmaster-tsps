# H-D1 measured — DrawArrays CPU is one stage: the quiet-pick sampler call

Build: canonical overlay + `image-update-fixed` + fixed ledger.
ELF `5566a5293eab7f506590cf6d97c7e94bbc70fd6a1460651bce0ca553895936a6`.
Fresh boot, 240 s scripted route, `WOL_OP_V3=1`, `WOL_DA_CPU_SPLIT=1`, **`AW_RELEASE=0`**.

## Why every earlier attempt showed nothing

`diag_printf()` is a **no-op while `AW_RELEASE=1`** (`native/aw_release.h:13`), and the probe's standard
env sets `AW_RELEASE=1`. The ledger was running the whole time and printing into a black hole; the
banner only appeared once the arm was run with `AW_RELEASE=0`. Any `diag_printf`-based instrumentation
run needs that flag, or must use plain `printf` like `WOL_OP_V3` does. This alone invalidated the
"gate never fires" hypothesis from the previous checkpoint.

## Result (63 completed 60-frame windows, medians)

| Quantity | ms/frame |
|---|---:|
| DrawArrays wall (enclosing span) | **7.620** |
| DrawArrays CPU (enclosing span) | **6.225** |
| Residual CPU (unexplained) | 0.063 |
| `NPS_A2C1` | **5.644** |
| `NPS_SUBMIT` (the `glDrawArrays` call itself) | 0.281 |
| `NPS_MID` | 0.111 |
| a1 / a2a / a2b / a2c2 / a2c3 / a2c4 / a3 / index | 0.011 / 0.012 / 0.027 / 0.031 / 0.003 / 0.003 / 0.011 / 0.026 |

Reconciliation against the independent same-run ledger:

```
H-D1 total CPU   6.225 ms/frame
WOL_OP_V3        6.186 ms/frame   (DrawArrays, n=3, sum_cpu_ms median over 3800 rows)
difference       +0.63%           (budget ±5%)
```

Profiler overhead: the ON arm measured 40.27 ms against the 40.98 ms control (same tree, same scene),
i.e. inside the ±2 ms boot-to-boot noise, and the reconciliation residual is 1% of the draw.

## Identification

`NPS_A2C1` (`nvn_render.h:1337-1449`) is the *quiet-pick* texture resolution: it walks up to 128 bound
fragment slots and calls `nvn_render_sampler()` on the first live candidate, then binds it. One such
call per draw, three per frame, and each one runs the full sampler preparation including
`zero_texture_refresh()` — the path already known to re-upload texture `id=82` (1280x720, format 0x25)
as **3.69 MB every frame** (14 GB per run, `ZERO_REFRESH_STATS`).

So the DrawArrays CPU budget is not program/uniform/vertex code and not the `glDrawArrays` driver call:
it is **texture/sampler preparation of the picked sprite sheet**, exactly the class the roadmap said to
hand to H-S1. The remaining ~0.4 ms is `glDrawArrays` submission plus state work.

## What this does and does not prove

- Proven: where the 6.2 ms of DrawArrays CPU goes, within ±0.6% of an independent ledger, with a 1%
  unexplained residual.
- Not proven: that removing the upload or caching the pick yields a frame-time win. The same upload was
  already shown to be off the critical path twice on the older build (`WOL_REFRESH_DIRECT` and the GPU
  blit), and the frame is bandwidth-shaped rather than core-clock shaped (pinning Mali at 600 MHz did
  nothing). H-S1 must therefore reconcile the sampler CPU against the whole frame, not just against the
  draw.
