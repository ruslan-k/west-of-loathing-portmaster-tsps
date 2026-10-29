# First matched pair: scaled arm renders 32% more frames

Same ELF `98681698…` (2 007 000 B), same 120 s probe, `AW_RELEASE=0`,
`T2_MEMORY_FLOOR_MIB=8` in both arms so neither dies early, title screen only.

| arm | frames | span | frames/s |
|-----|--------|------|----------|
| control (no flag) | 448 | 97.19 s | **4.61** |
| `ZERO_RENDER_SCALE=2` | 704 | 115.89 s | **6.07** |

+31.7% frames over the measured window, both runs ending on `TIME_LIMIT` rc=22.

Memory behaviour differs too: with the earlier diagnostic floor of 16 MiB the
control died at 50.6 s (`T2_MEMORY_FLOOR`, rc=26), while the scaled arm ran the
full 122 s under the same floor. Smaller storage therefore also lowers the
footprint — that is independent evidence, not a frame-rate claim.

## Limits of this pair

- one pair, title scene, no gameplay entered;
- the measured windows are not identical (97 s vs 116 s of the same 122 s run),
  because the counter starts when the first present happens and boot timing
  differs between the two sessions;
- absolute numbers (4.6 / 6.1 f/s) belong to a diagnostic build with full tracing
  on; they must not be compared with release figures or quoted as the title's
  performance;
- UI legibility at `storage=640x360` was NOT checked. The scale factor the
  runtime reports contradicts the mode-2 comment (640x360 vs 1280x720), so a
  glyph check is mandatory before anyone ships this flag.

Cleanup: `production_hashes_unchanged: 131` in both runs, no runtime process
left, MainUI back.

## Next

Repeat the pair once to see spread, then capture the title and menu at native
resolution and compare text. Only after that does this flag deserve a launcher
default.

## RETRACTED: the scaled arm renders a black screen

Physical check after the pair above, run `zrs2-shot` (same flag, 150 s):

```
WOL_PRESENT_TICK n=576      <- the guest is presenting
kmsgrab 1280x720            <- (0,0,0), exactly 1 colour
control capture g2-title.png <- (255,255,255), 2073 colours
```

Two captures 25 s apart are both fully black while the guest keeps presenting at
the same rate. So `ZERO_RENDER_SCALE=2` produces no visible frame on this title:
the extra 32% "frames" were presented into a surface that never reaches the
scanout. The +31.7% figure above is an artifact of drawing nothing and must not
be used.

Why the earlier `zrs2-a1` looked healthy: it also presented scaled
(`scaled=1`), but nobody looked at the screen that time. This is the same trap as
the 0-presents CMA run, from the other side: a counter is not a picture.

Status of the flag: **rejected**. The storage-scale path engages and is faster
only because the output is black. Any further work here needs a render-path fix
first (the scaled blit is not compositing), and it is not a launcher option.
