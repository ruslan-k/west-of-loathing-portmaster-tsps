# The 10 ms GPU wait inside the seven-draw list

Release run `split-a6`, ELF `bac9126f`, `AW_RELEASE=1 NVN_PROFILE=1`:

```
NVN_PROFILE frame=421 count=60 elapsed-ms=29.092 replay-ms=21.294 present-ms=1.747 readback-ms=0.000
NVN_COUNTER_PROFILE frame=421 ordinal=0 calls=60 wall-ms=0.107  cpu-ms=0.051 draws-mean=0.00 zero-draw-calls=60
NVN_COUNTER_PROFILE frame=421 ordinal=1 calls=60 wall-ms=9.973  cpu-ms=0.119 draws-mean=7.00 zero-draw-calls=0
```

## What this says

- Frame period in this run: **29.1 ms -> ~34 frames/s** (the 40 ms of run `split-a4` was a
  slower window; the spread across runs is 29-40 ms, so the honest statement is
  "25-34 f/s, not yet stable").
- The whole per-frame command list with the seven real draws costs **9.97 ms of wall time
  but only 0.12 ms of CPU**. A thread that burns 0.4% CPU while spending 10 ms of wall
  time is **waiting**, not working - that is the GPU (or the driver's fence) inside the
  draw list.
- Ordinal 0 is 60 calls of pure no-draw setup: 0.1 ms, harmless.

So of the ~21 ms of "replay", about **10 ms is a serialized GPU wait**, and roughly
19 ms is guest CPU. Frame time 29 ms ~ CPU 19 + GPU wait 10, running back to back.

## The lever this implies

If the GPU wait were overlapped with the guest's next frame instead of sat inside it,
the frame would be bounded by max(CPU ~19 ms, GPU ~10 ms) ~ **19-20 ms (~50 f/s)**.
That is the same conclusion the roadmap reaches from the other side (§18.6: narrow
fence/flush ordering, no blind `glFinish` removal, no async renderer rewrite) and the
same shape nx2android uses (bounded ticket queue between producer and GPU work).

Not attempted here: any change to fence/flush ordering. It requires pixel-coherence
and bounded-queue proof, and is exactly the class of change that produced regressions
before.

Caveat: this run's picture was not verified with `kmsgrab`; the counters are real, the
output is not.
