# Async frame, first real attempt on WoL (E1 follow-up, option 1)

`COTM_ASYNC_FRAME` was hard-refused for every title except the `ANIMAL_WELL_SHADERS` build, so the
snapshot machinery had never actually run on WoL. The gate now requires explicit `WOL_ASYNC_ACK=1`;
without that env the old fail-closed behaviour is unchanged (same stop, same message).

Async also needs the GL worker: `COTM_GL_THREAD=1`. Without it `nvn_async_frame_enabled()` returns 0
and nothing happens - an earlier run (`async2`) was silently a plain control for exactly that reason.

Full set: `COTM_GL_THREAD=1 COTM_ASYNC_FRAME=1 WOL_ASYNC_ACK=1`, ELF `a49d40b4`, scripted input.

## Result

```
STOP status=NVN_PROGRAM_INVALID pc=main.text.seg+0x532994 detail=0x0 query_memory_calls=0xa4
```

It stops on the guest program path, not on a snapshot miss. So the first qualification gap for WoL is
not "a guest read was not captured" but "a program object is not valid on the asynchronous path".
Nothing was rendered asynchronously; the run ended where the gate said it would.

## What this means for option 1

Qualification is a real project, not a flag: the snapshot/worker contract has to be extended to
whatever `main.text.seg+0x532994` expects (program validity across the worker thread). One stop site
is identified and reproducible, which is the required starting point.

No performance number is claimed from this run - it never completed a frame asynchronously.
`production_hashes_unchanged: 131`.

## Reading the stop site

`NVN_PROGRAM_INVALID` is raised only by `nvn_program_find()` (`native/nvn_shaders.h:47`): the object a
draw names is not in the live `nvn_programs[256]` table. On the synchronous path that table and the
draw are on the same thread, so a lookup can only fail if the title is genuinely wrong.

With `COTM_GL_THREAD=1` the replay runs on the worker from a snapshot of frame N while the guest thread
keeps running frame N+1. The guest is then free to destroy or relink a program that the snapshot still
references, and the worker's lookup fails. So the first qualification requirement is not "capture more
guest bytes" but **program lifetime**: every program a snapshot's draws name has to stay valid until
that snapshot completes.

Minimal shape of the fix (not implemented): a pin count on `struct nvn_program`, incremented when a
snapshot records a draw that names it and decremented when that snapshot completes; the program destroy
path defers recycling a pinned program. That is a lifetime contract change in the shader table, not a
flag, and it needs its own A/B once it exists.

Until then, `COTM_ASYNC_FRAME=1` on WoL stops at the first draw after the guest recycles a program.
