# Horizon roadmap §25 — item-by-item device status

> **Follow-up source audit, 2026-10-30; authoritative interpretation: [main roadmap `25](optimization-roadmap-active-native-unity-2026-10-29.md#25-current-horizon-v327680-re-audit--2026-10-30-head-38f05f66).** This status page preserves the original experiment results but its strong causal conclusions need qualifications: (1) `WOL_OP_V2` increments the selected operation *before* detecting a frame change, mixing the new frame's first operation with the previous bucket and labeling it as the new frame; (2) the first 60-frame `NVN_PROFILE` averaged **462.637 ms/frame**, not the earlier ~43-ms matched heavy-gameplay window, and the 90 V2 rows have no independently validated ~71–73-draw scene match; (3) **~10.1 ms ReportCounter wall with ~0.21 ms CPU across two calls** shows a large off-CPU span **in this diagnostic sample**, **not** a named GPU fence or a recoverable 10 ms in the old gameplay baseline; (4) `CmaFree` is system-wide, and the 95 samples include prestart/post-exit; 66 below the launch admission gate are a serious headroom warning, **not owner attribution or an observed OOM**; (5) zero texture-shadow GC events at `WOL_TEX_SHADOW_MB=192` are **not** a trusted peak-live-byte measurement because `sh_bytes` does not track all free/replace paths. Async pinning did **not** resolve `NVN_PROGRAM_INVALID`. Next single reversible experiment: default-OFF **H-E1c**, correctly frame-scoped wall/CPU profiler in physically verified heavy gameplay, with a passive CMA/SwapPSS host receipt. **No device changes were made by this audit.**


**Date:** 2026-10-30 · **ELF:** `21e23b58c3e2fb01018c71ab10ad4b9a08029e85e9a8ad0118765c89d345d956` (w32)
**Run:** `e1b`, `WOL_OP_SPLIT=1` (default-OFF profiler), scripted input, 90 reported frames
**Production Unity port and saves untouched; probe tree only.**

> **Later status, 2026-10-30 09:40:** H-E1c is now **closed** on ELF `f5c6f6f2` with a matched
> fresh-boot OFF/ON/OFF (40.608 / 40.412 / 40.184 ms p50, overhead +0.04 %) and a passive H-M1
> series — see the H-E1c section below and
> [evidence/horizon-e1c-abc-2026-10-30](../evidence/horizon-e1c-abc-2026-10-30/README.md).
> `ReportCounter` still blocks (8.48 ms wall / 0.20 ms CPU per frame) in the matched scene; the
> single next experiment is H-P1, naming that wait.

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

## H-P1 — attribute the actual wait — **NARROWED, not closed**

The wait is inside `ReportCounter` (wall ≫ CPU). What is not proven: which owner (GPU fence vs driver
submit) and whether it is per-counter or amortized. Needs a named fence/owner trace, not another
per-op timer.

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

Current state: heavy-scene frame ~42–43 ms. The H-E1b data localizes ~10.1 ms in `ReportCounter`
wait and ~5.5 ms in `DrawArrays` CPU; no change has been shown to move the critical path yet.

## Async gate correctness — **FIXED**

`WOL_ASYNC_ACK` now requires the exact value `"1"`; previously `0`, empty or any non-empty value
bypassed the fail-closed guard (`0593c9e`). Async remains default OFF.

## Recommended single next step (superseded by later audit)

**Now H-E1c first**, to repair the first-op rollover and measure the actual ~43 ms heavy gameplay scene. **Only if confirmed there**, H-P1 should name the exact ReportCounter wait and causal owner. The 10.1 ms class span alone does not prove a GPU fence.

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

