# West of Loathing on TrimUI Smart Pro S — performance and zero-swap roadmap

Status: **proposed work, not implemented**, unless explicitly marked otherwise.  
Baseline: **main at a6acb0e2d8d392dd31eb1de872ac361d36f99950**, 2026-10-16.  
Target: original Switch ARM64/IL2CPP Unity 5.6.5p1 through the native Horizon adapter on SpruceOS / Mali-G57 / OpenGL ES 3.2. No Box64.

This document tracks the next engineering steps after the 2026-10-15 A/B experiments. It supplements [resource-optimization.md](resource-optimization.md) and [memory-benchmark.md](memory-benchmark.md), not replaces their raw evidence. Re-evaluate the baseline when main changes; do not silently relabel proposed work as measured.

## 1. Goals and acceptance criteria

**Performance:** at least 30 independently verified game presents/second in representative gameplay, with P95 end-to-end frame interval at or below 33.33 ms after warm-up. Measure stationary and moving scenes, transitions, map, battle and a long session; a 30 s menu benchmark alone is insufficient. Distinguish NVN presents, actual KMS scanout and panel refresh (not identical metrics).

**Memory:** complete cold start and game session with **no swap enabled from before process launch**, no OOM or memory-floor stops, correct graphics/audio/save/load, and a meaningful MemAvailable/CmaFree safety margin at startup peaks and transitions. A warm process with near-zero swap I/O or a low VmSwap value does not prove zero-swap viability. Do not disable swap while the game is already running.

**Correctness:** preserve currently restored player/Cactus Bill geometry, WANTED stencil clipping, Sprite metadata/UV contracts, menus, dialogue, audio, saves and clean return to Spruce. The map's paper extent has improved, but marker/title placement remains unresolved; validate separately rather than asserting the map is fixed.

**Measurement:** every optimization must compare SHA-identified runtime and owner section with controlled save, identical launch environment, clocks and scene; run paired/alternating A/B repetitions and preserve actual KMS captures. Record frame-time P50/P95/P99, present rate, CPU consumption, major faults, swap-in/out, PSS/SwapPSS, sampled startup peaks, CmaFree and any GPU allocation metrics. Report noise and unknowns; do not convert estimates into measured gains.

### Reference measurements (not an A/B against future builds)

| Metric | Current evidence |
| --- | --- |
| Outdoor gameplay | about 24.9–26.2 presents/s in repeated M1/M5 probes |
| Ready menu | about 25.5–26.4 presents/s |
| Outdoor PSS + SwapPSS | about 910 MiB (process rollup, **not** entire physical RAM usage) |
| Startup minimum MemAvailable | 29.7–32.3 MiB |
| Startup minimum CmaFree | 0–12 KiB (sampled) |
| Outdoor live textures | 250, estimated host image extent 196.83 MiB |
| Guest heap pages outside NVN pool spans | about 699 MiB present-or-swapped; **not** identified free memory |
| Estimated work to reach 30 fps at 25–26 fps | around 5–7 ms/frame, subject to verified timing |

Sources: [M1/M5 observations](../evidence/memory-profile-m1m5/README.md), [M4 results](../evidence/mipstrip-m4/README.md), [resource-optimization evidence](resource-optimization.md). RSS, PSS, SwapPSS, NVN pool aliases, and estimated Mali images must **not** be added indiscriminately.

## 2. Completed or tested: do not redo without a new mechanism

