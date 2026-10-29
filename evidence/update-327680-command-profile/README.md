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

## Screen check (run `shot-a7`, same ELF)

```
kmsgrab 1280x720: centre pixel (198,198,198), 440 distinct colours,
mean 100/100/100, stddev 99.2
```

Not black, not a flat fill: a real high-contrast frame is on the panel while the
counters above are being produced. What I have **not** confirmed is whether the
image is the game's title or the SpruceOS menu - that needs a human eye or a
comparison against a known game capture, and the numbers alone cannot tell the two
apart.

Resolution of the "menu or game?" doubt: the harness sampled the process table at 55.4 s of
run `shot-a7` and `wol-horizon` was alive (`(8979, 'wol-horizon')`); it was gone by 76.7 s
(`rc=22` time limit, MainUI back). The capture was taken at ~50 s, inside that window, so the
440-colour frame belongs to the runtime, not to the SpruceOS menu. Screen identity as the
title versus an early in-game frame is still unconfirmed.

## Stability and the scene-content confound (run `stab-a1`)

Eight consecutive profile windows of the same release build:

```
frame=1081 39.567 ms   frame=1201 39.772   frame=1321 40.422   frame=1441 40.165
frame=1141 41.115 ms   frame=1261 39.904   frame=1381 40.389   frame=1501 39.759
replay 24.2-24.8 ms, present 1.66-1.80 ms
```

- **~40 ms -> ~25 frames/s, and it is stable**, not the 29.1 ms of `split-a6`. That single fast
  window is an outlier and must not be quoted as the frame rate.
- The confound is scene content: `split-a6` reported `draws-mean=7.00` per command list, this run
  reports `draws-mean=61.8`. The fast window was a *lighter scene*, not a faster runtime. Any
  claim about fps has to name what was on screen.
- `ordinal=1` here: `wall-ms=8.42` on `cpu-ms=0.141` across 60 sample sets - the same shape as
  before. Roughly **8 ms of wall time spent waiting with ~0.1 ms of CPU** inside the draw list.

## Where that leaves the 30 fps target

Frame 40 ms, target 33.3 ms, gap ~6.7 ms. The serialized wait inside the draw list is 8.0-8.4 ms.
Overlapping it with the guest's next frame is arithmetically enough to reach ~31-32 ms, i.e. just
over 30 frames/s - and it is the only measured block of the right size.
