# Where the frame time goes: CPU, not the blit

## Steady-state CPU share (run `cpu-share`, diagnostic build)

```
PID /proc/5851  cpu_pct_one_core=96.1
```

The runtime thread sits at ~96% of one core while presenting 4.6 frames/s. It is
CPU-bound, not waiting on the GPU: a stall-bound title would show a few tens of
percent with the rest idle.

## Release baseline (run `rel-a1`, `AW_RELEASE=1`)

```
WOL_PRESENT_TICK n=0    t=705.80 s  cpu_ms=0.000
WOL_PRESENT_TICK n=1024 t=822.15 s  cpu_ms=18.296
```

1024 frames over 116.35 s = **8.80 frames/s** on the title screen, with ~18 ms of
CPU inside the present call per frame.

So the diagnostic build's 4.61 f/s was roughly half logging cost, and the honest
release baseline for this update build is **~8.8 f/s**, not the 25.5 figure from an
older measurement path.

## What this rules out

- The 1080p-to-720p present blit: ~18 ms of a ~113 ms frame (16%), and it is CPU
  work that scales with the guest's 1080p surfaces, but it is not the frame.
- Swapchain resizing as a speed lever: with the thread pegged at 96% CPU, making
  the GPU do less cannot help.
- GPU frequency/thermal: the GPU is not the limiter, consistent with the earlier
  devfreq finding (150-600 MHz, never the bottleneck).

## What it points at

Reaching 30 f/s from 8.8 means ~3.5x less CPU work per frame. At 7 guest draws and
176 NVN commands per frame, the shim's per-call cost and the guest's own IL2CPP
execution are the only candidates of that size. That is a structural change, not a
flag, and it needs the phase ledger (guest submit vs replay vs present vs swap) to
be attributed honestly.

Cleanup: `production_hashes_unchanged: 131` in both runs, no runtime process left.

## Consult answer of record (share link, read 2026-10-29)

Borrow from nx2android, in this order:

1. **Resource identity and alias tracking** (`gfx_vk_tex.c`, `alias_link`/`alias_check`/`vk_tex`): identify an
   image by pool + offset + extent, not by handle; record overlapping writes and stale reads. Their strongest
   idea, and it targets exactly the unresolved question here - the 1080p window images have `target-seen=0`
   yet the unscaled title is visible, so their content arrives by a route the render-target counters do not see.
2. **GPU timing** (Vulkan timestamp queries there; GLES timer queries here) kept separate from CPU/wall time.
3. **Tile-based pass analysis** (`tbdr_*.py`): portable logic, but candidates only, never activation.
4. **Per-build NSO patching** (`patch_nso.py`): build-ID match, assert original bytes, observation hooks
   distinct from real patches.
5. Not to take: the Vulkan renderer, the BC upload path (their docs exclude Mali), async present (only if
   profiling shows CPU-side present blocking), ADPF hints, FPSLock, allocator region cuts.

Recommended first nx2android-derived experiment: a **read-only NVN image provenance probe** on the three
1080p window images - where do their pixels actually come from - not a memory optimisation.

Note against that answer's premise: it still assumes a release baseline near 25.5 f/s. Measured here on the
same update build, release mode gives **8.80 f/s** with the thread at **96% of one core**, so the missing
budget is CPU work, not GPU stalls; the provenance probe answers the black-screen question but not the 3.5x
CPU gap.
