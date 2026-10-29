## Hypotheses: which subsystem is most likely responsible?

My provisional ranking is:

1. **Diagnostic overhead plus CPU-side work or blocking** — most plausible explanation of the extreme 4.61 FPS result.
2. **GPU synchronization, memory traffic and GL driver work** — credible, particularly with heavy texture uploads and memory pressure.
3. **The final 1080p-to-720p present pass itself** — possible, but currently the weakest explanation for ~217 ms/frame.

This is a prioritization for measurement, not an attribution of milliseconds.

The older repository profiling found substantial GPU completion waits, including an immediate-copy experiment that increased finish time from 12.63 to 25.94 ms. That is useful evidence that synchronization matters in this runtime, **not** evidence that the updated title screen has the same bottleneck.

## One reversible experiment first: release-mode frame-phase ledger

Do not change image dimensions, texture identities, NVN commands, rendering paths or synchronization.

Use one isolated release-equivalent candidate with a small opt-in timing probe, `WOL_PHASE64=1`. Keep `WOL_PRESENT_TRACE=1` for the already-implemented release-visible frame ticks.

<box gap={2}>
  <text color="secondary" weight="medium" size="xs">Measurement boundaries for one frame</text>
  <box border radius="lg" padding={3} gap={2}>
    <grid columns={2} gap={2}>
      {#each [
        ["1","Guest / submit interval","Previous present exit → next present entry"],
        ["2","Replay and waits","Existing NVN replay, finish, fence and context-handoff spans"],
        ["3","Present CPU work","Quad submission and texture binding"],
        ["4","Swap and scanout","Swap call, completion and return"]
      ] as item}
        <grid-item>
          <box background="surface-secondary" radius="md" padding={2} gap={1}>
            <row align="center" gap={2}>
              <box background="surface-tertiary" radius="sm" padding={1}>
                <text weight="medium" size="xs">{item[0]}</text>
              </box>
              **{item[1]}**
            </row>
            <text color="secondary" size="xs">{item[2]}</text>
          </box>
        </grid-item>
      {/each}
    </grid>
    <divider color="subtle"/>
    <row align="center" gap={2}>
      <icon name="timer" color="secondary"/>
      <text size="sm">Record wall-clock and CPU time at each relevant boundary. Accumulate in memory; emit one summary per 64 presents.</text>
    </row>
    <row align="center" gap={2}>
      <icon name="cpu" color="secondary"/>
      <text size="sm">Add asynchronous GPU time for the present quad only if `GL_EXT_disjoint_timer_query` is supported.</text>
    </row>
  </box>
</box>

Reuse the existing `NVN_PROFILE`, `NVN_PROFILE_DETAIL`, `NVN_PROFILE_REPLAY_CPU` and phase counters rather than creating another profiling subsystem. Their current output is mostly suppressed by `AW_RELEASE=1`, so introduce a narrowly scoped, release-visible summary.

Use `CLOCK_MONOTONIC` for elapsed wall time and `CLOCK_THREAD_CPUTIME_ID` for CPU execution time. Also record process-wide CPU deltas, because guest work may span multiple threads. Include TIDs so thread-clock readings are never inadvertently compared across different threads.

A useful output record would be:

```text
WOL_PHASE64 frames=64
  frame_wall_ms=...
  process_cpu_ms=...
  guest_interval_wall_ms=...
  guest_interval_cpu_ms=...
  replay_wall_ms=...
  replay_cpu_ms=...
  finish_wait_ms=...
  present_wall_ms=...
  present_cpu_ms=...
  swap_wall_ms=...
  gpu_present_ms=...|unsupported
  major_faults=...
  voluntary_switches=...
```

`guest_interval` is a scheduling interval, not automatically pure IL2CPP time. Likewise, `finish_wait_ms` is CPU-observed blocking time and may include completion of earlier GPU commands. Do not add asynchronous GPU time to CPU wall phases as though the intervals cannot overlap.

For GPU timing, poll completed queries several frames later; never block waiting for the result. A timer query is specifically designed to obtain GPU execution duration without forcing pipeline synchronization. <Cite ref="turn985589search0"/>

**Do not introduce `glFinish()` for this measurement.** The repository already records a pathological 240 ms/frame case involving forced completion. Introducing that synchronization could manufacture the bottleneck being investigated.

### Execution and numerical acceptance criteria

