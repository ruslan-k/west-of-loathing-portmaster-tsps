# Horizon v327680 — latest update+DLC eligibility and GPU bottleneck (2026-10-30)

> **Current authoritative plan: [§28 mandatory update + DLC](optimization-roadmap-active-native-unity-2026-10-29.md#28-mandatory-update-and-dlc--architecture-and-optimization-reset-2026-10-30), [release acceptance gate](release-gate-update-dlc-2026-10-30.md).** Old statuses and §27's Unity-first recommendation below are **historical**, because it was not then established that installed Linux Unity data included the owner-required update. Do not promote a build lacking exact v327680 update or verified, owner-approved updated-PC content equivalence **and** real Gun Manor play.

> **Horizon v327680: UPDATED CONTENT PIPELINE PARTIAL, DLC PIPELINE PARTIAL.** `prepare_horizon_image.py` can generate an updated ExeFS/image table, and the validated source implements `WOL_AOC_HOUSE_BEGIN` and separate DLC `wol-house.romfs` data ID `0x010031b00a4e9001` (size 58,907,880 bytes); data-free IPC/storage tests pass. The merged program RomFS identity is pinned by hash; the DLC backing open path itself checks size/file type **but not whole-file SHA**. Real normal Dirtwater→ghost carriage→Manor gameplay, update-feature verification, save/load and ≥30 physical FPS remain **NOT certified**.

> **New H2: source copy owner identified, previous H-T0 hypothesis superseded.** [H2 measured evidence](../evidence/horizon-h2-2026-10-30/README.md) states that `nvn_render_color_copy(source=2,destination=82)` performs a **full 1280×720 1:1 CPU-side copy**, setting `dst->zero_cpu_dirty=1`, followed by the usual 3.69MB GL upload. Earlier text attributing the dirty mark to `zero_texture_pool_flushed` was incorrect for this run. Benchmark on H2 ELF lineage: baseline **42.90ms**, `WOL_REFRESH_OFF=1` **37.37ms with INVALID stale pixels** (~26.8 FPS, still ~4.04ms above 30 FPS target), 960×540 attempted **but hook never fired**. No shippable gain; do not declare disabled upload as optimization.

> **Unity track A3:** [41.4–41.6 host FPS, live audio, VmSwap=0](../evidence/unity-trackA-2026-10-30/README.md) over 90s through real principal flow, **but no moving gameplay/normal DLC entry/full save, and exact required update content not established**. Faster is not enough to qualify this as replacement. Both engines remain **release-INELIGIBLE** until update + DLC proofs are complete.

> **CI:** [run 41080886647](https://github.com/ruslan-k/west-of-loathing-portmaster-tsps/actions/runs/41080886647) **green** through ARM64 tests. Prior B0/B1 image-table fixes and H-D1 CPU accounting remain valid, but public data-free CI cannot test private update/DLC gameplay. Future work: first content identity and full DLC acceptance; only then one bounded GPU dataflow/copy-elision experiment if strict Horizon remains necessary.

> **Archived per-ELF reports below** are retained for historical traceability, and their “next step” instructions must not override §28.

**Date:** 2026-10-30 · **ELF:** `21e23b58c3e2fb01018c71ab10ad4b9a08029e85e9a8ad0118765c89d345d956` (w32)
**Run:** `e1b`, `WOL_OP_SPLIT=1` (default-OFF profiler), scripted input, 90 reported frames
**Production Unity port and saves untouched; probe tree only.**

> **Later status, 2026-10-30 09:40:** H-E1c is now **closed** on ELF `f5c6f6f2` with a matched
> fresh-boot OFF/ON/OFF (40.608 / 40.412 / 40.184 ms p50, overhead +0.04 %) and a passive H-M1
> series — see the H-E1c section below and
> [evidence/horizon-e1c-abc-2026-10-30](../evidence/horizon-e1c-abc-2026-10-30/README.md).
> `ReportCounter` still blocks (8.48 ms wall / 0.20 ms CPU per frame) in the matched scene. The
> named wait is `glFinish` (`nvn_counter_time.h:17`), and removing it is a **negative result**:
> frame 40.412 → 39.894 ms (§ H-P1 below). The next lever is the `DrawArrays` CPU path.

## H-E1b — per-class op budgets with explicit units — **IMPLEMENTED; frame-ownership bug identified**

`WOL_OP_SPLIT` was rewritten (commit `0593c9e`): separate accumulators for `DrawArrays` and
`ReportCounter`, explicit `sum_ms` / `mean_ms` / `cpu_mean_ms`, one `WOL_OP_V2` line per frame.
The earlier "50.5 µs/op" reading is retracted (commit `b884f9b`); the old printer already divided by 64.

Measured, medians over 90 frames:

| Class | calls/frame | sum ms/frame | mean ms/call (wall) | mean ms/call (thread CPU) |
|---|---:|---:|---:|---:|
| `DrawArrays` | 3 | 6.623 | 2.208 | **1.835** |
| `ReportCounter` | 2 | **10.107** | 5.053 | **0.105** |

`DrawArrays` + `ReportCounter` per-frame sum, median **16.879 ms**, max 350.181 ms (frame-boundary spike).

Two separable facts the old instrumentation could not produce:

1. **`ReportCounter` is a blocking wait, not work**: 5.05 ms wall with 0.105 ms thread CPU per call,
   ~10.1 ms per frame. This is the missing ~9.8 ms almost exactly.
2. **`DrawArrays` is real CPU work**: 1.835 ms CPU per call, ~5.5 ms per frame.

## H-M0 — memory receipts — **DONE as system-level sampling; ownership and headroom still unproved**

Host-side sampling every 3 s during the gameplay run `mem0` (95 points, ELF `21e23b58`), preflight
`CmaFree 129 188 kB`:

| Metric | min | median | max |
|---|---:|---:|---:|
| `CmaFree` | **12 kB** | 2 448 kB | 129 380 kB |
| `MemAvailable` | **34 812 kB** | 77 284 kB | 748 664 kB |
| `SwapFree` | 955 248 kB | 1 277 712 kB | 2 037 628 kB |

**66 of 95 samples are below the 65 536 kB admission gate**, and swap shrinks by ~1.08 GB during the
run. The 65 536 kB preflight is admission only, exactly as §25.4 warned: after startup the device has
effectively no contiguous CMA left. An extra async frame, buffer snapshot or pinned GL program cannot
be added on top of this — this is the hard wall in front of H-A1 and H-R1, independent of FPS.

Raw samples: `evidence/horizon-roadmap25-device-status/mem0-samples.txt`.

## H-P1 — attribute the actual wait — **CLOSED: named `glFinish`, not recoverable**

The wait is named: `nvn_replay.h` handles `nvnCommandBufferReportCounter` through
`nvn_counter_timestamp()`, which runs `if(!nvn_counter_time_enabled())glFinish();`
(`nvn_counter_time.h:17`) — twice per frame. `COTM_COUNTER_CPU_TIME=1` selects a CPU-wall
approximation (no GPU timestamp; submit completion unchanged).

Matched fresh-boot A/B on the same scene: baseline **40.412 ms** p50 with `ReportCounter`
**8.482 ms wall / 0.198 ms CPU**; with the option **39.894 ms** p50 and **0.014 ms / 0.014 ms**.
Removing 8.47 ms from the class removed **0.52 ms** from the frame — the drained GPU work reappears
in the unaccounted remainder (accounted share 39.2 % → 16.9 %). This is the roadmap's “a wait that
reappears later is no optimization” case. Do **not** pursue counter synchronization for 30 FPS.
Evidence: [horizon-e1c-abc-2026-10-30](../evidence/horizon-e1c-abc-2026-10-30/README.md#h-p1-follow-up--the-named-wait-is-glfinish-and-it-is-not-on-the-critical-path).

## H-G1 — 7-vertex draw provenance — **NOT STARTED**

Blocked on `id=0` (`gl_name` unpopulated) reported in `evidence/update-327680-drawarrays-target/`.
Identity join needs a real GL name/FBO attachment readback, which the current trace does not carry.

## H-A0 — async program identity trace — **NOT DONE; the pin hypothesis is retracted**

`w30` (pin counters) and `w31` (pin + skip pinned slots at `nvnProgramInitialize`) were built and run:
`async5` still stops at `NVN_PROGRAM_INVALID`, `main.text.seg+0x532994`, `detail=0x0`.
The `NVN_PROGRAM_PINNED_DESTROY` guard never fired, so no pinned program was destroyed — the
recycling premise was wrong. Per §25.7 this is now marked **no-go until H-A0 proves object lifetime**.

## H-A1 — bounded program lifetime fix — **BLOCKED by H-A0**

Not attempted beyond the retracted pin work.

## H-R1 — rewrite one expensive pass — **NOT STARTED**

§25.5 forbids touching the `flags=0x9` target before identity proof; H-G1 is a prerequisite.

## H-ACCEPT — final acceptance — **NOT REACHED**

The **current matched reference** is ~40.4 ms per 60-frame-window mean (~24.7 runtime presents/s); about **7.1 ms/frame** is still missing for 30. E1b's older ~10.1/5.5-ms estimates were **unmatched**. H-E1c/P1 improve attribution, not FPS. Individual-frame p95, physical distinct output, full save/audio/DLC and endurance remain unaccepted.

## Async gate correctness — **FIXED**

`WOL_ASYNC_ACK` now requires the exact value `"1"`; previously `0`, empty or any non-empty value
bypassed the fail-closed guard (`0593c9e`). Async remains default OFF.

## Previous recommendation — **SUPERSEDED**

H-E1c and H-P1 are **both closed** in the new report. Next is **H-D1**: identify where the three DrawArrays calls spend ~6.05 ms CPU/frame, with opt-in no-change instrumentation and matched scene/thermal/CMA controls.

## Architecture attempt A1 — bounded CPU texture mirrors — **NEGATIVE (measurement)**

Change: `WOL_TEX_SHADOW_MB` budget (default 0 = off) that evicts `cpu_snapshot` mirrors of the
oldest `cpu_generation` textures before allocating a new one (ELF `59ee0cdd`).

Run `shadow0` with `WOL_TEX_SHADOW_MB=192`: **zero `WOL_TEX_SHADOW_GC` events** — the budget was
never reached, so the texture CPU mirrors stay below 192 MB and are **not** the source of
`VmRSS 755 MB` / `VmSwap 1.08 GB`. The footprint is guest memory mapping and the shim's GPU-side
allocation, not readback shadows.

Consequence: evicting mirrors cannot lift the CMA wall. The next architectural lever must target the
guest RAM mapping (page reclaim / on-demand commit) or the Mali allocation rate, not the shadow cache.
The flag stays default-OFF and inert.

## H-E1c — V3 frame ownership repaired — **DONE, first matched data**

`WOL_OP_V3` (default OFF; ELF `f5c6f6f2`): bucket flushed **before** a new frame's first op, tagged by
entry frame + thread, separate classes, explicit sum/mean wall and CPU. First post-reboot run
(`v3on2`, `CmaFree 130 412 kB` at start), 4 832 V3 lines from a single worker thread:

```
frame=2414 DrawArrays    n=3 sum_wall=6.449 sum_cpu=4.713 mean_wall=2.150 mean_cpu=1.571
frame=2414 ReportCounter n=2 sum_wall=7.455 sum_cpu=0.171 mean_wall=3.728 mean_cpu=0.086
frame=2415 DrawArrays    n=3 sum_wall=8.723 sum_cpu=4.873 mean_wall=2.908 mean_cpu=1.624
frame=2415 ReportCounter n=2 sum_wall=6.868 sum_cpu=0.207 mean_wall=3.434 mean_cpu=0.104
```

Two findings that differ from E1b:

1. **`DrawArrays` is CPU-bound**, not cheap: ~4.7–4.9 ms of thread CPU per frame for three calls.
   That is a real optimization target inside the handler, not a wait.
2. **`ReportCounter` remains off-CPU**: ~6.9–7.5 ms wall at 0.17–0.21 ms CPU — a genuine block, but its
   owner (fence vs driver backpressure) is still unnamed.

`NVN_PROFILE` in that run showed 60.338 ms/frame at frame=121 (startup period dominated), so those
frames were **not** the historical 71–73-draw scene; the numbers are per-op facts, not a baseline
claim.

**Closed the gap the same day** with a matched fresh-boot **OFF/ON/OFF** (`c1-off` 40.608 ms,
`c2-on` 40.412 ms, `c3-off` 40.184 ms; p95 41.86/41.35/41.39, replay 24.4–24.8 ms). Ledger overhead
**+0.04 %**, scene identity confirmed by KMS captures at 180/240 s, CMA preflight 128–130 MB on each
boot. In the matched heavy scene `DrawArrays` is 7.264 ms wall / **6.047 ms CPU** per frame and
`ReportCounter` is 8.482 ms wall / **0.198 ms CPU** — accounted 15.84 ms (39.2 %). The
`ReportCounter` block therefore **does recur** in real gameplay; only its owner is still unnamed.
Evidence: [horizon-e1c-abc-2026-10-30](../evidence/horizon-e1c-abc-2026-10-30/README.md).
Known limit: the terminal partial bucket is still not flushed (≤1 frame), and only one worker
thread emitted rows.

## Earlier engineering handoff — H-D1 (SUPERSEDED by c5–c8 / H-S1)

**Why:** H-P1 proves the apparent 8.48-ms `ReportCounter` wait is not an independently recoverable 8.48 ms. The strongest new named cost is **three seven-vertex DrawArrays with ~6.047 ms thread CPU** and **~7.264 ms wall/frame**. Yet 40.412→33.333 ms still needs **7.079 ms**, so no single unproven 6.05-ms CPU removal certifies 30 FPS.

**New default-OFF candidate, not yet implemented:** `WOL_DA_CPU_SPLIT=1`; source location `nvn_render_draw_inner()` in `runtime/wol-adapter.patch`. Record **nonoverlapping thread-CPU and wall** spans for only DrawArrays: program/FBO/state setup, uniforms, samplers/texture refresh, vertex/attribute preparation, exact existing `glDrawArrays` and remainder. Existing `NPS_SUBMIT`/draw profiling are **wall-only and mix draw opcodes**. No new GL calls, waits, cache lifetime changes or target scaling. Aggregate by frame + specific draw/target, reconcile CPU stage totals to `WOL_OP_V3` (±5%), bound output. Synthetic no-draw/frame-boundary/worker tests plus a same-gameplay fresh-boot OFF→ON→OFF with KMS 180/240-second proof, temperature/devfreq if possible, CMA/SwapPss/fault receipts and 131 production hashes. ≤5% extra overhead, no black/repeated frames, clean Spruce recovery.

**Deferred:** if driver call accounts for CPU, validate existing `WOL_GPU_TIMELINE` without blocking and prove actual 1080p FBO/program before considering GPU changes; if software setup dominates, optimize ONE invariant-proved function. Guest-memory reclaim/extra async buffering remain **blocked** by near-zero CMA and unproven alias/lifetime. `COTM_COUNTER_CPU_TIME=1` is NOT a shipping optimization; previous `ZERO_RENDER_SCALE`, `WOL_UNIFORM_CACHE`, `MOMO_SUBMIT_FINISH` remain closed.

**Pacing caveat:** 60-frame-window p95 ≠ p95 of actual single-frame intervals. Report both and external physically distinct output at final acceptance.

## Latest H-S1 execution handoff — single next reversible experiment, NOT IMPLEMENTED

**Offline first:** read `evidence/horizon-e1c-abc-2026-10-30/c8-samsplit.log.xz` for existing `pp1…pp5` zone/call/window values. The c8 published README only prints `sm1=7.272ms`, not the fine-grained nested pp distribution. Do not add pp times to sm1 or a2c1: they are nested and different scopes.

**Source:** `runtime/wol-adapter.patch` includes `nvn_render_sampler_prepare_mode`, `WOL_SAMPLE_SPLIT`, and the quiet-pick loop calling `nvn_render_sampler(candidate,0,0,0,...)`. `real_sample=0` does **not** avoid `zero_texture_refresh`, normal/RT storage materialize or sampler storage require. Those can have later-state/fail-closed side effects. This source proves a promising question, not an authorized bypass.

**Proposal H-S1:** default-OFF `WOL_SAMPLER_OWNER=1`, add *only* exclusive thread-CPU+wall accounting by NVN opcode/draw ordinal, quiet-pick versus real sampled caller, `real_sample`, frame/worker/handle/generation, `pp1…pp5` and remaining `sm1`. Keep texture, GL, queue, sync and guest state unchanged. One 240-second same-script fresh-boot OFF→ON→OFF; ±5% reconciliation to same-frame `WOL_OP_V3` DrawArrays CPU, ≤5% overhead, verified moving KMS 180/240-second captures, stable temp/clocks, CmaFree/SwapPss/faults, 131 protected hash receipts and clean MainUI. A null/other sampler owner **closes the hypothesis**; there is no requirement to produce a speculative fix.

**Only if proven:** compare a read-only metadata quiet-pick alternative, but first prove same selected handle and **all** refresh/materialize/RT-storage/sampler/alias/GPU next-use side effects remain correct. Never turn `COTM_COUNTER_CPU_TIME`, `ZERO_RENDER_SCALE`, shader pins, shadow eviction or a forced async queue into a production default. With 40.412→33.333 requiring ~**7.08 ms**, even full 6.047-ms DrawArrays CPU removal alone does not certify 30 FPS.

**B0 must be green before calling a rebuilt candidate reproducible.** Production Unity has separate N0/N1 audio-enabled gameplay/endurance acceptance gates.

## Newest execution result H-D1 — STAGED, DEVICE BLOCKED

Evidence: [H-D1 report, ELF identities and exact failure](../evidence/horizon-hd1-2026-10-30/README.md), commit `04384a73`.

The source-stage profiler `WOL_DA_CPU_SPLIT` was implemented only in owner-relative diffs and `wol_da_split.h`. Unit fixture checked arithmetic and default-OFF in an owner workspace. **No gameplay from either rebuilt ELF**: one canonical neutralized-overlay build `9a64faed…` and one prior w9-source+H-D1 `5786a362…` failed `segment size mismatch rtld.text.seg`. Thus the earlier `H-D1 next fresh-boot OFF/ON/OFF` instructions are **blocked**, not complete. The working `f5c6f6f2…` was verified at the same time; failed candidate files restored, protected production hashes unchanged, MainUI returned, no CMA was consumed by this early failure.

**B1 one diagnostic:** record `T2_IMAGE_FILE_MAP` effective child environment, exact opened rtld segment (path/fd/stat) and expected `s->file_size`; rebuild without H-D1 to test whether failure is a generic source-image mismatch. Keep size check fail-closed; do not pad segments or silently swap images. After B1, rerun full frozen-source build and ensure H-D1 portable CI header exists and is not silently skipped.

**B0 current CI:** last actual run is [41044438709](https://github.com/ruslan-k/west-of-loathing-portmaster-tsps/actions/runs/41044438709), **not** older 41024788603. The failing code is in `tools/test_wol_memory_roadmap.py` and assumes one `--- a/` record per touched file; 125 entries/116 paths. Keep source/sparse/added-file completeness and validate ordered repeated patch sections or regenerate canonical once-per-file patch using the exact normalized frozen base.

**H-S0/H-S1:** c8 pp1–pp5 XZ must be parsed offline before another rebuild. Profile sampler `real_sample=0` quiet candidates versus actually sampled descriptors using same-opcode/thread exclusive CPU timing, preserving `zero_texture_refresh`, materialization, RT storage and fail-closed alias/lifetime rules. Only after measured CPU owner and safe side-effect proof is any metadata-only quiet-pick optimization eligible. No GPU/texture behavior change was performed by this audit.
