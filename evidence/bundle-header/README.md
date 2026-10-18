# Launch-bundle buffer identity and the first live stall capture

## Header probe: the 144 MiB read is a recycled managed Byte[]

`tools/wol_bundle_header_probe.py` is a bounded read-only observer for the
nonce-labelled, hash-pinned runtime. It reads at most 64 bytes per access from
mapped ranges of `/proc/<pid>/mem`; it never reads payload, never writes, never
walks GC roots and never calls ptrace. The `bundlehdr-b1` run (same ELF
`273b4638…`, same section/save, 720-first-level ON, `WOL_ROMFS_LIFETIME=1`,
`WOL_ALLOC_TRACE=1`) confirms:

- At read time the `ROMFS_READ` target address carries a consistent
  `System.Byte[]` header as an `Il2CppArray` prefix: `length = 144,392,040`
  equals the observed read (`byte_array_header_consistent: true`).
- At +10 s and +60 s the **same address** holds a different `System.Byte[]`
  of `11,633,735` bytes on the same class pointer. The launch bundle array was
  collected and its storage recycled inside the managed heap; the pages were
  not returned to the OS. That matches the observed mismatch between the
  ~136.9 MiB read and the ~60 MiB anonymous drop in the earlier phase diff.
- The native flow is `AssetBundle.LoadFromMemoryAsync(byte[])` over
  `nn::fs::File::Read(handle, offset, byte[], size)`; parameter maps are in
  `AssetBundleManager-map.json` and `AssetBundle-map.json`. Metadata/native
  identity alone does not prove GC reachability, pin lifetime, or safety of any
  free — the header probe only shows the header at three wall-clock moments.

**Consequence:** "release the launch buffer" is closed as a reclamation lever.
The buffer is released; its storage is reused. Any memory work must target the
live/steady working set, not this transient.

## First live stall capture (watchdog + owned diagnostics)

During this run the opt-in present-progress watchdog fired at the first long
gap after `continue-load` (frame 2001, gap 5.6 s against a 5 s budget; 27
checks passed). On the stall the probe recorded owned-PID/start-time-verified
proc/thread diagnostics and a bounded suggestively-safe `gdb` backtrace before
normal cleanup; the run then completed with clean save restoration and visible
Spruce.

What the capture actually shows (facts):

- The aborting screen was near-black (mean luma 7.48 of 255; title.png and
  world.png are the same frame), consistent with a heavy scene load still in
  its black phase.
- The process was **actively loading, not deadlocked**: `T2_MEMWATCH_SAMPLE`
  grows RSS 478 → 716 MiB (VmSwap 527 → 366 MiB in swap, MemAvailable
  251 → 91 MiB) across the stalled window; thread census shows the main thread
  running in `futex_wake`, 28 guest workers in `futex_wait_queue_me`, and all
  Mali/SDL threads in normal poll/sleep states.
- Neither permanence nor a root cause is established: the watchdog aborted the
  first long gap, so this could have been an unusually long load (the earlier
  upscope pair shows the same route completing when memory pressure is lower).

The earlier `upowner-a2` freeze (no extra tracing, 1080, gulch already visible)
remains the only extended freeze; its cause is still unknown. This run cannot
attribute either event to any flag: heavy lifetime tracing plus the 720 setting
were enabled, but A2 had neither.

## Budget guidance

A 5 s present-progress budget is only for steady gameplay windows. Around
scene loads under memory pressure, use 20–30 s before declaring a stall;
otherwise the watchdog cuts a legitimately slow load and hides whether it would
recover. The gate remains opt-in; healthy runs in `evidence/uprender-scope/`
passed 87 checks with the same ELF and no stall branch.

## Artifacts

`summary.json` joins the header timeline, stall memory samples, frame tail,
thread state census and cleanup receipt. Raw captures live under
`bundlehdr-b1/` (receipt, env, ledger, compressed log, `stall/` diagnostics,
two verified PNGs). No owner metadata, code, payload or private save is
published. Everything behavioural is still default OFF; no swap or DVFS policy
was changed.
