# Where the replay time actually goes, per NVN call

Run `opprof-a2`, release build `0bf76cca`, `COTM_REPLAY_PHASES=1` (the existing per-op ledger
in `nvn_queue.h`, now printed in release). Steady frame:

```
NVN_PROFILE frame=361 elapsed-ms=51.869 replay-ms=31.337 present-ms=1.772
NVN_REPLAY_OP nvnCommandBufferReportCounter     17.120 ms/frame  2.0 calls  8560 us/call
NVN_REPLAY_OP nvnCommandBufferDrawArrays         6.379           3.0         2126
NVN_REPLAY_OP nvnCommandBufferDownsample         4.293           3.0         1430
NVN_REPLAY_OP nvnCommandBufferCopyTextureToTexture 2.126         1.0         2126
NVN_REPLAY_OP nvnCommandBufferDrawElementsBaseVertex 0.466       4.0          116
NVN_REPLAY_OP nvnCommandBufferSetRenderTargets   0.332          15.0           22
```

## The dominant cost is a counter readback, not drawing

- `nvnCommandBufferReportCounter`: **8.56 ms per call, twice per frame = 17.1 ms**, i.e. more than
  half of the 31 ms replay and ~40% of the whole frame.
- Everything that draws the picture - `DrawElementsBaseVertex` (31 calls on the heavy frame),
  `DrawArrays`, `SetRenderTargets`, uniform binds - is in the 0.02-2 ms/call range by comparison.
- A slower loading frame (421) shows the same ranking with draws on top (31 calls at 1.9 ms each),
  so both the load spike and the steady frame are dominated by per-call synchronisation, not by
  the number of primitives.

## Why this matters for the 30 fps target

The gap to 33.3 ms was 6.7 ms, and a single call class holds 17 ms. If the counter value is not
consumed to drive gameplay (it is the title's own GPU-timing query), removing or deferring the
readback is worth three times the gap. That is the next thing to prove - by reading what the
guest does with the 16 bytes written back, not by guessing.

Caveat: this profile is from one run at 1280x720 on the update build; the frame timing here
(51.9 ms) includes the profiling overhead of the per-op ledger itself, so treat the *ranking* as
the result and the absolute ms as upper bounds.
