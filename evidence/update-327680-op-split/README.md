# E1 (roadmap §25.4): handler vs gap for the two costly op classes

`WOL_OP_SPLIT=1`, default OFF, ELF `9e55b5ec`, scripted input, 240 s.

Each line is one `DrawArrays` or `ReportCounter` as it passes through `nvn_replay_run_list()`:

- `handler` - `CLOCK_MONOTONIC` across `nvn_replay_record(&r)` alone;
- `gap` - wall time between the end of the previous such op and the start of this one (post + pre);
- `cpu` - `CLOCK_THREAD_CPUTIME_ID` across the same handler span.

First 64 ops of the run:

```
ops=64   handler sum 4.425 ms  mean 0.069  max 2.092
         gap     sum 9.654 ms  mean 0.151  max 2.849
         cpu     sum 2.883 ms  mean 0.045
ops with handler > 0.5 ms: 1  (n=2: handler 2.092, cpu 1.851, gap 0.056)
```

## What this does and does not show

- The handler is **not** routinely 2.28 ms. 63 of 64 sampled ops are sub-millisecond, and the single
  large one is real CPU (1.851 of 2.092 ms), consistent with first-use work rather than a per-call cost.
- The `6.84 ms / 3 calls` from the op ledger is therefore an **aggregate over expensive windows**, not
  a per-call price. Reading it as "2.28 ms each" was wrong.
- This sample is the **first 64 ops of the run**, i.e. early/title work, not the 71-73 draw gameplay
  window. It does not yet attribute the 6.8 ms seen at `frame=2041`.
- `gap` mean 0.151 ms is small, so between-op waiting is not dominant in this window either.

## Next

Repeat with the sampling window moved into gameplay (print a rolling aggregate per 64 ops for the
whole run instead of only the first 64), then compare against `NVN_PROFILE` at the same frame.
Until that exists, no renderer change is justified.

Run artifacts: `opsplit2-lines.txt` (device log extract). `production_hashes_unchanged: 131`.

## Second sample: rolling 64-op windows across the whole run (ELF `fa1b1b64`)

`opsplit2` only printed the first 64 ops; this run prints every 64, so late windows fall inside
gameplay. 31 windows:

```
late windows (n>=1500)  handler/64 median 3.234 ms   cpu/64 median 1.081 ms   gap/64 median 3.123 ms
per op                  handler 50.5 us              cpu 16.9 us
```

- The handler cost of `DrawArrays`/`ReportCounter` is **tens of microseconds**, and only ~17 us of it
  is thread CPU. Even at three such ops per frame that is ~0.15 ms, not 6.84 ms.
- The `DrawArrays 6.838 ms / 3 calls` figure in the op ledger is therefore dominated by the interval
  **between** ops (gap), not by work inside them - exactly the risk flagged in roadmap §25.2.
- `gap` is wildly variable (2.6 ms to 306 ms per 64 ops), i.e. the wait is bursty and lands on whichever
  op happens to follow it.

## Consequence

There is no handler-level CPU hotspot to optimise in these two classes. The remaining 9.8 ms is
submission/wait time, and the only legal levers there are synchronisation-overlap ones - which
`COTM_ASYNC_FRAME` currently refuses by design (`NVN_LC2_ASYNC_STAGE_PROGRAMS_UNQUALIFIED`).
No renderer change is justified by this evidence.
