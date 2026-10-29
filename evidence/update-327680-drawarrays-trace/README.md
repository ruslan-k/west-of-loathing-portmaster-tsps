# The three expensive DrawArrays are seven-vertex passes into two targets

`WOL_DRAWARRAYS_TRACE=1` on the scripted gameplay baseline (ELF `332b741a`):

```
WOL_DRAWARRAYS target=1280x720  prog=0/0 count=7 first=0 frame=1930
WOL_DRAWARRAYS target=1280x720  prog=0/0 count=7 first=0 frame=1930
WOL_DRAWARRAYS target=1920x1080 prog=0/0 count=7 first=0 frame=1930
(repeated every frame; frame 1921: elapsed 42.1 ms, replay 25.9)
```

- **Seven vertices.** The geometry is trivial, so the 2.28 ms per call measured in the op profile
  cannot be vertex work. What it is, is a pass into a different render target - twice into the
  1280x720 backbuffer and once into a 1920x1080 surface - every frame.
- The 1920x1080 target is the same intermediate that the earlier 720p work kept running into. It is
  drawn once per frame here, through the cheapest possible geometry, and still costs milliseconds.

## What this changes

The remaining 9.8 ms was split between the counter pair and these three calls. The three calls are
now known to be *target switches with 7 vertices each*, not a heavy scene pass, so the lever is
either fewer switches or a cheaper 1920x1080 surface - and both are renderer changes, not flags.

`prog=0/0` in the trace means the program identity was not populated at that point; that is a gap in
the trace, not evidence that no program is bound.
