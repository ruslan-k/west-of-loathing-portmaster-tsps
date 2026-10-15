# FPS experiment: GPU region blit for the per-frame 1:1 texture copy (`WOL_COPY_GPU`)

Date: 2026-10-15. Runtime: `wol-horizon-build-copygpu`
SHA256 `fab0b9fe6cc7b91a63dddfa80d6dd2dfd330c9f620ec3f240f0f8980f324003e`.
**Experimental checkpoint, not a release.** Owner section stays `a25600ce...`.
Default for `WOL_COPY_GPU` is OFF — this experiment measured a **regression**.

## The measured chain that motivated it

The per-draw standard path is unused on this title; during gameplay the substituted path
handles drawing, and one specific NVN command runs **every frame**:
`nvnCommandBufferCopyTextureToTexture` - a 1:1 copy of `1280x720` (3.69 MB) from the window
render target into texture `id=460`. The runtime implemented it as a CPU row copy into the
destination's pool storage plus a dirty mark, and `zero_texture_refresh()` then re-uploaded the
whole texture (3.69 MB `memcpy` + `glTexSubImage2D`) before the next sampler. Attribution
counters (this build) measured it exactly:

- `WOL_COLOR_COPY_STATS dst=460 calls=2560 bytes=9437184000` — 9.44 GB copied in one run.
- `ZERO_REFRESH_STATS id=460 calls=2560 uploaded-bytes=9437184000` — the same 9.44 GB uploaded.
- In the AW_PROFILE sampling run the largest non-symbolized libc hotspot (a memcpy-class
  function) and the upload helpers sat at the top of the host-side profile.
- `ZERO_POOL_FLUSH_STATS` never fired: texture 460's dirty flag came from this copy alone.

## What was tried

`WOL_COPY_GPU=1` replaces the CPU copy with a GPU region blit (`wol_blit_region`, FBO +
explicit-UV shader pair, texel-centre alignment; `WOL_COPY_GPU_FLIP=1` available for the
orientation A/B). Preconditions: no pending CPU writes on either texture, otherwise the CPU
path runs. On success the destination is deliberately NOT marked CPU-dirty (the CPU mirror is
not re-synchronised), so the refresh/upload chain disappears.

## Result — correct picture, slower frames

| run | arm | menu presents/s | game presents/s | slow frames | last slow frame replay/finish ms |
|---|---|---:|---:|---:|---|
| m1m5-copyE1 | control (CPU copy) | **26.74** | **25.30** | 605 | 28.4 / 12.6 |
| m1m5-copyE2 | `WOL_COPY_GPU=1` | **21.51** | **24.12** | 1856 | 28.6 / 18.3 |

- The GPU path engaged and was verified in-run: `WOL_RBLIT_REALIZE ok=1`,
  four bounded `WOL_COPY_GPU blit` receipts, `ZERO_REFRESH_STATS id=460` = **0** (upload chain
  eliminated), no `WOL_BLIT_REGION_GLERROR`.
- The in-game frame (`m1m5-copyE2-resume.png`) is right-side up and coherent — the orientation
  matched the CPU semantics, so no flip was needed.
- Despite removing 9.4 GB of CPU copies and the same volume of uploads, **the run was slower**:
  menu −5.2 presents/s, more slow frames, and the extra cost lands in the per-frame finish
  (12.6 → 18.3 ms), i.e. the mid-frame blit serialises GPU work (the source render target has
  to be resolved/sampled while the frame is still being produced) more than the overlapped CPU
  copies cost.

## Conclusion and limits

- The per-frame copy+upload chain is real and quantified, but replacing it with a mid-frame GPU
  blit is a **net loss** on this device; `WOL_COPY_GPU` stays **off by default** and the code
  remains env-gated for reference. A future attempt would have to avoid the mid-frame
  serialisation (e.g. cached FBOs and batching the blit at a pass boundary), not merely move the
  same copy onto the GPU.
- Limits: one control run and one experiment run (the regression is far outside the ±1.5
  presents/s window-to-window noise measured earlier); menu + starting street only; the
  no-pending-CPU-writes precondition was met in this scene, other scenes may fall back to the
  CPU path while identical counters still report copy volume.
- Integrity: both runs restored the owner save (SHA256 match), left no `wol-horizon` process and
  produced real Spruce menu frames; no GL errors were reported by the experiment.

## Files

- `run-copyE1/`, `run-copyE2/` — phase JSONs, receipts, effective env, raw runtime log
  (`runtime.log.xz`); the experiment is visible as `WOL_COPY_GPU enabled=1` / refresh counters.
- `profdiag/` — the attribution run that measured the copy/upload chain
  (`ZERO_REFRESH_STATS`, `WOL_COLOR_COPY_STATS`, `ZERO_POOL_FLUSH_STATS`).
- `awprofile/` — the `AW_PROFILE=1` + `COTM_GUEST_PROFILE=1` run whose top-list sampled the
  memcpy-class libc hotspot and the upload helpers (the harness forwarded both variables).
- `m5-layout-copygpu.json` — descriptor layout bound to this runtime's ELF SHA.
- The three counters introduced for this work are bounded aggregate diagnostics and remain in
  the runtime.

No owner bundle, executable or save is distributed here.