| Work | Status and evidence | Action |
| --- | --- | --- |
| Per-draw success logging gate | Implemented; approximately 92% lower log growth; modest measured FPS change in that experiment | Keep quiet production path; preserve failures |
| True present RGB-write proof and periodic readback | Implemented/tested | Retain real pixel health checks; never mislabel unsampled as healthy |
| CPU logical-to-host remap, native RGBA4444, fast RGBA8 copy | Implemented as flags with tests | Keep validated defaults; do not attribute combined gains to one flag |
| M2/M3 mip-tail strip + corrected RomFS entry length | Deployed, significant measured footprint reduction | Keep |
| M4 100 selected background textures | Deployed; reduced measured memory in sampled scenes | Keep |
| M4 wave2, 53 additional textures | Offline-verified only, approximately 18.75 MiB payload estimate | Optional later device A/B, **not** a proven RAM saving |
| WOL_PAIR_RING persistent/reused GL objects | Implemented; median 25.88 vs 25.51 game presents/s, difference within noise | Not next FPS priority |
| WOL_COPY_GPU texture-region blit | Implemented opt-in; menu 26.74 -> 21.51 presents/s and longer finish; default off | Avoid unless the algorithm/scheduling changes |
| WOL_REFRESH_DIRECT guest-storage upload | Implemented opt-in; no meaningful FPS improvement; default off | Avoid re-testing the same copy elimination |
| M1/M5 read-only profiler and heap/NVN pool census | Implemented and exercised | Extend to owner-level attribution |
| M7 ListDisplays override / M9 format-56/ASTC probes | Specific probes did not work | Defer; not proof every scaling/compression solution is impossible |
| M8 free-page decommit | Not implemented; ownership not proved | Block until allocator evidence exists |

Detailed evidence: [pair ring](../evidence/fps-pair-ring/README.md), [GPU copy](../evidence/fps-gpu-copy/README.md), [direct upload](../evidence/fps-refresh-direct/README.md), [memory profiling](../evidence/memory-profile-m1m5/README.md).

## 3. P0 FPS: attribute replay, GPU waits, and presentation

**Hypothesis:** the remaining approximately 5–7 ms/frame may lie in replay CPU work, per-submit GPU completion or driver synchronization; exact overlap of reported replay/finish phases must be verified before adding numbers.

**Relevant code:** runtime/wol-adapter.patch, especially native/nvn_present.h, native/nvn_render.h, the texture copy/refresh overrides; tools/wol_memory_benchmark.py.

**Implement:**
1. Add an opt-in bounded per-frame/command-category timeline (suggested flag: WOL_FRAME_TIMELINE=1). Aggregate timestamps in memory; do not printf per draw.
2. Attribute command decode, shader lookup, state application, vertex/index preparation, texture binding, refresh, GL draw submission, copy/resolve, wait and present. Capture count, accumulated wall/CPU time, maxima and affected bytes.
3. Time actual GPU completion using supported driver mechanisms where possible; keep CPU submission and GPU elapsed time separate, avoid blocking same-frame timer query collection. Classify finish/eglSwapBuffers/fence waits, surface changes and dependencies.
4. Correlate phases to game frame IDs and log one summary per 60–120 frames; confirm the profiler itself is low overhead via profiler off/on A/B.
5. Measure during startup, menu, stationary street, moving street, sheriff interior, map and battle. Correlate with CPU core/frequency and GPU frequency rather than inferring saturation from one snapshot.

**Deliverable:** evidence/fps-frame-timeline/ containing timestamp definitions, code paths, A/B results, KMS captures, log summaries, and ranked top three critical-path bottlenecks.

**Accept:** identify a reproducible component with enough time to explain the gap, or report that the current evidence cannot distinguish GPU/CPU limits. Do not begin major GPU scheduling rewrites without this attribution.

## 4. P0/P1 FPS: explore a genuinely different texture-460 copy model

The measured hot path performs a 1280x720 (3.69 MB) CopyTextureToTexture into texture id 460 each frame; the default CPU-copy + dirty re-upload path moved about 9.44 GB each way over the profiling run. Replacing this with an immediate GPU region blit was *slower*; bypassing staging memcpy was flat.

**Not implemented: a conditional lazy copy/alias**. Before touching the implementation, trace the exact dependency chain: source render-target writes, copy, source writes after copy, destination GPU sampling, destination CPU reads/writes, reuse and subsequent copies. IDs are per-session; use object/generation identities, not a hardcoded global texture number.

Possible strategy:
1. Record a deferred copy descriptor including source/destination identities, generation, region, format, levels, sampler/UV transform and destination snapshot semantics.
2. On GPU sampling, redirect to source storage only if the source still represents the copy-time snapshot and all format/origin/swizzle/filter/alpha rules match.
3. On source mutation, destination mutation, guest CPU access, incompatible blit or pending GPU dependency, materialize the destination **before** the conflicting operation.
4. Use an explicit hazard/ownership model and revertible flag. Never substitute a live source image for a destination that requires independent copy-time contents.

