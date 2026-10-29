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
