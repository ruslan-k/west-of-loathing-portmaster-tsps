# The runtime is a third of the frame; the guest is the rest

Release run `split-a3` (`AW_RELEASE=1 NVN_PROFILE=1`), candidate `fa8c5567…`:

```
NVN_PROFILE_REPLAY_CPU frame=301 cpu-ms=10.650   (guest NVN replay + shim)
NVN_PROFILE_REPLAY_CPU frame=361 cpu-ms=10.964
WOL_PRESENT_TICK n=384 ... cpu_ms=21.767          (present call, thread CPU)
release baseline (rel-a1): 8.80 frames/s -> ~113 ms/frame
```

## The split

- shim replay: **~10.8 ms**
- present: **~21.8 ms**
- runtime total: **~32.6 ms**
- everything else (guest IL2CPP + waits): **~80 ms** of a ~113 ms frame

So the port's own code is about a third of the frame, and the single largest
runtime component is the **present path**, not the NVN shim - roughly twice the
shim's cost.

## What that means for 30 fps

30 fps is 33 ms per frame. Even reducing the runtime's entire 33 ms to zero would
leave ~80 ms of guest execution, i.e. **~12.5 frames/s**. The guest's own native
code needs more than 80 ms per frame at 720p on this core.

Consequence: 30 fps is **not reachable by runtime optimisation** on this hardware
for this update build. It would require cutting the work the guest does (scene,
draws, resolution) or a different build - both are product decisions, not flags.
What remains worth doing inside the runtime is the present path (22 ms), which is
worth ~2 f/s at best.

Cleanup: run finished on TIME_LIMIT, no runtime process, production untouched.

## Correction (same day): 22 ms of present is CPU time, not a vsync wait

I first read the 21.8 ms present as the documented Mali fbdev `eglSwapBuffers`
vsync wait (the runtime's own comment measures 16-33 ms for that). That reading is
wrong on its own terms: `cpu_ms` is `CLOCK_THREAD_CPUTIME_ID`, and a thread blocked
in a vsync wait accumulates **no** CPU time. A blocking swap would show up as wall
time with near-zero CPU.

So the present path genuinely burns ~22 ms of CPU per frame, which is more than the
whole NVN shim (10.8 ms). That is unusual for a full-screen blit and needs one more
receipt before any change: split the present call into its parts (crop/quad setup,
texture bind, draw, swap, fence) with the same thread-CPU clock, and print them in
release.

The guidance about `AW_FB_COPY` still stands as a separate question (it is compiled
only under `ANIMAL_WELL_SHADERS`), but it is not the explanation for these 22 ms and
must not be "fixed" on that assumption.

## Corrected split with release-visible phase lines (run `split-a4`, ELF `1803571a`)

```
NVN_PROFILE frame=601 count=60 elapsed-ms=40.699 replay-ms=24.270 present-ms=2.601 readback-ms=0.000
NVN_PROFILE_DETAIL frame=661 counter-ms=8.337 finish-ms=0.045 receipt-ms=0.000 swap-ms=1.360
```

- frame: **~40 ms** -> **~24.6 frames/s**, not 8.8
- replay (guest NVN dispatch + GL submission): **~24 ms** (60%)
- counters: **~8.3 ms**
- present: **~2.6 ms**, swap **~1.4 ms**, finish **0.045 ms**

Two earlier numbers in this folder are therefore wrong and are retracted:

1. **8.80 f/s baseline** - the tick average included the slow startup window and the
   tick counter starts at the first present; `elapsed-ms` from the phase line is the
   honest frame period. The old 25.5 f/s figure was closer to reality than my 8.8.
2. **"present burns 22 ms of CPU"** - that instrument read the thread CPU clock at
   the tick print, which happens once every 64 presents, so it measured whole-frame
   CPU, not the present call. Present is 2.6 ms.

What survives: the process is CPU-bound (~96% of one core), the guest's own replay
dominates, and the gap to 30 f/s is about **7 ms per frame** (40 -> 33.3), not 80.