**Alternative** (also unimplemented): defer a copy to a render-pass boundary or test native GLES glBlitFramebuffer with cached FBOs, but only with correct ordering. Do not merely re-enable WOL_COPY_GPU.

**Accept:** bitwise or narrowly specified pixel-equivalent output for matched captures, safe CPU/GPU coherence, no new finish stalls, and a repeated >noise FPS win before enabling by default. If the trace shows unavoidable hazards every frame, reject lazy alias early.

## 5. P1 memory: M5 owner-level Unity/AssetBundle heap attribution

Current read-only snapshots see approximately 901 MiB present-or-swapped pages in the guest heap reservation, with approximately 202 MiB overlapping the NVN pool union and about 699 MiB elsewhere. This is *not* an identified 699 MiB free block.

**Relevant code:** tools/wol_memory_profile.py, tools/wol_memory_layout.py, tools/wol_memory_benchmark.py; restored owner runtime/guest Unity 5.6.5p1 allocations (not published).

**Implement in safe stages:**
1. Extend read-only phase snapshots to repeated scene cycles and identify which VMAs grow, stabilize or shrink; compare guest heap, GPU aliases and native mappings without double counting.
2. Establish call-site/owner attribution for large allocations (Unity native allocator, IL2CPP managed memory, AssetBundle, UnityFS read/decompression, texture staging, other). Start with bounded samples for allocations >=1 MiB; collect lifetimes and frees with minimal perturbation.
3. Determine whether the 136.9 MiB M4 core read buffer is released, retained as a lazy cache or duplicated. Do not free it solely because initial loading completed.
4. Characterize allocator reserved, committed, active and free-list bytes and whether fully free pages can be safely returned.
5. Repeat street -> sheriff -> street multiple times; compare stable endpoint memory and live texture ownership to distinguish caching from leaks.

**Deliverable:** proposed tools/wol_heap_ownership.py (or equivalent runtime trace) and evidence/m5-heap-owners/ with a reconciled per-owner table and explicit unknown bytes.

**Accept:** identify concrete live allocators/resources capable of saving measurable RAM. An unknown VMA label or pagemap swapped flag does not prove reclaimability.

## 6. P1 memory: M6 compressed and compact host GPU textures

**Not implemented.** Guest BC/DXT texture content is often decoded to host RGBA for GLES uploads. A static BC3 1024x1024 level needs about 1 MiB compressed but 4 MiB RGBA8 when expanded; these are *format* sizes, not a prediction of total driver-RAM savings.

**Relevant code:** runtime/wol-adapter.patch around zero_texture_refresh / zero_texture_bc_pixels and host texture creation, tools/wol_memory_repack.py for separate offline metadata.

**Implement:**
1. Collect native-format, sampled/static/mutable, mip, sRGB/swizzle, render-target and *measured if possible* driver-residency inventory. The ~196.83 MiB host image number is only an estimate.
2. Query Mali GLES support for ETC2/EAC and ASTC formats, then verify glCompressedTexImage2D on a single safe asset and inspect actual driver allocations.
3. Generate an owner-local, content-hash-identified cache (BC -> ETC2 RGBA/RGB or suitable ASTC) **outside** UnityFS. Leave original guest format/API contract unchanged. Keep RGBA fallback for dynamic, partially updated, render-target and unsupported textures.
4. Preserve mip levels, block sizes, alpha, linear/sRGB, wrapping, swizzle, sampler state and invalidation on guest writes.
5. For genuinely grayscale assets, evaluate R8 or RG8 plus exact channel reconstruction; do not indiscriminately replace RGBA for sprites with independent alpha.
6. Compare fine black outlines, characters, UI text and stencil masks on physical screenshots, plus PSS/SwapPSS, Mali allocations, GPU bandwidth (if available), startup, and FPS.

