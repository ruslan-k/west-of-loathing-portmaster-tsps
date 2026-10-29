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

## Why it is black (narrowed, not fixed)

From `diag-zrs2-shot.log`:

```
MOMO_WINDOW_COLOR index=0 id=2 size=1920x1080 flags=0x9 scaled=1 actual=1280x720 initial-uniform=1 target-seen=0 draws=0
ZERO_TEXEL_WRITE 2670    ZERO_TEXTURE_FLUSH 896    GL_INVALID 0
control: WOL_PRESENT_SRC ... draws=1 scaled=0   (no MOMO_WINDOW_COLOR line at all)
```

So `actual=1280x720` is what the code really allocates (the earlier `storage=640x360`
line belongs to a different print and was misleading), the guest's writes and
flushes do reach the scaled path, and GL reports no error. What is missing is the
handoff: the window images are never bound as render targets (`target-seen=0`)
and the presenter ends up sampling a surface with no content.

Next step is therefore not another flag but a receipt inside the scaled present:
log the sampler's texture name, `glIsTexture`, and whether the scaled copy-back
ran, on the same frame the presenter draws. Until that exists, every storage-scale
number is meaningless.

## Closing the lever: it is a foreign contract, not a switch

Read `zero_render_scale.h` end to end. The whole path is written against the
Momodora/Zero contract: `MOMO_SCALE_*` receipts, `zero_storage` ownership, pool
alias scans over `flags==0xa4` offscreen chains, and attachment checks that demand
colour and depth to be scaled together. WoL's window images are `flags=0x9`,
present-only sources with `target-seen=0` and no scaled depth partner.

That is why the output is black rather than degraded: the mechanism allocates a
smaller storage for a surface the guest never renders into, and nothing in this
title's render graph hands the frame over to it. Making it work here would mean
porting the mechanism to a different render graph - new code, new failure modes -
not enabling a documented option.

Decision: the storage-scale family is closed for this title. Remaining honest
options are the present-path cost (measure the crop/blit on the real 1080p
swapchain) or accepting this build's rate; no further flag work.
