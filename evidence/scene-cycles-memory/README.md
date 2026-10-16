# Scene-cycle memory stability probe (2026-10-16)

Roadmap section 12 pre-check: "stable memory over extended scene cycles". Run `mvtC` on build
`dtime8` (device ELF `414efb1f…`, section `a25600ce…`, save `tut_gulch`) drives an in-scene loop
with the diagnostic input channel - each press ~4 s apart, screenshots at every step:

- `ZL` (0x100) toggles the guide/map: three open/close cycles (z1..z6),
- `Y` (0x4) twice, `X` (0x8) twice, `START` (0x400, pause menu) twice, `B`, `A`, back to the map.

Frame diffs confirm the loop really toggles screens: every `ZL` transition differs by ~109-110k
pixels, each `START` transition by ~210k, `Y`/`B`/`A` by 5-10k (hints/no structural change), `X`
by ~26k (a small panel).

## Samples

Host sampler `snap-gpumem.sh` (30 x 6 s) ran during the session; the game lived for samples
1..10 (60 s), so those carry the data:

| sample | GPU commit (MiB, mali0/ctx/*/mem_allocs) | PSS (kB) | SwapPss (kB) |
| --- | --- | --- | --- |
| 1 | 264.6 | 467020 | 459160 |
| 2 | 270.6 | 461395 | 464752 |
| 3 | 272.6 | 459847 | 466544 |
| 4 | 272.6 | 459959 | 466232 |
| 5 | 272.6 | 460527 | 465676 |
| 6 | 261.9 | 469235 | 459776 |
| 7 | 261.9 | 469299 | 457872 |
| 8 | 261.9 | 469399 | 457772 |
| 9 | 262.0 | 459803 | 467396 |
| 10 | 274.0 | 460011 | 467308 |

No trend in either series: GPU commit oscillates in a ~12 MiB band, PSS/SwapPss in a ~10 MB
band around PSS+SwapPss ~925 MB. The toggling itself does not grow memory on this window.

## Limitations

- 60 s window (about three full map toggles and one pause toggle); interior/battle/scene
  transitions are not in this loop yet.
- The swap gate itself (cold start with swap disabled, long cycles, save/load) remains for a
  dedicated session per roadmap section 12.
- PSS+SwapPss ~925 MB against ~963 MiB RAM is still the standing margin problem, unchanged by
  this probe.

## Files

- `mvtC/*.png` (spike tree): the step screenshots (`z*` maps, `p*` pause, `w0` street).
- `mvtC-cycles/`: the raw sampler series (gpumem-*.txt with Pss/SwapPss, memalloc-*-*.txt).
- Harness: `session.py press` sequence as above; labels `mvtC`, sampler label `mvtC-cycles`.