**Accept:** verifiable physical-memory improvement, no correctness regression or new upload latency. A smaller compressed disk cache alone is not sufficient. Treat M9's unsuccessful in-bundle format replacement as a separate experiment, not a reason to skip M6.

## 7. P1 memory: GPU residency inventory and safe eviction

**Not implemented as a complete budget-based policy.** Endpoint counts in the M5 test were 217 -> 250 -> 246 -> 261 live textures; increased object count does not by itself imply leaked GPU memory.

**Implement:**
1. Track per-resource guest identity/generation, estimated and measured host bytes, last sampled/written frame, in-flight uses, render-target/depth status, guest backing and reconstructibility.
2. Report unused-for-5/15/30-second bytes and candidate safe-to-evict static storage. This first pass must **not** free resources.
3. Only if there is enough inactive reconstructible storage, add budgeted eviction with lazy re-creation and fence-aware retirement. Never evict unique GPU-authoritative render results without a correct restore path.
4. Use memory pressure and measured reload penalties to tune budget, rather than copying ScarletNX's exact fixed frame timeout.

**Accept:** lower peak resident physical memory after repeated transitions without excessive re-uploads, page faults, hitching, or loss of texture content.

## 8. P2: M8 allocator-safe decommit (blocked on M5)

**Do not** call madvise(MADV_DONTNEED), mprotect, unmap or perform a zero-page scan as a proxy for allocator ownership. Pagemap present/swapped/unmapped and NVN pool aliases do not show which Unity objects are live.

Implement only after the allocator exposes verified whole-page free ranges, free-list transitions and all aliases/GPU uses. Require page alignment, lock/epoch coordination, fail-closed guards and a fallback mode. Test long scene cycles and restoration of every reused allocation.

**Accept:** actual decline in committed/physical memory on device without guest data corruption, crashes, GPU faults or higher reload stalls.

## 9. P2: M7 coordinated internal render-target scaling

The 1920x1080 intermediate images cost about 2.25x the pixels of the 1280x720 screen for each equal-format full-screen pass. The existing ListDisplays override did **not** make Unity allocate smaller targets.

**Implement only after profiling indicates GPU fill/bandwidth or RT storage is significant:**
1. Trace render-target creation, dimensions, formats, usage, viewport/scissor, attachment graphs, sampled regions and physical output.
2. Identify camera-color/depth targets eligible for scaling while preserving logical guest dimensions and transformations, or find the genuine guest-side resolution decision.
3. A/B only one coordinated target class at a time, including downstream UV, copy regions, stencil, UI and sampling.
4. Compare cost/quality in gameplay, map, portrait mask and dialogue text; avoid a global 1920 -> 1280 lying-size substitution.

**Accept:** reduced GPU elapsed/present time or physical storage with visually correct compositing and no guest memory incoherence. If GPU is not the bottleneck, defer.

## 10. P2 other candidates (measure before coding)

- Cache redundant GL state changes and GL queries only after a bounded call-frequency profile; keep full error detection in diagnostics and invalidate cached state on all direct GL paths.
- Generation-tracked immutable vertex/index cache only if repeated unmodified guest ranges are common. WOL_PAIR_RING alone already eliminated object churn without a meaningful FPS improvement.
- Prewarm shader programs only if compilation/link stalls appear in timings.
- Pool transient texture upload workspaces only if peak allocation/lifetime measurements show an opportunity; WOL_REFRESH_DIRECT already showed staging memcpy is not a frame-time lever.
- Investigate true zero-copy or cheaper readback only when health-proof accounting and presentation correctness remain intact.

## 11. Experimental order and exit criteria

| Phase | Proposed work | Output / decision |
| --- | --- | --- |
| A — FPS baseline | WOL_FRAME_TIMELINE, GPU-wait classification, same-scene A/B | Rank exact critical-path costs |
| B — FPS mechanism | Texture-460 dependency trace, then lazy alias or pass-boundary copy behind opt-in flag | Keep only if repeatable >noise performance gain |
| C — memory baseline | M5 allocator/AssetBundle owners and multi-transition lifecycle | Account for large retained non-pool heap regions |
| D — compressed storage | M6 one immutable BC asset then limited rollout | Quantify physically saved RAM vs quality/latency |
| E — residency | Read-only inactivity census; gated eviction if worthwhile | Measured reduction in peak RAM |
| F — targeted optional | M4 wave2, M7 render scaling, M8 verified-free decommit | Each isolated; revert failures |
| G — full acceptance | Cold boot without swap, gameplay + save/load + late locations, performance and KMS capture | **30+ FPS + zero swap** proven in one build |

