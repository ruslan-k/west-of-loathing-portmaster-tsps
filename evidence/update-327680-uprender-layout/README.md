# v327680 UpRender instance is aspect-driven, not pixel-forced

Run `up24-layout2`, candidate ELF
`0a0e64450534d6bef3e01e9fe16087957bb6d6ec7dc9832f77a7b57031a7145e` (2 007 016 B),
`WOL_UPRENDER24_TRACE=1`, fresh boot, CMA 130 412 kB at launch, 150 s.

## Raw dump (32 words from the component pointer, little-endian pairs)

```
owner=0x3b60a5d80
0x00 0x34120AE60   uiCamera            (guest pointer)
0x08 0
0x10 0x34130xxxx   guest pointer
0x18 0x3B60A7E00   guest pointer
0x20 16, 9         <-- forceWidth, forceHeight  (the pair the old hook read)
0x28 0, 1
0x30 0x3B60A7xxx   guest pointer
0x38..0x7C 0
```

## What that means

- The fields at +0x20/+0x24 hold **16 and 9**, i.e. the aspect ratio, on a
  component whose Screen reads 1280x720. Nothing in the object holds a
  1920x1080 pair, so this instance is not the pixel-forcing UpRender of the v23
  build: there is no `forceWidth=1920` to rewrite.
- v23's accepted result (24.0 -> 32.6-33.9 presents/s) came from rewriting those
  same fields when they held pixels. In v24 they hold a ratio, so the lever does
  not exist at this site; treating 16/9 as pixels would render a 16x9 texture.
- The title's only 1080p cost stays the swapchain (three images + one depth), as
  measured before. Rewriting the aspect pair would change the camera fit, not
  the presented resolution.

## Consequence

The v24 update build needs a different lever than v23. Candidates left, in
order of evidence: reduce the guest swapchain itself at window creation (needs
the Unity resolution source, which is not Screen), or accept the update build's
25.5 presents/s on the title and optimise the present path instead. Anything
that touches the aspect pair must be dropped.

Cleanup: `production_hashes_unchanged: 131`, MainUI back, no runtime process.
The diagnostic candidate stays installed (explicit user preference); the last
known-good gameplay runtime is `b506d04e4cd7e4e02d5d85c6c161e00a65692e9dec6875f04d0b72cb7c19641b`.
