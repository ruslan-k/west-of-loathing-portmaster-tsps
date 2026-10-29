# Frame ticks: first measurable A/B, and it is not finished

Candidate `98681698…` (2 007 000 B) adds one diagnostic: `WOL_PRESENT_TICK n=<frames>
t=<CLOCK_MONOTONIC ns>` every 64 presents, printed only when `WOL_PRESENT_TRACE=1`
(default off). No other behaviour changed.

## Run ticks-ctl (no scale) — INVALID as a baseline

```
n=64  t=136.93 s
n=128 t=140.91 s
n=192 t=143.22 s
n=256 t=152.69 s
WOL_RUNTIME_EXIT status=26   (T2_MEMORY_FLOOR, elapsed 50.6 s)
```

The control died at 50.6 s on the memory floor, so its frame count covers a
different phase of the run. 256 frames over 50.6 s = 5.1 f/s average, with the
last window at 12.2 f/s. Not comparable to anything.

## Run ticks-zrs2 (`ZERO_RENDER_SCALE=2`)

```
n=64  t=137.61 s
n=704 t=227.14 s
WOL_RUNTIME_EXIT status=22   (TIME_LIMIT, elapsed 122.2 s)
```

704 frames over 122.2 s = 5.8 f/s average; last window (64 -> 704) = 7.15 f/s.

## What this does and does not show

- The tick counter works and gives real frames/s; before it there was no
  per-frame line anywhere in the log (checked by frequency: SVC 18 815,
  HID_RUMBLE_OUTPUT 10 847, nothing frame-shaped).
- With the scale on, the same binary survives the full 122 s where the control
  hit the memory floor at 50 s, i.e. the smaller storage also lowers the memory
  footprint. That is a real, measured difference in behaviour.
- It does NOT show a frame-rate win: the control is truncated, and both runs sit
  far below the 25.5 f/s figure recorded earlier, which came from a different
  measurement path. Do not quote 7 f/s as this title's performance.

## Next

A fair control needs the same 122 s of life: either `AW_RELEASE=1` (no
diagnostic cost) or a higher diagnostic floor, then re-run both arms and compare
the last window of ticks. Until then the scale's speed effect is unknown.

Cleanup: `production_hashes_unchanged: 131` in both runs, no runtime process,
two reboots with a full run between them.
