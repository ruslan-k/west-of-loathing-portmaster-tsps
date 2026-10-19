# West of Loathing / TrimUI Smart Pro S — FPS and zero-swap optimization roadmap

**Status:** living technical plan; tested and rejected experiments are explicitly separated from proposed work.  
**Reviewed:** 2026-10-19 against `main` `8ffa2f90b3106938c6c2323eeca1c90b207aeaa8`; sections 1–14 retain historical dated experiments, while [§15](#15-m7-after-handheld-preflight-unity-render-target-origin-and-720p-plan) is the current M7 execution plan.  
**Platform:** owner-supplied Switch Unity 5.6.5p1 ARM64/IL2CPP, native Horizon adapter, SpruceOS, Mali-G57 GLES 3.2, approximately 963 MiB RAM. No Box64.  
**Purpose:** identify *new* experiments after the first roadmap was executed. [Historical resource studies](resource-optimization.md) and [M1/M5 measurement contracts](memory-benchmark.md) remain authoritative for their own earlier checkpoints.

> This is **not** a claim that either 30+ FPS or zero-swap has been attained. Device reports use varying saves/scenes and diagnostic builds. At the original review, `dtime8` (`414efb1f…`) instrumentation was not published. That gap is now closed by `a3793a1`: clean overlay application matches all 199 native source files of the measured build. Further execution results and still-open gates are recorded in §11; implementation of an opt-in mechanism is not release acceptance.

**2026-10-19 current decision (supersedes the 2026-10-18 question):** [the device's handheld preflight](../evidence/handheld-preflight/README.md) established that the inherited AM implementation **already answers Handheld (`0`)**; the observed WoL launch calls only AM commands 0/1/9/6, with **no observed operation-mode (5), default-resolution (60), or VI ListDisplays request**. Unity still allocates 1920×1080 internal render targets and the SDL/KMSDRM output is 1280×720. **Do not implement another handheld/TV switch or speculative AM command 60.** Locate the Unity/SDK origin of the render-target dimensions as [§15](#15-m7-after-handheld-preflight-unity-render-target-origin-and-720p-plan) describes. The content-aware texture-460 upload skip was also tested without a reproducible FPS win; it is not P0 anymore.

**Latest §15 execution:** [native UpRender producer and repeated component-settings A/B](../evidence/uprender-owner/README.md) identifies the Switch IL2CPP consumer. Three 720 candidates observe **32.638 / 33.348 / 33.878 runtime presents/s** in gulch versus valid controls **24.019 / 24.226**. One attempted 1080 control freezes and is excluded, not concealed by successful cleanup. SwapPSS remains **533–552 MiB**; there is no full-game/no-swap acceptance or default promotion. See §§15.8–15.9; the original handheld and upload-skip decisions stand.

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
