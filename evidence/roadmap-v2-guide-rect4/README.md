# Guide screen after the trace-filter rebuild (rect 280,10 → 1010,700, all vertex counts)

The runtime's rect trace used to skip any draw with more than 96 vertices, which hides exactly the
kind of draw in question: a multi-quad text label or a panel-sized mesh. This session ran a
rebuilt runtime (`wol-horizon-build-guiderect4`, sha256
`ba5a0dd51d5c5618f8ab5761b9af9c5f341d83d3da021be6bd8d98c2dc6387ba`, deployed, owner save
restored, cleanup verified) whose cap is 4096 vertices (`WOL_RECT_MAXVTX`, same opt-in
`WOL_RECT_TRACE` gate, so normal play is unchanged).

## What the draw stream says on the guide screen

555–574 guide frames, 13,343 rect hits. Grouped by pair/count/sampled texture:

- **The only multi-glyph text draw in the whole panel is the one visible label**:
  `f191-draft / v189(d88c64a6)`, count = 126 vertices = 21 glyph quads, box 473,510 → 631,569,
  sampling texture 3233 (256×512, the font atlas). It is issued once per frame (370/574).
- Other text-sized elements are title-area glyph runs (`count=6…24` at x707–1037 / y12–96).
  **No label-sized draw exists at any of the reference's four other label positions** (x378–515
  y290–343; x747–917 y330–359; x565–718 y449–510; x825–983 y576–638).
- The panel's remaining content comes from `top-f-uvraw / top-v-draft`: 4,051 hits in the panel,
  counts 6…963 vertices per draw, sampling the same scene atlases the world screen uses (2935
  1024×512, 2939 512×256, 2941 512×1024, …), with transformed boxes that span 600–3,111 px and
  reach x = −1500…1611 — 2.4× the screen width.
- Guide-only machinery: draws sampling a 960×540 target chain (ids 3618 → 3619 480×270 →
  3620 240×135) and compositing it back with the *translated* pair `f08bad2f#a9b0/f309b86a#0184`
  (374 hits each, full screen). The world screen does not use this chain.
- The port's own substitution texture appears once per frame on this screen:
  `ZERO_TEXTURE_FLUSH_UPLOADED id=460 format=0x25 … before-sampler rgba8-copy-levels=1`, and the
  translated pair draws with `sampTex=460 1280x720` 573 times — the mechanism the runtime uses when
  a draw samples the target it is bound to.

## Same screen in a different save state

`--control-save` installed the saloon-state save (control hash `8a70c734…`), same route, same
runtime. The guide frame is **identical in content**: gulch 0.00 %, mine 1.76 %, boneyard 0.00 %,
town 4.49 %, fricker 4.56 %, centre 0.00 %, title 23.99 %, panel interior 2.23 % — and OCR still
reads the single label "Thousand Snakes Gulch" at the same coordinates
(`guide-open.png`, `world.png` here). A locations screen that shows the same one entry regardless of
which save is loaded is not following the save.

## Reading of the evidence

Measured: the guide screen renders the heading, EXIT sign, compass, bottom bar and ©1890 exactly as
in the owner's reference; the panel interior is empty paper apart from one label; the game issues a
single location label and nothing else text-like in the panel; and the panel's remaining draws go
through the draft pair with boxes 2.4× wider than the screen, plus a guide-only 960×540 target chain
that is composited back through the port's sampled-target substitution.

Two mechanisms are therefore named and both are port-side:
1. the panel's own layer is produced through the 960×540 target chain / sampled-target
   substitution, which is exactly the path that can drop a whole composited layer to white;
2. the panel's draft-pair draws carry a transform 2.4× wider than the screen (`x=-1500…1611`),
   while the same pair draws the world scene correctly.

Next session's shortest decisive measurement: log every write into targets 3618–3621 and every draw
that samples the substitution texture 460 (pair, bbox, target), then check whether the panel's art
is written into that chain and read back as the stub. If it is, the blank panel is a defect in the
sampled-target path, not in shader UVs — and the per-texture UV lists that were swept here
(`WOL_TOP_UV=raw|legacy`) are the wrong lever entirely.
