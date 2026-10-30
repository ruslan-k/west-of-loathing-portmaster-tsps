# Horizon v327680 — stop-loss experiments H-T1b/T1c (2026-10-30)

All numbers are 60-frame-window medians from `NVN_PROFILE` on the same scripted 240 s route,
same image (`image-update-fixed`), same ELF lineage (canonical overlay). Logs are in this
directory, one `.xz` per arm.

| Arm | ELF | Frame | Replay | Note |
|---|---|---:|---:|---|
| baseline (`da-on2`) | `5566a529` | **42.90 ms** | 26.17 | H-D1 ledger on, `AW_RELEASE=0` |
| refresh off (`ro1`) | `3568a74c` | **37.37 ms** | 21.60 | `WOL_REFRESH_OFF=1`, pixels stale (diagnostic) |
| flush census (`fc1`) | `64aa6f29` | — | — | `WOL_FLUSH_CENSUS=1` |
| render scale 960x540 (`sc1`) | `864354c8` | **42.00 ms** | 25.97 | `WOL_UPRENDER24_SCALE=1`, patch did **not** fire |

## H-T1b — the re-upload is a full-frame copy, not a slice

`WOL_REFRESH_OFF=1` skips the guest-write refresh entirely:

```
WOL_REFRESH_OFF enabled=1 diagnostic=stale-pixels expected-savings~6.7ms
pp3 (zero_texture_refresh)  6.7 ms -> 0.019 ms
frame                      42.90 ms -> 37.37 ms     (5.5 ms, above the 2 ms stop-loss bar)
```

So the copy is real, and it is the largest single lever in the frame. But it cannot be trimmed:

```
WOL_COLOR_COPY source=2 destination=82 region=1280x720@0,0->0,0 mode=copy-1:1
```

The guest copies the **whole 1280x720 frame** into texture 82 every frame, so every pixel changes;
partial upload would save nothing. The dirty flag comes from that CPU copy
(`nvn_render.h:3517`), which is why `zero_texture_pool_flushed()` (and the flush census built for it)
never ran in this build.

Ceiling arithmetic: with the copy removed entirely the frame is 37.37 ms = **26.7 fps**. The 30 fps
target needs 33.3 ms, so 4.1 ms must come from somewhere else (presentation/GPU).

## H-T1c — render scale

Goal: make Unity build a smaller camera target and let the presenter stretch it back, which attacks
both the copy (2.07 MB instead of 3.69 MB) and the GPU fill.

`sc1` rewrote the pinned `Screen::get_width/height` stores 1280x720 → 960x540, but **no site line was
printed** and the frame stayed at 42.00 ms: the hook never fired. Cause found in source:
`wol_up24_site()` returns 0 unless `mode = trace | (patch << 1)` is non-zero, and the scale arm only set
`wol_up24_scale`. Fixed in the next build by riding the patch bit:

```c
if(wol_up24_scale) wol_up24_patch = 1;   /* 1920->1280 is a no-op here, then 1280x720 -> 960x540 */
```

`diagnostics-source.patch` contains every source change used by these arms: the H-D1 ledger, the
`WOL_REFRESH_OFF` switch, the `WOL_FLUSH_CENSUS` census and the `WOL_UPRENDER24_SCALE` arm.

## Reproduce

```
# build (owner-local): canonical overlay + image-update-fixed
docker run ... -v <tree>:/src -v image-update-fixed:/image ... bash native/build.sh /image /src/out

# arms
E1C_EXTRA_ENV='{"WOL_REFRESH_OFF":"1","AW_RELEASE":"0"}'        ./e1c_boot_run.sh ro1 off
E1C_EXTRA_ENV='{"WOL_FLUSH_CENSUS":"1","AW_RELEASE":"0"}'      ./e1c_boot_run.sh fc1 off
E1C_EXTRA_ENV='{"WOL_UPRENDER24_SCALE":"1","AW_RELEASE":"0"}'  ./e1c_boot_run.sh sc1 off
```