Run FPS and memory work in parallel only when their experimental changes can be evaluated independently. No deadline or estimated FPS/RAM saving is a commitment.

### One-variable A/B discipline

- Start each trial from a SHA-pinned main revision and a known-good owner-only section/launcher/save, restoring all after each bounded run.
- Use a controlled real Spruce principal/menu handoff and consistent scenes; do not treat successful diagnostic Npad packets as physical controller verification.
- Alternate control/variant order, repeat enough times to separate approximately 1–1.5 presents/s natural variation from a true change; report full samples not just best run.
- Preserve startup samples plus 30 s menu/street, interior and return. Add movement, battle, map and extended play before promoting any flag.
- Capture actual KMS frames and compare exact locations; flag known map deficiencies. Check audio, save hashes, exact runtime PID cleanup, CPU online mask, MainUI recovery and absence of unowned process changes.
- Keep measured facts, projections and hypothesized benefits explicitly separate.

## 12. Zero-swap readiness gate

Before a no-swap test, demonstrate ample MemAvailable and CMA headroom **through cold-start peaks**, not just a warm street screenshot. Track host driver allocations separately and note possible overlaps with process accounting. Process PSS+SwapPSS around 910 MiB is not itself proof the game will fit into about 963 MiB physical RAM with kernel, display, GPU and other processes.

For a dedicated recovery-safe test environment, disable swap **before** launching the game, then verify no swap device/file is active, collect meminfo/oom/pagemap/driver indicators and run menu -> street -> interior -> battle -> map -> save/load -> return cycles. Do not force swapoff on a live, already swapped game. Re-enable the normal system configuration if the experiment fails.

**Release gate:** no OOM, no memory floor, no missing textures, no stale CPU/GPU copies, acceptable frame-time P95, stable memory over extended scene cycles, clean Spruce restoration and verifiable zero swap throughout.

## 13. Correctness, CI and repository follow-up

- Keep the [gfx265 visual baseline](../evidence/gfx265/README.md) and all owner-data SHA receipts. Character bodies and portrait mask are restored; map title/markers remain open.
- Add a real overlay-apply/build/regression CI job against the verified GPL reconstructed source when that source can be acquired lawfully in CI, while keeping commercial assets/NSO/game binaries and owner saves out of public CI. Existing .github/workflows/native-probe.yml does **not** prove full Horizon runtime performance or playability.
- Add focused data-free tests for timeline counter boundaries, copy hazards, texture generations, compressed formats, eviction and allocator-page safety as relevant changes land.
- Do not make experimental runtime flags production defaults until device A/B, KMS screenshot, audio/input and save/load acceptance.
- Update outdated status text in runtime/README.md and original PR descriptions separately if useful; this roadmap does not assert those documents are current.
- Keep new measurement evidence under evidence/<experiment>/ with effective environment, source/runtime/section hashes, scripts, raw metrics and explicit limitations; no commercial game assets or raw extracted shaders.

## 14. Recommended immediate next commits

1. **Instrumentation only:** lightweight frame timeline and GPU-wait attribution; no runtime behavior change by default.
2. **Instrumentation only:** heap/AssetBundle allocation owner and texture-residency inventory with repeat scene cycles.
3. **Experimental opt-in:** texture-460 dependency trace and guarded lazy copy, *only* if trace supports safe aliasing.
4. **Experimental opt-in:** M6 compressed upload for one validated immutable texture with cache/fallback and physical-memory comparison.
5. **Evidence/report:** choose the next production candidate based on measured critical-path milliseconds and reclaimable resident bytes, not source-level speculation.

Do not repeat ring-buffer, immediate GPU-blit, or direct-refresh-upload experiments without materially different scheduling/coherency logic.
