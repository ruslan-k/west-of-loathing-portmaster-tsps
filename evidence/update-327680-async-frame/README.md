# `COTM_ASYNC_FRAME=1` refuses this title, and says why

The one switch that would overlap the guest's CPU work with the GPU is the async frame path. On the
scripted gameplay baseline it stops immediately:

```
STOP status=NVN_LC2_ASYNC_STAGE_PROGRAMS_UNQUALIFIED pc=main.text.seg+0x52c8f4
     query_memory_calls=0x83 tls_trap_reads=0x0
run status=20
```

The path is written against a qualified stage-program set - it validates the title's programs before
it will record and replay asynchronously. West of Loathing's programs are not in that set, so it
fails closed rather than producing a wrong picture. That is the correct behaviour, and it means the
overlap lever is **not** a flag here: it would need the title's program set qualified first, which is
a project of its own (the same class of work as the Momodora/Zero contract that was closed earlier).

So of the two candidates left on the gameplay baseline:

- the counter pair (6.79 ms) - still unexplained, still worth one instrumented run;
- the three `DrawArrays` calls (6.84 ms at 2.28 ms each) - the largest per-call cost, most likely
  full-screen passes.

The overlap route is now explicitly off the table without qualification work, so the 9.8 ms has to
come from those two.
