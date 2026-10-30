> **CORRECTION AFTER H2, 2026-10-30:** this older stop-loss document's attribution of texture `id=82` dirty solely to a guest `zero_texture_pool_flushed()` is **superseded** by [new H2 source/device evidence](horizon-h2-2026-10-30/README.md): `nvn_render_color_copy` copies the **entire 1280×720 frame** from source `id=2` to destination `id=82` and itself sets `dst->zero_cpu_dirty=1`; `zero_texture_pool_flushed` was not reached in that build. The stale-pixel diagnostic `WOL_REFRESH_OFF=1` improved the H2 frame only 42.90→37.37ms and is **not valid gameplay**. Moreover, the project's actual release needs both exact requested update v327680 and Gun Manor normal entry, not just a fast installed Linux version. Current authoritative [§28](../docs/optimization-roadmap-active-native-unity-2026-10-29.md#28-mandatory-update-and-dlc--architecture-and-optimization-reset-2026-10-30). This file is historical evidence, not current optimization authority.

# Horizon stop-loss decision — 2026-10-30

Per roadmap §27: Horizon gets **at most** H-T0 (prove whether the `id=82` re-upload can be avoided
without changing the image) and one H-T1 A/B with a **≥2.0 ms whole-frame** threshold. Otherwise the
branch is parked.

## H-T0 answer from source and the committed logs (no new device run)

1. The dirty flag for `id=82` is not set by the runtime's own bookkeeping. It is set by
   `zero_texture_pool_flushed()` (`native/nvn_textures.h:608`), which runs only when the **guest**
   declares a write through `nvnMemoryPoolFlushMappedRange` or `nvnBufferFlushMappedRange`
   (`native/nvn_memory.h:213,234`).
2. The consequent upload is logged as `ZERO_TEXTURE_FLUSH_UPLOADED id=82 format=0x25
   native-cpu-bytes=preserved before-sampler rgba8-copy-levels=1` and `ZERO_REFRESH_STATS id=82
   calls == frames, uploaded-bytes 3.69 MB/frame` (14 GB per 3840-frame run, c1–c8 evidence).
3. So every frame the guest tells the runtime "these pixels are mine and they changed", and the
   runtime re-uploads the whole 1280x720 surface before sampling it.

**Conclusion: the upload is not a spurious wake-up; it is the guest's own declared write.** Avoiding it
would either skip pixels the guest just produced (image changes) or require a partial-range update,
which needs a flush-range diagnostic that this build does not emit (`ZERO_POOL_FLUSH_STATS` is not
present in any committed log). Producing that evidence is a new instrumentation cycle — exactly what
the stop-loss forbids without a quantified hypothesis, and the hypothesis here ("the guest over-declares
its write range") cannot be tested from existing data.

## H-T1

Not run. There is no proven avoidable operation to A/B, so a reversible test would only measure the
profiler again.

## Decision

**Horizon is parked as archived research.** The installed Unity port measures 24.1 ms (**41.4 fps**)
with live audio, zero swap and clean return to menu through the sanctioned principal launch
(`evidence/unity-trackA-2026-10-30/`). Horizon's best measured frame is 40.2–40.6 ms (**~24.7 fps**)
without an equivalent audio path. Nothing in the Horizon branch is on the shipping path for this game.

Reopening requires a new quantified hypothesis plus a credible remaining 2–5 ms lever, per §27.
