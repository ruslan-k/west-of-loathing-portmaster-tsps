# The third 7-vertex draw goes into the window swapchain

`WOL_DRAWARRAYS` now prints the target texture `id` and builder `flags` (ELF `39b36256`, w25).

```
frame 850   target=1280x720   flags=0x8
frame 1223  target=1280x720   flags=0x8
frame 1223  target=1920x1080  flags=0x9
frame 1590  target=1280x720   flags=0x8   (x2)
frame 1965  target=1280x720   flags=0x8
```

`flags=0x9` is the same value the window swapchain carries (`MOMO_WINDOW_COLOR ... flags=0x9`,
guest size 1920x1080, `actual=1280x720`, `scaled=1`). `flags=0x8` is an ordinary colour texture.

So the 1080p pass is not a separate intermediate layer: it draws straight into the window swapchain,
which the guest still believes is 1920x1080, and the shim scales it to 1280x720 at present. The cost
is the extra target switch plus 2.25x the pixels for that draw.

`id=0` for every target - `gl_name` is not populated for these textures at that point, so the pointer
identity, not the GL name, is what distinguishes them. Do not read `id=0` as "no texture".

Run: scripted input, 240 s, `production_hashes_unchanged: 131`.
