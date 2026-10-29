# ZERO_RENDER_SCALE=2 engages on v327680 (no code change)

Run `zrs2-a1` on candidate `0a0e6445…`, 122 s, fresh boot, CMA 119 964 kB at
launch, `T2_MEMORY_FLOOR_MIB=16`.

## What the runtime reports

```
ZERO_RENDER_SCALE_WINDOW colors=3 logical=1920x1080 storage=640x360 output=1280x720 native-crop=preserved
WOL_PRESENT_SRC frame=0 ... src=1920x1080 backbuffer=1280x720 crop=0,0,1280,720 half=0 scaled=1 draws=1
```

So the existing storage-scale path accepts this title's window family: three
colour images keep the guest's logical 1920x1080 but are backed by smaller
storage and presented with `scaled=1`. Before this, the same line read
`scaled=0` and the presenter cropped instead of scaling.

Two details worth knowing before trusting it:

- the window line reports `storage=640x360` (divisor 3), not the 1280x720 the
  mode-2 comment promises, so the effective scale factor is 9x per axis-pixel
  area, not 2.25x. That needs to be read from the code path, not assumed;
- `CmaFree` fell to 8-12 kB during startup with this profile, i.e. the run is on
  the edge of the CMA gate and needs a cold boot for a fair A/B.

## Still missing

No matched presents/s comparison yet: this run only proves the path engages and
presents scaled. The 25.5 presents/s baseline was measured without it, so a
control run on the same ELF and the same boot state is required before claiming
a speedup. Nothing here is an accepted optimisation.

Cleanup: `production_hashes_unchanged: 131`, `TIME_LIMIT` rc=22, no runtime
process afterwards.
