# West of Loathing / TrimUI Smart Pro S — FPS and zero-swap optimization roadmap

**Status:** living technical plan; tested and rejected experiments are explicitly separated from proposed work.  
**Reviewed:** 2026-10-16, `main` baseline `2f60f46992991f3bb47a96a1c13a12a7b7544e08` (before this documentation update).  
**Platform:** owner-supplied Switch Unity 5.6.5p1 ARM64/IL2CPP, native Horizon adapter, SpruceOS, Mali-G57 GLES 3.2, approximately 963 MiB RAM. No Box64.  
**Purpose:** identify *new* experiments after the first roadmap was executed. [Historical resource studies](resource-optimization.md) and [M1/M5 measurement contracts](memory-benchmark.md) remain authoritative for their own earlier checkpoints.

> This is **not** a claim that either 30+ FPS or zero-swap has been attained. Device reports use varying saves/scenes and diagnostic builds. At the original review, `dtime8` (`414efb1f…`) instrumentation was not published. That gap is now closed by `a3793a1`: clean overlay application matches all 199 native source files of the measured build. Further execution results and still-open gates are recorded in §11; implementation of an opt-in mechanism is not release acceptance.

**2026-10-18 review note (main at `6b55a2ad0e730367ee8ae9fbb3b5574e93189587`):** the device and final SDL/KMSDRM window already output 1280×720, but measured Unity camera/intermediate targets still include 1920×1080. Whether the inherited Horizon service layer actually reports Switch handheld (0) or docked/console (1) has **not been determined**; HID's `SetNpadHandheldActivationMode` is not the system operation mode. Before modifying render-target dimensions, see [§13 — handheld mode preflight](#13-m7-preflight-switch-handheld-operation-mode-and-720p).

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
| M7 1920×1080 camera targets → handheld operation-mode A/B **before** coordinated 1280×720 | `WOL_DISPLAY_MAX` / `ListDisplays` override did not change Unity target sizes. System handheld/docked mode has **not been traced or proven**. | First trace `nn::oe` / AM mode and default-resolution queries; try fail-closed startup-only handheld reporting. Only pursue direct RT scaling if Unity ignores mode. See [§13](#13-m7-preflight-switch-handheld-operation-mode-and-720p). |
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

Continue §13 handheld-only service work and §§4–6 M5 allocator/M6 post-copy ASTC independently. **Neither 30+ FPS nor no-swap is achieved or claimed** by adding this section. Maintain fixed build SHA, identical owner save/section/environment, alternating trials, actual KMS frames, phase + Mali/VM samples, scene restoration, no stolen owner process and clear accepted/rejected result for every experiment.
