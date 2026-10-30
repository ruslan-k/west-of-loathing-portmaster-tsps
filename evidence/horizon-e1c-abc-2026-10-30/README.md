# Horizon §25 H-E1c — matched fresh-boot OFF/ON/OFF on identical gameplay

**Date:** 2026-10-30 · **Runtime ELF:** `f5c6f6f2f6c87c3c1c0308c62ef070a39d3c8b60c41b1071c03a9230fbed75d3`
(update v327680 native Horizon adapter, WOL_OP_V3 default OFF) · **Device:** Longan, 963 MiB RAM.
**Production Unity/Mono port, saves and config untouched.**

## Question

Roadmap §25.6: does the `ReportCounter` off-CPU span seen in E1b recur in the same real gameplay,
with frame ownership repaired, and what is the instrumentation overhead? E1b's frame rollover was
buggy (§25.2), so its numbers could not be joined to a displayed frame.

## Procedure

Three arms, **one fresh boot each** (the 65,536 KiB CMA admission gate is not a reservation; it
recovers only on reboot):

```
c1-off (boot bf8a329a) → c2-on (boot 1310723f) → c3-off (boot 8ce2c2f7)
```

Each arm: real Spruce principal handoff (`/tmp/cmd_to_run.sh`, MainUI TERM) → 240 s bounded run →
`WOL_SCRIPT_INPUT='20000:250:0x1,60000:150000:0x4000'` (one A press; hold right 60–210 s, the
scripted walk that reaches movement) → KMS captures at 5/100/180/240 s → watchdog exit → menu
restored → production hashes re-checked (131 files unchanged) → CPU online bits/modes restored.
CMA preflight passed on every arm: 128 228 / 130 412 / 130 404 kB free (gate 65 536).

## Result — frame time (NVN_PROFILE 60-frame windows, frames ≥1200)

| Arm | V3 | windows | p50 ms | p95 ms | min–max | replay p50 |
|---|---|---|---:|---:|---|---:|
| c1-off | off | 43 | **40.608** | 41.855 | 39.519–42.520 | 24.683 |
| c2-on | **on** | 46 | **40.412** | 41.353 | 39.579–41.986 | 24.805 |
| c3-off | off | 47 | **40.184** | 41.391 | 39.356–42.832 | 24.395 |

Overhead of the V3 ledger: **+0.016 ms (+0.04 %) against the mean of the two OFF arms**
(40.412 vs 40.396) — far inside the ≤5 % gate. The three arms are one scene: cross-arm pixel MAD at
180 s / 240 s (5.3–6.2 grey levels on a 160×90 signature) is the same magnitude as within-arm
180→240 s motion (4.5–5.4), and replay stays 24.4–24.8 ms.

This band is **40.2–40.6 ms (~24.6–24.9 fps)**, not the historical 42.1–43.1 ms of ELF `332b741a`.
Different ELF and scene receipt: this is a **different baseline**, not a speed change.

## Result — V3 per-class ledger (c2-on, 2 772 complete frames, frames ≥1200)

| Class | calls/frame | sum wall ms | sum CPU ms | wall/call | CPU/call |
|---|---:|---:|---:|---:|---:|
| `DrawArrays` | 3 | **7.264** | **6.047** | 2.42 | 2.02 |
| `ReportCounter` | 2 | **8.482** | **0.198** | 4.24 | 0.099 |

Accounted wall: **15.84 ms median = 39.2 % of the 40.4 ms frame** (p95 16.72 ms, max 18.79 ms);
invariants hold for all 5 544 rows: one row per (frame, tid, class),
frames strictly increasing, `mean×n = sum`; a single worker thread emitted every row.

Two separable facts:

1. **`ReportCounter` is still a block, not work** — 8.48 ms wall at 0.20 ms CPU per frame. It
   recurs in the matched heavy scene, so the §25.6 falsification test did **not** falsify it.
   Its owner (GPU fence, driver backpressure, futex, page fault) is still **unnamed**; H-P1 is the
   next branch.
2. **`DrawArrays` is real CPU work** — 6.05 ms of thread CPU for three 7-vertex passes, ~2 ms each.
   This is a handler-level target independent of the wait.

Historical receipt for comparison (ELF `332b741a`, 42.1–43.1 ms): DrawArrays 6.84 ms,
ReportCounter 6.79 ms. The per-class split is the same shape; the absolute values belong to this ELF.

## Memory series (H-M1, passive host sampling, same runs)

| Arm | pre `CmaFree` kB | gameplay `CmaFree` kB | PSS MiB (start→play) | SwapPss MiB | VmSwap MiB |
|---|---:|---:|---|---:|---:|
| c1-off | 130 192 | 0.3–1.0 k | 640 → 392 | 930 | 931 |
| c2-on | 130 300 | 0.4–1.9 k | 641 → 400 | 926 | 926 |
| c3-off | 130 328 | 1.9 k | 612 → 395 | 922 | 923 |

`CmaFree` collapses to ~0 during gameplay in **every** arm and recovers to ~117–130 MB only after
the runtime exits. Guest `VmSwap` reaches ~0.92 GB of the 963 MiB device. This confirms §25.3 as a
hard wall for any additional async frame, pinned shader lifetime or extra render target; it is a
system-level series, not per-object attribution.

## Verdict

- **H-E1c closed**: frame ownership is repaired, ledger overhead is 0.04 %, and the matched-scene
  data is valid for per-op conclusions. The terminal partial bucket is still not flushed by the
  emitter (one frame at most); statistics use completed frames only.
- **H-M1 done as passive accompaniment**: CMA/SwapPss/swap-I/O series exist for all three arms.
- **H-P1 becomes the single next experiment**: name the existing wait inside `ReportCounter`
  (8.48 ms wall per frame) and prove whether deferring it is legal before touching any renderer path.
- No 30 FPS claim: gap from 40.4 ms to 33.333 ms is 7.1 ms (17.6 %) and no change has moved the
  critical path yet.

## Limits / threats to validity

- One worker thread; multi-thread bucket ordering untested on device (synthetic tests only).
- Arms are sequential fresh boots, not interleaved; die temperature/devfreq was not recorded.
- The c1-off 100 s capture is black while c2-on/c3-off are bright; 180 s and 240 s match in all arms.
  A single transition frame is the likely cause, but it is not proven.
- Diagnostic runtime only: no audio, save/cold-reload, menu or controller acceptance is claimed.
- Raw logs: `c1-off.log.xz`, `c2-on.log.xz`, `c3-off.log.xz`; analysis:
  `tools/wol_op_v3_ledger.py --from-frame 1200 <logs>`; tests: `tools/test_wol_op_v3_ledger.py`.
