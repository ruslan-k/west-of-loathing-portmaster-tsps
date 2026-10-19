# West of Loathing / TrimUI Smart Pro S — FPS and zero-swap optimization roadmap

**Status:** living technical plan; tested and rejected experiments are explicitly separated from proposed work.  
**Reviewed:** 2026-10-19 against `main` `f7c72a3232eeb06e9ee63356f026f1f78db99247` (source/evidence/static audit; no new handheld run). **Current plan: [§18](#18-post-acceptance-repository-audit-and-bounded-finish-plan-2026-10-19).** §§1–15 are historical, §§16–17 preserve pre-acceptance decisions and measurements; §18 supersedes their obsolete default/scene-status lines. No Box64; permanently handheld only.
**Platform:** owner-supplied Switch Unity 5.6.5p1 ARM64/IL2CPP, native Horizon adapter, SpruceOS, Mali-G57 GLES 3.2, approximately 963 MiB RAM. No Box64.  
**Purpose:** identify *new* experiments after the first roadmap was executed. [Historical resource studies](resource-optimization.md) and [M1/M5 measurement contracts](memory-benchmark.md) remain authoritative for their own earlier checkpoints.

> This is **not** a claim that either 30+ FPS or zero-swap has been attained. Device reports use varying saves/scenes and diagnostic builds. At the original review, `dtime8` (`414efb1f…`) instrumentation was not published. That gap is now closed by `a3793a1`: clean overlay application matches all 199 native source files of the measured build. Further execution results and still-open gates are recorded in §11; implementation of an opt-in mechanism is not release acceptance.

**2026-10-19 current decision (supersedes the 2026-10-18 question):** [the device's handheld preflight](../evidence/handheld-preflight/README.md) established that the inherited AM implementation **already answers Handheld (`0`)**; the observed WoL launch calls only AM commands 0/1/9/6, with **no observed operation-mode (5), default-resolution (60), or VI ListDisplays request**. Unity still allocates 1920×1080 internal render targets and the SDL/KMSDRM output is 1280×720. **Do not implement another handheld/TV switch or speculative AM command 60.** Locate the Unity/SDK origin of the render-target dimensions as [§15](#15-m7-after-handheld-preflight-unity-render-target-origin-and-720p-plan) describes. The content-aware texture-460 upload skip was also tested without a reproducible FPS win; it is not P0 anymore.

**Latest §15 execution:** [native UpRender producer and repeated component-settings A/B](../evidence/uprender-owner/README.md) identifies the Switch IL2CPP consumer. Three 720 candidates observe **32.638 / 33.348 / 33.878 runtime presents/s** in gulch versus valid controls **24.019 / 24.226**. One attempted 1080 control freezes and is excluded, not concealed by successful cleanup. SwapPSS remains **533–552 MiB**; there is no full-game/no-swap acceptance or default promotion. See §§15.8–15.9; the original handheld and upload-skip decisions stand.

**Correction to latest memory interpretation:** the [readiness/lifetime audit](../evidence/allocator-history/README.md) found that the old `allocmin` phases were still splash/title, not gameplay, and that nested `Reallocate(NULL,n)` could duplicate the tracer's live pointer. §15.15's original counters are retained as historical observations, but its **complete gameplay census / decisive owner exclusion is withdrawn**. The replacement uses actual KMS title/HUD gates, unique live pointers, page unions including allocation history, and a read-only SDK span-table census. No validated no-swap acceptance exists.

**2026-10-19 decision:** [§16](#16-resource-optimization-decision-after-the-720p-and-arena-swap-results) is now authoritative for *next* work. The real Unity `UpRender` 720p component change repeatedly improves measured gulch performance to ~33–34 runtime presents/s; the remaining high-value work is **stability and real-game acceptance**, not another display/NVN override. A guarded 64 MiB zero `TransferMemory` sparse copy measurably reduces swap, but hundreds of MiB remain in unattributed Unity guest arenas; speculative pool caps/page discard/VM tuning are not justified. Experimental optimizations remain default OFF pending broader acceptance.

**2026-10-19 decision update:** existing `UpRender` 720p is the first repeatable whole-frame FPS improvement (+6.2 to +10.0 presents/s moving), while `T2_TRANSFER_SPARSE_COPY` is a separately repeated limited swap-pressure improvement (−44 to −75 MiB SwapPSS). The inner Unity/SDK owner census established no safe page reclaim, so **stop open-ended zero-swap research**. Prioritize full gameplay correctness/acceptance, a rare NVN command-buffer guard, then qualified 720p/sparse defaults. See [§17](#17-october-19-technical-re-evaluation-resource-roi-and-stop-rules).

## 1. Current measurable baseline and open gates

| Measurement | Observed | Interpretation / limit |
| --- | --- | --- |
| Previously repeated Boring Springs street | ~25–27 presents/s | Not guaranteed panel FPS or all-scene FPS |
| Controlled `tut_gulch` sampler run | ~34.0 ms mean frame, with large slow-frame tail; normal mode | Different saved scene than the earlier Boring Springs baseline; do **not** compare as strict A/B |
| `tut_gulch` normal texture sample prepare `pp3` | **5.773 ms/frame** | `zero_texture_refresh`, dominated by per-frame full upload of texture 460 |
| `tut_gulch` `WOL_COPY_GPU=1` | `pp3` ~0.019 ms, but frame ~48.0 ms vs 34.0 ms control | Finish **25.94 vs 12.63 ms**; immediate GPU blit loses overall |
| Guest texture 460 | 1280×720 RGBA8, 3,686,400 bytes, once per frame | ~2,816 refreshes / ~10.38 GB upload in one profiler run |
| Controlled street PSS + SwapPSS | ~910–935 MiB across reported runs | Process committed/swap accounting, not whole-device RAM footprint |
| Short map/pause cycle (60 s) | GPU context commit ~262–274 MiB; PSS ~460–469 MB, SwapPss ~458–467 MB | No growth trend in this window; not a long gameplay/scene-transition or no-swap proof |
| GPU residency census | ~153 MiB estimated host images, ~97 MiB inactive >5 s | Only **~7.1 MiB safely reconstructible** with current semantics |
| ASTC create-time experiment | +8.08 MiB GPU committed without cache before BC content copies; later both ~255 MiB | Native compressed storage works; **no persistent saving after subsequent BC uploads** |
| Zero-swap cold boot | **Not demonstrated** | Process still uses hundreds of MiB of swap; startup/CMA pressure remain |

Goals: at least **30 presents/s sustained** in representative moving, dialogue, map, battle and late-game scenarios, **P95 full frame interval ≤33.33 ms** where appropriate, and **no swap configured before game launch** with no OOM, low memory-pressure stalls and adequate MemAvailable/CmaFree headroom. Benchmark observed presents and screen output separately. Do not claim any target on a single 30-second idle scene.

## 2. Work already implemented, verified, or intentionally closed

| Earlier roadmap item | New status (2026-10-16) | Evidence |
| --- | --- | --- |
| NVN frame phase, draw split, critical-path timing | **Measured**: `COTM_REPLAY_PHASES` with `NVN_DRAW_SPLIT`, ~25.9 ms replay / ~11.8 ms finish in one street profile | [Frame timeline](../evidence/fps-frame-timeline/README.md) |
| First sampler sub-zones | **Measured and reconciled**: `dtime8` source/overlay parity, 199 native files, committed in `a3793a1` | [Source parity](../evidence/roadmap-v2-source-parity/README.md), [sampler split](../evidence/fps-sampler-split/README.md) |
| Resource lookup cache | **Closed for FPS**: 99.4% hit rate; ~0.4 µs/frame lookup scan, no meaningful gain | [Resource-lookup A/B](../evidence/resource-lookup-ab/README.md) |
| Texture-460 copy dependency trace | **Measured**, 256/256 intervals: copy → destination sampled twice → source rewritten; generic deferred snapshot alias **rejected** | [Copy trace](../evidence/copy460-dependency-trace/README.md) |
| Immediate GPU copy (`WOL_COPY_GPU`) | **Rejected/default off**, GPU finish regression confirmed again by micro-zones | [Sampler split](../evidence/fps-sampler-split/README.md) |
| Direct guest-storage upload (`WOL_REFRESH_DIRECT`) | **Neutral** in measured A/B; default off | [Direct upload](../evidence/fps-refresh-direct/README.md) |
| Reusable buffer objects (`WOL_PAIR_RING`) | Implemented, no statistically useful FPS gain | [Pair ring](../evidence/fps-pair-ring/README.md) |
| CPU logical→fast-core remap | Isolated A/B **no repeatable speed-up**; existing launcher still exports `WOL_CPU_OFFSET=4` unless overridden: review default separately | [CPU remap](../evidence/cpu-remap-ab/README.md) |
| Truthful present proof / sparse reads | **Validated**, first proof frame 4, period 300, 2,895 `NOT-SAMPLED` frames | [Sparse proof](../evidence/present-proof-sparse/README.md) |
| M4 wave2 (53 additional textures) | **Device A/B done but not adopted**: −4.7 MiB menu / −1.7 MiB street PSS+SwapPSS, no measured FPS change; original section restored | [Wave2 A/B](../evidence/m4-wave2-device-ab/README.md) |
| M5 `smaps`/VMA phase diffs | **Done read-only**; major Unity allocation owners/free lists **still unknown** | [Heap observations](../evidence/m5-heap-owners/README.md) |
| Texture residency census | **Done read-only**; eviction gate not met with only ~7 MiB demonstrably restorable | [GPU residency](../evidence/gpu-texture-residency/README.md) |
| M6 ASTC device proof and initial cache | **Implemented/tested**: ASTC 6×6 hardware decode, WOL6 cache builder, runtime hook, 16 null-content hits, upload/fallback GL error fixed, GPU RAM delta measured | [ASTC acceptance](../evidence/m6-compressed-textures/astc-acceptance.md), [E2E](../evidence/m6-compressed-textures/astc-e2e-device.md) |
| M6 *create-time content* cache | **Closed as current design**: BC textures observed empty at creation in `tut_main`, `tut_gulch` and `tut_saloonbasement`; content arrives later via CopyBufferToTexture | [Content scene probes](../evidence/m6-compressed-textures/content-scene-probes.md) |
| Map/pause memory stability | **Limited acceptance**: no trend over 60 s while toggling visible map and pause | [Scene cycles](../evidence/scene-cycles-memory/README.md) |

**Do not repeat** earlier buffer-gen/delete, hash-lookup, immediate GPU blit, direct-storage upload, simple fast-core remap, or create-time ASTC content caching without a materially different algorithm and a falsifiable device hypothesis.

## 3. P0 FPS — avoid the texture-460 host upload without an immediate GPU blit

**Why first:** the new sampler micro-zones put roughly **5.8 ms/frame** inside the full 1280×720 `glTexSubImage2D` refresh in `tut_gulch`. Its per-frame CPU-side RGBA copy is already a fast `memmove` and bypassing staging memcpy did not help. The immediate GPU blit removed the upload but cost more GPU-finish time. No approach is yet proven faster end to end.

### 3.1 New candidate: same-frame **GPU sample redirection** while preserving the CPU snapshot

This is deliberately **not** the previously rejected generic lazy-copy algorithm. Keep the existing guest-visible CPU row copy into the destination pool so CPU reads and the copy-time byte snapshot remain correct, but, *only for proven-consistent sampling in the current command interval*, redirect the destination's **GPU sampler binding** to the already-current producer render-target GL texture rather than refreshing/uploading the CPU mirror.

Potentially removes the ~3.7 MB GL upload while retaining cheap CPU copying; it performs **no extra GPU blit**. The opportunity is based on the observed sequence (copy → two destination samples → next source write), but that sequence was observed only for the stationary route and is **insufficient to enable this generically**.

**Preflight instrumentation (required before changing rendering):**
1. Expand `WOL_COPYTRACE` to moving frames, `tut_main`, `tut_gulch`, `tut_saloonbasement`, battle, map, reload and transitions. Log *all* CPU and GPU reads/writes of source and destination, render-target bindings/attachments, acquire/release, source/destination versions and GL context.
2. Verify that both destination samples happen **before** the source is modified, the source GL texture contains the correct copy-time pixels, and destination CPU reads still see the existing CPU copy. A later destination sample (after source modification), changed sampler semantics or unknown context must cause immediate fallback.
3. Confirm no read/write feedback loop, implicit GLES resolve, rotation/crop/flip, filtering, multisample, stencil, texture-level or per-target hazard changes. The three rotating sources cannot be reduced to one unversioned ID.
4. Prototype a single per-command or per-submit **GPU-only redirect** under a new default-off flag (proposed `WOL_COPY_SAMPLE_REDIRECT=1`), restoring ordinary uploads on the first unsafe event. Invalidate the redirect before source rewrites and retain a correct CPU mirror.
5. Trace GPU finish separately: eliminating a driver upload might shift cost into source resolve/sampling and still lose overall.

**Acceptance:** identical visual output in physical KMS captures, correct CPU readback/guest snapshot contracts, no GL errors, no stale textures after source redraw or scene changes, improved *full-frame* P50/P95 in alternating A/B (not only lower `pp3`), and clear per-frame proof of which draws used the shortcut. Abort if hazards are unavoidable in real gameplay.

**Source areas:** `runtime/wol-adapter.patch` → `native/nvn_render.h` sampler resolve and `zero_texture_refresh`, `nvnCommandBufferCopyTextureToTexture` special-case, `native/nvn_texture.h`/NVN coherence hooks; `tools/analyze_copytrace.py`. Record the actual reconstructed source file paths during implementation (overlay diff hunks are not standalone runtime source files).

### 3.2 Fallback candidates if sample redirection loses

- **Render-graph pass restructuring:** a terminal composite that samples the producer directly with correct transformed UVs, avoiding intermediate destination sampling/copy only when the graph semantics allow it. Not equivalent to the already-rejected mid-frame GPU blit. Requires per-pass instrumentation, FBO detachment and host/guest order proof.
- **Async PBO upload experiment:** double/triple bounded unpack buffers, non-blocking fence retirement, full-image upload semantics unchanged. Only worthwhile if driver stall is attributable to synchronous GL upload; PBO still transfers 3.7 MB and can worsen total bandwidth or RAM. A/B against both normal and `WOL_REFRESH_DIRECT`.
- **Damage-region upload** only if a pixel/region diff over real moving frames demonstrates a *small* changed area and dirty rects are accurate. Otherwise full 1280×720 conversion is unavoidable. Avoid CPU full-frame diff overhead without an off-thread/producer source of changed-region metadata.
- **Avoid assuming `glBlitFramebuffer` alone helps**; a previous GPU-side copy serialized the pipeline. Try any alternative only after a dependency/driver timing argument.

Do not accept a 5.8 ms reduction of sampler CPU work that adds ≥5.8 ms to GPU finish. The metric is complete frame interval and visual correctness.

## 4. P0/P1 memory — M6 second-generation, **post-CopyBufferToTexture** compressed cache

**Existing mechanism proven:** ASTC 6×6 `glCompressedTexImage2D` works on Mali-G57, shader sampling matches the tested astcenc reference, and the runtime's WOL6 hash cache/fallback is real. While 82 cached **empty** textures are resident, the GPU context commits 8.08 MiB less than control; after their real BC content is copied in, cache textures convert back to RGBA and the memory delta disappears. A create-time content-hash lookup is therefore not a production optimization.

**Implemented experimentally, default off:** serve the *completed, actual* BC texture from a precomputed ASTC entry **after** its content arrives via `nvnCommandBufferCopyBufferToTexture`. `WOL_ASTC_POSTCOPY=1` requires an explicit texture identity (`WOL_ASTC_POSTCOPY_ID`) and owner-local `WOL_ASTC_CACHE`. The read-only mapped WOL6 cache uses runtime-exact decoded keys, not empty creation-time content. [Single-image A/B](../evidence/roadmap-v2-postcopy-ab/README.md) and [group A/B](../evidence/roadmap-v2-postcopy-group/README.md) distinguish real hits, physical-memory observations and remaining acceptance limits.

**Stages:**
1. **Trace BC writes by texture, region, mip and scene:** count full-image versus partial/multi-call updates, duplicate updates, last-write→first-sample lifetime, format, dimensions and whether the texture ever serves as render target. The `tut_saloonbasement` sample contained 74 BC texture creations but only 8 observed buffer→texture copies; do not assume all BC textures have an immediate complete upload.
2. For a fully populated immutable level-0 BC texture, compute a stable key over the **canonical decoded bytes** (builder already uses `tools/wol_bcdecode_host.c` to reproduce runtime rounding); alternatively verify a canonical BC-block hash only if host/guest linearisation is exact. No fuzzy matching.
3. On a WOL6 cache hit with matching width/height/level/format, replace host RGBA storage **at the point of the completed copy**, or avoid creating RGBA storage for that complete upload when proven possible. Do not issue RGBA `glTexSubImage2D` onto compressed storage. On later partial writes, CPU-image refresh, render-target binding or copy, recreate RGBA backing and clear cache state, with correct GPU synchronization.
4. On a cache miss keep the existing RGBA path. **Never run astcenc synchronously during gameplay**; cache must be generated offline, used read-only, and ideally mapped/lazy-loaded without holding the entire content cache in anonymous RAM.
5. Start with one *real, nonempty, copy-populated* BC texture, then a small group in `tut_saloonbasement`; compare actual `mali0/ctx/<ctx>/mem_allocs` commit, process memory, texture-load latency and visual diff through multiple scenes.

**Go/no-go:** persistent GPU memory reduction *after* real BC content uploads, with no repeat-transfer penalties or bad compression artifacts on thin black strokes/alpha, and no correctness regression. If most textures receive partial updates or future overwrites, reject this route rather than encode on the device. A disk-side cache ratio is not evidence of physical RAM savings.

**Sources:** `tools/wol_m6_cache_build.py`, `tools/wol_bcdecode_host.c`, `runtime/wol-adapter.patch` (`nvn_textures.h` creation ASTC hook and `nvnCommandBufferCopyBufferToTexture` / `zero_texture_refresh` fallback), [M6 reports](../evidence/m6-compressed-textures/astc-e2e-device.md), [scene content probe](../evidence/m6-compressed-textures/content-scene-probes.md). Do not re-run the earlier empty-image cache expecting lasting savings.

## 5. P0/P1 memory — M5 actual Unity allocation owners and 136.9 MiB read lifetime

**Partially resolved:** the ≥1 MiB SDK allocator trace now associates the 143,554,106-byte core read with a containing 144,080,896-byte allocation, including its 32-byte output offset and call chain. No matched free of that SDK allocation is observed in the recorded cycle. [The reconciled ledger](../evidence/roadmap-v2-allocations/README.md) separates pool aliases and requested SDK extents. Inner Unity native/IL2CPP/AssetBundle object liveness, free lists, last page access and safely reclaimable bytes remain **unknown**. Neither an aggregate PSS drop nor reuse of the read address proves safe release.

**Next instrumentation:**
1. Locate the actual guest allocator entry/exit paths in the owner Unity/IL2CPP binaries and the Horizon allocation bridges. Sample large allocations (initial threshold ≥1 MiB) with caller PC/backtrace identity, allocation address, size, arena, time/scene and matched frees. Instrumentation must be bounded and fail closed on uncertain pointers.
2. Specifically trace the 143,554,106-byte RomFS read buffer: who allocates it, whether Unity copies it, when the guest no longer reads it, and how much of the underlying mapping remains resident. Distinguish file-backed, anonymous and remapped pages.
3. Report **reserved vs committed vs active vs free-list bytes**, anonymous mappings, native mappings, pool aliases and driver memory without double counting. Re-run identical cold starts and full street↔interior scene loops, not just map/pause toggles.
4. Only if a genuinely retained redundant copy is shown, explore streaming reads, bounded staging or valid owner-level release. Do not simply free the buffer when the initial load ends: Unity might still access compressed/serialized AssetBundle data lazily.
5. Treat allocator-safe `madvise(MADV_DONTNEED)` (former M8) as **blocked** until complete, page-aligned free ownership and no guest/GPU aliases are proven.

**Acceptance:** a reconciled allocation-lifetime table accounting for major non-NVN pages, clear evidence for a concrete reclaimable resource, and same-scene lower physical pressure after an isolated change. Zero-swap is **not** solved by `VmSwap≈0` in a warm session.

**Files:** `tools/wol_memory_profile.py`, `tools/wol_memory_benchmark.py`, `tools/analyze_memory_phases.py`, `tools/analyze_vma_diff.py`; [phase owner report](../evidence/m5-heap-owners/README.md).

## 6. P1 — correct physical-memory accounting and peak-lifetime model

The new `mali0/ctx/*/mem_allocs` series supplies an actual GPU context commit estimate (~262–274 MiB in one short loop), which is different from the earlier ~153 MiB texture-level-0 *estimate* and from process PSS. **Do not add GPU commit to process PSS as if allocations cannot overlap**; also do not infer entire physical RAM from PSS+SwapPSS. `CmaFree` reached ~0 at earlier startup peaks.

**Implement a bounded, minimally perturbing sampler** recording per-process `Pss`, `SwapPss`, `VmSwap`, guest pool residency, global `MemAvailable`/`CmaFree`, Mali context allocations, process major faults, global `pswpin/out`, and CPU/GPU clocks at the *same timestamps*. Record an allocation-high-water/phase chart for cold startup, first gameplay, map, interior, battle, save/load and restart.

**Accept:** one consistent accounting ledger with explicit overlaps and uncertainty, identifying what must decrease for a swap-disabled cold boot. The 60-second map/pause observation has **no growth trend**, not a no-leak endurance certificate.

## 7. P2 — opportunities still open, ranked by new evidence

| Idea | Current gate | Reason to defer / test |
| --- | --- | --- |
| GPU pass completion / fence scheduling | Only coarse `finish` (~11–26 ms depending on path); `T2_GPU_PIPELINE=1` previously hit `EGL_BAD_SURFACE` | First distinguish implicit upload stall, GPU resolve, context/surface wait and VSync. Never flip async mode blindly |
| Vertex/index generation cache | Stationary guest vertex streams were byte-identical (100% sampled) | Need moving/battle census and data-version invalidation; buffer ring already showed churn was not bottleneck |
| Shader program/constant upload cache | ~0.8–1.1 ms/frame in earlier draw split | Count truly redundant uniforms/program switches before implementing |
| NVN non-draw `Downsample` operations | ~1.9–3 ms/frame in sampler reports | Break down CPU vs GL/wait and test only if top candidate fails |
| M7 1920×1080 camera targets → identify **Unity/SDK allocation origin** before 720p A/B | [Handheld preflight](../evidence/handheld-preflight/README.md) completed: existing AM reply already handheld; the observed launch did not query mode/resolution or VI. Unity still requests 1080p. | **Current P0:** trace NVN texture-builder guest callers and identify the actual Unity RT dimension decision. Prefer guest-native 720p if proven; otherwise audit `host_scaled` for an eligible target. See [§15](#15-m7-after-handheld-preflight-unity-render-target-origin-and-720p-plan). |
| Monochrome R8/RG8 GPU representations | Thin black/white graphics may permit exact compact formats | Requires content+alpha/channel audit, shader swizzle, immutable-resource gating and real GPU allocation A/B |
| GPU eviction | Read-only inventory showed just ~7 MiB safely reconstructible | **Not a promising standalone zero-swap lever** unless an additional recovery path is proven |
| M4 wave2 | Device A/B measured only ~1.7 MiB street PSS+SwapPSS reduction | Optional owner-quality A/B, not a breakthrough; accepted baseline remains installed |

## 8. Required gameplay coverage and harness repairs

Earlier frame/memory samples were mostly stationary. The first attempted in-game movement test (documented in [round-up](../evidence/roadmap-roundup-20261016/README.md)) showed diagnostic A/B/START/L/R working, but character movement was **not proven** from the starting scene: four held stick directions and D-pad did not move the character. Press duration is capped at **2,000 ms per event**; longer diagnostic packets are rejected, so a script claiming 10 s of one continuous hold may actually be issuing repeated/invalid presses.

Before generalizing optimizations:
- Identify a verified, controllable save/scene where world movement changes real KMS pixels; use accepted HID duration packets and observe movement, not just input receipts.
- Extend automated smoke test through a confirmed battle, map, interior, return, save and restart/load (owner data stays private).
- Include scenes `tut_gulch` and `tut_saloonbasement` because their BC upload patterns differ and the latter includes many BC textures.
- Fix/validate remaining map marker/title positioning independently of optimization work; preserve skinned character bodies, WANTED stencil and Spruce UI restore.
- Run multi-minute and longer memory stability plus physical-button/audio checks before claiming readiness; map/pause 60 s is not enough.

## 9. Proposed next commits on main, with falsifiable decisions

| Order | Scope | Change | Acceptance / stop condition |
| --- | --- | --- | --- |
| 1 | **Evidence/source parity** | Reconcile `dtime8` `WOL_SAMPLE_SPLIT` timers into the published overlay or archive an exact data-free patch/build recipe; add bounded same-timestamp Mali+VM metrics | Same binaries and instrumentation definitions reproducible; no shader/resource behaviour changed |
| 2 | **P0 FPS preflight** | Expand CopyTextureToTexture dependency and sampler trace across movement, combat, map and multiple saves | Prove exact sample-before-overwrite and CPU snapshot contract, or reject redirection |
| 3 | **P0 FPS opt-in** | GPU sample redirect of 460 while retaining CPU row-copy semantics, *not* a generic deferred alias | Visual/CPU/GPU-coherence parity and stable >noise whole-frame improvement; auto-fallback on hazards |
| 4 | **P0 RAM preflight** | M5 allocation owner trace incl. 136.9 MiB RomFS read and heap lifetime; same-time host GPU snapshots | Evidence of actual reclaimable copy/arena or explicit unknown; no speculative freeing |
| 5 | **P1 RAM opt-in** | M6 post-copy real BC-content → precomputed ASTC, one immutable level-0 texture first | Persistent GPU commit saving after content upload; no errors/visual regression |
| 6 | **Decision branch** | If sample redirect fails, test pass-boundary composite/async PBO only with measured GPU timing; if M6 fails, prioritize owner-level heap work and optional R8/RG8 | No repeated null-cache/immediate-blit or generic ring experiments |
| 7 | **Acceptance** | Cold start without configured swap in a recovery-safe test setup, multi-scene gameplay and save/load | No OOM, no swap, sufficient RAM+CMA headroom, 30+ FPS with P95 bound where appropriate |

These are **proposed**, not completed tasks. Sequence 4 and 5 can be developed alongside 2 and 3 if source/runtime hashes, owner sections and device A/B controls stay isolated.

## 10. Experimental safety, baselines, CI and release criteria

- Pin `main` source commit, restored GPL runtime source manifest, owner-only `RomFS` section, SHA-256 ELF/launcher/save, exact env and profiler flags for each run. Experimental source from a local restored tree is not automatically present in the public overlay.
- Run alternating A/B (prefer ≥3 per arm where practical), the **same verified scene and save**, cold startup, 30 s menu/game, transitions and memory peaks; track natural ~1–1.5 presents/s variance and report interval distributions, not a best run.
- Collect real KMS screen evidence, pixel diffs where meaningful, sprite/portrait/map/alpha checks, input/audio, no GL errors, original save restoration and MainUI recovery. Never overwrite a save belonging to a running/unowned process.
- Use the existing `.github/workflows/native-probe.yml` for its proven synthetic tests, but add data-free overlay-apply/build and isolated unit tests for redirect hazards, BC post-copy fallback and allocator ownership as code lands. Public CI must not ship game assets, Switch NSO or extracted shader binaries.
- Defer any global `swapoff`, swappiness, GPU frequency, unsafe `madvise` or production-fast-path toggles until controlled proof. A no-swap acceptance run requires swap disabled **before** launching, with recovery available.
- No performance or memory win is claimed until measured on TSPS with the genuine game frame and independent, unmodified control arm.

### Reference index

- [Round-up of original roadmap stages](../evidence/roadmap-roundup-20261016/README.md)
- [Sampler micro-zones (critical new FPS result)](../evidence/fps-sampler-split/README.md)
- [Frame timeline](../evidence/fps-frame-timeline/README.md)
- [Copy-460 dependency trace](../evidence/copy460-dependency-trace/README.md)
- [M6 ASTC E2E and fallback findings](../evidence/m6-compressed-textures/astc-e2e-device.md)
- [M6 real-content scene probes](../evidence/m6-compressed-textures/content-scene-probes.md)
- [M6 measured GPU memory](../evidence/m6-compressed-textures/device-memory/README.md)
- [M5 heap owners and VMA diffs](../evidence/m5-heap-owners/README.md)
- [60-second scene-cycle memory check](../evidence/scene-cycles-memory/README.md)
- [Original measured resource optimization log](resource-optimization.md)

## 11. Execution checkpoint — implemented mechanisms versus unmet acceptance

**This roadmap is not fully accepted. Neither sustained 30+ presents/s nor a swap-disabled cold boot is demonstrated.** The following finite experiments were executed; rejected mechanisms and missing prerequisites are not relabeled successful optimizations.

1. **Source/ledger — delivered.** `a3793a1` reconciles all 199 `dtime8` native files. The bounded same-window collector records Mali context commit, PSS/SwapPSS/VmSwap, faults, swap I/O, MemAvailable/CmaFree and clocks, with its own sampling cost. Heavy guest-page observations are opt-in and excluded from the reported FPS comparison windows.
2. **Copy preflight — decisive counterexample, coverage partial.** [Gulch/saloon audits](../evidence/roadmap-v2-copy-audit/README.md) show rendered producer GPU pixels disagree with the zero CPU snapshot; later destination-GPU audits match the CPU snapshot. Movement/guide/interior frames are real. Combat, complete scene travel and reload/late-game coverage are not inferred from requested action names.
3. **Sample redirect — rejected at its prerequisite gate.** No sampler substitution is enabled: sample-before-overwrite ordering cannot make unequal copy-time images equivalent. Pass restructuring that samples that producer directly would require a separately proven rendering contract, not the rejected shortcut under a different name.
4. **Allocator owners — SDK evidence delivered; reclaim remains blocked.** [The owner ledger](../evidence/roadmap-v2-allocations/README.md) identifies the large core-read allocation and borrowed NVN pool aliases. Inner Unity active/free-list bytes, final read lifetime and safe reclaimable pages remain explicit unknowns. No speculative free or `MADV_DONTNEED` is introduced.
5. **Post-copy ASTC — experimental window-specific positive result.** [Three single-image pairs](../evidence/roadmap-v2-postcopy-ab/README.md) prove real hits but not a causal physical saving. [Three group pairs](../evidence/roadmap-v2-postcopy-group/README.md) each hit nine nonempty textures and reduce stable post-content idle Mali commit by 2.5–4.9 MiB; later transient map-return differences are inconsistent. No GL error/fallback is recorded in these windows. Thin-stroke/alpha review is limited to captured scenes. Default remains off; this is not all-scene memory or release acceptance.
6. **Conditional FPS branch — measured and not promoted.** [Queue-drain timing](../evidence/roadmap-v2-upload-timing/README.md) separates ~11.4 ms prior GPU backlog from ~2.0 ms drained upload calls. [A new bounded unpack-PBO comparison](../evidence/roadmap-v2-pbo-ab/README.md) exercises real fenced uploads against both normal and direct upload. Its exploratory gain is within noise and GPU commitment rises; no production PBO/async default is adopted. R8/RG8 is not required as an ASTC-failure fallback because the group mechanism now has a limited positive memory result, but it remains unvalidated rather than assumed safe.
7. **Final acceptance — blocked/unmet, not complete.** Repeated owned runs restore save hashes and the real Spruce screen; the published helper refuses unowned live games. The original black-transient cleanup-observer flaw is documented and fixed. However, a three-pulse interaction route did not reproduce combat, map-marker/reference parity is still independent, and physical buttons/audio plus save/load/travel are unverified. Startup approaches RAM/CMA floors with substantial swap use; no proven alias-free reclaimable arena or independently validated hard-recovery setup supports disabling swap safely. Global swapoff, blind async and production fast-path switches remain unchanged.

### Reproducibility and limits

- `ed06488` publishes the copy/allocator/post-copy hooks, synthetic hazard tests, exact-source evidence and the initial six-run ASTC study; its push CI passed. Later group/PBO reports pin their own build/overlay/section/save/helper identities.
- Local ARM64 builds apply the data-free overlay to the manifest-pinned owner-restored GPL tree. Public CI validates overlay syntax, compiles actual added helpers against data-free fixtures and runs the standalone ARM64 probe tests; it does **not** claim to restore private game/source archives on GitHub.
- The memory/overlay/hazard suite now has 32 passing tests; the broader local data-free suite has 39, with 11 additional source-contract CLI programs and 22 standalone native-probe cases all passing under their proper invocation contracts. [Final validation](../evidence/roadmap-v2-final-validation/README.md) records scope and limitations. Owner payloads, caches, saves, raw texture pixels and console binaries remain outside Git.
- [An ordinary-title relaunch](../evidence/roadmap-v2-clean-title/README.md) verifies the new default-off input-injection socket, actual title image, unchanged owner saves and real Spruce recovery. This closes the leftover diagnostic-default issue, not the physical gameplay or no-swap gates.
- **Combat coverage now exists.** The owner triggered a battle on the device; while it ran I captured real frames and measured the runtime's own frame clock: median **40.74 ms**, P95 **45.25 ms**, max 55.81 ms over the last 200 battle frames (~24.5 presents/s), one frame split period 44.4 / replay 27.2 / finish 12.9 / present 6.1 / swap 5.8 ms, `MemAvailable` 89–93 MB, `CmaFree` 9.9–11.6 MB, zero GL errors. The 30+ presents/s and P95 ≤ 33.33 ms targets are therefore **measured as unmet in combat**, not merely unverified. Evidence: [owner battle](../evidence/roadmap-v2-owner-battle/README.md). Scripted combat triggers remain unreproduced: three bounded routes (basement `left×3 + interact×3`, gulch `right×7 + A`, gulch `stick-right×4 + A×2`) moved the character but started no battle.
- **Guide/map defect — fixed and owner-confirmed.** The previous “game-content question, not a dropped draw” conclusion is withdrawn. A same-save real desktop reference shows five destinations and three NEW tags. Indexed one-frame geometry tracing plus application layout inspection identified the actual fault: mip repacking halved `Sprite.rect` while authored map-node coordinates remained in original pixels. The protected map repack restores only 23 Texture2D and 23 Sprite objects, leaves 53,919 other objects byte-exact, and retains mip-tail stripping. Controlled KMS captures and an independently owner-launched session now show all five destinations and three NEW tags correctly on the paper. See [map pixel-space fix](../evidence/roadmap-v2-map-pixel-space/README.md).
- [Earlier frame parity](../evidence/roadmap-v2-frame-parity/README.md) establishes relative consistency between post-copy ASTC arms, **not absolute map fidelity**. Both old arms shared the same repack coordinate defect. A stable-content mask cannot substitute for a same-save correct-game reference.
- Repeated process launches use the same warm host/device setup; they are not cache-cold or swap-disabled device boots. Runtime presents are not independent physical-panel FPS. PSS, driver commit, pool spans and CMA are not added into a synthetic physical total.
- Before closing acceptance, obtain verified travel/save/load coverage, physical input/audio evidence and a validated recovery-safe no-swap setup. Do not repeat the rejected source redirect, null-image ASTC or PBO promotion as though their prerequisites were satisfied.

## 12. Follow-up after the map correctness fix

The owner confirmed the ordinary map and requested an audit for similar defects plus the remaining optimization work. A live owner process is not an owned test: do not inject, replace its files, restore saves or terminate it while permission is absent.

| Work | Current decision / acceptance |
| --- | --- |
| Same-save map correctness | **Passed** in controlled KMS frames and owner ordinary launch; protected repack installed, source/evidence checkpoint being published. |
| Other pixel-coordinate consumers | **Audited, mechanism identified, extension not applied.** The name-based load path (`SpriteLoader.TryLoadResourceOrDevCache`) rebuilds a sprite whenever the stored PPU or the pivot/texture-dimension relation disagrees with the caller, which is exactly what a rect/PPU rescale causes; `OptionImage.set_sprite` (raw rect into LayoutElement) and `PortraitBuilder.UpdateSize` (pivot / rect.size) are the remaining raw-pixel consumers, while `OptionsContentBlock`, `WorldOverlay`, `TiledImage` and every `bounds`/world path are ratio-only and unaffected. 62 sprites over 11 textures in `core` still carry a rescaled rect+PPU (inventory/journal/map/options icons, combat log, victory/defeat cards, character-creation art, PC body parts, pad glyphs); the map family is untouched. Restoring all 11 textures' authoring dimensions costs a measured **+22.64 MiB** serialized payload, so protection is not widened before a live owned session shows one of those screens actually reaching a raw-pixel consumer. See [pixel-consumer audit](../evidence/roadmap-v2-pixel-consumer-audit/README.md). |
| GPU finish/downsample attribution | Still open for new bounded telemetry; preserve target, context, CPU copy and ordering. Existing timing is not permission to remove finish/resolve. |
| Program/constant and vertex caches | **Census measured; cache stays off.** A default-off census of the pair-path constant banks (`WOL_UNIFORM_CENSUS=1`, 180 s, 3 781 frames) counted `calls=191838 redundant=87943 skipped=0 invalidations=1` — **45.8 %** of the 96-float bank uploads repeat byte-identical bytes (≈ 33.8 MB of redundant CPU→GPU traffic, ≈ 8.9 KB/frame). Invalidation is by context switch and draw-time GL error; the census itself skips nothing, so the picture is unchanged. Promotion is not justified by this number: the battle-present path spends ~44 ms/frame on replay (27.2) and finish (12.9), and a gain must be shown by a matched A/B with pixel parity, not by a redundancy share. See [uniform census](../evidence/gfx266-uniform-census/README.md). |
| Allocation lifetime / file-backed read hypothesis | SDK allocation ownership is known only at arena level. Do not free/discard retained compressed core data. Any alternative backing needs a separately reviewed byte-exact COW/output-range/alias contract. |
| Post-copy ASTC | Existing nine-image group has a limited positive idle GPU result; default remains off. Broader scene and thin-stroke/alpha acceptance is still required. |
| R8/RG8 / target resizing / eviction | Unvalidated optional mechanisms, not accepted fallbacks. Do not invent restored pixels, shrink logical dimensions or discard non-reconstructible resources. |
| Gameplay, physical input/audio, save/load, endurance | Map and one real battle covered. Full travel/reload/late-game and physical/audio gates remain explicit. |
| No-swap / 30+ presents/s acceptance | **Unmet**. The corrected map adds 42,958,848 bytes of serialized texture payload, not a measured RAM delta. Passive ordinary-map memory still has ~492–498 MiB SwapPSS and CMA headroom as low as ~2.1 MiB; disabling swap is not presently safe. |

Every new experiment must end in measured acceptance, explicit rejection or a concrete unmet prerequisite. Implementation, installation and publication are distinct from a performance win.

## 13. M7: permanently handheld Horizon profile (no TV mode / no switch)

**2026-10-19 execution result — CLOSED AS A RESOLUTION OPTIMIZATION.** The existing AM handler already returns `u8 Handheld=0` for command 5 and `u32 Normal=0` for performance mode command 6. In the actual game launch only AM commands 0/1/9/6 were observed; **no cmd 5, cmd 60 or VI ListDisplays query was observed**, and some internal textures remain 1920×1080. The static handheld-only helper and bounded `WOL_MODE_TRACE=1` are implemented and tested, **but forcing handheld is not a demonstrated way to get 720p internal render targets**. The original §§13.4–13.5 are the historical test design; do not repeat them absent newly observed guest service calls. Continue with [§15 Unity RT origin](#15-m7-after-handheld-preflight-unity-render-target-origin-and-720p-plan). Evidence: [handheld preflight](../evidence/handheld-preflight/README.md).

**Requirement confirmed 2026-10-18:** **handheld is the only supported mode** of this WoL PortMaster runtime. There must be **no user-facing or diagnostic runtime option** for switching to TV/docked mode: no `WOL_SWITCH_MODE=auto|handheld|docked`, no `docked` branch in the runtime's own operation-mode policy and no dynamic mode-change notifications. Build-to-build historical controls may be used for A/B; they are not an operating-mode toggle. **Status:** emulator implementation surveyed, current game's guest-reported mode still unknown; no runtime modification or device A/B is claimed. See [cross-emulator code audit](handheld-mode-emulators.md).

### 13.1 What we know

| Layer | Actual state | Limitation |
| --- | --- | --- |
| Native Switch handheld screen | 1280×720 output | Does not prohibit an internal 1080p render target |
| WoL host window on TSPS | 1280×720 SDL/KMSDRM and KMS captures | Host output size does **not** prove guest operation mode |
| Unity/NVN render graph | Includes 1920×1080 camera/intermediate targets | Still unproven that docked mode caused these allocations |
| `native/input.h` HID cmds 128/129 | Npad handheld **controller activation** already implemented | **Not** `nn::oe::GetOperationMode` |
| `native/display.h` `WOL_DISPLAY_MAX` | Existing `vi` `ListDisplays` maximum *layer* dimensions (default 1920×1080) | Earlier override test did not change Unity RT sizes; this value is not docked state |
| Guest applet/oe mode query | Not yet captured from WoL | Inherited GPL runtime might already answer handheld |

A single uncompressed RGBA8 1920×1080 level is ~7.91 MiB compared with ~3.52 MiB at 1280×720: theoretical ~4.39 MiB/image host or guest storage difference when an *actual allocation* shrinks, not an FPS or RAM promise.

### 13.2 What other open-source Switch emulators actually do

- **[Ryujinx — `ICommonStateGetter.cs`](https://github.com/kotx/Ryujinx/blob/534f92506bf8c6aba29bb86917bf10954a360d8e/src/Ryujinx.HLE/HOS/Services/Am/AppletAE/AllSystemAppletProxiesService/SystemAppletProxy/ICommonStateGetter.cs)**: command **5** returns a u8 from shared system `DockedMode`, command **60** returns two u32 values from actual display information, command **6** delegates to APM. Event handles and notification queue are separate.
- **[Skyline — `ICommonStateGetter.cpp`](https://github.com/msummers10/skyline/blob/master/app/src/main/cpp/skyline/services/am/controller/ICommonStateGetter.cpp)**: `GetOperationMode` returns its mode field; `GetDefaultDisplayResolution` returns **1280×720** for handheld and **1920×1080** for docked. The service [declarations](https://github.com/msummers10/skyline/blob/master/app/src/main/cpp/skyline/services/am/controller/ICommonStateGetter.h) register commands **5**, **6** and **60** and define `Handheld=0`, `Docked=1`; events/ReceiveMessage are independent.
- **[ScarletNX — `am.c`](https://github.com/scarletnx/ScarletNX/blob/main/src/nx/hle/services/am.c)**: command 5 helper writes `g_opt_docked ? 1 : 0`; resolution helper writes `g_opt_docked ? 1920 : 1280` and `g_opt_docked ? 1080 : 720`. Its [SWIPC service declarations](https://github.com/scarletnx/ScarletNX/blob/main/src/nx/hle/services/am.swipc) confirm return types u8 for command 5 and two i32 for command 60. Our port can eliminate that setting and hardcode handheld.
- **Historical yuzu**: its AM service also selected mode via `use_docked_mode`; not required for this single-device title-specific runtime. **[ReverseNX](https://github.com/masagrator/SaltyNX/blob/master/saltysd_core/source/ReverseNX.cpp)** demonstrates why querying default resolution, operation mode and applet notifications are different mechanisms. These are **design references**, not code or libraries copied into this GPL overlay.

**Preferred specialization:** return `Handheld=0` and `1280,720` from the *version-correct Horizon API actually used by WoL*, using one immutable internal policy (ideally two constants and shared helper). There is no need for a TV-mode config flag, alternate runtime mode or mode-switch UI.

### 13.3 Implementation boundaries and correct API contracts

- `nn::am::service::ICommonStateGetter::GetOperationMode`: command **5**, reply `u8 0` with correct CMIF/domain shape.
- `ICommonStateGetter::GetDefaultDisplayResolution`: command **60**, reply **two 32-bit values** `1280,720` with original ABI/endianness and successful result.
- `GetPerformanceMode`: command **6**, **separate APM contract**. Do not write a u8 as a 32-bit response or assume guest handheld operation mode automatically sets host CPU/GPU clocks. If service supports a handheld performance profile, ensure it reports a semantically compatible value after verifying the original SDK/APM ABI and observed call path.
- Mode change / display resolution change notification events: if mode is immutable throughout the process, retain valid handles and legitimate initial focus/startup messages but **never synthesize dock/undock change messages** or spuriously signal resolution-change events.
- HID's `SetNpadHandheldActivationMode` (128) must **not** be used as an operation-mode switch. Confirm handheld controller IDs/style are accepted for real device input independently.
- `vi` `ListDisplays` maximum layer size is **capability metadata, not handheld/docked mode**. Do not blindly hardcode its maximum 1280×720 if guest needs a larger layer or if previous tests were inert. Keep the current output window 1280×720.
- Other APIs such as `omm`/SDK shared-state getters must be implemented **only when observed in the owner's request trace**; firmware/version and SDK-specific service IDs differ. No unconditional fake endpoint.

### 13.4 Execution sequence — no mode toggle

**P0A: determine what the original guest is actually told.** Reconstruct the manifest-pinned GPL runtime, inspect the actual inherited AM/service dispatch and the guest SDK call sites; add an optional **read-only logging flag** `WOL_MODE_TRACE=1` (logging, **not a TV/handheld toggle**). Trace `GetOperationMode`, `GetDefaultDisplayResolution`, `GetPerformanceMode`, `ListDisplays`, and relevant event access, with returned values and boot/Unity-init timing. Correlate with `NVN_TEXTURE_REAL` allocation dimensions.

**P0B: implement the immutable handheld policy at the one authoritative service boundary.** If the inherited runtime already returns 0 and 1280×720 consistently, keep that behavior and add regression assertions rather than patching redundantly. Otherwise implement explicit replies `0` and `1280,720` in the actual observed AM/oe path with proper IPC payload sizes. No environment-variable choice, no TV fallback, no dynamic console mode state. Invalid calls retain existing fail-closed behavior.

**P0C: A/B via **different builds**, not a mode switch.** A = pinned pre-change HEAD; B = fixed handheld-only implementation, both built from the same owner data, with identical save, scene, launcher, clock profile and instrumentation. Alternate A–B–A–B across cold process starts. Never expose A as a selectable runtime TV mode. Measure returned mode/resolution, actual 1920×1080 vs 1280×720 guest RT allocations, GPU memory, process PSS/SwapPSS, `MemAvailable`, `CmaFree`, full-frame intervals P50/P95/P99, KMS renders and clean Spruce recovery. Include street movement, title/WANTED stencil, map/title/markers, dialogue, saloon and owner-observed battle.

**Acceptance for the mode feature:** every observed mode query returns handheld, every default-resolution query returns 1280×720, no contradictory performance/notification state, no TV mode setting exists, output and controls work. **Separate performance acceptance:** lower-sized *real* internal RT allocations and a reproducible FPS/memory gain. It is valid for the fixed handheld feature to succeed even if Unity still creates 1080p targets.

### 13.5 Decision following measurements

| Device evidence | Next step |
| --- | --- |
| Runtime was already handheld and returning 1280×720 | Document verified existing handheld-only contract, add tests, **no unnecessary behavior patch**. 1080p targets must originate elsewhere |
| Runtime reported docked or 1080p default on an observed AM/oe path | Implement **fixed handheld** responses; no switch. Retest Unity RT dimensions and full frames |
| No mode/resolution service calls observed | Audit guest Unity/Nintendo SDK configuration and guest render-target constructor; report API as unused, do not create fake service replies |
| Fixed handheld but internal 1920×1080 targets persist | Determine Unity render-scale/quality or explicit NVN target creation, then return to coordinated M7 720p target work; **do not** add TV mode |
| Correct 720p targets, but frame time unchanged or regressions | Keep handheld contract and fix the independent render graph/texture-copy/sync issue rather than inventing a dock fallback |

**Do not confuse aims:** fixed handheld mode is a deterministic functional requirement; FPS ≥30 and swap-free cold boot are separate unmet performance requirements. Mode work should precede unsafe manual downscaling, but does not supplant texture-460 full upload optimization or Unity heap allocation work.

## 14. Cross-emulator optimization opportunities (Ryujinx / Skyline / ScarletNX)

**2026-10-19 revision:** §14.2's exact content-aware destination upload skip was **implemented and compared** in [two alternating A/B pairs](../evidence/emucache-upload-ab/README.md). The repeated-snapshot census found 3,598 identical copies out of 3,600 observations, and one test skipped 3,478 uploads, but control 23.491/23.460 versus candidate 23.363/23.629 presents/s showed **no repeatable end-to-end gain**; default remains OFF. The previous P0 priority in the matrix below is historical. Use §15's new ordering instead. Likewise §13 handheld detection is complete and not a source of 720p scaling.

**Reviewed 2026-10-18, `main` `7fa5fa5f3b4bbaedcc7a9fbe141d613faacaf016`. Status: engineering proposals, NOT implemented or device-verified by this review.** This section records candidates identified by a source audit of other open-source Switch emulators. It must be read alongside the *later* execution verdicts in §§11–12: in particular, the generic texture-460 **GPU source sample redirect has already been REJECTED** by [copy-time image mismatch evidence](../evidence/roadmap-v2-copy-audit/README.md), and the PBO/ring and immediate blit variants have already been evaluated. Do not use the older §3 wording as permission to re-enable them.

Only adopt small algorithms relevant to the existing native ARM64 Horizon → GLES 3.2 path. Do not import full Maxwell emulation, Vulkan renderer, guest JIT, giant shader caches, or invasive full-guest page protection. **Handheld remains permanently the only operation mode**, per §13, with no TV/docked switch.

### 14.1 Candidate matrix and measured constraints

| Priority | External implementation / design | Current WoL situation | Proposed new mechanism / go-no-go |
| --- | --- | --- | --- |
| **P0** | [Ryujinx TextureGroup dirty ranges](https://github.com/kotx/Ryujinx/blob/534f92506bf8c6aba29bb86917bf10954a360d8e/src/Ryujinx.Graphics.Gpu/Image/TextureGroup.cs), [ScarletNX surface write generations](https://github.com/scarletnx/ScarletNX/blob/main/src/nx/gpu/vk/surface.c) | Every full 1280×720 copied texture-460 guest image is marked dirty and commonly re-uploaded; normal sampler time ~5.8 ms/frame in one run, but post-drain upload median ~1.97 ms | **Prove whether repeated CPU copy results are identical to the destination's *already uploaded* image**, then conditionally skip redundant host uploads. Do NOT sample the rendered producer instead of the zero-filled guest copy |
| **P1** | [ScarletNX deferred releases](https://github.com/scarletnx/ScarletNX/blob/main/src/nx/gpu/vk/release.c), [Skyline fence-owned resource lifetimes](https://github.com/msummers10/skyline/blob/master/app/src/main/cpp/skyline/gpu/fence_cycle.h) | Replay/finish and a substantial pre-upload GPU backlog measured; old `T2_GPU_PIPELINE=1` produced `EGL_BAD_SURFACE` | Trace NVN-visible release and host waits; experiment with fenced, correctly ordered deferred retirement **inside a valid EGL context**, not blanket async |
| **P1** | [ScarletNX render-pass attachment retention](https://github.com/scarletnx/ScarletNX/blob/main/src/nx/gpu/vk/render.c) | GLES FBO switching/resolve costs not separately attributed; immediate GPU blit increased finish time | Count redundant framebuffer binds/attachment reconfigurations, tile load/store and resolve dependencies; reduce only proven redundant transitions |
| **P1 (RAM)** | [Skyline compatible guest-mapping views](https://github.com/msummers10/skyline/blob/master/app/src/main/cpp/skyline/gpu/texture_manager.cpp), [Ryujinx TextureCache overlap checks](https://github.com/kotx/Ryujinx/blob/534f92506bf8c6aba29bb86917bf10954a360d8e/src/Ryujinx.Graphics.Gpu/Image/TextureCache.cs) | `zero_texture_storage_state()` already joins **some** host views. Read-only inventory reports ~7.1 MiB safely reconstructible static images, so blanket eviction is not justified | Inventory remaining compatible GPU-storage duplicates by *physical guest mapping + layout + generation + writer*. Share only precisely equivalent live storage, not merely same pixel hashes |
| **P1 quick A/B** | [Ryujinx cached shader/resource state](https://github.com/kotx/Ryujinx/blob/534f92506bf8c6aba29bb86917bf10954a360d8e/src/Ryujinx.Graphics.Gpu/Shader/ShaderCache.cs) | `WOL_UNIFORM_CACHE=1` is **already implemented**, default OFF; census reports 45.8% identical uploads, only ~8.9 KB redundant/frame, no matched FPS proof | Isolated on/off A/B with complete image and driver-error parity. Do not implement another identical uniform cache |
| **P2** | [Ryujinx shader disk cache](https://github.com/kotx/Ryujinx/blob/534f92506bf8c6aba29bb86917bf10954a360d8e/src/Ryujinx.Graphics.Gpu/Shader/DiskCache/ParallelDiskCacheLoader.cs) | Fixed catalogue GLSL programs already link and cache in the title runtime; first-link stalls not proven | First measure per-program compile/link time in cold scenes; if material, test GLES program binaries keyed by GLSL source, driver/renderer and GL version. Avoid eight compilation threads / large prewarm memory on 1 GiB |
| **P2** | [Ryujinx GPU-modified buffer range list](https://github.com/kotx/Ryujinx/blob/534f92506bf8c6aba29bb86917bf10954a360d8e/src/Ryujinx.Graphics.Gpu/Memory/BufferModifiedRangeList.cs) | `WOL_PAIR_RING` already reuses VBO objects without FPS win; read-only *stationary* census finds unchanged sampled vertex bytes (~29 KB/frame) | Only if moving/battle traces show sufficiently large unchanged streams: content generation + precise invalidation to skip `glBufferData`; otherwise close, not a P0 item |

**Hard measured context:** real battle last 200 frames have median ~40.74 ms, P95 ~45.25 ms, about 24.5 presents/s ([owner battle](../evidence/roadmap-v2-owner-battle/README.md)). The 30 FPS median budget requires ~7.4 ms improvement; the current P95 target needs ~12 ms improvement. No single cache is assumed to deliver that. End-to-end GPU completion, actual screenshots, CPU/GPU clocks, RAM/CMA and swap must be measured in matched scenes, not estimated from bytes skipped.

### 14.2 P0 — full-image **content-preserving** upload skip: a new hypothesis

This is **not** the abandoned §3 same-frame source-GPU redirection. Its prerequisite was disproved: the real producer GL render-target pixels differ from the destination guest memory copy, while the destination GPU image matches the guest CPU copy. The new hypothesis instead compares **two successive destination CPU snapshots**, or verifies an exact generation identity, and only avoids uploading destination bytes that are **already authoritative in its own host GPU image**.

**Read-only preflight before optimizing:**

1. In the real `wol_color_texture_copy()` path, identify each destination by NVN object **and storage generation**, guest pool physical address/offset, GL storage generation and EGL context; account for view aliases and resource recreation. Distinguish first copy, subsequent identical copies, changed copies and GPU/CPU side effects. Avoid hardcoding texture ID 460 as a universal lifetime identity.
2. At a bounded diagnostic cadence, compare **actual bytes copied into the destination** with its immediately previous complete destination snapshot (or a collision-safe check plus exact byte verification). A zero/nonzero census can be reported first. Record `copy_equal`, `copy_changed`, `upload_needed`, `host_valid`, `bytes_avoidable`. The existing source→destination `memcpy` stays as-is in the initial experiment.
3. Prove that the destination's GL storage still contains the same copy-time bytes: track guest write generations, `zero_cpu_dirty`, complete/partial uploads, render-target GPU writes, sampler bindings, context switches, texture reallocation, post-copy ASTC conversion/fallback and any write through overlapping NVN views. An unchanged CPU copy **alone** does not permit an upload skip.
4. Use exact byte equivalence for acceptance (hash-only collisions cannot silently corrupt the game). A full 3.6864 MB per-frame compare may itself cost enough to erase the win; profile the comparison, and where safe replace it with precise write-generation tracking / zero-image sentinel established once. Do **not** indiscriminately hash every RT on every draw: ScarletNX limits costly hashes after measuring them.
5. Only if a significant amount of *valid* repeated destination host content exists, add a **default-off** guarded skip and a fail-closed fallback to the existing `glTexSubImage2D`. Never redirect to the differently rendered producer. Record actual upload count, skipped bytes, GPU finish, P50/P95/P99, Mali commit, image parity and fallback reasons.

**Decision:** if the destination bytes vary, the GPU storage loses validity each frame, or comparison overhead neutralizes the saved upload, mark this mechanism REJECTED. Positive acceptance means a repeatable *whole-frame* improvement (not merely reduced sampler CPU time) without graphics/input/save regressions. Since a forced queue drain measured ~11.4 ms backlog before an ~1.97 ms upload, the older 5.8 ms sampler zone is **not** guaranteed transferable savings.

### 14.3 P1 — GPU release/retirement and EGL-safe FBO scheduling

ScarletNX queues CPU-visible sync releases behind the GPU submit that owns them rather than blindly finishing at each release; Skyline attaches resource lifetimes to fence completion. Our GLES adapter can borrow their **dependency accounting**, not Vulkan primitives.

1. Instrument real NVN QueueSubmitCommands, fence/syncpoint, CPU-visible release, implicit glFinish, frame finalization and `eglSwapBuffers`. Enumerate all cases where guest CPU must observe completed contents **synchronously**. Classify CPU submission time, GPU elapsed and queue backlog separately; they are not additive without proving serial dependence.
2. Prototype a bounded, single-context `glFenceSync`/zero-time `glClientWaitSync` tracker with correct GL ES 3.x semantics, ownership of in-flight textures/VBOs/FBOs, resource retirement and guest-wait fulfillment. Never destroy/recycle a resource or acknowledge guest-visible completion prematurely.
3. Respect the prior `EGL_BAD_SURFACE` fault: no unchecked `T2_GPU_PIPELINE=1`, background EGL context or blindly concurrent renderer.
4. For framebuffer transitions, first record actual FBO IDs, attachments, load/store needs, target-switch calls, full-screen resolves and whether tile contents are read later. Test suppression of redundant binds and validated `glInvalidateFramebuffer` only for provably dead attachments; never invalidate the texture-460 source/destination or frame-history content by guesswork.
5. Compare A/B/A/B under battle as well as street and map. Require P50/P95 full-frame improvement and exact visual/CPU coherency, no new GPU stalls or GL errors. Reset all scoped states on EGL context generation change.

### 14.4 P1 RAM — guest physical alias / compatible host texture-view census

Before adopting Skyline/Ryujinx sharing:

- Inventory live unique host storage vs guest NVN objects and views, with **actual backing ranges/aliases**, format, dimensions, mip chain, row pitch/tile layout, GL storage generation, current GPU writer, guest dirty status and pending fences. Current `zero_texture_storage_state()` already handles some shared storage: report **incremental** missed sharing opportunities.
- Do not join unrelated render-target results merely because they share an old guest mapping, nor merge textures based only on matching CPU bytes. Distinct GPU-authoritative pixels require distinct physical storage until a proven content merge/copy contract exists.
- For compatible read-only views, benchmark one owner/view group behind a default-off flag. Validate alpha, swizzle, mip, stencil and ownership on save/reload and scene transitions; measure real Mali context commit (not only level-0 calculated MiB).
- If few duplicates exist, close this candidate rather than creating a large manager on 963 MiB RAM. Existing GPU eviction census had only ~7 MiB safely reconstructible, so generic age-based eviction is **not** the solution.

### 14.5 P1 quick experiment — existing uniform cache; P2 shader and vertex caches

**Uniform cache:** `WOL_UNIFORM_CACHE` and `WOL_UNIFORM_CENSUS` already exist in `runtime/wol-adapter.patch`. [Census](../evidence/gfx266-uniform-census/README.md): 191,838 uploads, 87,943 byte-identical repeats (45.8%), with `skipped=0` because it was census-only. The reported 33.8 MB redundant total is ~8.9 KB/frame; it is not proof of a useful driver-time win. Run a production-equivalent on/off A/B, confirming catalogue-program + uniform-location + byte equality, invalidation on context/GL error/any program relink, and pixel parity; retain default OFF unless full-frame improvements exceed noise.

**Shader cache:** first measure cold first-link stalls and their frequency. If they matter, query GLES `GL_NUM_PROGRAM_BINARY_FORMATS`, test `glGetProgramBinary`/`glProgramBinary` and validate each recovered program before replacing source link. Key to exact GLSL source and Mali driver/renderer/version. Use a small bounded disk cache (or skip entirely if links do not account for stutter). Do not transplant Ryujinx's host-size or parallel thread policy.

**Vertex/index cache:** extend [stationary vertex census](../evidence/gpu-texture-residency/README.md) to independently verified **moving and battle** scenes, and count index data too. Only if changed-byte and `glBufferData` cost justify it, track content/owner generations on all guest writes and skip identical uploads without reintroducing stale skinned geometry; no second VBO ring rewrite.

### 14.6 First practical sequence and experiment artifacts

| Order | New evidence / implementation | Stop or promote criterion |
| --- | --- | --- |
| **1** | `evidence/emucache-texture460/`: read-only destination-copy equality + own-host-validity generations, upload and GPU-queue timings | If copies aren't identical *and* host content isn't valid, **stop**; don't optimize the rejected source alias |
| **2** | If 1 passes, guarded upload skip A/B on identical destination bytes only | Real frame P50/P95/presents improvement plus KMS and CPU/GPU coherency |
| **3** | `WOL_UNIFORM_CACHE=1` matched multi-scene A/B and source/cache invalidation tests | Promote only if >noise, not because census found 45.8% |
| **4** | Read-only GPU release/fence + FBO transition timing and dependency graph | Quantify a safe serialization bottleneck, including combat |
| **5** | Bounded GLES sync and/or redundant-FBO avoidance behind experimental gate | Pass full battle/street/map pixel parity, P95 and memory-pressure checks |
| **6** | Host texture view-compatibility census; if positive, one sharing A/B | Measurable incremental Mali commit saving beyond existing joined views |
| **7** | Cold shader-link and moving/battle immutable-stream profile | Implement bounded caches only if measurements justify their costs |

- **Latest execution checkpoint:** [handheld preflight](../evidence/handheld-preflight/README.md), [exact destination census](../evidence/emucache-texture460/README.md), [guarded upload skip A/B](../evidence/emucache-upload-ab/README.md) and [effective GPU clock experiment](../evidence/gpu-governor-ab/README.md) are now implemented/measured. Existing AM mode is already fixed handheld; only performance-mode queries were observed, and internal 1080p allocations persist. Exact destination repeats are real, but the default-off upload skip has no repeated whole-frame gain (gulch controls 23.491/23.460 vs candidate 23.363/23.629 presents/s). Two requested-governor arms were invalid because effective clocks returned to 150 MHz; a min-frequency arm actually sustained 600 MHz and observed 26.540 presents/s, P95 40.259 ms in the same gulch. That remains below target and is not a production clock change. SwapPSS remains >500 MiB; no swapoff or speculative page discard was attempted. All finite owned runs restore original saves and Spruce. The overlay build generator now includes new/deleted/nested source paths and verifies exact native-file parity before building.

Treat §13 handheld-mode resolution discovery and §14.2 guarded texture-460 upload skipping as **executed and closed for performance** on current evidence; proceed to [§15 Unity RT origins and controlled 720p work](#15-m7-after-handheld-preflight-unity-render-target-origin-and-720p-plan), while §§4–6 M5 allocator/M6 post-copy ASTC remain independent. **Neither 30+ FPS nor no-swap is achieved or claimed** by the completed experiments. Maintain fixed build SHA, identical owner save/section/environment, alternating trials, actual KMS frames, phase + Mali/VM samples, scene restoration, no stolen owner process and clear accepted/rejected result for every experiment.

## 15. M7 after handheld preflight: Unity render-target origin and 720p plan

**Execution checkpoint: 2026-10-19; source baseline: `main` at `8ffa2f90b3106938c6c2323eeca1c90b207aeaa8`.** Current decision supersedes earlier *proposed* `13 handheld-mode overrides and `14.2 upload-skip experiments. This section contains **new, unimplemented next experiments**; nothing below claims that guest render targets have been switched to 720p, that FPS improved, or that no-swap works.

### 15.1 What is proven, what is not

| Proven in code or device logs | Interpretation and remaining unknown |
| --- | --- |
| Existing AM operation mode is `0`, handheld; performance mode is `0`, Normal | [Mode preflight](../evidence/handheld-preflight/README.md). Correct ABI widths tested; no docked mode or selector needed |
| AM requests 0/1/9/6 observed, but **not** 5/60; no VI ListDisplays seen in measured window | No evidence the game asks a service to choose 720p versus 1080p in this run. Unobserved paths in later scenes remain possible, not a reason to invent a service |
| Guest NVN color/camera targets still requested at **1920×1080**, including an earlier target=5, samples=2 path | Physical host KMS output is already **1280×720**; internal-size selection remains unexplained |
| `WOL_DISPLAY_MAX`/`ListDisplays` experiment did not resize camera targets | Changing advertised display maximum or physical window alone is **not** a solution |
| Exact texture-460 copies repeat (3,598/3,600 observations), but the guarded destination-host upload skip did not improve matched FPS | [Equality census](../evidence/emucache-texture460/README.md), [A/B](../evidence/emucache-upload-ab/README.md): controls 23.491/23.460, skip 23.363/23.629 presents/s; default OFF. Don't return to upload-skip as P0 |
| Effective GPU frequency locked to **600 MHz** in one valid `gpumin600` device run | [DVFS report](../evidence/gpu-governor-ab/README.md): gulch 26.540 presents/s, P95 40.259 ms versus ordinary 150 MHz controls ~23.46–23.49 presents/s. Exploratory *one* valid high-clock arm, not a repeatable tuned profile |
| Large measured swap remains | The high-frequency run's game SwapPSS median was ~537 MiB; no cold zero-swap acceptance. GPU frequency is **not** a memory fix |

**Hard limitation:** the public repository contains an overlay patch and hashes for the reconstructed GPL runtime, not the complete original proprietary WoL Unity/IL2CPP binary or owner game payload. A call-site/Unity-target root cause cannot be identified from patch context alone. A proposed guest modification needs **local owner-only analysis** and a legally obtained source/runtime; do not commit proprietary binaries, game assets, shader dumps or save files.

### 15.2 P0 — identify **who requested 1920×1080** before changing any image

**Goal:** distinguish Unity display/quality policy, a `RenderTexture` constructor / `GetTemporary` call, explicitly serialized target settings, Nintendo SDK graphics initialization, and a native fixed-size allocation. All are hypotheses until identified in measured guest PC / code.

1. Add a bounded **read-only** `WOL_RT_ORIGIN=1` trace at the *actual* NVN texture builder/texture initialize request boundary, not just `glTexImage2D`. Include create command identity, guest caller PC or return address, caller module and offset, thread, lifecycle/scene marker, guest texture object, GPU/guest backing pool and offset, `format`, `target`, requested `width×height`, `mip levels`, `samples`, texture usage/flags and first bind/draw/sample/copy.
2. Capture the relevant **guest-side** call chain if safely obtainable from the restored executable/guest stack; attribute repeated 1920×1080 requests to specific owner Unity/IL2CPP or Nintendo SDK instructions/functions. A single adapter caller PC is *not necessarily* the game logic callsite. Prefer offline owner-only disassembly and exact PC->module offsets to speculative backtraces or runtime patching.
3. Record a **render-target flow graph**: source size, logical guest size, actual GL storage size, viewport/scissor, attachment, depth/stencil, downsample/resolve, CPU/GPU copy regions and sampled UV. Separate color, depth, multisample and on-screen window textures; categorize fixed-size versus screen-derived resources, including 1280×720 surfaces.
4. Use existing `NVN_TEXTURE_REAL` / `WOL_DOWNSAMPLE_BLIT` / `WOL_PRESENT_SOURCE` / texture-view logs as join points, and distinguish virtual guest target dimensions from actual host allocation bytes and driver memory. No changes to runtime content, filters or user saves at this stage.
5. On the owner-only `StreamingAssets/core` and any supplied legitimate Unity configuration assets, inspect `QualitySettings`, `PlayerSettings`, boot/display settings and serialized `RenderTexture` references **read-only**. UnityPy can enumerate objects; it does not prove the compiled game references a particular 1080p constant. Map a discovered reference back to a measured target when possible.
6. For matched cold launches, menu, moving street/gulch, saloon interior, map and real battle, record **how many** unique 1080p targets are created and peak simultaneously live/attached, not merely the number of constructors called. End with a table: `guest owner/callsite → creation size → consumers → safe override candidate`.

**Deliverable:** `evidence/rt-origin/` with owner-excluded addresses/hashes, source/build/section receipts, requested-size histograms, GPU image lifetime graph, proof frames and a classification of each 1080p allocation. Leave ownership `unknown` where the available evidence cannot resolve it. A documented 1080p allocator callsite is the **go gate** for a patch; a random size grep or an inert AM override is not.

### 15.3 P0/P1 — prefer *guest-native* 720p target selection when proven possible

**Decision gate:** if the 1920×1080 dimensions arise from one or a few actual guest functions or serialized settings, test a narrowly scoped 1280×720 variant in the owner-only executable/configuration. Potential sources include `UnityEngine.Screen`, `QualitySettings`, `RenderTexture.GetTemporary` or explicit sizes; their presence is **not confirmed**. Altering `Screen.SetResolution` alone is insufficient when camera targets are explicitly 1920×1080.

- Do not search/replace every occurrence of 1920/1080 in the executable or serialized assets. Prove the exact instruction/data consumer and version/ABI, preserve original binary with hash and revert path, and patch only a verified camera-target size decision.
- Prefer letting Unity recalculate viewport, texel size, matrices, scale-dependent shader constants and related color+depth target sizes itself. Preserve logical/UI coordinates and Npad input behavior; keep **handheld-only**, with no TV fallback or mode-selection flag.
- Start with one identified target family, not global texture rebinding. Record first target requests, subsequent downsample/copy region sizes and KMS output. If guest still creates 1080p despite a display setting, identify the explicit secondary `RenderTexture`/camera target owner before expanding scope.
- Validate physical screenshots and gameplay UI against **the same save and known-good reference**: player outlines and skinned body, WANTED stencil/portrait, map title/markers, dialog/menus, moving camera, saloon, battle and save/load/restart. Historical repack changed map pixel-space semantics: do not accept a cosmetically sharper but wrongly positioned image.
- **Promote only on** correct render graph plus lower actual GPU time and/or measured memory commitment, with no regressions. Reversion to the accepted 1080p path must remain possible during development, but **not** through a TV-mode option.

**Estimated storage arithmetic, not an expected observed saving:** a single RGBA8 1920×1080 mip-0 image holds **7.91 MiB**, versus **3.52 MiB** at 1280×720: ~**4.39 MiB / 55.6% fewer pixels** for that *one eligible target*. Multiply only by independently identified, concurrently allocated instances; depth formats, tiling/alignment, MSAA, copy buffers and host-guest overlap affect real totals. There is no basis to claim a 2.25× game FPS improvement.

### 15.4 P1 fallback — repurpose existing `host_scaled` only for safe render-target owners

The runtime already uses `host_scaled` / `host_width` / `host_height` and `zero_render_scale.h` for *other* paths. This is infrastructure to inspect, **not evidence WoL supports host-scaled 1080p camera images today**. In particular, `nvn_render_sampler_prepare_mode` contains a fail-closed `NVN_LC2_SCALED_CPU_VIEW_REQUIRED` condition for CPU views. NVN texture creation also logs `NVN_LC2_SCALED_STORAGE` where relevant.

1. Audit `zero_render_scale.h` and all `host_scaled` references, including the existing fail-closed CPU-view check, GL upload/readback, framebuffer attachments, depth/stencil resolves, texture views, window crops and synchronization across all EGL contexts. Do not silently bypass guards.
2. Pick **one** trace-proven eligible color target with **no conflicting guest CPU-visible 1080p read/write**; bind a 720p host allocation behind a *default-off experimental flag*. Keep guest-facing metadata truthful; any cross-resolution readback/copy must materialize or reject rather than return improperly sized bytes.
3. Transform viewport/scissor and host texel/UV coordinates consistently. Match **depth/stencil and multisample attachment dimensions**, FBO completeness, GL state restoration, downsample dimensions and all texture sampling; fail closed if an unsupported alias, partial update or texture format appears.
4. Distinguish *resident GPU storage reduction* from guest NVN pool memory, which may remain 1080p-sized. Correct GLSL texture filtering, pixel-centre sampling, edge/stencil coverage and UI layout are acceptance gates.
5. Compare A/B with one target family before attempting a graph-wide 720p scale; revert on `GL_INVALID_FRAMEBUFFER_OPERATION`, stale CPU/GPU mirrors, missing pixels, coordinate shifts, newly triggered `stop()` conditions or higher P95.

**Choose this path only if guest-native selection fails or is unreasonably invasive.** A blanket dimension override in `glTexImage2D` / `NVN_TEXTURE_REAL` is explicitly prohibited by the documented guest layout, copy and asset-coordinate contracts.

### 15.5 P1 independent experiment — GPU DVFS with **effective** clocks

One [`gpumin600` device run](../evidence/gpu-governor-ab/README.md) **really** sustained 600 MHz and observed 26.540 runtime presents/s, P50 37.151 ms, P95 40.259 ms in gulch idle; same-scene ordinary controls were 23.491 and 23.460 presents/s. This is promising but not a repeated, tightly cache/VM-controlled A/B. Two other requested-governor arms are **invalid** as 600 MHz tests because Spruce put the effective clock back to 150 MHz.

- Discover the **actual available OPP/frequency steps** from sysfs before proposing settings (300/400/500/600 MHz are example targets *only if supported*). In owned, recovery-safe tests, apply minimum frequency at the correct post-launch lifecycle phase and continuously **read back effective clock** during every measured window.
- Compare ≥3 alternating valid arms at ordinary policy and chosen OPPs, *same* owner game build, section, save, scene, render flags, startup/warm state and measurement cadence. Include real combat/movement, not just a stationary gulch idle window.
- Log GPU temperature/thermal throttling, power/battery if accessible, frame P50/P95/P99, dropped/late presents, CPU clocks, VM/page faults, Mali allocations and clean clock policy restoration. Do not treat a requested governor as proof of frequency.
- If sustained high clocks deliver repeatable >noise gains without unacceptable thermals, consider an opt-in **device-level performance policy** with guaranteed restoration; this is **not** a TV mode, and not an unreviewed default. Do not create persistent global policy, blindly set `performance` governor or claim zero-swap improvements.

**Go/no-go:** measurable performance improvement under confirmed actual clocks, with heat and battery cost documented; target still **30+ FPS and P95 ≤33.33 ms** in representative gameplay, not one favorable map window.

### 15.6 Updated execution order and acceptance criteria

| Priority | Next change (all currently proposed) | Output and stop condition |
| --- | --- | --- |
| **1 — P0** | Read-only NVN builder → guest Unity/SDK PC + RT lifetime/consumer mapping | Evidence of **actual 1080p allocator origin**, with versioned owner-only offset and impact graph; if none is attributable, report blocked |
| **2 — P0/P1** | Narrow owner-side Unity/`RenderTexture` 720p size decision A/B **only when origin is identified** | Same-scene picture parity, correctly scaled color/depth/downsample, reduced real GPU workload or memory |
| **3 — P1 fallback** | Existing `host_scaled` safety and compatibility audit, then one 720p host target | No CPU-view/alias contract violation, framebuffer/stencil regression or guest memory incoherence |
| **4 — P1 parallel** | Valid effective-clock OPP sweep with thermal and battery trace | Repeated actual-GPU-frequency A/B; keep settings restored, no production clock policy without proof |
| **5 — P1 RAM** | M5 inner Unity allocator/free-list ownership and retained core-read-lifetime; M6 post-copy ASTC expansion only with measured driver commit | Target reclaimable *live* bytes; no speculative `madvise` or global `swapoff` |
| **6 — full acceptance** | Owner-demonstrated movement, guide, combat, transitions, save/load and cold recovery-safe swap-disabled launch | Stable **30+ FPS**, P95 ≤33.33 ms where applicable; **no swap configured before launch**, no OOM/CMA collapse, correct KMS/audio/input and Spruce recovery |

**Closed/deprioritized as FPS levers after device A/B:** another Handheld/TV operation-mode override; `WOL_DISPLAY_MAX` layer-cap change; generic texture-460 producer sampling; repeated destination `WOL_UPLOAD_SKIP`; immediate `WOL_COPY_GPU`; bounded `WOL_PBO_UPLOAD`; `WOL_REFRESH_DIRECT`; simple VBO ring and resource-lookup cache. Keep `WOL_UNIFORM_CACHE` as a small separate A/B if requested; it is not an answer to M7's 1080p target selection.

**Evidence and reproducibility:** preserve the exact pinned reconstructed GPL overlay, owner-only ELFs/data and save hashes, source offsets, test binary identity, cold/warm protocol, physical KMS frames and per-phase GPU/VM measurements. Do not treat runtime presents as independently measured panel FPS; separate pixel fill from frame intervals, and never sum overlapping `PSS + GPU commit` as independent RAM. Public artifacts must not include owner Switch binaries, proprietary Unity assets, extracted shader blobs or private saves.

### 15.7 Execution after this revision — origin checkpoint, not target acceptance

- **Revisions applied:** owner updates `620a9b1` and `f79c12f` were fetched and fast-forwarded during execution. No new AM mode/resolution endpoint, TV selector or content-skip promotion was added.
- **Read-only §15.2 trace now exercised:** [RT origin](../evidence/rt-origin/README.md), ELF `5bb707bb…`, 207-file native source parity. Bounded original-guest NVN initialization/finalization records include descriptor, pool, thread, monotonic time and up to eight saved return addresses. 512 events (365 initialize / 147 finalize) include 13 1080p requests; the cap was reached, so later lifetimes and a full graph remain incomplete. Initial window images are distinct from dynamic camera/MSAA/depth requests crossing a Unity render-thread queue. That queue boundary is **not** the IL2CPP producer callsite.
- **Concrete configuration lead:** actual owner Switch `level0` object 29 references UpRender script 165 and decodes to `forceWidth=1920`, `forceHeight=1080`. Read-only desktop IL shows that `forceHeight` imposes a minimum rendering height before RenderTexture construction. The native Switch consumer/producer join is still required before attributing all dynamic targets or patching this setting. Owner data is unchanged; only hashes/settings metadata are published.
- **Earlier narrow guest-native trial not promoted:** [startup/query 720p](../evidence/guest-rt720/README.md) really shrank initial swapchain/depth allocations, but later 1080p targets persisted. Same-ELF OFF control: 23.936 presents/s, P95 45.148 ms; ON trials: 23.996 / 23.520, P95 45.303 / 45.767 ms. This is not a completed three-pairs study or a repeatable FPS win; it is not §15.3 coordinated graph acceptance. Default remains OFF in the latest installed diagnostic build.
- **Other bounded follow-ups closed/documented:** [compatible-view and SDK-owner census](../evidence/memory-owner-followup/README.md) found no incremental exact host duplicate group or matched free; [shifted private COW read](../evidence/romfs-cow/README.md) really mapped 144,384,000 bytes but Unity dirtied most of them, so no memory win; [GPU elapsed-query classifier](../evidence/gpu-pass-timeline/README.md) observes selected pass timing, not an additive total or permission to remove waits. All experimental fast paths stay OFF; the attempted independent COW review did not clear because its external credentials expired.
- **Validation:** 42 memory/helper tests, 24 additional selection/sprite/map/frame-parity tests, clean local ARM64 build/source reproduction, owned-run save restoration, zero analyzer GL errors and real Spruce recovery. Neither >30 representative gameplay presents/s nor recovery-safe swap-disabled cold launch is achieved. No swap policy or speculative page discard changed. Next: trace the queued native producer back to UpRender and complete the target/viewport/depth/copy consumer mapping before another size variant.

### 15.8 Native producer resolved; first component-settings A/B above 30 in gulch

The [UpRender checkpoint](../evidence/uprender-owner/README.md) supersedes §15.7's unresolved native-consumer lead, **not** its full-scene/no-swap acceptance limits. A read-only metadata-v23/code-registration/field-offset join resolves Switch UpRender.Awake at main+0x513df8, UpdateTexture at main+0x513eb4 and its exact RenderTexture constructor call at main+0x514838. Native fields +32/+36 feed the actual width/height arguments. A live control confirms one component creates two 1920×1080 RenderTextures; this is no longer merely a desktop IL or serialized-field hypothesis.

The default-OFF `WOL_UPRENDER_720=1` variant changes only this component's eight process-local settings bytes during Awake, before allocation, with original 1920/1080 settings, full main.text hash and exact instruction checks. Unity runs its original downstream camera/texture setup. It does **not** change owner files, protected section, SDK startup constants, NVN descriptors, GLSL, swap, clocks or operation mode. It cannot be combined with the earlier WOL_GUEST_RT720 trial.

Same-ELF A/B `upowner-a1`/`upowner-b1`: gulch **24.019 → 32.638 runtime presents/s**, P95 **44.960 → 33.438 ms**, Mali commit median **253.344 → 232.023 MiB**. Capped NVN logs show nine dynamic 1080p color/depth/MSAA create events becoming 720p; the four initial SDK/window events remain 1080p. Same section/save/non-treatment environment, zero GL errors, restored original saves and visible Spruce after both runs; spot-reviewed world, map and title preserve layout/body/WANTED content. Backend resource pointers are not directly identified with the RenderTexture native pointers; full queue identity, lifetime and consumer coverage is still open.

**Verdict at the first-pair checkpoint:** actual producer and an initial causal FPS effect established; no promotion or full acceptance. This is one pair, P95 is still slightly above 33.33 ms, and candidate SwapPSS median is **551.668 MiB** (control 537.770 MiB). No no-swap or total working-set saving is claimed. Next gate: alternating repeated same-ELF controls/candidates and moving/interior/battle/load coverage; maintain the independent M5 memory-owner gate. Do not disable swap or discard pages based on this GPU-target improvement.

### 15.9 Repetition and stability stop condition

All six A1/B1/A2/B2/A3/B3 attempts are collected with matching identities/environment and clean save/Spruce restoration. **Only five have valid gulch performance windows**: A1/A3 are 24.019/24.226 presents/s (P95 44.960/44.293 ms); B1/B2/B3 are 32.638/33.348/33.878 (P95 33.438/32.157/31.904 ms). A2 stops presenting at frame 1481 before the idle window while audio/HID continue; all seven requested route frames are byte-identical, including the supposed map. Its frame window is missing, not zero FPS, and the failed run remains published. No live stack proves the cause.

The repeated local gain is real but is **not** three complete valid pairs, all-scene acceptance or a stable production profile. Separate the exact component-only Awake setting from extended constructor/queue observations; next runs must use a matched trace-off profile and collect owned-process diagnostics if presents stall. The report now excludes absent/short frame windows explicitly. Candidate SwapPSS still measures 532.668–551.668 MiB. Keep both flags default OFF, do not swapoff/discard, and continue the M5 memory-owner work only with live ownership evidence.

### 15.10 Component-only scope and progress watchdog exercised

[Trace-off same-profile A/B](../evidence/uprender-scope/README.md), ELF `273b4638…`, now observes **23.549 → 33.564 runtime presents/s**, P95 **45.798 → 32.425 ms**, Mali commit **261.660 → 221.566 MiB**. OFF installs none of the five observation sites; size-only ON intercepts only the verified component Awake. Constructor/return/queued-create observations require their separate explicit trace flag. Both runs pass 87 real present-progress checks, preserve section/save/environment and cleanly recover Spruce with zero GL errors. Correct candidate gulch body/UI and genuine map are spot-checked in KMS frames.

The opt-in probe watchdog no longer equates PID/audio/HID activity with present progress; a stale marker aborts and attempts owned-process diagnostics before the existing save/menu cleanup. Offline replay catches the real A2 stall. No healthy-run GDB attach was used, no cause/fix for the older freeze is claimed, and this remains one lower-observation pair, not endurance/physical/multi-scene acceptance. Candidate SwapPSS is still **537.852 MiB**; the remaining no-swap work is M5 ownership/lifetime, not another fill-rate claim. No default or swap policy is promoted.

### 15.11 Launch-buffer identity closed; first live stall capture

[Bundle-header evidence](../evidence/bundle-header/README.md): the in-process 144,392,040-byte `ROMFS_READ` target **is** a consistent `System.Byte[]` at read time (bounded read-only `/proc/<pid>/mem` header/name observation on the hash-pinned runtime, parameter maps for `AssetBundle.LoadFromMemoryAsync`/`nn::fs::File.Read`). At +10 s/+60 s the same address holds an 11.6 MB `Byte[]`: the launch array was collected and its storage recycled in the managed heap, which explains the missing ~76 MiB anonymous drop versus the 136.9 MiB read. **"Free the launch buffer" is closed as a reclamation lever**; memory work must target the live steady set. GC-root reachability and any free safety remain unproven and no page was discarded.

The same run provides the first live stall capture: the opt-in watchdog fired at the first >5 s present gap after `continue-load` (black load phase, mean luma 7.5/255) while the process was **actively loading, not deadlocked** (RSS 478→716 MiB, MemAvailable 251→91 MiB, swap churn; main thread `futex_wake`, workers waiting, Mali/SDL normal). The 5 s budget cut a possibly-recoverable load, so permanence and root cause stay unestablished, and A2's earlier gulch freeze remains unexplained. Budget guidance: 5 s only in steady gameplay; 20–30 s around scene loads. No flag is implicated (A2 had none of this run's extra tracing), no default or swap policy changes.

### 15.12 M5: big blocks are pools, and the pools are sparse

[Pool residency evidence](../evidence/m5-pool-residency/README.md) (owner-local disassembly + `poolres-b1`, 720 candidate, `--block-pages` read-only pagemap):

- The two dominant 192 MiB live blocks are Unity's **BufferPool/TexturePool**, allocated through a clamp path (`min(requested, 0xC000000)` vs the in-code alternative `0x4000000`) whose strings are `BufferPool # %zi` / `TexturePool # %zi`. The clamp runs after a failed first attempt, which is why both sit at exactly 192 MiB.
- Their residency is small: **62.8 MiB + 13.5 MiB present of 384 MiB requested**, and a third 96 MiB graphics-family block has **0 MiB present**. Total of all eleven live ≥4 MiB blocks: 813.9 MiB requested → **362.3 MiB present / 12.7 MiB swapped**.
- **Capping the pools is closed as a no-swap lever**: it would shrink virtual reservation, not resident RAM, and risks pool exhaustion. The 138 MiB GC segment (127.5 MiB present) is the launch `Byte[]`'s segment, already established as recycled in place.
- Because tracked present pages (362 MiB) nearly equal steady-state PSS, the ~550 MiB of swap must come from allocations **below the 4 MiB trace threshold**. The next memory instrument is a lowered allocation threshold (≤256 KiB) with caller aggregation - not another pool or page-discard experiment.

`poolres-b1` also measured an **episodic 10.7 s gulch-entry stall** inside its window (9.86 presents/s, max gap 10.745 s) that stayed under the 20 s watchdog. Its FPS window is therefore invalid and excluded; this confirms both that the earlier 5 s budget cuts recoverable loads and that scene-entry stalls are real and intermittent. No reclaim, swapoff or page discard was attempted; the candidate remains default OFF.

### 15.13 Where the swap lives: guest arenas plus a fully-cold 72 MiB mapping

[Per-VMA swap census](../evidence/m5-swap-location/README.md) from two same-ELF arms (`vmaswap-b1` 720 / `vmaswap-a1` control, `--vma-swap`):

- The **guest-heap arenas hold ~70% of all swapped pages**: 358.0 MiB (720) / 366.8 MiB (control) inside the largest anonymous VMA, plus 41.3 / 59.4 MiB in a second guest arena. Since the tracked ≥4 MiB blocks inside them are already proven sparse, that swap belongs to **sub-4 MiB allocations** - the next instrument is a lowered allocation-trace threshold (≤256 KiB) with caller aggregation.
- Both arms also contain a **deterministic 72.0 MiB anonymous mapping with 0 MiB resident and 64.1 MiB swapped**, at a randomized host address. Something wrote ~64 MiB once and never touched it again; releasing a proven-cold block of that size would remove ~**12%** of the measured swap. Ownership is unresolved (not one of the port's direct mmap sites; no 72 MiB constant in the native tree); the next run adds startup/menu/game-idle maps timeline plus bounded 64-byte head/tail content samples for the largest cold VMAs.
- Totals at game-idle: 720 **419.4 Pss + 509.1 SwapPss**; control **391.3 + 536.4**. The single-pair swap difference is not a promoted win.

Nothing was reclaimed, discarded or swapped off; both arms remain the same default-OFF diagnostic ELF.

**Phase timeline (`vmaswap-b2`):** the 72 MiB zero-filled mapping exists already at the startup sample (before CONTINUE) and is byte-identical in character through precleanup: 0.2 MiB resident, 63.9 MiB swapped, first/last 64 bytes all-zero - something zero-filled it once during the initial load and never touched it again. SwapPss by phase: **startup 623.8 → menu 619.8 → game-idle 556.0 → precleanup 508.2 MiB**, i.e. the initial load itself parks more in swap than steady gameplay. The 193.5 MiB texture-pool VMA carries 63.6 → 45.9 MiB of swap with 0xFF-filled head bytes. Next instrument: a bounded host-side mmap logger (default OFF) that records size+caller for host mappings ≥32 MiB, then a guarded release only for a proven-cold owner; nothing is discarded on the current evidence.

### 15.14 TransferMemory backing copy: the cold 72 MiB owner is named, and its sparse-copy A/B

The fully-cold 72.0 MiB anonymous mapping from [15.13] is the runtime's own guest **TransferMemory backing copy**: a bounded host-allocation log (`hmmap-b1`, LD_PRELOAD shim, default OFF) shows `wol-horizon+0x53afc` calling `mmap(64 MiB, ANON)` and `memory.h transfer_create_locked` memcpy-ing the whole region; the 72 MiB VMA is that copy merged with an adjacent 8 MiB mapping. The equality gate that ships in the runtime settles the content question directly:

```
T2_TRANSFER_SPARSE_COPY index=0 source=0x1078b00000 bytes=67108864 copied-bytes=0 skipped-bytes=67108864
```

The transferred region is **entirely zero**, so the sparse copy (`T2_TRANSFER_SPARSE_COPY=1`) commits nothing. Matched pair (same ELF `273b4638`, 720 both arms, only that gate differs):
[evidence/transfer-sparse](../evidence/transfer-sparse/README.md).

- Cold 72.0 MiB VMA: 64.1 MiB SwapPss in every control phase (as in all five earlier runs) - gone in the candidate; no ≥64 MiB VMA carries swap.
- **SwapPss (MiB) control -> candidate**: startup 582.3 -> 557.5; game-idle 526.4 -> 495.8; precleanup 488.5 -> **454.8** (-33.7).
- Ledger accounting removes the copy contribution exactly; the rest is phase-level respread (guest arena +76.8, second arena -47.0), so only the net deltas are claimed.
- Presents 4882 vs 4877 over the identical route; KMS frames near-identical (world diff mean 0.1/255).

The gate stays **opt-in and default OFF**; nothing else changed. The remaining swap is dominated by the guest arenas.

### 15.15 Lowered-threshold census: historical checkpoint, interpretation corrected

> **Superseded interpretation:** a later visual/lifetime audit found that `allocmin-b1`/`b2` remained on splash/title and the old tracer could duplicate nested realloc pointers. The figures below remain raw-window observations, not a complete gameplay allocation census or proof that the untracked arena pages are reclaimable. See [allocator-history follow-up](../evidence/allocator-history/README.md). The earlier "measured false" conclusion is withdrawn pending corrected real-gameplay sampling.

[Lowered-threshold allocator census](../evidence/alloc-min/README.md) — two read-only single-arm runs on ELF `84819832…` (`allocmin-b1` `WOL_ALLOC_MIN=262144`, `allocmin-b2` `WOL_ALLOC_MIN=65536`), every other flag OFF, 87 progress checks per arm, saves restored, real Spruce screen after each run:

- **Complete enumeration** at both thresholds (227 / 778 events, `incomplete=0x0`, no pagemap errors, no truncation): the game's direct pinned SDK StandardAllocator traffic is small — 96 / 261 live blocks ≥256 KiB / ≥64 KiB.
- Tracked blocks carry 332.5 / 395.3 MiB present but only **83.6 / 38.9 MiB** of a 454.6 / 411.6 MiB process SwapPss; the outside-tracked remainder is stable (~371–373 MiB) across thresholds, phases and runs.
- The **1524.7 MiB anonymous arena** carries 290–295 MiB swap; tracked blocks inside explain only 21.9–31.9 MiB — **~263–275 MiB unattributed** (allocated below 64 KiB or through non-traced paths).
- The 64–256 KiB band (≈164 new blocks) is **resident, not swapped** (~3.5 MiB): mid-size SDK blocks are rejected as the swap holder at this granularity.
- The known cold 72.0 MiB TransferMemory copy (64.1 MiB swap) is present in these control arms (sparse gate OFF) and stays a separate, already-measured lever ([transfer-sparse](../evidence/transfer-sparse/README.md)).

**Position:** "the remaining arena swap hides in known ≥64 KiB SDK allocations" is now measured false; no pool cap, page discard or swap change is justified by this. Open: sub-64 KiB vs non-SDK suballocation ownership of the ~265 MiB unattributed arena swap and its page liveness. Instrument shipped here: `WOL_ALLOC_MIN` (runtime), streaming `scan_log` + per-caller aggregation (probe), `tools/wol_allocmin_report.py`.

## 16. Resource optimization decision after the 720p and arena-swap results

**Reviewed:** 2026-10-19; baseline main `9d125e06cbdc37ffbaa4e8e9f218b66bec683353`. **This section is the current decision and future-work contract**, not a claim of a new device run. Sections 1–15 are historical and include proposals later rejected; if they conflict with this section, the later measured verdict prevails. All experiments listed as "next" are **proposed**, not yet deployed or accepted. The owner binary, original assets, save files and raw shader dumps must remain private.

### 16.1 The decision: finish the 720p port; avoid unlimited no-swap R&D

**Is further optimization worth doing? Yes, selectively.** The first large, repeated FPS win has already been found. A native Switch IL2CPP inspection identified `UpRender.Awake` (main+0x513df8) and `UpdateTexture` (main+0x513eb4), the component's `forceWidth`/`forceHeight` fields at +32/+36, and their flow to the real Unity `RenderTexture::.ctor` at main+0x6e7ca8. The opt-in size-only `WOL_UPRENDER_720=1` changes only these two fields **1920×1080 → 1280×720 before Unity allocates**. It does not rewrite NVN texture descriptors, GLSL, game files, SDK display policy or handheld operation mode.

- Three measured 720 candidates: **32.638 / 33.348 / 33.878** runtime presents/s in stationary gulch. The two valid earlier controls: **24.019 / 24.226**; a third 1080 control froze and is **invalid for FPS**. [Owner/native proof and A/B](../evidence/uprender-owner/README.md).
- An independently isolated **component-only, trace-off** pair: **23.549 → 33.564** runtime presents/s, **P95 45.798 → 32.425 ms**, Mali context commit **261.660 → 221.566 MiB**. Game process PSS **377.845 → 392.198 MiB**, SwapPSS **550.789 → 537.852 MiB**. This is one isolated pair, not whole-game acceptance. [Scope and watchdog](../evidence/uprender-scope/README.md).
- The core release criterion is now **correct gameplay, reproducible frame progress and a stable 720p pipeline**, not further speculative frame-rate micro-optimizations. If these pass, a port **with normal swap available** may be worth delivering as an explicitly qualified experimental build.
- **Zero-swap is not solved.** The system has ~963 MiB usable RAM, while typical current gameplay already accounts for roughly 380–500 MiB process PSS and 410–550 MiB SwapPSS in different runs, plus the OS and Mali resources. PSS/SwapPSS are page-accounting metrics, not a guarantee that every swapped page must be resident simultaneously; Mali commitments can overlap process memory and **must not simply be added**. Nevertheless hundreds of MiB of anonymous swap make a recovery-safe cold boot with swap OFF highly uncertain. Treat zero-swap as an **independent, conditional research goal** until real owners/free lifetimes are proven.

**If the actual goal is a stable, playable West of Loathing on TrimUI, continue the limited 720p stability/acceptance work. If strict zero-swap is non-negotiable, do not present a swap-enabled build as meeting that requirement or turn swap off experimentally without recovery safeguards.** One more bounded allocation-ownership investigation is reasonable; open-ended memory interventions are not.

### 16.2 What has been measured — close nonproductive options

| Hypothesis or implementation | Measured evidence | Current decision |
| --- | --- | --- |
| Handheld/TV mode switch | AM already reports handheld `0`; no cmd 5, cmd 60 or VI query observed in normal start; 1080p internal RT remain | **Closed for FPS**. Always handheld, no docked selector |
| `WOL_GUEST_RT720` SDK/startup immediate patches | Initial window targets become 720p, **dynamic Unity RT remain 1080p**, no repeatable FPS gain | **Closed**; don't widen global instruction patches |
| **UpRender component fields** | Native owner proven, dynamic RT become 720p, stationary gulch FPS improves, Mali commit falls | **Promising P0**: stabilize, qualify across game, then promote |
| Copy source GPU image into destination / generic lazy alias | Producer GPU pixels differ from destination CPU-copy content | **Rejected for correctness** |
| Guarded `WOL_UPLOAD_SKIP` for texture 460 | 3,598/3,600 repeated snapshots; >3,400 transfers avoided in one run, controls 23.491/23.460 vs ON 23.363/23.629 presents/s | **Closed for FPS**, default OFF |
| Immediate GPU blit / unpack PBO / direct-upload / VBO ring / resource lookup | No repeatable full-frame benefit; PBO costs ~8.2 MiB extra Mali commit | **Closed** absent new causal mechanism |
| Shader uniform cache | `WOL_UNIFORM_CACHE` already exists, 45.8% redundant bank updates but ~8.9 KiB/frame | Small optional A/B, not a 30-FPS driver |
| Create-time ASTC | Hardware decode works; title creates empty BC textures later filled by CopyBufferToTexture | **Rejected variant**; post-copy caching still optional if *real* static groups |
| Same-storage GPU views | Measured 116 game descriptors show no missing compatible host-name alias group | **Closed on observed scene** |
| `WOL_ROMFS_COW` | 144.4 MB input mmap engages but Unity dirties most pages; swap remains high | **Closed for RAM** |
| Launch `System.Byte[]` | Original read buffer is GC-recycled and reused; its segment remains used | **Do not free or madvise** on this inference |
| 192 MiB BufferPool/TexturePool caps | 384 MiB requested but only ~76 MiB resident in measured two pools | **Closed**: virtual reservation != resident RAM |
| **TransferMemory zero sparse copy** | Eliminates cold 64 MiB copied zero pages, **net** SwapPSS ~−24.8 / −30.6 / −33.7 MiB by phase | **Promising bounded P1**, repeat/lifetime audit |
| Historical direct StandardAllocator request census ≥64 KiB | 778 events in the old splash/title capture; complete-gameplay attribution withdrawn by the readiness/lifetime audit | **Not a gameplay owner exclusion**; use corrected page/span evidence, not ever-lower hook thresholds |
| GPU min=600 MHz | One **actual** sustained 600 MHz run ~26.54 presents/s vs stock ~23.5 in 1080 route | Not a default; 720p already reaches target locally and battery/heat unknown |
| GPU query pass timing | Sampled 1080p ordinal-7 ~10.576 ms; zero-draw ordinal-6 ~10.296 ms; only first 8 of ~24 switch ordinals | Read-only profile incomplete; not license to omit waits |

Current sources: [handheld](../evidence/handheld-preflight/README.md), [UpRender](../evidence/uprender-owner/README.md), [720-only](../evidence/uprender-scope/README.md), [upload skip](../evidence/emucache-upload-ab/README.md), [COW](../evidence/romfs-cow/README.md), [GPU timing](../evidence/gpu-pass-timeline/README.md), [texture ownership](../evidence/memory-owner-followup/README.md), [large pools](../evidence/m5-pool-residency/README.md), [alloc-min](../evidence/alloc-min/README.md).

### 16.3 P0 — turn proven UpRender 720p into an accepted, stable game profile

**Mechanism already implemented:** `WOL_UPRENDER_720=1`, `WOL_UPRENDER_TRACE=0`. The size-only variant installs only the native Awake hook with exact main.text SHA/instruction guards. It edits **eight process-local bytes** at +32/+36 only after verifying original 1920/1080 component fields. Unity then performs the ordinary render-texture, camera and dependent setup. No alternate TV mode, descriptor mismatch, fake output resolution or runtime clock change.

**Next steps, in order:**

1. **Freeze identities and defaults.** Pin owner main.text SHA, exact UpRender symbol/field offsets and ABI, compiler, rebuilt source manifest/overlay, ELF hash, original corrected-map section, owner save hash and full launcher flags. Confirm the guard fails closed on a different game revision and on incompatible `WOL_GUEST_RT720=1`. Save a recoverable last-known-good binary. Keep UpRender trace and heavyweight page inspection **OFF** in performance arms.
2. **Three *valid* alternating A/B pairs** with one identical trace-off ELF. Control: size flag OFF. Candidate: size flag ON. Same verified gulch save, scenes, stock effective GPU/CPU policy and sampling cadence; alternate A-B/B-A across repeated runs to separate cache warming from the change. Missing/stalled windows count as **failed trials**, not 0 FPS or a successful cleanup. A previous 1080 A2 froze at frame 1481; its cause is unknown, so a new complete control series is essential. Record P50/P95/P99, runtime presents/s, first-frame-after-load, long-frame bins, actual host clocks, GPU memory, PSS/SwapPSS, active swap page-ins/out and all environmental differences. Repeats must show benefit above observed natural variance; do not cherry-pick best frames.
3. **Actual scene coverage:** start menu → CONTINUE → independently verified *moving* world → map/return → saloon/interior → **real battle** → dialogue/guide and pause/inventory → save/load/restart → at least one extended world/interior return cycle. The automated button label does **not** prove movement or combat. Request owner-supplied known battle save/route if the diagnostic injector cannot trigger combat; do not invent scene coverage.
4. **Per-scene correctness:** compare owner reference and same-save 1080 control to 720 KMS images at consistent event positions. Explicitly check PC/Cactus Bill limbs, WANTED stencil/alpha, map paper + all five markers/NEW tags, guide/title, sprite texture rectangles, character animation, menu overlays, antialiasing edges, dialogue portrait, combat log, inventory and cursor. A screenshot mismatch may be due to animation phase; pair with event/geometry traces, not just raw pixel differences. Include sound and physical buttons, not only synthetic HID, plus save integrity and return to Spruce.
5. **Map actual render graph:** dynamically requested 1080 targets decreased 13→4 in capped trace; nine *creation events* moved to 720, **not nine simultaneous independent images**. Confirm GL-storage sizes and lifetime, all four remaining initial SDK/window 1080 objects, FBO color/depth/MSAA compat, downsample and copy extents, viewport/scissor, texel-size shader constants, UV and final 720 KMS window. Do not optimize the remaining initial 1080 objects until a measured live consumer/size audit justifies it.
6. **No false acceptance by process liveness:** full route requires monotonic present progress and scene content changes. Save/Spruce recovery receipts do not prove gameplay was responsive. Keep the new watchdog in diagnostic owned runs with **5 s only during settled gameplay** and a **20–30 s load/transition window**, because earlier traces show legitimate load gaps and a 10.7-s entry pause. Use proper scene classification, not requested stage names.
7. **Recovery and production checks:** snapshot installed ELF/section/save, verify owner PID/start-tick before any cleanup, run normal launcher with no diagnostic input socket or trace, restore original save, check actual Spruce MainUI image and physical controls/audio. Report explicit accepted scenes vs untested areas; avoid promoting an unstable experimental ELF merely because gulch is fast.

**Promotion gate:** stable ≥30 runtime presents/s and P95 ≤33.33 ms in *representative moving, interior and combat windows* (or explicit documented exceptions), no frame-progress stalls or GL errors, scene/UI parity, working input/audio/save/load, no memory/thermal regression and repeatable A/B. The original A2 hang must be reproduced/understood or ruled out by a sufficiently extensive valid stability series; do not call it "fixed by removing instrumentation" without a live stack.

**Stop the FPS optimization track** once 720p is genuinely stable and meets owner-visible performance targets at default clocks. Do not add a new cache/renderer overhaul for sub-noise improvements. Reopen only for a reproducibly slow scene with measured bottleneck.

### 16.4 P0 — diagnose freezes and swap-related scene-transition stalls

Do not conflate two distinct observations. `upowner-a2` froze presenting at frame 1481 while HID/audio continued and its requested route screenshots were identical; **root cause unknown**. Other runs experienced genuine **5.8–10.7 s loading/entry gaps**, with memory pressure and page activity, that may resolve normally. The previous 5-s watchdog was too aggressive during loading; a failed presentation is not necessarily a permanent deadlock.

1. Time-stamp input trigger, Unity load start/end, ROMFS file and asset read milestones, first camera draw, first changed present, first verified successful movement, scene exit and reentry. Do **not** use only action-request labels.
2. Capture bounded, synchronized `/proc/<pid>/stat` major faults, `/proc/vmstat` §pswpin§/§pswpout§, `/proc/<pid>/smaps_rollup`, process threads/wait channels, actual GPU clocks, driver allocation estimate, frame gap and memory/CMA headroom. Avoid heavy smaps/pagemap scans during FPS windows and never blindly sum GPU commit with PSS.
3. If *true stall* occurs, obtain an owned-process stack-only thread snapshot, last NVN queue submit/GL draw/present, EGL surface/context, fence/wait ownership, futex/worker states and the last KMS image. Guard GDB/process inspection with owner PID and start tick; no unbounded stack dumps or saves in public logs. Record whether the watchdog's optional GDB branch was actually exercised.
4. Use adaptive 5-s stable-play/20–30-s load windows, the exact frame counter and monotonic clock. A diagnostic watchdog timeout should trigger evidence+clean restore rather than count as a performance failure with a fabricated frame interval.
5. Only when **actual** GPU wait dominates an identified failing window, extend existing EXT_disjoint_timer_query classifier from ordinal 0–7 to all **~24** target switches with bounded nonblocking queries and disjoint checks. An expensive zero-draw pass may be a clear/resolve/scheduling wait and must not be deleted on assumption. Existing evidence: one true final wait and three already-elided completion waits; a blanket `MOMO_SUBMIT_FINISH=0` gives an invalid guest-completion promise, while old async mode hit `EGL_BAD_SURFACE`.
6. **Accept** only a matched fix for a demonstrated stall cause or lower P95/P99/scene-load latency with correct frame/scene progress. If extended 720p play has no disruptive stalls, close this investigation rather than adding unbounded synchronization machinery.

### 16.5 P1 — one modest memory win: correct sparse TransferMemory backing

The [TransferMemory report](../evidence/transfer-sparse/README.md) names the cold **72 MiB anonymous VMA** (64 MiB backing plus merged neighbor): the inherited `memory.h transfer_create_locked` created an anonymous 64 MiB host mapping and eagerly copied a guest buffer found to be **entirely zero**. The runtime already has a default-OFF `T2_TRANSFER_SPARSE_COPY=1` that avoids committing untouched zero pages. In the measured same-ELF A/B: the cold VMA's 64.1 MiB SwapPSS disappears; **net** process SwapPSS startup **582.3→557.5**, game-idle **526.4→495.8**, precleanup **488.5→454.8 MiB**. The reduction is not a fixed −64 MiB across process snapshots: other guest arenas redistribute pages. Normal-route 4,882 vs 4,877 presents and near-identical KMS world frames indicate no visible difference in that *one* pair.

**Remaining acceptance sequence:**

1. Audit the exact zero/nonzero **source at transfer creation**, not old page observations. Check parent mapping lifetime, guest writes after transfer creation, read/write aliases, concurrency, byte order, page alignment and rollback. Prove all skipped pages are logically zero and that future writes naturally materialize correct pages. No missing copy due to uninitialized memory.
2. Add synthetic and on-device ARM64 fixtures for all-zero, sparse mixed pages, dense nonzero, offset/unaligned, shortened range, read after write, map reuse, double creation, aliasing and allocation failure. Every unsupported case must fall back to ordinary full copy without touching partial destination state.
3. Repeat **≥3 matched A/B pairs** using the accepted, otherwise unchanged **UpRender 720 trace-off profile** and stock clocks; report per-VMA page sums and process net SwapPSS/RSS, memory pressure, swap faults, startup/transition latency, Mali commit and real KMS/state parity. A candidate reducing SwapPSS by 30 MiB but adding 30 MiB peak RSS is not a zero-swap win.
4. Validate full game route and cleanup, including battle/save-load; mark the gate accepted only if exact bytes and lifecycle hold under actual reallocation. **Only then consider default-on.**
5. If net physical-pressure improvement disappears, a nonzero input breaks the contract or lifecycle cannot be proved, **stop**. This is a small memory optimization, not a claim of eliminating 400–500 MiB remaining swap.

Do not retry `WOL_ROMFS_COW`: it mapped 144,384,000 bytes but Unity dirtied the vast majority, leaving high anonymous swap. File-backed mappings are not a substitute for object-level lifetime proof.

### 16.6 P1/P2 — remaining RAM: one bounded investigation of the **inner Unity/GC arena**, then a stop decision

**Historical counters, not current gameplay attribution:** the old [allocation census](../evidence/alloc-min/README.md) used thresholds **256 KiB** / **64 KiB** with 227 / 778 events. The later [readiness/lifetime audit](../evidence/allocator-history/README.md) established that its actual images were splash/title, not the requested gameplay phases; nested realloc also broke live-pointer consistency despite the old incomplete flag being zero. Its 38.9/411.6 MiB and ~263–275 MiB arena-gap figures remain observations of those historical captures and **must not exclude present SDK owners or establish gameplay free space**. The corrected real-scene `allocfix16b` 16 KiB trace reaches 8,192 events and explicitly incomplete=1; do not lower it again without an inner-owner join. A separate trace-off, heavy read-only `sdkbase1` span census classifies actual SDK-owned pages: large state-1 spans hold **280.09 / 294.81 MiB swapped**, while state-2 free spans have **41.48 / 32.33 MiB present** and **96.69 / 101.06 MiB swapped** at game-idle / precleanup. These sequential snapshots are NOT a free/alias/GPU-lifetime contract and permit no release. The optional inner Unity/GC owner investigation and stop rule below remain unchanged; **720p acceptance takes priority**.

The large SDK blocks and Unity pool caps have already been measured. Two 192 MiB BufferPool/TexturePool mappings had only 62.8+13.5 MiB resident; an extra 96 MiB graphics mapping was effectively untouched. **Virtual size reduction would not recover the measured swap.** The 144.4 MB launch System.Byte[] is collected/recycled in its GC segment; therefore "free the launch read buffer" is not supported. The remaining swap might be sub-64 KiB SDK allocations, **suballocated Unity/IL2CPP/GC objects within larger arenas**, internal free lists or untraced APIs. Its *liveness* is unproven.

**One rational next forensic increment:**

1. On the exact owner version, inspect read-only native Unity/IL2CPP/GC allocation-entry sites, arena/segment creation and growth, small-object size classes, free-list and collection/unload paths. Reuse the proven IL2CPP metadata-v23 method/field join where applicable; **do not infer allocator identity from names alone**. Instrument the owner behind precise hashes, ABI and bounded counters rather than hooking hundreds of unverified addresses.
2. Record a page- and segment-aware ledger at cold boot, menu, game-idle, scene entry/exit, reload and after repeated visits: virtual reserved bytes, committed, present, swapped, anonymous/file-backed, logically live/free-list, GPU/pool aliases and allocation owner where proven. Reconcile to `smaps_rollup` and sampled `pagemap`; do **not** add process PSS and driver commit as independent RAM totals. Keep heavy scans outside frame-time A/B windows.
3. Investigate **which inner allocator owns pages** in the large arena and whether any pages become provably empty after GC/scene unload. Residency=0, all-zero head/tail, §Referenced=0§ or large SwapPSS do **not** prove future nonuse. Avoid speculative `madvise(MADV_DONTNEED)`, guest page mappings, protection-based guessing or destructive swap-off.
4. A potential patch must have a real owner-approved free/lifetime contract: e.g. allocator says entire aligned page is free, no object, worker, texture view, DMA/GPU or after-frame pointer can reach it, and recreation/rollback is defined. If that is not shown, do not implement release. Prioritize actual **peak resident physical pressure** and page-in stalls over synthetic virtual-memory reduction.
5. Publish a go/no-go table of **specific owner group → proven reclaimable bytes → estimated peak-resident savings → cost/overhead → correctness risks → exact A/B**. Continue only if a concrete change can save **tens of MiB** *safely and at the relevant peak*, or reduce major-fault stalls in a measured scene. A 2–5 MiB texture-level estimate or unattributed swapped pages alone does not justify risk.
6. **Stop rule:** if one full allocator/segment census plus repeated scene transitions still cannot identify a safe reclaimable owner, **park zero-swap** as an unsupported resource target on the ~1 GiB device. Do not lower SDK trace below 64 KiB merely to create more events without an inner-allocator owner join and bounded collector. If zero-swap remains mandatory, treat release as **blocked**, not solved by swapping policy.

**Only after real material savings** should a recovery-safe **swap-disabled before launch** cold-boot test even be considered, with an owner-approved rollback plan, actual MemAvailable/CmaFree headroom, OOM monitors and all-scene play. Leaving swap enabled is the appropriate baseline while ownership is unresolved.

### 16.7 P2 — opportunities to defer (or deliberately close)

- **GPU clocks:** one valid min=600 MHz profile observed 26.540 presents/s vs ~23.46–23.49 at stock 150 MHz on 1080; earlier requested governor switches reverted to 150 MHz and are invalid. If 720p is already ≥30 FPS at stock clocks, don't trade battery/thermals for more numbers. If a *new* scene is GPU-limited, enumerate supported OPPs, read **effective** clocks during every scene, measure thermals/power and restore governor/min/max after each controlled run.
- **Real GPU pass classifier:** if 720p combat remains slow, expand existing ordinal 0–7 timer query coverage across ~24 RT switches using nonblocking, disjoint-aware queries. Map zero-draw 10-ms passes to clears/attachments/resolve and only remove exact redundant transitions. GLES tile-store/invalidate is unsafe without load/store graph proof.
- **ASTC post-copy:** actual ASTC sampling works but immutable, completed BC groups must be shown. Reopen only for persistent **driver-committed** memory savings measured after real copy, without increased anonymous cache residency or visible alpha/sRGB damage.
- **Uniform cache:** `WOL_UNIFORM_CACHE=1` is already implemented; a cheap on/off test can close it if measured full-frame speed is within noise. The repeated bytes are only ~8.9 KiB per frame.
- **Shader program binaries, immutable VBO generations, GPU texture sharing/eviction, async/fences:** not new P0 work. Existing source census, absent compatible duplicate views, PBO regression and legitimate sync contracts make a general subsystem rewrite unjustified. Reconsider only when a new scene has a measured relevant stall.

### 16.8 Verification matrix — what *must* appear in evidence before calling it complete

| Gate | Minimum evidence | Passing condition |
| --- | --- | --- |
| Source/build | Pin main commit, recovered GPL manifest, overlay/apply hash, exact ARM64 ELF, owner main.text hash, modified code sites, section and save checksums, effective flags | Reproducible build (warnings-as-errors), all data-free tests and fail-closed wrong-version fixtures; no proprietary assets in Git |
| Stationary FPS | ≥3 **valid** full control/candidate pairs, same save and scene, stock clock, no intrusive trace in timing arms | Repeatable >noise whole-frame gain, no missing frame windows or stalls |
| Gameplay FPS | Independently confirmed moving world, map/guide, interior, combat, dialogue/controls and repeated travel | Target ≥30 runtime presents/s and P95 ≤33.33 ms where specified; exceptions listed precisely, not hidden in averages |
| Visual parity | Real KMS captures plus same-save/reference review, alpha/stencil, PC body, map markers/title, UI, combat, dynamic UV | No material pixel/layout/scene regressions or black/unchanged frames masked by output counters |
| Load/stall | Distinguish active loading versus frozen render, adaptive watchdog and thread evidence on stall | Complete transitions and save/load; capture cause of any long gap, no unexplained stable-gameplay freeze |
| Resource accounting | Process PSS, SwapPSS, VM faults, global MemAvailable/CmaFree, Mali context allocations and actual GPU clocks at aligned timestamps | Show overlap/unknown categories, phase highs; no false §PSS+Mali§ physical total |
| Memory safety | TransferMemory sparse content/lifecycle tests, then one feature at a time; separate arena-owner investigation | Correct bytes, matching game output, real **net** pressure saving; no guessed page discard |
| Final device acceptance | Normal Spruce launch, physical controller/audio, extended play, save/load/restart, exact cleanup + visible MainUI | Safe usable build; no owner-save changes and no unowned PID termination |
| Zero-swap (independent) | Disabled **before** cold start, verified disabled, recovery-safe setup and memory/driver headroom | No OOM, memory collapses or gameplay regressions. Until performed it remains **NOT ACHIEVED** |

**Evidence folders if work continues:** `evidence/accept-720/`, `evidence/transfer-sparse-repeat/`, `evidence/unity-arena-owners/`, and only if warranted `evidence/no-swap-feasibility/`. Each README must list exact identity and flags, valid and rejected arm counts, same-save scene receipts, KMS screenshots, per-phase P50/P95/P99, memory/page counts, input/audio results and hard stop/promotion verdict. Frame-progress failure should invalidate the run even if save restoration succeeded.

### 16.9 Ordered next changes, criteria for stopping work, and release options

| Order | Work | Stop / promote |
| --- | --- | --- |
| **A — do first** | Trace-off `WOL_UPRENDER_720` repeated real-scene gameplay, combat and quality validation with watchdog | **Promote 720p default** only if repeated stable full-game parity and FPS target. Otherwise fix the exact freeze or failed scene first |
| **B — alongside A** | Investigate a new actual frozen-present episode vs loaded scene-page stalls; collect live thread/GPU/VM evidence | Solve documented root cause; do not loosen completion semantics |
| **C — small RAM candidate** | Repeat `T2_TRANSFER_SPARSE_COPY` under accepted 720 profile and test zero/nonzero lifecycle | Promote only if data-correct, repeatable net RAM pressure savings without added load stalls |
| **D — optional, one bounded research pass** | Resolve inner Unity/IL2CPP/GC arena page ownership below SDK ≥64 KiB census | Continue only after proving a recoverable owner with meaningful physical peak savings; otherwise **STOP deep memory R&D** |
| **E — only if slow scenes remain** | Complete GPU-pass classifier / thermal-confirmed OPP A/B / relevant shader pass | Optimize the actual measured 720p bottleneck, not an old 1080p profiler |
| **F — choose release contract** | User-facing stable handheld 720p with accepted safe opts **and normal swap**, or strict no-swap blocker | Never claim "zero swap" until a separate swap-disabled cold boot succeeds |

**Final recommendation:** the profitable next step is **not another broad cache, mode, or memory-limit rewrite**. It is to turn the *already measured* 720p UpRender improvement into a stable, complete gameplay build. After that, only a narrowly verified sparse TransferMemory copy and one allocator-owner investigation remain cost-justified. If no reclaimable Unity arena pages are identified, stop resource research, document that zero-swap is unmet, and prioritize correctness/port completion over progressively riskier paging hacks.

### 16.10 Status log — 2026-10-19 (device reports committed on October 19)

**A (720p acceptance).** First full alternating series executed (six trials, frozen ELF `b60057ea…`, A-B/B-A/A-B, all clean; saves restored, Spruce recovered). Clean-window moving: **+9.04 / +9.99 / +6.19 fps** (720−1080), p95 **−9.9…−13.8 ms**, process SwapPSS **−35…−45 MiB**. World movement independently verified by phase correlation: **86/86 strong segments scroll with the pressed dpad direction**. One trial (`accept-b2`) crossed a scripted fade → guide-reveal state; its non-world windows are excluded from the moving figures (raw pool kept). **Promotion gate NOT met**: moving p95 34.4–37.9 ms (limit 33.33) and one arm at 29.02 fps; defaults unchanged. Evidence: `evidence/accept-720/`. Guide-map travel attempts (five owned runs) reached the Boring Springs approach and town center — Horsery, BAR, TRADE, HOTEL, ALICE M.D., player movement confirmed, and one sign/dialogue text box captured — but no interior/battle entry succeeded; an owner-supplied known save/route is requested for those scenes (`evidence/scene-coverage/`).
**B (stalls).** Four >1 s gaps appeared in the acceptance series — all with major-fault bursts and MemAvailable minima of 54.7–85.4 MiB (memory-pressure page-in); none triggered the adaptive watchdog (5 s settled / 30 s transitions) and none was a deadlock. The sparse series that followed had zero gaps. No live thread/GPU snapshot exists for a sub-watchdog gap; a bounded gap-snapshot mode is the next step if gaps recur under the accepted profile. Separately, one scene-coverage run (`nav5`) ended in a **fail-closed runtime guard stop** — `STOP status=NVN_COMMAND_RECORD_SIZE … detail=0x0` (a command record whose size prefix read as zero), `WOL_RUNTIME_EXIT status=24` — about **0.9 s after entering gameplay** with normal 28–29 ms frame gaps, no memory stress at the moment (Pss 492 MB / SwapPss 445 MB / MemAvail 73 MB / flat major faults) and the full thread census plus `NVN_COMMANDS_RECORDED` state preserved in the log. The 5 s settled watchdog reported the stall 5.1 s later with the process already exited (its proc diagnostics correctly recorded the dead PID). This exact guard appears nowhere else in the collected history (17th run of the frozen ELF); the identical repeat `nav5b` was clean — **not reproduced (1/18)**, and if it recurs the first falsification A/B is `T2_LIST_RANGES=verify` against the active ranges fast-path. Evidence: `evidence/scene-coverage/`.
**C (sparse TransferMemory).** Fixtures done (verbatim block, host matrix, on-device ARM64 commit-avoidance: 0/64 KiB Rss delta vs 64 MiB dense). Paired repeat done: three valid alternating pairs show **−44…−75 MiB net SwapPSS** — the whole 64.1 MiB transfer-VMA swap eliminated — moving parity within ±0.4 fps, zero stalls, KMS parity (`evidence/transfer-sparse-repeat/`). Flag stays default OFF pending battle/save-load route coverage.
**D (arena owners).** Go/no-go published (`evidence/unity-arena-owners/`): no safe reclaimable owner behind the remaining swap; **zero-swap parked** per the §16.6 stop rule.
**E.** Not triggered: no new reproducibly slow 720 scene beyond the documented stall windows.
**F (release).** The swap-enabled qualified build remains the deliverable path; zero-swap stays **NOT ACHIEVED** and is not claimed.

## 17. October 19 technical re-evaluation: resource ROI and stop rules

**Reference baseline:** `main` `4e44d7c4a0d33753bdd50754d0f78781979269d7` on 2026-10-19. **Status: documentation assessment only; no new device run or runtime default enabled in this review.** This section is the current decision/implementation contract. Prior sections retain historical experiments and may describe goals now disproven. Private owner Switch game binary, IL2CPP metadata, assets and saves must never be published. No Box64, no TV/docked mode; only fixed handheld.

### 17.1 The verdict — distinguish three different goals

| Goal | Verified evidence | Cost-benefit conclusion |
| --- | --- | --- |
| **Stable playable handheld WoL in 720p** | Exact `UpRender.Awake` owner proven; three valid 720p/1080p moving pairs gain **+6.19…+9.99 runtime presents/s**, and P95 improves **9.9…13.8 ms**; one isolated A/B lowered Mali context commit **261.660→221.566 MiB** | **YES, keep working**, but on validation/stability and scene-specific tails; highest return on effort |
| **Reduce memory pressure without disabling swap** | `T2_TRANSFER_SPARSE_COPY` eliminates one **64 MiB** truly-zero eager copy; three repeated A/B pairs show **−44…−75 MiB net SwapPSS**, moving performance within ±0.4/s | **YES, complete a finite correctness gate** and consider promotion only after real battle/interior/save-load coverage |
| **Run all WoL scenes with swap OFF on ~963 MiB usable RAM** | ~400–500 MiB SwapPSS remains in normal runs; SDK/Unity arena census finds **no proven safely reclaimable owner** | **NO** to more deep speculative RAM archaeology. **PARK ZERO-SWAP**, do not perform unsafe swapoff, force GC/free pages or page decommit |

**Release stance:** target a reliable **swap-enabled, 720p, fixed-handheld experimental port**. If quality/scene acceptance and real-world performance pass, promote it; otherwise keep an honestly qualified experimental label with exact untested scenes and tail-rate exceptions. Do not call runtime presents independently measured physical panel FPS. Do not claim `−75 MiB SwapPSS` equals `−75 MiB physical resident RAM`, or add process PSS to GPU commitment as disjoint physical totals. If the user requires strict zero-swap, the present hardware/resource contract is **BLOCKED**, not solved.

### 17.2 Actual evidence at this HEAD, before deciding what to build

**720p FPS and moving scene** — [accept-720](../evidence/accept-720/README.md). Frozen ELF `b60057ea…`, corrected map owner section `49bd1671…`, same save and stock effective GPU clocks. Three alternating A/B pairs differ only by `WOL_UPRENDER_720`. Verified directional scrolling: **86/86** sufficiently strong left/right hold segments move correctly. A scripted fade/guide state in B2 was excluded from real-world moving windows, not treated as movement.

| Pair (720 − 1080) | Control moving presents/s | 720 moving presents/s | 720 P95 | Reproducible benefit |
| --- | ---: | ---: | ---: | --- |
| A1/B1 | 22.53 | 31.57 | **34.4 ms** | **+9.04/s**, P95 −13.8 ms |
| B2/A2 | 22.97 | 32.97 | **35.7 ms** | **+9.99/s**, P95 −11.7 ms |
| A3/B3 | 22.83 | 29.02 | **37.9 ms** | **+6.19/s**, P95 −9.9 ms |

Idle, movement, guide, map/return and real KMS Spruce recovery were confirmed. Process SwapPSS fell **35.6–45.2 MiB** in paired idle windows. **Strict promotion failed:** all three moving P95 values are greater than 33.33 ms, B3 moving rate is less than 30/s, and verified actual interior/combat/save-load/physical-input/audio remain missing from this batch. The original `upowner-a2` frozen control is **invalid** for performance and has no proved cause; subsequent accepted six-arm runs did not reproduce it, but do not prove it fixed. [Native owner details](../evidence/uprender-owner/README.md), [component-only hook and watchdog](../evidence/uprender-scope/README.md).

**Mechanism:** pinned native Unity IL2CPP `UpRender.Awake` `main+0x513df8`; instance fields `forceWidth+32` and `forceHeight+36` are verified 1920/1080 and rewritten to 1280/720 before normal `RenderTexture` creation. Nine *creation events*, not nine live allocations, move from 1080p to 720p. Initial three window color images and a depth buffer remain 1080p. No broad NVN descriptor-size lie, guest TV mode, shader patch or GL storage replacement is required.

**Sparse memory** — [transfer-sparse-repeat](../evidence/transfer-sparse-repeat/README.md). The `memory.h transfer_create_locked` source supplies a wholly zero 64 MiB page-aligned buffer. Eager creation copied 64 MiB into a new anonymous VMA that later occupied ~64.1 MiB SwapPSS. Page-wise sparse copying avoids committing those pages; real 64 MiB ARM64 fixture confirms **0 KiB RSS delta for zero**, **64 KiB for 16 nonzero pages**, **64 MiB for dense**. Host source/copyback/reuse fixtures passed. In three alternating whole-route pairs the original VMA swap disappeared, net SwapPSS reduced **44–75 MiB** with no movement regression, no >1 s stalls in six runs and KMS equality at reviewed scale. **Default still OFF**: no verified actual battle/interior/save-load/long-lifetime contract.

**Remaining swap and RAM stop rule** — [unity-arena-owners](../evidence/unity-arena-owners/README.md), [allocator-history](../evidence/allocator-history/README.md). SDK allocated state-1 spans have **~280/295 MiB swapped** (game-idle/precleanup). SDK nominally free state-2 spans have **~97/101 MiB swapped**, plus **~41/32 MiB resident**, but the adapter has no allocator lock, free-list metadata/alias/pointer-lifetime proof, or safe decommit ABI. Internal Unity/GC object liveness remains unknown. Historical old request census was misclassified splash/title, not gameplay; corrected 16 KiB requests hit a hard **8192-event cap**. A further lower threshold or raw VMA zeros do **not** prove reclaimable pages. Zero-swap stops under `16.6, do not reopen by default.

**Reliability, not just resource rates** — [scene-coverage](../evidence/scene-coverage/README.md). User input reached Boring Springs approach and town center, visible HORSERY/BAR/TRADE/HOTEL/ALICE M.D., and one true interaction/dialogue; **no interior or battle in this route**. One `nav5` trial (1 observed in 18 relevant frozen-ELF runs, not an inferred population crash rate) exited with fail-closed `NVN_COMMAND_RECORD_SIZE`: record-size prefix zero, guest caller `main.text.seg+0xaf2c0c`, exit 24, ~0.9 s after game entry. At that moment frames were ~28–29 ms apart, major faults flat, process PSS ~492 MiB, SwapPSS ~445 MiB and MemAvailable ~73 MiB: **do not label this OOM or paging-stall without evidence**. Identical route `nav5b` finished cleanly. Separately, four >1 s gaps in the moving A/B coincided with major-fault bursts and MemAvailable minima of ~55–85 MiB; **these are a different, likely page-in-related mechanism**. Sparse six-arm repeat had zero such gaps, which is promising but not causal proof.

### 17.3 Resource work decision matrix: expected value versus risk

| Rank | Work | Evidence-based potential | Cost/risk and decisive stop |
| --- | --- | --- | --- |
| **P0 A** | Freeze/qualify **current UpRender 720p**, no further RT scaling | **Real repeatable +6…10 presents/s moving**, smaller measured GPU commitment in isolated pair | Moderate quality/lifetime risk; **GO now** until scene correctness, P95/stability are known |
| **P0 B** | Reproduce **interior, real combat, save/load, input/audio** with owner-known route/save; investigate NVN record stop only as appropriate | Resolves the real release blocker | Correctness highest priority; **GO now**, stop blind input scripts |
| **P1 C** | Complete **existing sparse TransferMemory** full-lifetime qualification | **Net −44…−75 MiB SwapPSS** in 3 pairs, no measured FPS cost | Low/medium memory-contract risk; **GO finite**, then promote or leave OFF |
| **P1 D** | Trace **new/repeated >1 s frame gaps** and page faults in actual 720p; targeted long-tail fix | Real user-visible stutter | **Conditional** on recurrence; targeted cause only, no generic major memory rewrite |
| **P1 E** | Targeted *720p-scene* GPU pass/CPU bottleneck if moving P95 really unacceptable | May recover remaining 1–5 ms P95, **unproven** | Moderate and uncertain; **defer until all real-scene tests** |
| **P2** | Real OPP/DVFS sweep | One 1080 run at 600 MHz 26.54/s vs 150 MHz ~23.5/s | Battery/heat unknown; 720p already near 30; **defer, no forced clocks** |
| **P2** | Post-copy ASTC for proved immutable groups | Only ~2.5–4.9 MiB lower idle Mali commitment in 3 previous paired groups | Small gain/quality risk; **not general RAM solution** |
| **NO-GO** | Guest SDK/free-span decommit, anonymous page release, GC arena discard, launch Byte[] free | No safe owner, weak physical benefit, high corruption risk | **STOP**; owner-approved real free contract required to reopen |
| **NO-GO** | Another generic render state/cache/PBO/VBO/upload/alias rewrite | Tested no whole-frame benefit, or producer/destination pixels provably differ | **STOP** until an entirely new 720-scene bottleneck is identified |
| **NO-GO** | TV mode, `WOL_DISPLAY_MAX` as a resolution fix, or unconditional NVN 1080→720 patch | Runtime already handheld, UpRender is actual dynamic-size owner | **CLOSED**, no display-mode selector |

### 17.4 P0 A — exact 720p release-engineering work breakdown

**Current status:** the size-only native hook is implemented, measured, default OFF. **Not yet accepted as the release default**.

1. **Pin build and private owner identity.** Re-verify full `main.text` SHA, IL2CPP metadata-v23 join, `UpRender.Awake` at `main+0x513df8`, `UpdateTexture` at `main+0x513eb4`, instance fields +32/+36, and exact old values 1920/1080. The only enabled native instrumentation in trace-off 720 arms must be the intended Awake hook. Unknown game version, wrong method bytes, bad object/field or conflicting `WOL_GUEST_RT720=1` must **fail closed**, never perform partial writes or modify other Unity components. Maintain original ELF/section/save backup + rollback.
2. **Freeze a stable benchmark binary.** Same complete game/owner section/save/launcher, all resource/cache clocks equal. Compare `WOL_UPRENDER_720=0` vs `1` with `WOL_UPRENDER_TRACE=0`, `WOL_RT_ORIGIN=0`, `WOL_GPU_TIMELINE=0`, `WOL_UPLOAD_SKIP=0`, sparse OFF, normal CPU/GPU policy. Attach every **effective environment** and actual clocks. Use verified scene readiness, not fixed delays that previously labeled splash/title as gameplay.
3. **Build *real-scene* fixtures.** Preserve original owner saves; request cloned known-good interior and pre-battle saves or an owner-demonstrated deterministic route. Existing guided town door attempts did **not** enter interiors. Accept only screenshots plus real content/scene IDs and player motion as proof, not a sent A/ZL action label. Make a route corpus for: fresh/CONTINUE, moving Gulch, map with five places + NEW tags, town dialogue, actual interior, real combat, inventory/character creation if available, pause, save/load/restart and repeated world↔interior.
4. **Validate picture and game semantics.** Compare same-save KMS frames to control/reference; verify PC/Cactus Bill skinned sprites and alpha, WANTED stencil, map paper, all markers/text/NEW tags, world depth and outlines, UV scaling, dialog, inventory and combat HUD. Historical texture repack **broke actual map pixel-space coordinates** until repaired, so a complete but shifted screen is a functional regression. Animation can differ between arms; use semantic/region comparisons and known input transitions instead of demanding byte-identical whole frames.
5. **Audit whole render-target lifecycle.** Distinguish creation count vs **simultaneously live** images, actual GL allocation vs requested NVN dimensions; check camera color/depth/MSAA, remaining initial 1080 window+depth objects, FBO completeness, downsample/copy regions, shader texel-size inputs, viewport/scissor, CPU view reads and context switching. **Never globally force remaining 1080 target metadata to 720** without a proven consumer path and exact pixel/layout contract.
6. **Valid repeated performance.** Existing moving A/B already proves a real win. Repeat across **new verified interior/battle** scenarios (at least 3 alternating valid pairs for any new causal improvement claim), P50/P95/P99, presents/s, gaps >100 ms and >1 s, VM major faults/swap I/O and actual clock + thermal profile. **Strict goal:** ≥30/s and P95 ≤33.33 ms in each designated representative gameplay scene. Missing windows, scripted map state and dead render thread must be marked failed/unknown, never silently omitted from acceptance.
7. **Long-game/owner acceptance.** Test real buttons/dpad/sticks, sound playback, physical SAVE→QUIT→LOAD, return to Spruce MainUI and at least one extended mixed-scene route. PID liveness/audio/HID logs alone do not establish progressing frames. Keep adaptive watchdog **5 s settled gameplay / 30 s transitions**, exact owned PID/start-tick and bounded recovery receipts.
8. **Promote or explicitly qualify.** If visual/lifecycle/scene acceptance passes and strict FPS target repeats, enable 720 size-only default in normal handheld launcher. If quality is good but moving P95 remains ~34–38 ms or a scene is 29/s, prefer an **honest experimental label with scene exceptions** over unsafe further downscaling or GPU overclocking. If a concrete scene breaks, freeze FPS work until its specific producer/texture-lifetime bug is fixed.

**Deliverable:** `evidence/release-720/README.md` containing exact build and private-hash references, per-scene pass/fail matrix, same-save KMS captures, P50/P95/P99, long gaps, physical input/audio/save receipt, regressions vs 1080 and explicit *default OFF/ON* decision. Do not claim this artifact exists yet.

### 17.5 P0 B — rare NVN command-record stop: investigate by evidence, not disabling guards

**Known event:** `nav5` ended on a zero-size record-prefix guard `NVN_COMMAND_RECORD_SIZE`, exit 24; identical `nav5b` finished. This was **not** accompanied by a page-fault burst or growing frame times. One isolated event does not prove a race, but an invalid command prefix can signify buffer lifetime/order corruption and is more critical than a marginal performance optimization.

1. Preserve a minimal metadata-only failure receipt: pinned command buffer handle/**generation**, writer/replayer thread identity, arena address range (redacted or offset-only), producer/replay cursors and last accepted record offsets/sizes, ordered timestamps, FBO/EGL context and `NVN_COMMANDS_RECORDED` counts. Do not publish proprietary command records or owner guest bytes.
2. Distinguish plausible causes: uninitialised prefix, producer publication before payload, premature reuse, concurrent write, incorrect mapped-region fast path, record overwrite or wrong arena bounds. **Do not assert any as root cause until a before/after invariant fails**.
3. Run a **finite** exact-build, exact-save `nav5` reproduction set, keeping clean and failed receipts and requiring actual scene readiness. Never turn fatal guard into a warning, never synthesize a record size or let replay run past a zero prefix.
4. If reproduced, first run the targeted `T2_LIST_RANGES=verify` A/B against active `ranges` mode, checking per-read pointer bounds, page/span lookups and release/reuse. If no mismatch, add bounded producer-publication ordering/generation checks at the actual failure owner. No blanket locking of all command recording without measured need.
5. If clean finite repeats do not reproduce, keep it documented as **rare, unconfirmed** and monitor owner-visible runs; do not launch indefinite stress work. Escalate immediately for a reproducible crash, scene-specific trigger, save corruption or multiple independent occurrences.
6. Mandatory recovery: exact owner PID/start-time checked before intervention, maintain save hashes, capture true STOP vs watchdog-detected dead PID, restore visible Spruce. A process exit is **not** a GPU hang.

### 17.6 P1 C — sparse TransferMemory: final compatibility and promotion gate

**Current candidate:** `T2_TRANSFER_SPARSE_COPY=1`, opt-in/default OFF. It is a correct-copy optimization for a particular fully zero **TransferMemory input at creation**, **not** decommit or global guest-memory deduplication.

1. Recheck pinned source `native/memory.h` and serialized owner version: source bytes at transfer creation, alignment/page size, fresh zero-filled private destination, map failure fallback, handoff/protection, concurrent CPU writes, aliasing, second creation and full `transfer_release_locked` copyback semantics. Existing host/device tests cover all-zero, 16-page sparse, dense, read/write, double creation and copyback; don't replace byte-exact comparison with hashes.
2. Before timing, add only light bounded counters of transfer identity, pages scanned/copied/skipped, later write/dirty pages, copyback count and eventual resource destruction. Do **not** print data or perform heavy `smaps` during 720p FPS arms. Verify the expected 64 MiB input was zero **at that exact handoff** in each candidate.
3. Repeat OFF/ON with **720p fixed ON** in real battle, interior, save/load, restart and extended travel; at least one owner-known route, not the previous town entrance guesswork. Ensure scene progress, controller/audio/save correctness and GL error/stop absence, not only same final KMS map.
4. Collect separate per-VMA and net **process SwapPSS**, PSS and resident peak, global MemAvailable/CmaFree, swapin/out, major faults and time-to-first-responsive-gameplay. A lower SwapPSS is useful but does not automatically imply fewer peak physical bytes; interpret resource-accounting overlap explicitly.
5. **Promote only** with correct bytes, lifetime and true route parity and a repeated lower peak-memory-pressure or swap-cost signal with no frame-tail/load regression. If any alias/mapping/release case fails, retain original eager copy as reliable fallback and leave default OFF.
6. **Stop there.** Do not generalise to all buffers, whole-guest sparse page protection, glibc allocator replacement or ad hoc mmap decommit without a distinct observed bottleneck and new owner/lifetime proof.

### 17.7 P1 D/E — target the actual remaining jitter only after scene acceptance

First 720 acceptance saw **four >1 s gaps** with major-fault spikes and ~55–85 MiB MemAvailable. Sparse repeats saw **none**, but six runs are insufficient to claim eliminated stutters. A different `nav5` command guard with flat major faults must be separately classified.

- **Trigger-only lightweight diagnostics:** when a verified gaming frame gap exceeds ~1 s, record monotonic frame/input/asset-load phase, delta process major faults and global swap I/O, MemAvailable/CmaFree, actual CPU/GPU clocks, recent EGL/GL submission completion and threads' current waits. Keep reader overhead quantified; do not use destructive `glFinish` or page-by-page scans in ordinary speed arms.
- **Separate five cases:** expected load/transition, swap/page-in pressure, renderer/GPU wait, input routed to an already-open map/guide, and process exit on STOP. Actual current 720 P95 of 34.4–37.9 ms is a **different scale** from 1–3 s page-in stalls; optimize both only when each has a causal trace.
- **If CPU/VM faults dominate:** investigate one live identified asset-read/scene-switch owner; bounded prefetch might shift cost earlier without reducing memory use. No `mlock`, global `vm.swappiness` or speculative pinned page sets. Record peak CMA and major faults before accepting any prefetch.
- **If GPU dominates:** the existing [`EXT_disjoint_timer_query` pass profiler](../evidence/gpu-pass-timeline/README.md) samples only ordinals 0–7 of roughly 24 switches; a ~10 ms zero-draw pass is not proof of removable work. Expand with nonblocking, disjoint-aware measurements **only for that measured slow 720p scene**, then audit load/store/clears/texture copies before any GLES FBO change.
- **If CPU draw path dominates:** sample the bounded `a2c1` sampler, shader/constant and VBO path under the *720p profile*. Old 1080p bottlenecks need not survive. `WOL_UNIFORM_CACHE` has a census (45.8% repeated), not a proven frame gain; allow one quick existing on/off test only if uniform upload cost is still material.
- **Stop criterion:** no reproducibly slow user-visible scene or measured >noise P50/P95 improvement => **no new renderer subsystem**. If one critical scene is slow, implement the smallest safeguarded correction and run at least 3 matched A/B pairs with pixel, timing and memory parity.

### 17.8 Explicit memory NO-GO: why further deep allocation research is poor ROI

| Idea | Measured reason for closure | Reopen only with |
| --- | --- | --- |
| `madvise(MADV_DONTNEED)` over SDK free-span pages | ~32–41 MiB *resident* in sampled state-2 free spans; no allocator lock/free-list/alias contract; losing metadata can corrupt allocator | Proven allocator-mediated whole-page free, unobservable to owners/GPU and recoverable on next allocation |
| Discard state-1 allocated pages | ~280–295 MiB swapped in allocated spans; they remain owned | A real free/lifetime event, not idle age or swapped-out status |
| Drop 144 MB Unity launch `Byte[]` | GC later recycles/reuses its segment; original content address re-used | Owner-level GC and last-access evidence of a truly detached segment |
| Shrink two 192 MiB BufferPool/TexturePool caps | Huge virtual reservations but only much smaller resident footprints | Demonstrated resident pressure in the pool, not virtual size |
| `WOL_ROMFS_COW` or arbitrary file-mapped asset copy | Unity dirties most pages; previous swap remained large | New source owner with truly immutable mapped content |
| More atlas/mip promotion | M4 cut broke map pixel-space until repaired; some UI/combat sprites have sensitive logical pixel dimensions | Owner-approved measured OOM + safe exact Sprite/text/camera parity |
| GPU texture eviction/sharing | ~7.1 MiB safely rebuildable at one measured game point; no remaining exact compatible host-name view alias groups in observed census | Proven safe recovery source and significant active committed memory |
| New ASTC post-copy expansion | ~2.5–4.9 MiB driver commit savings in idle group A/B, no whole-game FPS rescue | A new real constrained GPU scene and net headroom benefit incl. CPU cache costs |
| Run swap-disabled cold boot now | Hundreds MiB swapped while current safe-reclaim inventory is zero; historical CMA ~0 | A **new, proven** physical high-water saving large enough plus owner-approved safe rollback |
| Lower SDK trace threshold or log every allocation | Corrected 16 KiB trace is incomplete at 8192 entries, detailed owners remain unjoined | A specific symbolised inner allocator with complete lifetime/locking proof |

**Formal stop policy:** `evidence/unity-arena-owners/` already completed the bounded owner go/no-go; result **NO safe owner**. This satisfies `16.6's termination rule. Do not create a third "last try" memory profiler without a new observed *allocator* free contract, bytes and measured peak-headroom estimate. Under a strict no-swap requirement, the next rational choice is **different hardware/RAM budget or a reduced game scope**, not unsafe Linux VM calls. Swapped pages are not automatically resident, and large swapped-byte numbers alone cannot quantify swapoff's exact failure margin.

### 17.9 Acceptance, CI and artifact requirements

| Gate | Evidence needed | Explicit status on 2026-10-19 |
| --- | --- | --- |
| Fixed owner build | Source/overlay hash, original executable `main.text` and metadata v23, elf/section/save SHA, fail-closed hook tests, no wrong-build patch | Available in experiment receipts; redo for final release candidate |
| Real moving world + guide/map | KMS reference/parity, verified world scroll, 720p P50/P95/P99, no black/false UI scene | **Done for Gulch** in six 720 A/B arms, *not strict P95 accepted* |
| Town travel + dialogue | Correct input route, changed world/interaction screenshot, user input source | **Town center and one real dialogue captured** |
| Interior and battle | Owner-known save/route, verified gameplay state (not action request), pixel/UI and FPS, transitions | **MISSING** |
| Save/load and physical buttons/audio | Normal user controls, disk hashes, audio checks, recovery of game and Spruce | **MISSING as a full release acceptance** |
| Stability / rare NVN stop | Bounded owned-process repeat/monitor, actual STOP/stack/cursor/guard receipt; no gameplay frozen silently | **One rare fail-closed nav5 stop, nav5b clean**, not proven root cause |
| 720p performance | **≥30 presents/s + P95 ≤33.33 ms** in independently verified *representative* scenes at stock clocks, no moving-window cherry-picking | **Not met** in all moving arms (P95 34.4–37.9; one 29.02/s) |
| Sparse lifecycle | Host+device byte tests, real battle/save/route parity, 3+ valid pairs per new claim, net PSS/SwapPSS/VM | **3 Gulch pairs passed**, full scene lifecycle missing |
| Recoverable no-swap | Swap disabled **before** boot, real physical CMA/OS peak + fully safe rollback, no OOM | **PARKED/NOT ACHIEVED; not safe to test now** |

**Protocol details:** distinguish requested action labels from verified scenes, replayed/out-of-phase fades from movement, and KMS signal from content correctness. Preserve failed arms. Use one pinned ELF, one flag variable per pair, ≥3 valid alternating A/B pairs for new claims, actual host CPU/GPU clocks, full interval statistics, explicitly timed collector overhead and aligned per-phase VM samples. Never add `PSS + Mali commitment` as disjoint RAM. Save/section untouched, owners' PID/starttime verified, original data backed up, visible Spruce MainUI restored.

**Code and CI:** existing [`.github/workflows/native-probe.yml`](../.github/workflows/native-probe.yml) runs source/overlay syntax, frozen native build, synthetic memory tests, QEMU ARM64 native traps. Retain these; add small data-free regression cases for any new `nav5` guard diagnosis, sparse-copy lifecycle/failure fallback and 720 size-hook version mismatches. No game binary, captured owner asset or private shader in git. CI **cannot replace** real TSPS graphical/audio/save acceptance.

### 17.10 Go/stop sequence and deliverable definition (no deadline guessing)

| Next step | Exact deliverable | End of this line of work |
| --- | --- | --- |
| **1. 720 candidate identity** | Frozen size-only/trace-off ELF and full version guard; section/save and source-parity receipt | If reproducibility fails, **stop new perf tuning** |
| **2. Scene and stability gap** | Owner-confirmed interior & real battle inputs, town/world travel, inventory, audio, saves, watchdog, command-record monitor | If scene cannot be reached, record **UNTESTED**; don't make full-play claim |
| **3. Sparse TransferMemory finish** | Data/lifecycle checks during those scenes + peak and per-VMA ledgers, paired OFF/ON | Promote only on byte- and lifecycle-correct repeatable gain; otherwise leave OFF |
| **4. Final 720 P95** | Trace-off FPS distribution and verified gameplay scene list, only then targeted GPU/CPU/VM bottleneck | Correct, small fix if causal and >noise; otherwise document tolerated experimental exceptions |
| **5. Release gate** | Stable handheld 720p normal Spruce launcher, same-save reference KMS, physical inputs/audio, save-load and clean return | Ship/label *swap-enabled experimental* if agreed; never advertise zero-swap |
| **6. Memory deep-optimization** | **No further task**; `unity-arena-owners` already ends with NO-GO | Reopen only on newly proven *real free pages* at needed physical peak; no speculative arena work |

**Stopping point for optimization:** once the 720p route is sufficiently correct and responsive and sparse TransferMemory has an explicit promotion/rollback decision, **freeze resource settings**. Continued effort should be ordinary game compatibility/testing, not further unbounded cache, allocator, VM, Vulkan, GPU-clock or texture alias exploration. Only a reproducible user-visible slow scene/OOM, a new safely owned reclaimable segment or a correctness failure should reopen that specific path.

**Answer:** **continue the bounded port qualification work, not an open-ended resource-reduction campaign.** The highest-leverage frame-time win and one genuine memory-pressure optimization already exist; the remaining blockers are primarily correctness and coverage.

## 18. Post-acceptance repository audit and bounded finish plan (2026-10-19)

**Scope and review identity.** This is a source/tree/documentation/CI audit of public `main` at **f7c72a3232eeb06e9ee63356f026f1f78db99247**, cross-checked against the latest actual [release-720 acceptance](../evidence/release-720/README.md), [owner 720 battle/cave](../evidence/scene-coverage/owner-battle-720/README.md), [alternating 720 pairs](../evidence/accept-720/README.md), [sparse TransferMemory repeat](../evidence/transfer-sparse-repeat/README.md) and [Unity allocator owner stop decision](../evidence/unity-arena-owners/README.md). No fresh source rebuild on the recovered owner runtime, actual TSPS performance run, independent physical-control audit or owner-save manipulation was performed during this review. The private reconstructed 435-file source baseline, owner NSO/Unity metadata, data section and final installed ELF are **not** contained here, so public static inspection cannot certify the whole binary. The source tree contains 4,634 blobs: 4,486 under `evidence/`; do not mistake the quantity of logs/captures for exhaustive title/gameplay validation.

**Decision (supersedes the old §17.4 “default OFF / no acceptance document” statement):** the owner **accepted** the 720p `UpRender` size-only profile in real battle/cave play and enabled it in the installed ordinary Spruce launcher on 2026-10-19. [The published acceptance report](../evidence/release-720/README.md) explicitly calls this an **experimental default ON**, not a strict 30 FPS/P95 certification. In battle, two live windows were **32.1 / 31.7 runtime presents/s** with active 720 profile, ALSA output running and a matching on-screen battle; the earlier 1080-class session recorded **28.3 / 28.1**, but those owner sessions are not independently paired. The controlled three moving pairs remain the stronger FPS causality evidence: gains **+9.04 / +9.99 / +6.19 presents/s**, P95 improvements **13.8 / 11.7 / 9.9 ms**. The 720 arms' moving P95 **34.4–37.9 ms** still misses 33.33 ms; one has **29.02 presents/s**. No no-swap claim.

### 18.1 New issues uncovered by the public-tree audit (before more optimizations)

| Priority | Source/evidence finding | Why it matters | Next action |
| --- | --- | --- | --- |
| **P0 reproducibility** | The [release report](../evidence/release-720/README.md) records an installed launcher with `export WOL_UPRENDER_720="${WOL_UPRENDER_720:-1}"` (SHA-256 `272a499c…`). The **checked-in** [West of Loathing Switch.sh](../West%20of%20Loathing%20Switch.sh) at this reviewed HEAD has **no** `WOL_UPRENDER_720` export. | A clean checkout's stock launcher does not represent the owner-accepted on-device default. Readers may unknowingly benchmark the old resolution profile. | Synchronize launcher with the accepted production-safe flag as a **separate reviewed change**; add exact default/override regression tests and fresh device rollout receipts. Until then say **installed device ON, repository launcher unsynchronized**. |
| **P0 source parity** | `runtime/source-manifest.sha256` pins baseline `native/memory.h` at **3db35657…**. The sparse fixture and [its test](../tools/test_wol_memory_sparse_copy.py) identify frozen **post-change** `native/memory.h` SHA-256 **68974762…** and a verbatim scan block. The published `runtime/wol-adapter.patch` includes other `native/memory.h` additions but contains **no** `T2_TRANSFER_SPARSE_COPY` implementation/flag string. | A successful standalone fixture on the original device **does not prove** that `build_horizon.sh` from the declared 435-file baseline plus published overlay can reproduce the measured sparse-enabled ELF. The accepted runtime is pinned by hash, but the published rebuild path is incomplete for this opt-in change until proved otherwise. | Reconstruct two temporary trees from the *manifest-pinned* source and the frozen tested source; identify and isolate the actual sparse diff. Incorporate it in the GPL overlay only after lifecycle review; verify exact source parity, compile and test a new ELF. Do **not** turn sparse ON in the launcher meanwhile. |
| **P0 CI coverage** | [native-probe.yml](../.github/workflows/native-probe.yml) runs `git apply --numstat` (syntax/format) and data-free tests. It does **not** apply the overlay to the recovered 435-file source and build the complete `wol-horizon` in CI; `build.sh` builds the *independent* minimal probe. | Passing Actions is **not** a release-runtime reproducibility/build certificate. | Add a private/owner-local full overlay-build verification job/script (with no proprietary files uploaded); retain the public data-free CI and add static contracts that fail when tested runtime feature source is absent. |
| **P1 docs status** | [README](../README.md) still calls gfx265 the “latest device evidence”; [runtime/README.md](../runtime/README.md) still says the overlay only reaches shader capture; old §17.4 and §17.9 say battle/720 default unavailable. | A reader cannot tell what is truly deployed/accepted, which is merely historical, and which remains open. | Refresh README/runtime overview and link the authoritative release report and this §18. Preserve dated historical evidence without rewriting it as if a test never happened. |
| **P2 maintenance** | 4,486 evidence files, many large raw `runtime.log` files, ~1.77 GiB aggregate *working-tree blob sizes* at HEAD (not the GitHub compressed repository size). | Checkout, review, deduplication and evidence provenance become expensive; unrelated to TSPS runtime RAM. | Keep concise receipts, hashes, safety-critical failure logs and representative KMS images in git; for **future** runs compress/filter repetitive logs and put bulky raw artifacts in versioned release/workflow artifacts. Do not rewrite history or delete original evidence without an explicit retention/audit decision. |

**Reproducibility caveat:** the mismatch above is a concrete **published-build gap**, **not** evidence that the device's measured sparse feature is fake, broken, or absent. Its compiled ARM64 fixture and six measured runs are real report-level evidence. Conversely, the existence of `tools/fixtures/t2_sparse_copy_fixture.c` does not cause the patch built by `build_horizon.sh` to contain that code. Compare actual patched source and built symbols/strings; do not assume.

### 18.2 P0-R1 — reconcile and rebuild the accepted source/launcher release

**Entry:** freeze the **known-working** device ELF `b60057eaeafa738e9b48cf2b68b356545ee5ffde2c57bb84a5da5722e5935158`, section `49bd16718ed0dc46f16599255791c7603e8aa2b5f04898784a39d6cacb9d0722`, owner saves and deployed launcher SHA independently. Preserve immutable backups first. This gate has higher priority than any new profiler.

1. From the exact 435-file base pinned by `runtime/source-manifest.sha256`, use `build_horizon.sh` in a **fresh, uniquely named output directory**. Verify `sha256sum -c`, `git apply --check`, actual patch application, native AArch64 compilation and its full object/link logs. Do not swap in the already-customized 68974762 memory header as if it were baseline.
2. Generate a **source parity report** comparing every deployed native file with the fresh baseline+overlay (paths and SHA-256, explicit added/deleted files, compiler flags, optimization level, static provider inputs and toolchain versions). Determine whether the sparse implementation or any other installed local fix is outside the published overlay. Require **zero unexplained differences** before calling the repo reproducible.
3. Produce a **feature presence matrix** for build output: 720 Awake hook and wrong-image fail-closed guard; sparse transfer flag (if truly built); readback cadence; ordinary input-injection OFF; logging/dump OFF; CPU online-mask restoration; safe save path and Spruce exit. A string in an ELF is not sufficient—add behavioral host fixtures and on-device receipts.
4. **Launcher source parity:** add the already-accepted, opt-out-able `WOL_UPRENDER_720` default in a dedicated launcher commit, with tests proving unset→1, explicit 0→0, explicit 1→1; never silently add TV/docked mode, `WOL_GUEST_RT720` or change KMS resolution. Record the repository launcher hash and the deployed hash **after** installation. Keep the tested rollback path.
5. Validate actual ordinary launch from Spruce (not only diagnostic CLI): `WOL_UPRENDER_CONFIG component-settings-720=1`, original game version accepted, 1280×720 scanout, real gameplay, owner-visible title/map/battle, no `STOP`, intact saves, and real MainUI on exit. Verify wrong-build detection separately on non-owner synthetic fixtures—never patch unknown NSO bytes speculatively.
6. Ensure the final documentation clearly distinguishes **device-tested ELF**, **source-rebuilt ELF**, and **newly deployed ELF**. They may not be byte-identical because of different compiler/linker build inputs; in that case rerun the acceptance basis on the rebuilt artifact rather than borrowing the old hash's result.

**Pass:** published build inputs lead to a reviewable native source tree and working device artifact, with no unexplained source delta, launcher default parity and successful rollback. **Fail/stop:** source mismatch, patch application mismatch, unknown executable identity, real visual/saving regression, or unclear lifetime semantics. Restore the previously known working 720 device build; stop resource tuning.

### 18.3 P0-R2 — finish the actual experimental release acceptance

The new [release-720 report](../evidence/release-720/README.md) closes **owner-observed battle and cave**, not everything required for full-game certification. It also supersedes §17's outdated “battle missing” and “default OFF” entries.

1. **SAVE → QUIT → cold relaunch → LOAD:** keep an untouched owner-save backup and known same-save checkpoint. Perform an in-game save, verify changed save files are valid/nonempty, exit normally, verify genuine Spruce MainUI, cold-start the exact launcher/build again, load the saved state, verify player coordinates, inventory/quest/dialogue state and scene continuity, then restore original owner data. Capture timestamps, checksums, logs, KMS pictures and exact failure/recovery status. A working “CONTINUE” alone is not this test.
2. **Physical controls:** audit D-pad, both sticks, A/B/X/Y, shoulder/trigger buttons, ZL/- map access, pause/inventory, battle choices and navigation. Distinguish injected diagnostic Npad events from normal physical evdev/Spruce controls. Verify the input injection socket remains disabled in normal launch. Test press/hold/release and repeat, not only a single accepted command.
3. **Scene/lifetime matrix:** actual Gulch and directional motion (already verified 86/86 strong segments), five-marker guide/map, travel to Boring Springs, conversation, cave interior, at least one **town-building interior** if independently reachable, battle, post-battle return, save/load and repeated indoor↔outdoor transitions. A captured cave battle does not prove every town-door interior; mark missing cells “NOT TESTED,” not “PASS.”
4. **Visual contract:** title, full character/Cactus Bill bodies, WANTED stencil clipping, map text/NEW tags and pixel-space coordinates, world outlines, combat sprites/HUD, dialogue clipping, font and alpha, pause/inventory and save-selection UI. Use real KMS captures and same-save semantic region comparisons; animation/time/input changes are not byte-equivalent evidence.
5. **Audio:** verify not just ALSA `RUNNING` state but audible music/effects, scene transitions, stop/resume and sustained absence of glitches. Do not infer audio quality from a PCM stream counter.
6. **Long route:** record at least one mixed-scene owner-approved play session with monotonic presents and input progression; separate ordinary scripted fades from >1 s true display gaps; record memory pressure, major faults, GPU allocation, thermal/clocks, restore save, and exit cleanliness. Never terminate non-owned PIDs or discard a live save after uncertain process death.
7. **Performance decision:** continue to record full-distribution P50/P95/P99 and true >1 s gaps, but do **not** relabel the owner's **experimental acceptance** as strict ≥30/≤33.33 ms certification. If owner-visible play is good, retain the experimental label with the exact missed P95 and open scenarios. Accept a small, reproducible targeted FPS fix only if it improves a new real problem without degraded textures/UI/battery life.

**Pass:** reproducible normal play, correct saved state after full restart, controls/audio/cave/combat/map parity and clean recovery at the accepted 720 setting. **Fail:** corrupted/irretrievable saves, scene-specific black/frozen output, repeated fail-closed guard, input/audio failure or inability to restore Spruce. A performance exception alone does not retroactively invalidate owner acceptance; it remains documented.

### 18.4 P0-R3 — rare zero-prefix NVN command record and genuine stalls

The one [nav5 failure](../evidence/scene-coverage/README.md) is `NVN_COMMAND_RECORD_SIZE` with **prefix bytes=0**, exit 24, one observed event across 18 relevant frozen-ELF runs; identical `nav5b` passed. Its flat major faults and normal prior frame periods argue against simply naming it a paging/low-memory stall.

1. First use the **same binary/source/save** and source-visible ranges-vs-verify option proposed in §17.5. Run a finite repeated route or only reuse the already-collected history if the failure remains rare. Log exact command arena/generation, producer/replay cursor, last fully published record offset+size, writer and consumer thread IDs and monotonic times. Never log proprietary payload bytes.
2. On a reproduced failure, test **publication order**, snapshot atomicity, bounds/arena retirement, address-range fast-path equality, concurrent recording/replay and stale command reuse one by one. A zero-length command can be an uninitialized/overwritten prefix, but no cause has been proved. Retain the fatal guard—**never** skip the offending record or synthesize its length.
3. If it cannot be reproduced after a bounded matching set, retain a low-overhead on-failure receipt in the release build rather than running all-thread/page instrumentation every frame; classify it “rare unresolved.” Reopen immediately for a second independent failure, a reproducing save/route or save corruption.
4. Independently classify >1 s screen intervals into: legitimate scene fade/loading, major-fault page-in, GPU fence/finish, input now controlling a map instead of the world, or exited runtime. The previous 720 A/B yielded four gaps associated with page faults and MemAvailable of ~55–85 MiB; the sparse series yielded zero but sample size is too small to assert elimination.
5. Preserve watchdog distinction: process exited with `STOP` vs live process blocked on GPU/IO vs scripted screen. Record exact owner PID/start ticks, save restoration and KMS MainUI capture.

**Pass:** no recurrent unexplained hard stop on the representative accepted build, or a causal, narrowly scoped fix with a regression fixture and device A/B. **Do not block all ordinary port improvements indefinitely** on a single non-reproducible old event; do not call the event fixed without reproducing the cause.

### 18.5 P1-R4 — finish sparse TransferMemory once, then decide ON/OFF

**Mechanism established:** for the actual 64 MiB zero transfer at handoff, skipping zero page copies avoids committing an otherwise anonymous copy; device fixture shows 0 KiB RSS delta for all-zero vs 64 MiB for dense, and three alternating real scene pairs report **−44…−75 MiB net SwapPSS**, verified world/map/pause visuals and moving-rate parity within ±0.4 presents/s. **Not established:** an entire save/load/battle lifetime, reliable *peak physical RAM* reduction, or parity of an independently reproduced source build.

1. **Source prerequisite:** finish §18.2 first. Identify the sparse scan in the actual published rebuilt `native/memory.h` after overlay application. Bind host fixture's verbatim SHA check to **real transformed source**, not only to an embedded copy of a frozen block. Verify destination is fresh private zero-filled page-aligned mapping; validate refusal before partial mapping and source handoff/exclusive ownership, protection, dirty/write semantics, overlapping aliases, later reused pages and full release copyback.
2. **Broaden owner states:** use the same accepted **720 ON** with sparse OFF/ON in battle, cave/other interior, save→quit→load, world transitions and longer normal play. Require actual KMS scene proof and a checkpoint where the transfer is read/written again if it exists; do not assume that zero initial contents means the mapping is disposable forever.
3. **Instrument only on handoff/release:** guarded aggregate counters for scanned/copy/skipped 4 KiB pages, destination mapping identity, later writes/copyback, failed mappings and lifetime. Ensure all-zero observed **at handoff**, not just in a separate synthetic fixture. Bounds, alignment and size overflow must fail closed; no unbounded per-page logs.
4. **Repeat at least three alternating valid A/B pairs** with identical rebuilt ELF, section, save, physical CPU/GPU settings, clock/temperature, KMS scenes and instrumentation; P50/P95/P99, time to first responsive game, major faults, swap-in/out, PSS/SwapPSS per VMA, global MemAvailable/CmaFree and Mali commitment. Report observer overhead separately. The `-64 MiB transfer-VMA swap` observation and `-44…-75 MiB net process SwapPSS` are **not equivalent to physical resident bytes saved**.
5. **Promote only if all of the following hold:** byte/lifecycle/source correctness; battle/save/restart quality; repeated nontrivial memory-pressure or active swap cost benefit; no increased peak, P95 tail, load time or EGL/GL error; owner-approved rollback. Otherwise **leave OFF permanently** and close this branch as a well-executed experiment. Do not expand sparse scanning globally to other memory pools.

### 18.6 Conditional P1-R5 — the *only* remaining justified performance experiments

**Do not schedule these as parallel work.** Trigger an item only if a **fresh, verified 720p normal-play scene** repeats a concrete lag and the instrumented phase is a material share of its frame period. The old 1080 texture-460 sampler profile is not automatically the current 720 critical path.

| Triggered measurement | Narrow candidate | Why not automatic | Accept / stop |
| --- | --- | --- | --- |
| CPU uniform uploads significant in **720** frame split | One `WOL_UNIFORM_CACHE=0/1` test with existing byte-exact NaN-safe/epoch invalidation and context restoration | Historical census showed **45.8% duplicate uniforms**, not whole-frame speed-up; old GL uniform sites were ~0.8–1.1 ms/frame | 3 valid paired real 720 scene runs; gains outside timing noise, exact picture parity and clean context-change tests; otherwise close |
| GPU time dominated by a specific FBO pass in 720 | Extend existing nonblocking `EXT_disjoint_timer_query` sampling across the actual ~24 target switches, including later ordinals, disjoint results and driver limits | Earlier profiler only sampled first ~8; a “zero-draw 10 ms” phase is not proof of removable work | One named expensive target/load/store/copy barrier, a correctness-preserving change and full-frame P95 win; otherwise no GLES rewrite |
| Repeated page-fault-driven transition hitch | Trace the **specific** asset/VMA fetch and transition owner, consider bounded proactive file read/prefetch at a proven safe point | Prefetch shifts IO in time and may **increase physical peak**; swapoff, mlock and global swappiness are unsafe shortcuts | Fewer genuine major-fault hitches without higher CMA pressure, broken assets or degraded load time; otherwise stop |
| Measured GLSL compilation/program creation dominates real transitions | Only then inspect warm shader cache/profile identity and first-use compilation; preserve exact shader/control SHA and compatible GL context | Legacy shader translation is complex; unnecessary cache grows memory and can break picture | Same scene/assets, cold and warm restart A/B, clear hit/miss/GL error/peak-memory proof; no speculative persistent cache |
| Proven per-frame GPU finish/fence wait **after** 720 | Narrow fence/flush ordering or nonblocking staging if existing producer/consumer ownership is conclusively mapped | Immediate GPU copy and previous async/context attempts regressed or failed; removing `glFinish` blindly breaks NVN ordering | Pixel and memory-coherence proof, bounded queue depth, no EGL_BAD_SURFACE, P95 improvement; otherwise no async renderer rewrite |

**Previously tried: do not repeat without a *new* dependency graph.** Per-draw VBO/EBO ring; zero-content or create-time ASTC cache; 53-texture second mip wave; full GPU copy into texture 460; direct guest source re-upload; exact-image upload skip (little/no causal gain); hash resource lookup (99.4% hit and negligible cost); CPU logical→big core remap; 600 MHz exploratory GPU forcing; selective PBO; post-copy ASTC (small/no robust net gain); ROMFS COW; host texture alias/evict with only ~7 MiB provably safe; VI layer-size/AM handheld overrides; `WOL_GUEST_RT720` broad patches; unsafe SDK/free-span decommit. See §§2–17 and the respective dated evidence—“closed at this benchmark” does **not** prove all imaginable future algorithms impossible.

### 18.7 P2 hygiene — tests, source identity, logging and evidence retention

1. CI must distinguish four certificates: (a) data-free Python unit tests; (b) **actual** patched recovered-source build, owner-local when necessary; (c) device feature/default/rollback checks; (d) full real gameplay acceptance. A green (a) does not imply (b)–(d). Add tests that inspect freshly patched output, fail if `T2_TRANSFER_SPARSE_COPY` is missing when advertised, and check the version-gated `UpRender` hook against deliberately wrong synthetic instruction/hash inputs.
2. Test the **checked-in stock launcher** via bash-only extraction (as is done for `COTM_INPUT_DIAGNOSTIC`), covering `WOL_UPRENDER_720` default/override and normal diagnostics off. Verify shell safety (`bash -n`), CPU mask restoration on normal/abnormal exits, reliable signal recovery, writable log-directory errors, and no uncontrolled full-frame dumps.
3. Full overlay parity requires SHA of actual recovered source input and output; CI `git apply --numstat` is only a parse/syntax check. Include the 435-file manifest verification, fail-closed patch apply, no missing changes and a full build on an owner-controlled runner if redistributable source inputs cannot legally be embedded.
4. Ordinary play still redirects all stdout/stderr to `logs/latest.log`; distinguish bounded first-use/errors from any per-frame `NVN_PRESENT_UNMEASURED` cadence. Measure disk bytes/minute and storage exhaustion; use opt-in bounded/rotated diagnostics where appropriate, preserving first fatal receipt. Do not disable actual error and black-screen safety purely to improve FPS.
5. Large experiment artifacts: preserve pinned reports, failure receipts, exact hash indexes and representative same-save KMS images. For **new** tests publish compact summaries + compressed/externally hosted raw logs with an immutable manifest. Existing history is safety/audit evidence—no history rewrite as a “performance optimization.”
6. Update README and `runtime/README.md` to point first to `evidence/release-720/`, §18 and the real executable status; stale gfx265 first-page headline should be labeled historical. Document **installed launcher ON vs repo launcher not yet synced** until §18.2 closes.

### 18.8 Explicit stop/go decisions and ordered deliverables

| Order | Deliverable / invariant | Decision at completion |
| --- | --- | --- |
| **0 (now)** | Source parity for sparse, public patch+baseline reproducibility, accepted launcher default parity, working rollback | **Block new perf experiments** until consistent. Do not assume fixture proves release binary. |
| **1** | Physical input, battle+cave, map, real SAVE→QUIT→LOAD, mixed scene and MainUI cleanup from the *reproduced* 720 artifact | Ship/retain **swap-enabled experimental 720p** if robust; label unresolved scenes. |
| **2** | Bounded zero-prefix command-stop analysis and ongoing failure receipt | Fix only if reproducible or corroborated; never bypass integrity guards. |
| **3** | Sparse page-copy OFF/ON broad lifecycle acceptance under fixed 720, with full source contract | **One explicit promote OR reject**; no expanded arbitrary page reclaim. |
| **4 (conditional)** | Profiling of a new, reproducibly bad 720 scene and one narrow targeted fix | Continue only if clear full-frame/P95 or visible-stall win beyond noise; otherwise close. |
| **5** | CI/docs/evidence hygiene and changelog; mark unsupported strict claims | Freeze resource flags and focus on ordinary game-port quality. |

**Hard NO-GO for this hardware:** unbounded Unity allocator archaeology, changing SDK free-page semantics without allocator locks/lifetime proof, forcibly dropping swapped pages, turning swap off on the current build, overcommitting CMA, arbitrary GPU buffers from stale snapshots, global 1080→720 descriptor lies, Box64, or a docked/TV-mode selector. Old SDK state-1 spans had ~280–295 MiB swapped and state-2 nominally free spans only ~32–41 MiB resident at snapshots; no safely reclaimable physical owner was proved. Sparse transfer removes one redundant **copy**, not the game heap. The exact swap-off physical peak is unknown—do not claim it is mathematically impossible, only **not demonstrated safe and not worth attempting without a new major proven saving**.

**Stopping point for resource research:** once the accepted 720p ordinary launcher is **rebuildable**, full save/load+physical-control gameplay is sufficiently correct, rare-stop risk is explicitly classified, and sparse copy has a final ON/OFF decision, **freeze optimization knobs**. Reopen *only* for a repeatable owner-visible slowdown/OOM or a newly proven safe source-owner/lifetime contract with a credible peak-memory benefit. The likely high-return next project is compatibility/completeness, not more memory heuristics.

**Final answer to “have we tried everything?”** No finite project can exhaust all rendering, scheduling and allocator approaches. But the repository has already tested the plausible cheap/high-payoff ones with more care than typical ports. There is **no untried, presently evidence-backed large safe RAM saving** and no reason to embark on another broad optimization campaign.