<list marker="number" gap={2}>
  <list-item>
    **Build a single opt-in candidate.** Use `AW_RELEASE=1`, unchanged rendering and `WOL_PHASE64` default-off. Confirm the new timing probe adds no GPU synchronization and no per-frame text output. A valid result must have 64-frame wall accounting consistent with the monotonic frame ticks to within roughly 5%.
  </list-item>
  <list-item>
    **Run a matched off/on/off diagnostic comparison**, changing only `WOL_PHASE64`. Keep the same ELF, title state, frequencies, thermal conditions and memory guards. Preserve the 65,536 KiB CMA preflight. Avoid full tracing, readback probes and frame dumps. Capture an independent KMS image to prove visible output. The timing probe should change throughput by less than approximately 5%; otherwise its attribution is too intrusive.
  </list-item>
  <list-item>
    **Identify the dominant critical-path span.** For the 4.61 FPS diagnostic rate, a subsystem would need to explain more than ~108 ms/frame to account for a majority of the interval. Apply this classification to the newly measured release rate, not the old 4.61 value. If the present phase takes under 3 ms/frame, reject swapchain resizing as the next FPS intervention. If it consumes at least 6 ms/frame on the critical path, it becomes worth investigating for the 25.5-to-30 scenario.
  </list-item>
  <list-item>
    **Only if present is demonstrably expensive, investigate its producer/storage handoff.** First establish the actual source of the window image contents and the required memory aliases. A valid 720p experiment must preserve source-to-present image identity and visible pixels. Require `actual=1280x720`, a nonblack capture matching the expected scene, and no invalid GPU operations. Then compare frame time and memory using the same release ELF and scene.
  </list-item>
</list>

This is one profiling experiment followed by a conditional decision—not permission to start modifying the swapchain immediately.

## CPU-bound IL2CPP or GPU-stall-bound?

The best discriminator is a **scheduler-aware on-CPU/off-CPU profile, attributed to program-counter ranges**, during the measured slow frames.

Use an external `perf` sampling run if the target kernel supports the necessary events and stack capture. Correlate it with the frame-phase ledger.

| Observed result | Interpretation |
|---|---|
| Guest thread CPU time ≥80% of elapsed time, with most on-CPU samples in `main.text.seg` | Strong evidence for guest IL2CPP execution being CPU-bound |
| High CPU time, samples primarily in `libmali` or host NVN code | CPU-side graphics driver or translation bottleneck, not guest IL2CPP |
| Low CPU time, large fence/GL completion waits, backed by GPU timing | Strong evidence for GPU-bound stalls |
| Low CPU time, major faults or storage waits dominant | Memory/swap or I/O bottleneck, not proven GPU-bound |
| Low CPU time, mostly futex/context waits without corresponding GPU activity | Scheduling/contention bottleneck remains possible |

The CPU-time/wall-time ratio is the first number to inspect, but **the ratio alone does not prove GPU stalls**. A blocked thread could be waiting on a mutex, page fault, I/O, another guest thread or display pacing.

If GPU timer queries are unavailable and no trustworthy GPU activity trace exists, GPU execution versus driver-side waits may remain unresolved. Report that uncertainty rather than treating `eglSwapBuffers()` duration as GPU rendering time.

## Should you resize the three swapchain images?

**Not yet.** This is a different operation from reducing an internal render target.

Assuming RGBA8 colours and a 32-bit depth/stencil surface, the approximate allocation sizes are:

| Surfaces | 1080p | 720p | Potential reduction |
|---|---:|---:|---:|
| Three colour images | 23.73 MiB | 10.55 MiB | 13.18 MiB |
| One depth image | 7.91 MiB | 3.52 MiB | 4.39 MiB |
| Total | 31.64 MiB | 14.06 MiB | **17.58 MiB** |

These are nominal storage calculations, not measured driver-committed memory. Alignment, intermediate copies and aliases may change the real saving.

Against ~582 MB of unique physical footprint, this is useful but not transformational.

More importantly, `target-seen=0` means the window images are not established as the actual render targets. The guest may be rendering into another image and transferring or copying its contents into the present source. Resizing only the destination without understanding that producer is exactly the kind of contract violation that can produce valid frames containing black pixels.

A correct 720p handoff is technically possible in principle. It would need to account for guest-visible pitches, dimensions, offset calculations, copy/resolve semantics, texture aliases and depth relationships where relevant. **It is not a low-risk allocation-only patch.**

## Three mistakes most likely to derail this effort

1. **Treating measurements from different execution regimes as directly comparable.** The difference between 4.61 diagnostic FPS and historical 25.5 release FPS is too large to ignore, but neither proves the other is wrong. Establish the current release-equivalent rate before optimizing against either figure.

2. **Treating a valid present count as a valid rendered frame.** The 6.07 FPS black-screen run demonstrated that faster submission can mean less useful work. Every performance comparison must retain a visible-output correctness check.

3. **Assuming that 1080p allocations imply 1080p shading cost, and that reducing their storage is sufficient.** The true owner, producer and lifetime of the surface matter more than its descriptor dimensions. A seemingly small optimization can disconnect the entire render graph.

---

## Final decision

<text weight="medium">The next action is a release-mode phase ledger, not a swapchain patch.</text>

The actual target depends on what the new baseline shows:

- From 4.61 FPS to 30 FPS requires reducing frame time from ~217 ms to 33.33 ms—an approximately 85% reduction.
- From 25.5 FPS to 30 FPS requires only ~5.9 ms/frame—potentially achievable through one targeted bottleneck.

**The single result that changes the plan is a trustworthy, release-mode critical-path breakdown.** If present costs 2 ms, stop investigating swapchain dimensions for FPS. If it costs 10–15 ms and substantially delays completion, investigate the producer and the handoff. If guest IL2CPP dominates, changing surface storage is unlikely to solve the primary problem.

Until those numbers exist, claiming that the 1080p swapchain is the path to 30 FPS would be speculation.
