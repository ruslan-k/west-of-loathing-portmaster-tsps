# Horizon v327680 — device and optimization status (updated 2026-10-30)

> **LATEST RE-AUDIT against HEAD `fd067783`:** previous H-D1 plan is now **superseded**. c5–c8 profiling found **a2c1 7.764 ms/frame across ~60 draws** and **sm1 7.272 ms/frame across ~120 sampler calls**. These are **different runs and mixed-class wall aggregates**, **not 7.272 ms CPU exclusive to three DrawArrays**. Sampler preparation invokes refresh/materialization even when the quiet-pick selector calls `nvn_render_sampler(...,real_sample=0)`. Before any metadata-only bypass, read existing c8 `pp1–pp5` spans and perform default-OFF **H-S1 opcode/quiet-pick/real_sample thread-CPU attribution**. No GL/texture behavior change has yet been justified. [Current `25](optimization-roadmap-active-native-unity-2026-10-29.md#25-full-repo-optimization-re-audit--2026-10-30).
>
> **B0 CI BLOCKER:** latest GitHub Actions [run 437](https://github.com/ruslan-k/west-of-loathing-portmaster-tsps/actions/runs/41024788603) FAILED: **one of 113** memory-contract tests asserts each file occurs once in the patch; current source has **125 file headers, 116 unique paths** and repeated hunks for five paths. `git apply --numstat` parses, but following ARM64 build/tests were skipped. Fix/harden the safety contract and verify application to the frozen source; do NOT delete the test.
>
> **Completed:** V3 default-OFF profiler and matched E1c OFF/ON/OFF at **40.608 / 40.412 / 40.184 ms** per **60-frame-window mean** (~0.04% profiler overhead), 3 DrawArrays ~**7.264 ms wall / 6.047 ms CPU**, 2 ReportCounter ~**8.482 ms wall / 0.198 ms CPU**. H-P1 identified counter `glFinish`; one guest-semantics-changing c4 run reduced whole-frame median by only **0.52 ms**, not a shippable ~8-ms win. Gameplay `CmaFree` ~**0.3–1.9 MiB**, process SwapPss ~**922–930 MiB**; async/new GPU buffer headroom remains unproven. Frame P95 values in existing reports are **P95 across 60-frame averages**, not actual per-frame scanout P95. Native Unity installed game/audio/saves remain separate and unchanged.

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
