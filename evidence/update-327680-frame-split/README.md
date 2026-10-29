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
