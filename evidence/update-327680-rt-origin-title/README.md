# RT origin census on the v327680 title: only the swapchain is 1080p

Run `opt-origin-a2`, candidate ELF
`b506d04e4cd7e4e02d5d85c6c161e00a65692e9dec6875f04d0b72cb7c19641b`,
`AW_RELEASE=0 WOL_RT_ORIGIN=1 WOL_PRESENT_TRACE=1`, 240 s, fresh boot
(`CmaFree` 130 412 kB at launch).

## Measured

- 290 `NVN_TEXTURE_REAL` allocations and 290 matching `WOL_RT_ORIGIN
  event=initialize` records (join by guest object pointer).
- Of those, **21** are ≥1280x720 and exactly **four** are 1920x1080:
  three swapchain images (`caller=0x5419a4/0x5419f0/0x541a38`, parents
  `0x52cba4 -> 0x4dd610 -> ... -> 0x20288c/0x202a9c`) plus one
  (`caller=0x5392dc`, parent `0x20b5b8`).
- The dominant initialize caller is `main.text.seg+0x540fd8` (316 events):
  the game's NVN wrapper, not a Unity producer.
- Largest other targets: 1362x1308 (x2), 2048x1024, 1647x1247 — UI atlases and
  the like.

## Conclusion

On the title there is **no dynamic 1080p camera render target** to shrink; the
only 1080p cost is the guest swapchain, which the accepted v23 profile also left
at 1080p (documented in `evidence/uprender-owner/README.md`: four initial
window/SDK textures stay 1080p, nine *dynamic* targets become 720p).

So title-screen numbers cannot measure the 720p optimisation. The v23 A/B
(24.0 -> 32.6-33.9 presents/s) was taken in gulch gameplay, where those nine
dynamic colour/depth/MSAA targets exist. The same experiment here needs a loaded
save, and the same owner lever (`forceWidth`/`forceHeight` before the
`RenderTexture` constructor).

## Diagnostic defect found

`WOL_RT_ORIGIN` reads the texture builder 8 bytes late for this image
(`width=0x9 height=0x1 levels=0x438` — 0x438 is the real height 1080), so
per-allocation dimensions must come from `NVN_TEXTURE_REAL` (host side, correct)
until the builder offset is fixed. The object-pointer join is what makes this
census valid.
