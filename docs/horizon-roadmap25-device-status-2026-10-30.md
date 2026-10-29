# Horizon roadmap §25 — item-by-item device status

**Date:** 2026-10-30 · **ELF:** `21e23b58c3e2fb01018c71ab10ad4b9a08029e85e9a8ad0118765c89d345d956` (w32)
**Run:** `e1b`, `WOL_OP_SPLIT=1` (default-OFF profiler), scripted input, 90 reported frames
**Production Unity port and saves untouched; probe tree only.**

## H-E1b — per-class op budgets with explicit units — **DONE (diagnostic success)**

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

## H-M0 — memory receipts — **DONE, and it is a wall**

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

## Recommended single next step

Trace the owner of the `ReportCounter` wait on one matched frame (H-P1): name the fence/driver call
and its caller, with wall + thread CPU at the call site. It is the only measured span of the right
size (~10 ms) and it is not CPU work, so it cannot be optimized away inside the handler.
