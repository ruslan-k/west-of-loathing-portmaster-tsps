# West of Loathing / TrimUI Smart Pro S — FPS and zero-swap optimization roadmap

**Status:** living technical plan; tested and rejected experiments are explicitly separated from proposed work.  
**Reviewed:** 2026-10-16, `main` baseline `2f60f46992991f3bb47a96a1c13a12a7b7544e08` (before this documentation update).  
**Platform:** owner-supplied Switch Unity 5.6.5p1 ARM64/IL2CPP, native Horizon adapter, SpruceOS, Mali-G57 GLES 3.2, approximately 963 MiB RAM. No Box64.  
**Purpose:** identify *new* experiments after the first roadmap was executed. [Historical resource studies](resource-optimization.md) and [M1/M5 measurement contracts](memory-benchmark.md) remain authoritative for their own earlier checkpoints.

> This is **not** a claim that either 30+ FPS or zero-swap has been attained. Device reports use varying saves/scenes and diagnostic builds. At the original review, `dtime8` (`414efb1f…`) instrumentation was not published. That gap is now closed by `a3793a1`: clean overlay application matches all 199 native source files of the measured build. Further execution results and still-open gates are recorded in §11; implementation of an opt-in mechanism is not release acceptance.

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
| M7 1920×1080 camera targets → coordinated 1280×720 | Earlier `ListDisplays` override did nothing | Requires full render graph / logical coordinate and stencil validation; do not lie about storage dimensions |
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
- **The guide-screen "missing locations" report is a game-content question, not a dropped draw.** With the guide open on the owner's save, OCR of the real frame shows one two-line destination ("Thousand Snakes Gulch"); 13 navigation probes (d-pad and analog stick, all four directions) never scroll or change the list; and two instrumented sessions (`WOL_DRAW_TRACE=1`, and `WOL_RECT_TRACE` over the list band) show the game issuing only the text elements that are visible — no surplus text draws and no extra row in the band. The save meanwhile carries five marked locations, three marked unvisited, complete horse-taming progress and the map reminder, with the tutorial still unfinished. Evidence: [guide investigation](../evidence/roadmap-v2-owner-map/README.md), [draw trace](../evidence/roadmap-v2-guide-diag/README.md), [list band](../evidence/roadmap-v2-guide-rect2/README.md).
- [Frame parity](../evidence/roadmap-v2-frame-parity/README.md) settles the §8 marker/title question and the §9.3/§9.5 visual-coherence question from already published captures: on pixels the control arm reproduces byte-for-byte (99.475 % of the group map frame), the post-copy arm differs by less than two control runs differ from each other, and no marker, glyph or panel is relocated. Whole-frame raw amplitude still exceeds the within-arm range on animated/dither-prone pixels, which is why the conservative raw rule keeps printing `review`; that is recorded, not hidden.
- These repeated process launches use the same warm host/device setup; they are not cache-cold or swap-disabled device boots. Runtime presents are not independent physical-panel FPS. PSS, driver commit, pool spans and CMA are not added into a synthetic physical total.
- Before closing acceptance, obtain a verified pre-combat/travel route or owner-demonstrated interaction, independent map reference, physical input/audio evidence and a validated recovery-safe no-swap setup. Do not repeat the rejected source redirect, null-image ASTC or PBO promotion as though those prerequisites were satisfied.
