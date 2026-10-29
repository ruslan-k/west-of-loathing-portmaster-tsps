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

## Where inside the call the 8.5 ms must be

The handler itself is a 16-byte store (`nvn_async_frame.h:191`): `{0, now}` written through
`nvn_gpu_pointer(a[1],16,PROT_WRITE)`. That cannot cost 8.5 ms, so the time is in what the pointer
path does underneath it:

- `nvn_gpu_pointer` (`nvn_replay.h:46`) walks the 257-slot pool table and calls
  `zero_texture_require_cpu(p, offset, size)` on every hit - the CPU-coherence hook that makes a
  guest buffer readable/writable on the host side.
- A counter buffer the guest polls every frame is exactly the kind of buffer whose coherence path
  ends in a GPU sync.

So the next measurement is not another profile of the whole frame: it is a counter inside
`zero_texture_require_cpu` (how many calls actually sync, and how many ns they take), plus the
identity of the pool that `a[1]` falls into. If that sync is the cost, the fix is to keep the
counter buffer permanently CPU-coherent instead of re-establishing it twice per frame - and it is
then a contained change, not a renderer rewrite.

## Correction: the coherence hook is not the cost

The hypothesis above is wrong, and cheaply so. `zero_texture_require_cpu` (`nvn_textures.h:166`)
returns on its second line for this title: it only proceeds when `pool->zero_r8_target_seen` is set
or the ZERO contract is active (`zero_render_scale_enabled() && pool->flags==0xa4`). West of
Loathing has neither, so the call the previous section blamed is a no-op.

Second, the replay's own handler for `NI_nvnCommandBufferReportCounter` is a `break`
(`nvn_commands.h:168`): a sixteen-byte store, nothing that can take 8.5 ms.

Which leaves the uncomfortable explanation: the per-op figure is *elapsed since the previous op*,
so whatever waits between the two calls - a GPU drain, a fence, a batch flush - is charged to the
counter because that is where the clock stands still. The counter is the *place* the frame pauses,
not necessarily the *reason*.

## What the next probe has to separate

1. Time the ReportCounter handler on its own clock, inside the case, not via the op ledger.
2. Count `nvn_gl_finish_current()` / `glFlush` calls between ops, and whether one lands between the
   two counters.
3. If the drain is real, the answer is the same as before but for a different reason: the frame is
   serialized around a wait, and the fix is to overlap it - not to touch the counter.
