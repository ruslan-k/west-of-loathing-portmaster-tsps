# Draw-success diagnostic overhead: same-binary A/B/A/B

Experimental owner-device checkpoint, 2026-10-15. Only the success-log gate is implemented; no asset, shader, resolution, affinity, clock, VM, readback or allocator change is part of this checkpoint.

## Change and safety contract

- Default: successful per-draw and downsample traces are off. `WOL_DRAW_TRACE=1` restores the verbose control without rebuilding. Only literal `1` enables it; `WOL_QUIET` keeps its existing separate meaning.
- Retain one `WOL_DRAW_TRACE detailed=...` startup receipt and existing periodic telemetry. Keep failures, unknown operations and pointer/range guards visible.
- Both original `glGetError()` calls still execute unconditionally; the error is stored before deciding whether to print. Nonzero draw/blit errors print in either mode. No GL operation, texture binding, draw counter or resource lifetime was gated.
- The compiled policy regression uses the actual C helper and the two actual GL-result blocks, tests six environment values, flips the environment after initialization, and verifies all four mock GL queries plus both error outputs.

## Method and observed result

Four separate principal/menu launches of the **same binary**, with the same SHA-verified initial owner-save snapshot before each launch: A1(trace=1), B1(0), A2(1), B2(0). Continue into stationary Boring Springs outside Alice's office; visually confirm the same location/position before each read-only `/proc` sample. Each window is approximately 30 seconds.

Identical measurement overrides: `COTM_INPUT_DIAGNOSTIC=1 WOL_RECT_TRACE=off MOMO_FRAME_CLOCK=1`. The launcher keeps its repaired UV/stencil defaults. Only `WOL_DRAW_TRACE` differs. `off` is an explicit non-rectangle value: an empty value would trigger the launcher's `${VAR:-default}` fallback. The older gfx265 window used different diagnostics and is **not** the A comparator.

See [comparison.json](comparison.json) for per-run measurements and definitions:

- Log growth: A **312.26 / 329.46 KiB/s**, B **27.04 / 23.80 KiB/s**. Mean **320.86 → 25.42 KiB/s**, **−92.08%**.
- Presents/s: A **11.64 / 11.65**, B **12.36 / 12.13**. Mean **11.65 → 12.25**, observed **+5.12%**.
- Summed process CPU ms/frame: mean **133.24 → 126.23**, observed **−5.26%**. Overall utilization stays about **155% of one CPU core**, not 155% of the whole machine.
- Median period: A **82.25 / 83.46 ms**, B **77.89 / 79.32 ms**. P95: A **88.56 / 89.73 ms**, B **84.24 / 84.06 ms**.
- Zero nonzero `glerror` records in all four sample windows. This means the retained error checks reported no errors, not that quiet mode eliminated the queries.
- Every observed complete present still has full readback, `texture-draws=0 status=INCONCLUSIVE`. This phase does **not** repair presentation-proof accounting or enable sparse sampling.

These are exploratory two-repetition measurements per mode, not a confidence interval or a universal gameplay FPS claim. The scene animates and cache/swap pressure differs: process major faults span **29.78–42.41/s**. Mean RSS did not decrease, and swap remains occupied. No energy, watts, battery-life or speaker-output improvement is claimed.

## Visible acceptance and cleanup

- Real KMS captures: A1/B1 menus including the WANTED mask; all four matched gameplay scenes including player/Cactus Bill bodies; A1/B1/B2 map state. The largely blank map remains an unresolved independent defect, not a claimed fix.
- B2 `walk-right` and `walk-left`: visible relative movement after diagnostic Npad stick commands. These are **not physical-button validation**. Map open/close returns to the live scene.
- Each test stopped only its recorded runtime PID/start identity, then allowed principal to restore MainUI. Final [read-back](final-readback.json): installed runtime SHA-256 verified, original save snapshot restored and hashed equal, no `wol-horizon`, MainUI alive. The [final real KMS capture](trace-off-b2-restored-menu.png) shows the Spruce PORTS menu.
- Old runtime and owner saves are retained privately on the device; no owner-save data, executable or game bundle is published.
- Harness-only retries: a cross-filesystem save-directory rename to UDISK was rejected before activation; save rotation was redone on the SDCARD filesystem. A negative integer cannot be packed directly into the unsigned packet field; the successful left-stick retry used `x & 0xffff` for its signed-int16 half. Neither is a runtime failure.

## Artifacts and reproduction

- Runtime SHA-256: `c35548fb7e56e6d4edb03523ab579fdce1577ffaa3b8cd2b68df32b7d99ecb5b`.
- Four `*-profile.json` files: bounded raw `/proc` samples and summaries, produced by [the existing sampler](../gfx265/resource-sampler.py).
- Four `*-profile.runtime-interval.log.xz`: byte-for-byte compressed raw log slices. Four `*-config.log` files: extracted identity, diagnostic-mode and input receipts from the corresponding complete owner-local logs.
- `reduce.py`: recompute with `python3 evidence/resource-draw-logging/reduce.py`; output must match `comparison.json`. Frame clocks must be contiguous and monotonic; one final A2 readback/slow-frame receipt is outside the byte-slice boundary, explicitly recorded in the result rather than treated as a missing internal frame.
- `tests.json`: 22 baseline unit tests, seven standalone regression commands, and successful upstream overlay dry-check.
- `review.json`: independent code-only review passed for the small runtime diff and its compiled policy test. This does not retroactively clear historical code or certify device performance.
- `build.log.xz`, `artifact.json`, `SHA256SUMS`: native build output, artifact/deployment metadata and evidence hashes.
